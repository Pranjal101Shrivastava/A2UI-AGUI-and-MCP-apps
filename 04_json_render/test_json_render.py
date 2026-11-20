"""Offline tests for the four json-render codelabs."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE)]

import jsonrender  # noqa: E402
from shared.devserver import load_agent  # noqa: E402


def run(mode, name="run", body=None):
    agent = load_agent(HERE / mode)
    return list(agent.handle(name, body or {"prompt": agent.PROMPT}))


def test_state_bindings_resolve_and_missing_ones_are_reported():
    spec = {"root": "m", "elements": {"m": {"type": "Metric", "props": {"label": "x", "value": {"$state": "/v"}}}}, "state": {}}
    assert jsonrender.check_state(spec) == ["state has nothing at /v"]
    spec["state"]["v"] = 7
    assert jsonrender.resolve(spec)["elements"]["m"]["props"]["value"] == 7


def test_static_fills_a_registry_spec_from_app_data():
    spec = next(e for e in run("1_static") if e["type"] == "spec")["spec"]
    assert jsonrender.validate(spec) == [] and spec["state"]["cups"] == 385
    patch = run("1_static", "action", {"name": "reorder_beans"})[-1]
    assert patch["op"]["path"] == "/state/alert"


def test_declarative_patches_rebuild_a_valid_spec():
    spec = json.loads(json.dumps(jsonrender.EMPTY))
    events = run("2_declarative")
    for e in events:
        if e["type"] == "patch":
            spec = jsonrender.apply_line(spec, json.dumps(e["op"]))
    assert jsonrender.validate(spec) == [] and len(spec["elements"]) == 9
    assert events[0]["op"]["path"] == "/root"          # the root comes first, so the first paint is early


def test_open_spec_blocks_handlers_and_css_urls():
    events = run("3_open_ended")
    assert "onclick" in events[0]["text"] and "blocked CSS" in events[0]["text"]
    spec = events[1]["spec"]
    assert jsonrender.validate_open_spec(spec) == []
    bad = {"root": "s", "elements": {"s": {"type": "script", "props": {}}}}
    assert "tag <script> is not allowed" in jsonrender.validate_open_spec(bad)[0]


def test_mixed_patches_and_terminal_renderer_agree():
    run("4_mixed")
    events = run("4_mixed", "action", {"name": "plan_prep"})
    assert [e["op"]["op"] for e in events if e["type"] == "patch"] == ["add", "add", "add", "replace", "remove"]
    text = jsonrender.render_terminal(load_agent(HERE / "4_mixed").STATE["spec"])
    assert "Prep for Friday" in text and "HTML region" in text
