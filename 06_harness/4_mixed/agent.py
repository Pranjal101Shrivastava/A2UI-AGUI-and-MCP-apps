"""Harness, mixed mode: catalog UI, one generated region, and an approval gate.

* ``render_ui`` accepts catalog specs with at most one ``GeneratedView``.
  The model uses it for a review card whose diff view is model-written HTML.
* ``write_file`` is gated: instead of writing, it raises ``Pause``. The run
  stops and the review card waits on screen.
* "Approve" or "Reject" is an action. The harness finishes the paused tool
  call with that answer and continues the same loop: the model sees the
  result, runs the tests and shows a summary.
"""
import html as html_lib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import harness  # noqa: E402
import terminal  # noqa: E402
import ui_tools  # noqa: E402
from fixture import BUGGY, FIXED, PROMPT  # noqa: E402
from shared.llm import get_model  # noqa: E402

rows = "".join(
    f'<div class="l {"del" if a != b else ""}"><span>{i + 1}</span>{html_lib.escape(a)}</div>'
    f'<div class="l {"add" if a != b else ""}"><span>{i + 1}</span>{html_lib.escape(b)}</div>'
    for i, (a, b) in enumerate(zip(BUGGY.splitlines(), FIXED.splitlines())) if i >= 6)
DIFF_HTML = f"""<style>.g{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);font:11px ui-monospace,monospace;background:#0f172a;
color:#cbd5e1;border-radius:8px;overflow:hidden}}.h{{padding:6px 10px;background:#1e293b;color:#94a3b8;font:600 11px system-ui}}
.l{{padding:2px 8px;white-space:pre;overflow:hidden;text-overflow:ellipsis}}.l span{{color:#475569;margin-right:10px}}.del{{background:#7f1d1d55}}.add{{background:#14532d77}}</style>
<div class="g"><div class="h">calc.py · before</div><div class="h">calc.py · after</div>{rows}</div>"""

REVIEW = {"root": "card", "elements": {
    "card": {"type": "Card", "props": {"title": "Review the proposed fix"}, "children": ["why", "diff", "buttons"]},
    "why": {"type": "Text", "props": {"text": "average() divides by len(values) - 1. The fix divides by len(values)."}},
    "diff": {"type": "GeneratedView", "props": {"title": "Side-by-side diff", "html": DIFF_HTML, "height": 150}},
    "buttons": {"type": "Row", "children": ["approve", "reject"]},
    "approve": {"type": "Button", "props": {"label": "Approve and write", "action": "approve", "variant": "primary"}},
    "reject": {"type": "Button", "props": {"label": "Reject", "action": "reject"}},
}}
SUMMARY = {"root": "s", "elements": {
    "s": {"type": "Card", "props": {"title": "Result"}, "children": ["row"]},
    "row": {"type": "Row", "children": ["tests", "badge"]},
    "tests": {"type": "Metric", "props": {"label": "Tests passing", "value": "3/3", "delta": "+1"}},
    "badge": {"type": "Badge", "props": {"text": "approved by you · written · verified", "tone": "ok"}},
}}
SCRIPT = [
    {"tool_calls": [{"name": "list_files", "arguments": {}}, {"name": "run_tests", "arguments": {}}]},
    {"tool_calls": [{"name": "read_file", "arguments": {"path": "calc.py"}}]},
    {"content": "I found the bug. Please review the change before I write it.",
     "tool_calls": [{"name": "render_ui", "arguments": {"spec": REVIEW, "slot": "review"}},
                    {"name": "write_file", "arguments": {"path": "calc.py", "content": FIXED}}]},
    {"tool_calls": [{"name": "run_tests", "arguments": {}}, {"name": "render_ui", "arguments": {"spec": SUMMARY, "slot": "result"}}]},
    {"content": "Written with your approval. All 3 tests pass."},
]
SESSIONS: dict = {}
LAST_EVENTS: list = []


def gated_write(s: harness.Session) -> harness.Tool:
    real = harness.coding_tools(s)["write_file"]

    def run(path: str, content: str) -> str:
        raise harness.Pause({"summary": f"write {path} ({len(content)} chars)", "args": {"path": path, "content": content}})
    return harness.Tool(real.schema, run)


def finish(s: harness.Session, pending: dict, answer: str) -> str:
    """Complete the paused write_file with the user's decision."""
    decided = {"type": "Badge", "props": {"text": "approved" if answer == "approve" else "rejected",
                                          "tone": "ok" if answer == "approve" else "bad"}}
    s.ui_events.append({"type": "UI", "kind": "spec", "slot": "review", "spec": {"root": "card", "elements": {
        **REVIEW["elements"], "buttons": decided}}})
    if answer != "approve":
        return "error: the user rejected this change"
    return harness.coding_tools(s)["write_file"].run(**pending["args"])


def record(gen):
    for e in gen:
        LAST_EVENTS.append(e)
        yield e


def handle(name: str, body: dict):
    if name == "run":
        s = harness.Session(model=get_model(SCRIPT), workspace=harness.new_workspace())
        s.tools = {**harness.coding_tools(s), "write_file": gated_write(s),
                   "render_ui": ui_tools.render_ui(s, max_generated=1)}
        SESSIONS["current"] = s
        LAST_EVENTS.clear()
        return record(harness.start(s, body.get("prompt", PROMPT)))
    if name == "action" and body.get("name") in ("approve", "reject"):
        return record(harness.resume(SESSIONS["current"], body["name"], finish))
    raise ValueError(f"unknown api {name}")


def demo_notes() -> str:
    return "both requests on the terminal surface:\n" + terminal.transcript(LAST_EVENTS)


DEMO_STEPS = [{"screenshot": "demo_before.png"}, {"click": "button[data-action='approve']"}]
