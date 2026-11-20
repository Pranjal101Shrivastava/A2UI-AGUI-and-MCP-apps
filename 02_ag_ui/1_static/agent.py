"""AG-UI, static mode: the frontend owns pre-built components for two tools.

The agent never describes UI. It calls ``show_flight`` and ``show_weather``;
AG-UI carries each call as ``TOOL_CALL_START/ARGS/END`` events, and the page
draws its hand-written component for that tool name while the arguments
stream in. A "Refresh" button starts a second run on the same thread.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import agui  # noqa: E402
from shared.llm import get_model, tool  # noqa: E402

PROMPT = "I fly to Kyoto on Friday on JL 5. What should I expect?"
TOOLS = [
    tool("show_flight", "Show the flight card", {"flight": {"type": "string"}, "route": {"type": "string"},
         "departs": {"type": "string"}, "status": {"type": "string"}, "gate": {"type": "string"}}),
    tool("show_weather", "Show a 3-day forecast card", {"city": {"type": "string"},
         "days": {"type": "array", "items": {"type": "object"}}}),
]
FLIGHT = {"flight": "JL 5", "route": "SFO → KIX", "departs": "Fri 11:05", "status": "On time", "gate": "G98"}
SCRIPT = [
    {"content": "Your flight is on time, and Kyoto will be mild with rain on Sunday.", "tool_calls": [
        {"name": "show_flight", "arguments": FLIGHT},
        {"name": "show_weather", "arguments": {"city": "Kyoto", "days": [
            {"day": "Sat", "high": 19, "low": 11, "sky": "sunny"}, {"day": "Sun", "high": 16, "low": 10, "sky": "rain"},
            {"day": "Mon", "high": 18, "low": 9, "sky": "cloudy"}]}}]},
    {"content": "Updated: boarding has started at gate G98.", "tool_calls": [
        {"name": "show_flight", "arguments": {**FLIGHT, "status": "Boarding"}}]},
]
MODELS: dict = {}


def handle(name: str, body: dict):
    if name != "run":
        raise ValueError(f"unknown api {name}")
    run = agui.parse_run_input(body)
    model = MODELS.setdefault(run["threadId"], get_model(SCRIPT))
    yield agui.run_started(run["threadId"], run["runId"])
    history = [{"role": m["role"], "content": m.get("content", "")} for m in run["messages"] if m["role"] in ("user", "assistant")]
    reply = model.complete(history, TOOLS)
    for call in reply["tool_calls"]:
        if call["name"] not in {"show_flight", "show_weather"}:
            yield agui.run_error(f"unknown tool {call['name']}")
            return
        yield from agui.tool_call(call["name"], call["arguments"], call["id"])
        yield agui.tool_result(call["id"], "rendered by the frontend")
    if reply["content"]:
        yield from agui.text_message(reply["content"])
    yield agui.run_finished(run["threadId"], run["runId"])


DEMO_STEPS = [{"screenshot": "demo_before.png"}, {"click": "button[data-action='refresh_flight']"}]
