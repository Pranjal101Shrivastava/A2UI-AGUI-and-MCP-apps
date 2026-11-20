"""Harness, declarative mode: one ``render_ui`` tool, validated against the catalog.

The model composes its own report from catalog components. The harness
validates the spec; an invalid spec is not shown, and the error goes back to
the model as the tool result, so the model corrects itself inside the normal
loop. The terminal surface draws the same spec with the json-render terminal
renderer.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import harness  # noqa: E402
import terminal  # noqa: E402
import ui_tools  # noqa: E402
from fixture import FIXED, PROMPT  # noqa: E402
from shared.llm import get_model  # noqa: E402

REPORT = {"root": "r", "elements": {
    "r": {"type": "Column", "children": ["t", "k", "files", "why"]},
    "t": {"type": "Text", "props": {"text": "Fixed calc.average()", "variant": "h2"}},
    "k": {"type": "Row", "children": ["tests", "changed", "state"]},
    "tests": {"type": "Metric", "props": {"label": "Tests passing", "value": "3/3", "delta": "+1"}},
    "changed": {"type": "Metric", "props": {"label": "Files changed", "value": 1}},
    "state": {"type": "Badge", "props": {"text": "all green", "tone": "ok"}},
    "files": {"type": "Table", "props": {"columns": ["File", "Change"],
                                          "rows": [["calc.py", "divide by len(values), not len(values) - 1"]]}},
    "why": {"type": "Text", "props": {"text": "The mean of [2, 4, 6] was computed as 12 / 2 = 6 instead of 12 / 3 = 4.",
                                       "variant": "muted"}},
}}
BROKEN = {"root": "r", "elements": {**REPORT["elements"],
                                    "files": {"type": "DiffViewer", "props": {"file": "calc.py"}}}}
SCRIPT = [
    {"tool_calls": [{"name": "list_files", "arguments": {}}, {"name": "run_tests", "arguments": {}}]},
    {"tool_calls": [{"name": "read_file", "arguments": {"path": "calc.py"}}]},
    {"content": "Off-by-one in the divisor. Fixing and re-running.",
     "tool_calls": [{"name": "write_file", "arguments": {"path": "calc.py", "content": FIXED}},
                    {"name": "run_tests", "arguments": {}}]},
    {"tool_calls": [{"name": "render_ui", "arguments": {"spec": BROKEN}}]},
    {"tool_calls": [{"name": "render_ui", "arguments": {"spec": REPORT}}]},
    {"content": "Done. The report is on screen."},
]
SESSIONS: dict = {}
LAST_EVENTS: list = []


def handle(name: str, body: dict):
    if name != "run":
        raise ValueError(f"unknown api {name}")
    s = harness.Session(model=get_model(SCRIPT), workspace=harness.new_workspace())
    s.tools = {**harness.coding_tools(s), "render_ui": ui_tools.render_ui(s)}
    LAST_EVENTS.clear()

    def events():
        for e in harness.start(s, body.get("prompt", PROMPT)):
            LAST_EVENTS.append(e)
            yield e
    return events()


def demo_notes() -> str:
    return "the same run on the terminal surface (terminal.py + the json-render terminal renderer):\n" + \
        terminal.transcript(LAST_EVENTS)


DEMO_STEPS = []
