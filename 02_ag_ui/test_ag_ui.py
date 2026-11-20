"""Offline tests for the four AG-UI codelabs. No model, no network, no browser."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE)]

import agui  # noqa: E402
from shared.devserver import load_agent  # noqa: E402


def run(mode, messages, state=None, tools=None, thread="t1"):
    body = {"threadId": thread, "runId": "r1", "messages": messages, "state": state or {}, "tools": tools or []}
    return list(load_agent(HERE / mode).handle("run", body))


def user(text):
    return [{"id": "u1", "role": "user", "content": text}]


def types(events):
    return [e["type"] for e in events]


def test_json_patch_add_replace_remove():
    doc = agui.apply_patch({"a": [1, 3]}, [{"op": "add", "path": "/a/1", "value": 2},
                                           {"op": "replace", "path": "/b", "value": {"c": 1}},
                                           {"op": "remove", "path": "/a/0"}])
    assert doc == {"a": [2, 3], "b": {"c": 1}}


def test_static_streams_two_tool_calls_with_valid_args():
    events = run("1_static", user("Kyoto trip"), thread="s1")
    assert agui.check_sequence(events) == []
    names = [e["toolCallName"] for e in events if e["type"] == "TOOL_CALL_START"]
    assert names == ["show_flight", "show_weather"]
    raw = "".join(e["delta"] for e in events if e["type"] == "TOOL_CALL_ARGS" and e["toolCallId"] == events[1]["toolCallId"])
    assert json.loads(raw)["flight"] == "JL 5"


def test_declarative_rejects_unknown_component_then_builds_three_days():
    events = run("2_declarative", user("Plan Kyoto"), thread="d1")
    assert agui.check_sequence(events) == []
    rejected = [e for e in events if e["type"] == "CUSTOM"]
    assert rejected and "Map" in rejected[0]["value"][0]
    state = {}
    for e in events:
        if e["type"] == "STATE_SNAPSHOT":
            state = e["snapshot"]
        if e["type"] == "STATE_DELTA":
            state = agui.apply_patch(state, e["delta"])
    assert [c["props"]["title"][:3] for c in state["ui"]["children"][1]["children"]] == ["Sat", "Sun", "Mon"]


def test_declarative_follow_up_edits_the_state_the_client_sent():
    first = run("2_declarative", user("Plan Kyoto"), thread="d2")
    state = {}
    for e in first:
        state = e["snapshot"] if e["type"] == "STATE_SNAPSHOT" else agui.apply_patch(state, e["delta"]) if e["type"] == "STATE_DELTA" else state
    second = run("2_declarative", user("[action] rain_plan"), state=state, thread="d2")
    deltas = [e for e in second if e["type"] == "STATE_DELTA"]
    assert deltas[0]["delta"][0]["value"]["props"]["title"] == "Sun · Indoor Kyoto"


def test_open_ended_streams_policy_checked_html():
    events = run("3_open_ended", user("poster"), thread="o1")
    raw = "".join(e["delta"] for e in events if e["type"] == "TOOL_CALL_ARGS")
    assert "genux.send" in json.loads(raw)["html"]
    assert agui.check_sequence(events) == []


def test_mixed_requires_the_frontend_tool_then_resumes_on_the_tool_message():
    no_tool = run("4_mixed", user("book"), thread="m0")
    assert no_tool[-1]["type"] == "RUN_ERROR"
    tools = [{"name": "confirm_booking"}]
    first = run("4_mixed", user("book"), tools=tools, thread="m1")
    call_id = next(e["toolCallId"] for e in first if e["type"] == "TOOL_CALL_START")
    state = next(e["snapshot"] for e in first if e["type"] == "STATE_SNAPSHOT")
    answer = user("book") + [{"id": "t", "role": "tool", "toolCallId": call_id, "content": json.dumps({"approved": True})}]
    second = run("4_mixed", answer, state=state, tools=tools, thread="m1")
    patched = agui.apply_patch(state, next(e for e in second if e["type"] == "STATE_DELTA")["delta"])
    assert patched["ui"]["children"][2]["children"][1]["props"]["tone"] == "ok"
