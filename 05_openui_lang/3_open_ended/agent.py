"""OpenUI Lang, open-ended mode: one statement, one ``HtmlArtifact``, all of the UI in a string.

The only component is ``HtmlArtifact(html, title, height)``. The model writes
a complete timetable as HTML inside an OpenUI string literal, so every quote
and newline is escaped. Nothing can render until the line is complete,
because the parser only reads finished statements. A click in the sandbox
becomes an action; the model answers with a new ``root``.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import openui  # noqa: E402
from shared.llm import approx_tokens, get_model  # noqa: E402
from stream import program_events  # noqa: E402

PROMPT = "Show my spring timetable as a weekly calendar"
SYSTEM = 'Answer with ONE OpenUI Lang line: root = HtmlArtifact("<html>", "title", height). ' \
         'Report clicks with genux.send("action", {name: "course_details", context: {code}}).'

BLOCKS = [("CMPE 280", 0, "#4f46e5"), ("CMPE 280", 2, "#4f46e5"), ("CMPE 281", 1, "#0f8a5f"),
          ("CMPE 281", 3, "#0f8a5f"), ("CMPE 258", 4, "#b45309")]
grid = "".join(
    f'<div class="b" data-code="{code}" style="grid-column:{day + 2};grid-row:{4 if code == "CMPE 258" else 7} / span 3;'
    f'background:{color}">{code}<small>{"15:00" if code == "CMPE 258" else "18:00"}</small></div>'
    for code, day, color in BLOCKS)
TIMETABLE = f"""<style>
.t{{display:grid;grid-template-columns:44px repeat(5,1fr);grid-template-rows:24px repeat(9,26px);gap:3px;font:12px system-ui;padding:8px}}
.h{{color:#667085;text-align:center}} .r{{color:#98a2b3;font-size:11px}}
.b{{color:#fff;border-radius:8px;padding:6px;font-weight:600;cursor:pointer;box-shadow:0 2px 6px #0002}}
.b small{{display:block;font-weight:400;opacity:.85}} .b:hover{{filter:brightness(1.1)}}
</style><div class="t"><div></div>{"".join(f'<div class="h">{d}</div>' for d in ["Mon", "Tue", "Wed", "Thu", "Fri"])}
{"".join(f'<div class="r" style="grid-row:{i + 2};grid-column:1">{h}:00</div>' for i, h in enumerate(range(13, 22)))}
{grid}</div>
<script>document.querySelectorAll(".b").forEach((b) => b.onclick = () =>
  genux.send("action", {{name: "course_details", context: {{code: b.dataset.code}}}}));</script>"""
DETAILS = """<style>.d{font:14px system-ui;padding:14px}.d h2{margin:0 0 4px}.k{color:#667085}
.chip{display:inline-block;background:#eef0ff;color:#4f46e5;border-radius:99px;padding:2px 9px;margin:8px 6px 0 0}</style>
<div class="d"><h2>CMPE 281 · Cloud Technologies</h2><div class="k">Tue/Thu 18:00-20:45 · Engineering 189</div>
<p>Virtualization, containers, serverless and cloud-native design. 2 seats left.</p>
<span class="chip">3 units</span><span class="chip">project-based</span><span class="chip">prereq: CMPE 202</span></div>"""

line = lambda html, title, height: f"root = HtmlArtifact({json.dumps(html)}, {json.dumps(title)}, {height})"  # noqa: E731
SCRIPT = [line(TIMETABLE, "Spring 2027 timetable", 330), line(DETAILS, "CMPE 281", 200)]
STATE: dict = {}


def run(prompt: str):
    STATE["model"] = get_model(SCRIPT, delay=0.004)
    yield from program_events(STATE["model"], [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                              lambda text: openui.check(text, openui.HTML_ARTIFACT)[1])


def on_action(body: dict):
    code = body.get("context", {}).get("code")
    yield {"type": "trace", "text": f"action {body['name']} {code} from the sandbox"}
    yield from program_events(STATE["model"], [{"role": "user", "content": f"Show details for {code}"}],
                              lambda text: openui.check(text, openui.HTML_ARTIFACT)[1])


def handle(name: str, body: dict):
    if name == "run":
        return run(body.get("prompt", PROMPT))
    if name == "action":
        return on_action(body)
    raise ValueError(f"unknown api {name}")


def demo_notes() -> str:
    from shared.devserver import load_agent

    static = load_agent(HERE.parent / "1_static").SCRIPT[0]
    declarative = load_agent(HERE.parent / "2_declarative").PLAN
    rows = [("static (3 widgets)", static), ("declarative (primitives)", declarative), ("open-ended (HtmlArtifact)", SCRIPT[0])]
    escapes = SCRIPT[0].count("\\")
    return ("model output size (tokens, estimated):\n" + "\n".join(f"  {n:<28} {approx_tokens(t):>5}" for n, t in rows)
            + f"\nthe open-ended line carries {escapes} backslash escapes, and nothing renders until its last character")


DEMO_STEPS = [{"screenshot": "demo_before.png"}, {"frame": "iframe.c-sandbox", "click": "[data-code='CMPE 281']"}]
