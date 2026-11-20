"""Offline tests for the harness codelabs. The coding tools really run the toy project's tests."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE)]

import harness  # noqa: E402
from shared.devserver import load_agent  # noqa: E402


def run(mode, name="run", body=None):
    return list(load_agent(HERE / mode).handle(name, body or {"prompt": "fix it"}))


def test_toy_project_really_fails_before_the_fix():
    s = harness.Session(model=None, workspace=harness.new_workspace())
    out = harness.coding_tools(s)["run_tests"].run()
    assert out.startswith("2/3 passed") and s.last_tests["failures"] == ["test_average"]


def test_static_shows_real_test_numbers_and_a_real_diff():
    ui = [e for e in run("1_static") if e["type"] == "UI"]
    reports = [e["props"] for e in ui if e["component"] == "TestReport"]
    assert (reports[0]["passed"], reports[-1]["passed"]) == (2, 3)
    diff = next(e["props"]["diff"] for e in ui if e["component"] == "DiffView")
    assert "+    return total(values) / len(values)" in diff


def test_declarative_invalid_spec_returns_an_error_result_to_the_model():
    events = run("2_declarative")
    results = [e for e in events if e["type"] == "TOOL_RESULT" and e["name"] == "render_ui"]
    assert [r["ok"] for r in results] == [False, True] and "DiffViewer" in results[0]["summary"]
    assert sum(e["type"] == "UI" for e in events) == 1


def test_open_ended_has_a_terminal_fallback_and_rerun_action():
    html = next(e for e in run("3_open_ended") if e["type"] == "UI")
    assert html["kind"] == "html" and html["fallback"]
    again = run("3_open_ended", "action", {"name": "rerun_tests"})
    assert again[1]["summary"] == "3/3 passed"


def test_mixed_pauses_before_writing_and_resumes_on_approval():
    first = run("4_mixed")
    assert first[-1]["type"] == "PAUSED"
    s = load_agent(HERE / "4_mixed").SESSIONS["current"]
    assert "len(values) - 1" in (s.workspace / "calc.py").read_text()       # nothing written yet
    second = run("4_mixed", "action", {"name": "approve"})
    assert second[-1]["type"] == "RUN_FINISHED" and s.last_tests["ok"]


def test_mixed_rejection_leaves_the_file_untouched():
    run("4_mixed")
    s = load_agent(HERE / "4_mixed").SESSIONS["current"]
    events = run("4_mixed", "action", {"name": "reject"})
    assert events[1]["ok"] is False and "len(values) - 1" in (s.workspace / "calc.py").read_text()
