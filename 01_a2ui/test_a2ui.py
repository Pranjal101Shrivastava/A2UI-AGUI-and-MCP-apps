"""Offline tests for the four A2UI codelabs. No model, no network, no browser."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE)]

import a2ui  # noqa: E402
from shared.devserver import load_agent  # noqa: E402


def run(mode, name="run", body=None):
    agent = load_agent(HERE / mode)
    return list(agent.handle(name, body or {"prompt": agent.PROMPT}))


def envelopes(events):
    return [e for e in events if "version" in e]


def action(name, surface, context, source="root"):
    return {"version": "v0.9", "action": {"name": name, "surfaceId": surface, "sourceComponentId": source,
                                          "timestamp": "2026-11-20T10:00:00Z", "context": context}}


def test_validator_accepts_a_minimal_surface():
    v = a2ui.Validator()
    assert v.check(a2ui.create_surface("s")) == []
    assert v.check(a2ui.update_components("s", [{"id": "root", "component": "Text", "text": "hi"}])) == []


def test_validator_rejects_unknown_components_and_dangling_children():
    v = a2ui.Validator()
    v.check(a2ui.create_surface("s"))
    errors = v.check(a2ui.update_components("s", [{"id": "root", "component": "Column", "children": ["x"]},
                                                   {"id": "y", "component": "DatePicker"}]))
    assert any("DatePicker" in e for e in errors) and any("'x' does not exist" in e for e in errors)


def test_validator_requires_a_created_surface():
    assert "was not created" in a2ui.Validator().check(a2ui.update_data_model("nope", "/", {}))[0]


def test_static_sends_the_template_then_data_only():
    events = envelopes(run("1_static"))
    assert [next(k for k in e if k != "version") for e in events] == ["createSurface", "updateComponents", "updateDataModel"]
    assert events[2]["updateDataModel"]["value"]["room"]["id"] == "B12"
    after = envelopes(run("1_static", "action", action("book_room", "room_card",
                                                       {"roomId": "B12", "time": "Tomorrow 14:00-16:00"}, "book")))
    assert after == [a2ui.update_data_model("room_card", "/status", "Booked: B12, Tomorrow 14:00-16:00")]


def test_declarative_correction_loop_fixes_the_form():
    events = run("1_static") and run("2_declarative")
    traces = [e["text"] for e in events if e.get("type") == "trace"]
    assert any("DatePicker" in t and "placeholder" in t for t in traces)
    comps = [e for e in envelopes(events) if "updateComponents" in e]
    assert len(comps) == 1 and {c["component"] for c in comps[0]["updateComponents"]["components"]} >= {"TextField", "Button"}


def test_declarative_submit_needs_a_name_then_confirms():
    run("2_declarative")
    ctx = {"name": "", "when": "Tomorrow 14:00-16:00", "people": "4", "room": "B12"}
    refused = run("2_declarative", "action", action("submit_booking", "booking_form", ctx, "submit"))
    assert any("rejected" in e.get("text", "") for e in refused)
    ok = envelopes(run("2_declarative", "action", action("submit_booking", "booking_form", {**ctx, "name": "Alex"}, "submit")))
    assert ok[0]["updateDataModel"]["value"]["summary"].startswith("Alex")
    assert ok[1]["updateComponents"]["components"][0]["id"] == "root"


def test_open_ended_policy_rejects_cdn_script_then_accepts_clean_html():
    events = run("3_open_ended")
    assert any("external <script src>" in e.get("text", "") for e in events)
    frames = [e for e in envelopes(events) if "updateComponents" in e]
    assert len(frames) == 1 and "https://" not in frames[0]["updateComponents"]["components"][0]["html"]


def test_open_ended_refuses_unknown_actions():
    run("3_open_ended")
    events = run("3_open_ended", "action", action("delete_everything", "floor_plan", {"room": "B12"}))
    assert envelopes(events) == []


def test_mixed_map_click_updates_the_bound_text_field():
    events = envelopes(run("4_mixed"))
    comps = events[1]["updateComponents"]["components"]
    assert sum(c["component"] == "HtmlFrame" for c in comps) == 1
    picked = envelopes(run("4_mixed", "action", action("select_room", "room_picker", {"room": "B12"}, "map")))
    assert picked[0] == a2ui.update_data_model("room_picker", "/booking/room", "B12")
    booked = envelopes(run("4_mixed", "action", action("book", "room_picker", {"room": "B12", "name": "Alex"}, "book")))
    assert "Booked B12 for Alex" in booked[0]["updateDataModel"]["value"]
    taken = envelopes(run("4_mixed", "action", action("select_room", "room_picker", {"room": "C3"}, "map")))
    assert "Pick a free room" in taken[0]["updateDataModel"]["value"]


def test_every_message_in_every_mode_is_json_serialisable():
    for mode in ("1_static", "2_declarative", "3_open_ended", "4_mixed"):
        json.dumps(run(mode))
