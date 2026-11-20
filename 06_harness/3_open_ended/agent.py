"""Harness, open-ended mode: ``render_html`` gives the web surface any HTML it wants.

The model writes a self-contained fix report: before and after code side by
side, styled freely. The harness checks the content policy, the page shows
it in a sandbox, and the terminal gets the plain-text ``fallback`` the tool
requires, because a terminal cannot run HTML. The report's button sends an
action that the harness answers by re-running the real tests.
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

line_of = lambda src: next(l for l in src.splitlines() if "return total" in l).strip()  # noqa: E731
REPORT = f"""<style>
 .r{{font:14px system-ui;padding:14px;color:#1f2430}} .r h3{{margin:0 0 4px}} .k{{color:#667085;margin-bottom:10px}}
 .cols{{display:grid;grid-template-columns:1fr 1fr;gap:10px}} .col{{border-radius:10px;padding:10px}}
 .before{{background:#fef2f2;border:1px solid #fecaca}} .after{{background:#f0fdf4;border:1px solid #bbf7d0}}
 code{{font:12px ui-monospace,monospace}} .tag{{font:600 11px system-ui;letter-spacing:.08em;margin-bottom:6px}}
 .math{{margin-top:12px;display:flex;gap:16px;align-items:center}} .eq{{font:600 18px ui-monospace}}
 button{{margin-top:12px;padding:8px 14px;border:0;border-radius:8px;background:#4f46e5;color:#fff;cursor:pointer}}
</style><div class="r"><h3>calc.average(): off by one</h3><div class="k">1 file · 1 line · 3/3 tests passing</div>
<div class="cols"><div class="col before"><div class="tag">BEFORE</div><code>{html_lib.escape(line_of(BUGGY))}</code></div>
<div class="col after"><div class="tag">AFTER</div><code>{html_lib.escape(line_of(FIXED))}</code></div></div>
<div class="math"><span class="eq">[2, 4, 6] → 12 / 2 = 6 ✗</span><span class="eq">12 / 3 = 4 ✓</span></div>
<button id="again">Run the tests again</button></div>
<script>document.getElementById("again").onclick = () => genux.send("action", {{name: "rerun_tests"}});</script>"""
SCRIPT = [
    {"tool_calls": [{"name": "list_files", "arguments": {}}, {"name": "run_tests", "arguments": {}}]},
    {"tool_calls": [{"name": "read_file", "arguments": {"path": "calc.py"}}]},
    {"tool_calls": [{"name": "write_file", "arguments": {"path": "calc.py", "content": FIXED}},
                    {"name": "run_tests", "arguments": {}}]},
    {"tool_calls": [{"name": "render_html", "arguments": {"title": "Fix report", "html": REPORT,
                     "fallback": "calc.average(): divide by len(values) instead of len(values) - 1. 3/3 tests pass."}}]},
    {"content": "Fixed and verified. See the report."},
]
SESSIONS: dict = {}
LAST_EVENTS: list = []


def handle(name: str, body: dict):
    if name == "run":
        s = harness.Session(model=get_model(SCRIPT), workspace=harness.new_workspace())
        s.tools = {**harness.coding_tools(s), "render_html": ui_tools.render_html(s)}
        SESSIONS["current"] = s
        LAST_EVENTS.clear()

        def events():
            for e in harness.start(s, body.get("prompt", PROMPT)):
                LAST_EVENTS.append(e)
                yield e
        return events()
    if name == "action" and body.get("name") == "rerun_tests":   # handled by the harness, not the model
        s = SESSIONS["current"]
        summary = s.tools["run_tests"].run().splitlines()[0]
        return iter([{"type": "TOOL_CALL", "id": "user_rerun", "name": "run_tests", "args": {}},
                     {"type": "TOOL_RESULT", "id": "user_rerun", "name": "run_tests", "ok": s.last_tests["ok"], "summary": summary},
                     {"type": "TEXT", "text": f"Re-ran the tests on request: {summary}."}])
    raise ValueError(f"unknown api {name}")


def demo_notes() -> str:
    return "the same run on the terminal surface (the HTML is replaced by its fallback):\n" + terminal.transcript(LAST_EVENTS)


DEMO_STEPS = [{"screenshot": "demo_before.png"}, {"frame": "iframe.c-sandbox", "click": "#again"}]
