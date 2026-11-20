"""A2UI, mixed mode: catalog components plus one sandboxed HtmlFrame region.

The form (title, inputs, button, status) uses basic-catalog components bound to
the data model. Only the floor plan, which no catalog component can draw, is an
``HtmlFrame``. A click on the map becomes an ``action``; the server answers with
``updateDataModel``, and the catalog ``TextField`` bound to ``/booking/room``
updates. Neither action needs another model call.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import a2ui  # noqa: E402
from rooms import BOOKED, ROOMS  # noqa: E402
from shared.llm import get_model  # noqa: E402

PROMPT = "Help me pick and book a study room for tomorrow 14:00"
SURFACE = "room_picker"
SLOT = "Tomorrow 14:00-16:00"
SYSTEM = f"""Reply with A2UI {a2ui.VERSION} JSONL using catalogId {a2ui.BASIC_PLUS_HTML_CATALOG}.
Prefer basic components (Text, Row, Column, Card, Button, TextField). Use at most ONE HtmlFrame, only for
what the basic components cannot draw. In HtmlFrame HTML, report clicks with
genux.send("action", {{name: "select_room", context: {{room}}}}). Rooms: {json.dumps(ROOMS)}"""

MAP = """<style>svg{font:12px system-ui}.r{cursor:pointer}.r rect{fill:#c7f0d8;stroke:#334}
.r.busy rect{fill:#f8c9c4;cursor:not-allowed}.r:hover rect{stroke-width:3}</style>
<svg viewBox="0 0 420 120" width="100%">
<g class="r" data-room="A7"><rect x="10" y="10" width="100" height="90" rx="6"/><text x="30" y="60">A7 · 2</text></g>
<g class="r" data-room="B12"><rect x="130" y="10" width="140" height="90" rx="6"/><text x="170" y="60">B12 · 4</text></g>
<g class="r busy" data-room="C3"><rect x="290" y="10" width="120" height="90" rx="6"/><text x="315" y="60">C3 · taken</text></g>
</svg>
<script>document.querySelectorAll(".r:not(.busy)").forEach(g => g.onclick = () =>
  genux.send("action", {name: "select_room", context: {room: g.dataset.room}}));</script>"""

COMPONENTS = [
    {"id": "root", "component": "Card", "child": "body"},
    {"id": "body", "component": "Column", "children": ["title", "map", "fields", "status", "book"]},
    {"id": "title", "component": "Text", "text": "Pick a room on the map", "variant": "h2"},
    {"id": "map", "component": "HtmlFrame", "html": MAP, "height": 140},
    {"id": "fields", "component": "Row", "children": ["room", "name"]},
    {"id": "room", "component": "TextField", "label": "Room", "value": {"path": "/booking/room"}},
    {"id": "name", "component": "TextField", "label": "Your name", "value": {"path": "/booking/name"}},
    {"id": "status", "component": "Text", "text": {"path": "/booking/status"}, "variant": "caption"},
    {"id": "book", "component": "Button", "child": "book_label", "variant": "primary", "action": {"event": {
        "name": "book", "context": {"room": {"path": "/booking/room"}, "name": {"path": "/booking/name"}}}}},
    {"id": "book_label", "component": "Text", "text": "Book"},
]
SCRIPT = ["\n".join(json.dumps(m) for m in [
    a2ui.create_surface(SURFACE, a2ui.BASIC_PLUS_HTML_CATALOG),
    a2ui.update_components(SURFACE, COMPONENTS),
    a2ui.update_data_model(SURFACE, "/booking", {"room": "", "name": "", "status": "Free rooms are green."}),
])]


def run(prompt: str):
    BOOKED.discard(("B12", SLOT))
    model, validator = get_model(SCRIPT), a2ui.Validator()
    text = "".join(model.stream([{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]))
    for number, msg, parse_error in a2ui.parse_jsonl(text):
        problems = [parse_error] if parse_error else validator.check(msg)
        if problems:
            yield {"type": "trace", "text": f"line {number} rejected: {'; '.join(problems)}"}
        else:
            yield msg


def on_action(body: dict):
    """Both actions are plain server code: checked, then answered with data only."""
    action = a2ui.parse_action(body)
    ctx = action["context"]
    yield {"type": "trace", "text": f"action {action['name']} from {action['sourceComponentId']}, context={json.dumps(ctx, ensure_ascii=False)}"}
    room = ROOMS.get(ctx.get("room", ""))
    if action["name"] == "select_room" and room and (room["id"], SLOT) not in BOOKED:
        yield a2ui.update_data_model(SURFACE, "/booking/room", room["id"])
        yield a2ui.update_data_model(SURFACE, "/booking/status", f"{room['name']} · {room['details']}")
    elif action["name"] == "book" and room and ctx.get("name"):
        BOOKED.add((room["id"], SLOT))
        yield a2ui.update_data_model(SURFACE, "/booking/status", f"Booked {room['id']} for {ctx['name']}, {SLOT} ✓")
    else:
        yield a2ui.update_data_model(SURFACE, "/booking/status", "Pick a free room and enter your name first.")


def handle(name: str, body: dict):
    if name == "run":
        return run(body.get("prompt", PROMPT))
    if name == "action":
        return on_action(body)
    raise ValueError(f"unknown api {name}")


DEMO_STEPS = [
    {"frame": "iframe.c-sandbox", "click": "[data-room='B12']"},
    {"fill": "label.c-field:has-text('Your name') input", "value": "Alex"},
    {"screenshot": "demo_before.png"},
    {"click": "button[data-action='book']"},
]
