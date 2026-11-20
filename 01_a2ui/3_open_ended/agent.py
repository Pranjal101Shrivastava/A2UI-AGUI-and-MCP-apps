"""A2UI, open-ended mode: one custom component, ``HtmlFrame``, and the model writes all of it.

The surface uses a custom catalog that contains only ``HtmlFrame``. The model
writes complete HTML, CSS and JavaScript for the floor plan. The server checks
the HTML against a content policy before sending it; the page shows it in a
sandboxed iframe. A click inside the frame becomes an ordinary A2UI ``action``.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import a2ui  # noqa: E402
from rooms import BOOKED, ROOMS  # noqa: E402
from shared.llm import approx_tokens, get_model  # noqa: E402

PROMPT = "Show me a map of the study rooms so I can pick one"
SURFACE = "floor_plan"
SYSTEM = f"""Reply with A2UI {a2ui.VERSION} JSONL. Use catalogId {a2ui.HTML_ONLY_CATALOG}: its only component is
HtmlFrame(html, height). Write self-contained HTML/CSS/JS. No external URLs. To report a click call
genux.send("action", {{name, context}}). Allowed action names: select_room, book_room. Rooms: {json.dumps(ROOMS)}.
Booked slots: {sorted(BOOKED)}"""

FLOOR_PLAN = """<style>
 .plan{font:13px system-ui;padding:8px} .plan h3{margin:0 0 6px}
 .room rect{stroke:#334;stroke-width:1.5;cursor:pointer;transition:filter .2s}
 .room:hover rect{filter:brightness(1.1)} .free rect{fill:#c7f0d8} .busy rect{fill:#f8c9c4}
 .room text{font-size:12px;pointer-events:none} .legend span{display:inline-block;width:10px;height:10px;margin:0 4px 0 10px}
</style>
<div class="plan"><h3>King Library · study rooms</h3>
<svg viewBox="0 0 420 170" width="100%">
 <rect x="2" y="2" width="416" height="166" fill="#f4f5fa" stroke="#99a"/>
 <g class="room free" data-room="A7"><rect x="20" y="20" width="90" height="60" rx="6"/><text x="34" y="55">A7 · 2 seats</text></g>
 <g class="room free" data-room="B12"><rect x="140" y="20" width="130" height="90" rx="6"/><text x="160" y="70">B12 · 4 seats</text></g>
 <g class="room busy" data-room="C3"><rect x="300" y="20" width="100" height="130" rx="6"/><text x="312" y="90">C3 · booked</text></g>
 <text x="20" y="150" fill="#667">Entrance ▸</text>
</svg>
<div class="legend"><span style="background:#c7f0d8"></span>free tomorrow 14:00<span style="background:#f8c9c4"></span>booked</div></div>
<script>
 document.querySelectorAll(".room.free").forEach(g => g.addEventListener("click", () =>
   genux.send("action", {name: "select_room", context: {room: g.dataset.room}})));
</script>"""

ROOM_PAGE = """<style>.r{font:14px system-ui;padding:10px}.r h3{margin:0}.r button{margin-top:10px;padding:8px 14px;
border:0;border-radius:8px;background:#4f46e5;color:#fff;cursor:pointer}.chip{display:inline-block;background:#eef0ff;
color:#4f46e5;border-radius:99px;padding:2px 8px;margin:6px 4px 0 0;font-size:12px}</style>
<div class="r"><h3>Room B12 · Quiet floor</h3><div>King Library, 2nd floor</div>
<span class="chip">4 seats</span><span class="chip">whiteboard</span><span class="chip">large display</span>
<p>Free tomorrow 14:00-16:00.</p><button id="b">Book B12</button></div>
<script>document.getElementById("b").onclick = () =>
 genux.send("action", {name: "book_room", context: {room: "B12", time: "Tomorrow 14:00-16:00"}});</script>"""

CONFIRM_PAGE = """<style>.ok{font:15px system-ui;padding:16px;text-align:center}.ok div{font-size:40px;color:#0f8a5f}</style>
<div class="ok"><div>✓</div><b>B12 is yours</b><p>Tomorrow 14:00-16:00 · King Library, 2nd floor</p></div>"""

frame = lambda html: json.dumps({"version": a2ui.VERSION, "updateComponents": {  # noqa: E731
    "surfaceId": SURFACE, "components": [{"id": "root", "component": "HtmlFrame", "html": html, "height": 240}]}})
create = json.dumps(a2ui.create_surface(SURFACE, a2ui.HTML_ONLY_CATALOG))
# Reply 1 loads a charting library from a CDN; the content policy refuses it.
SCRIPT = [
    create + "\n" + frame('<script src="https://cdn.example.com/plan.js"></script>' + FLOOR_PLAN),
    frame(FLOOR_PLAN),
    frame(ROOM_PAGE),
    frame(CONFIRM_PAGE),
]
ALLOWED_ACTIONS = {"select_room", "book_room"}
STATE: dict = {}


def generate(model, messages, validator):
    for attempt in range(3):
        text = "".join(model.stream(messages))
        errors, valid = [], []
        for number, msg, parse_error in a2ui.parse_jsonl(text):
            problems = [parse_error] if parse_error else validator.check(msg)
            errors += problems
            if not problems:
                valid.append(msg)
        yield from valid
        if not errors:
            return
        yield {"type": "trace", "text": f"content policy / validator: {'; '.join(errors)}"}
        messages = messages + [{"role": "user", "content": "Fix: " + "; ".join(errors)}]


def run(prompt: str):
    BOOKED.discard(("B12", "Tomorrow 14:00-16:00"))
    STATE["model"], STATE["validator"] = get_model(SCRIPT), a2ui.Validator()
    yield from generate(STATE["model"], [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                        STATE["validator"])


def on_action(body: dict):
    action = a2ui.parse_action(body)
    yield {"type": "trace", "text": f"action {action['name']} from the sandbox, context={json.dumps(action['context'], ensure_ascii=False)}"}
    if action["name"] not in ALLOWED_ACTIONS or action["context"].get("room") not in ROOMS:
        yield {"type": "trace", "text": "rejected: action or room not allowed"}
        return
    if action["name"] == "book_room":
        BOOKED.add((action["context"]["room"], action["context"].get("time", "")))
    prompt = f"The user clicked {action['name']} with {json.dumps(action['context'])}. Show the room page."
    yield from generate(STATE["model"], [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                        STATE["validator"])


def handle(name: str, body: dict):
    if name == "run":
        return run(body.get("prompt", PROMPT))
    if name == "action":
        return on_action(body)
    raise ValueError(f"unknown api {name}")


def demo_notes() -> str:
    """Compare what each A2UI mode asks the model to write for the room-picking task."""
    from shared.devserver import load_agent

    static = load_agent(HERE.parent / "1_static")
    declarative = load_agent(HERE.parent / "2_declarative")
    rows = [
        ("static (tool call args)", json.dumps(static.SCRIPT[0]["tool_calls"][0]["arguments"])),
        ("declarative (A2UI JSONL)", declarative.SCRIPT[1]),
        ("open-ended (HtmlFrame HTML)", SCRIPT[1]),
    ]
    lines = ["model output size for one screen (tokens, estimated):"]
    lines += [f"  {name:<30} {approx_tokens(text):>5}" for name, text in rows]
    return "\n".join(lines)


DEMO_STEPS = [
    {"screenshot": "demo_before.png"},
    {"frame": "iframe.c-sandbox", "click": "[data-room='B12']"},
    {"screenshot": "demo_room.png"},
    {"frame": "iframe.c-sandbox", "click": "#b"},
]
