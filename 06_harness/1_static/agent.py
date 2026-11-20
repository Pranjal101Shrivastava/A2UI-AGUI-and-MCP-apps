"""Harness, static mode: three pre-built panels the agent can show, filled by the harness.

The model gets three UI tools besides the coding tools: ``show_status``,
``show_test_report`` and ``show_diff``. It decides *when* to show a panel.
The harness supplies the *data*: the test numbers come from the real test
run, the diff from the real file change. Both surfaces draw the same events.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import harness  # noqa: E402
import terminal  # noqa: E402
from fixture import FIXED, PROMPT  # noqa: E402
from shared.llm import get_model, tool  # noqa: E402

SCRIPT = [
    {"tool_calls": [{"name": "show_status", "arguments": {"step": "Inspecting the project", "detail": "Listing files, then running the tests."}},
                    {"name": "list_files", "arguments": {}}, {"name": "run_tests", "arguments": {}}]},
    {"tool_calls": [{"name": "show_test_report", "arguments": {}}, {"name": "read_file", "arguments": {"path": "calc.py"}}]},
    {"content": "average() divides by len(values) - 1. Fixing it.",
     "tool_calls": [{"name": "write_file", "arguments": {"path": "calc.py", "content": FIXED}}, {"name": "show_diff", "arguments": {}}]},
    {"tool_calls": [{"name": "show_status", "arguments": {"step": "Verifying", "detail": "Running the tests again."}},
                    {"name": "run_tests", "arguments": {}}, {"name": "show_test_report", "arguments": {}}]},
    {"content": "Fixed: average() now divides by len(values). All 3 tests pass."},
]
SESSIONS: dict = {}
LAST_EVENTS: list = []


def ui_tools(s: harness.Session) -> dict:
    def emit(component, props):
        s.ui_events.append({"type": "UI", "kind": "component", "component": component, "props": props})
        return f"shown {component}"

    return {
        "show_status": harness.Tool(tool("show_status", "Show what you are doing now.",
                                         {"step": {"type": "string"}, "detail": {"type": "string"}}),
                                    lambda step, detail: emit("Status", {"step": step, "detail": detail})),
        "show_test_report": harness.Tool(tool("show_test_report", "Show the latest test results.", {}),
                                         lambda: emit("TestReport", s.last_tests or {"ran": 0, "passed": 0, "failed": 0, "failures": []})),
        "show_diff": harness.Tool(tool("show_diff", "Show your changes as a diff.", {}),
                                  lambda: emit("DiffView", {"diff": harness.unified_diff(s)})),
    }


# The terminal's versions of the three panels.
TERMINAL = {
    "Status": lambda p: [f"  ▸ {p['step']}: {p['detail']}"],
    "TestReport": lambda p: [f"  ▸ tests: {p['passed']}/{p['ran']} passed" + (f", failing: {', '.join(p['failures'])}" if p["failures"] else "")],
    "DiffView": lambda p: ["  ▸ diff:"] + ["      " + line for line in p["diff"].splitlines()],
}


def handle(name: str, body: dict):
    if name != "run":
        raise ValueError(f"unknown api {name}")
    s = harness.Session(model=get_model(SCRIPT), workspace=harness.new_workspace())
    s.tools = {**harness.coding_tools(s), **ui_tools(s)}
    SESSIONS["current"] = s
    LAST_EVENTS.clear()

    def events():
        for e in harness.start(s, body.get("prompt", PROMPT)):
            LAST_EVENTS.append(e)
            yield e
    return events()


def demo_notes() -> str:
    return "the same run on the terminal surface (terminal.py):\n" + terminal.transcript(LAST_EVENTS, TERMINAL)


DEMO_STEPS = []
