"""A2UI, static mode: the UI is a pre-built template; the model only picks and fills.

The developer authored ``room_card.jsonl`` (structure) in advance. The model
calls one tool, ``show_room``. The server validates the arguments against its
own room list and sends the template plus one ``updateDataModel``. The model
never writes a component.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import a2ui  # noqa: E402
from rooms import BOOKED, ROOMS  # noqa: E402
from shared.llm import get_model, tool  # noqa: E402

PROMPT = "Find me a quiet study room for 4 people tomorrow afternoon"
TEMPLATE = [json.loads(line) for line in (HERE / "room_card.jsonl").read_text().splitlines() if line.strip()]
SURFACE = TEMPLATE[0]["createSurface"]["surfaceId"]

TOOLS = [tool("show_room", "Show one bookable study room in the room card.", {
    "room_id": {"type": "string", "enum": sorted(ROOMS)},
    "time": {"type": "string", "description": "the slot, e.g. 'Tomorrow 14:00-16:00'"},
    "reason": {"type": "string", "description": "one short sentence: why this room fits"},
})]
SYSTEM = "You help students book library study rooms. Rooms: " + json.dumps(ROOMS) + \
    " Pick the best room and call show_room exactly once."

# The scripted model reply used offline (GENUX_LIVE=1 swaps in a real model).
SCRIPT = [{"tool_calls": [{"name": "show_room", "arguments": {
    "room_id": "B12", "time": "Tomorrow 14:00-16:00",
    "reason": "Quiet floor and exactly 4 seats, with a whiteboard for group work."}}]}]


def run(prompt: str):
    model = get_model(SCRIPT)
    reply = model.complete([{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}], TOOLS)
    for call in reply["tool_calls"]:
        args = call["arguments"]
        yield {"type": "trace", "text": f"model called {call['name']}({json.dumps(args, ensure_ascii=False)})"}
        room = ROOMS.get(args.get("room_id"))
        if call["name"] != "show_room" or room is None:
            yield {"type": "trace", "text": "rejected: unknown tool or room"}
            continue
        yield from TEMPLATE                          # structure: fixed, written by a developer
        yield a2ui.update_data_model(SURFACE, "/", {  # data: the only part the model influenced
            "room": room, "time": args["time"], "reason": args["reason"], "status": "Available"})


def on_action(body: dict):
    action = a2ui.parse_action(body)
    yield {"type": "trace", "text": f"action {action['name']} context={json.dumps(action['context'], ensure_ascii=False)}"}
    ctx = action["context"]
    if action["name"] != "book_room" or ctx.get("roomId") not in ROOMS:
        yield {"type": "trace", "text": "rejected: unknown action or room"}
        return
    if (ctx["roomId"], ctx["time"]) in BOOKED:
        yield a2ui.update_data_model(SURFACE, "/status", "Sorry, that slot was just taken")
        return
    BOOKED.add((ctx["roomId"], ctx["time"]))
    yield a2ui.update_data_model(SURFACE, "/status", f"Booked: {ctx['roomId']}, {ctx['time']}")


def handle(name: str, body: dict):
    if name == "run":
        BOOKED.discard(("B12", "Tomorrow 14:00-16:00"))  # keep demos repeatable
        return run(body.get("prompt", PROMPT))
    if name == "action":
        return on_action(body)
    raise ValueError(f"unknown api {name}")


DEMO_STEPS = [{"screenshot": "demo_before.png"}, {"click": "button[data-action='book_room']"}]
