"""AG-UI, open-ended mode: the agent writes HTML and streams it as a tool call.

There is no catalog. The model calls ``render_html`` with a complete page.
The server checks the HTML against the content policy *before* streaming the
arguments, because once ``TOOL_CALL_ARGS`` leave the server they cannot be
taken back. The page mounts the HTML in a sandboxed iframe on
``TOOL_CALL_END``. A button inside the frame posts a message; the page turns
it into the next run on the same thread.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import agui  # noqa: E402
from shared.llm import get_model, tool  # noqa: E402
from shared.sandbox import check_html  # noqa: E402

PROMPT = "Make me a beautiful one-page plan for a Kyoto weekend"
TOOLS = [tool("render_html", "Show a self-contained HTML page to the user. No external URLs. "
              "Report clicks with genux.send('action', {name}).", {"html": {"type": "string"}})]

POSTER = """<style>
 body{background:linear-gradient(160deg,#fdf2f8,#eef2ff)} .p{font:14px Georgia,serif;padding:18px 22px;color:#2d1b3d}
 h2{font-size:26px;margin:0;letter-spacing:.02em} .sub{color:#8b5a7a;margin-bottom:12px}
 .day{display:grid;grid-template-columns:62px 1fr;gap:10px;padding:10px 0;border-top:1px dashed #d8b4d0}
 .d{font:700 13px system-ui;color:#be185d} .spot{display:inline-block;background:#fff;border-radius:99px;padding:2px 9px;margin:3px 4px 0 0;
 box-shadow:0 1px 2px #0001;font:12px system-ui} button{margin-top:12px;font:600 13px system-ui;padding:9px 16px;border:0;
 border-radius:99px;background:#be185d;color:#fff;cursor:pointer} .sun{float:right;font-size:38px}
</style><div class="p"><span class="sun">⛩️</span><h2>Kyoto, slowly</h2><div class="sub">three days · temples, lanes, tea</div>
<div class="day"><div class="d">SAT</div><div>Early light at Kiyomizu-dera, then the stone lanes.<br>
<span class="spot">Kiyomizu-dera</span><span class="spot">Sannenzaka</span><span class="spot">Gion at dusk</span></div></div>
<div class="day"><div class="d">SUN</div><div>Rain is likely: keep it under a roof.<br>
<span class="spot">Nishiki Market</span><span class="spot">National Museum</span><span class="spot">Tea ceremony</span></div></div>
<div class="day"><div class="d">MON</div><div>Sunrise gates, then deer.<br>
<span class="spot">Fushimi Inari</span><span class="spot">Nara Park</span></div></div>
<button id="save">Save to my trips</button></div>
<script>document.getElementById("save").onclick = () => genux.send("action", {name: "save_trip"});</script>"""

SCRIPT = [
    {"content": "Here is a one-page plan. Sunday stays indoors because of the rain.",
     "tool_calls": [{"name": "render_html", "arguments": {"html": POSTER}}]},
    {"content": "Saved. You will find 'Kyoto, slowly' under My trips.", "tool_calls": []},
]
MODELS: dict = {}


def handle(name: str, body: dict):
    if name != "run":
        raise ValueError(f"unknown api {name}")
    run = agui.parse_run_input(body)
    model = MODELS.setdefault(run["threadId"], get_model(SCRIPT))
    yield agui.run_started(run["threadId"], run["runId"])
    reply = model.complete([{"role": "user", "content": agui.last_user_text(run)}], TOOLS)
    for call in reply["tool_calls"]:
        html = call["arguments"].get("html", "")
        problems = check_html(html)                     # check before anything is streamed
        if call["name"] != "render_html" or problems:
            yield agui.run_error(f"refused render_html: {'; '.join(problems) or 'unknown tool'}")
            return
        yield from agui.tool_call("render_html", {"html": html}, call["id"], chunk=160)
        yield agui.tool_result(call["id"], f"shown in a sandbox ({len(html)} chars)")
    if reply["content"]:
        yield from agui.text_message(reply["content"])
    yield agui.run_finished(run["threadId"], run["runId"])


DEMO_STEPS = [{"screenshot": "demo_before.png"}, {"frame": "iframe.c-sandbox", "click": "#save"}]
