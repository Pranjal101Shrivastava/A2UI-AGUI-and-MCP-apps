"""A2UI, declarative mode: the model writes the surface itself, as JSONL.

The model may use any component in the basic catalog. The server streams its
output line by line, validates every envelope, forwards the valid ones at
once and returns the errors to the model, which answers with a fix. A form
submit comes back as an ``action``; the model writes the next surface and the
server fills its data model from the action context.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import a2ui  # noqa: E402
from rooms import ROOMS  # noqa: E402
from shared.llm import get_model  # noqa: E402

PROMPT = "I need to book room B12 for 4 people tomorrow afternoon"
SURFACE = "booking_form"

SYSTEM = f"""You build user interfaces with A2UI {a2ui.VERSION}. Reply with JSONL only: one envelope per line.
Envelopes: createSurface, updateComponents, updateDataModel. Use catalogId {a2ui.BASIC_CATALOG}.
Components (flat list, children by id, one has id "root"): Text(text, variant), Row(children), Column(children),
Card(child), Divider, Button(child, action:{{event:{{name, context}}}}, variant), TextField(label, value).
Bind values to data with {{"path": "/..."}}. Rooms: {json.dumps(ROOMS)}"""

E = lambda kind, body: json.dumps({"version": a2ui.VERSION, kind: body})  # noqa: E731
FORM = [
    {"id": "root", "component": "Card", "child": "body"},
    {"id": "body", "component": "Column", "children": ["title", "hint", "name", "date", "people", "room", "submit"]},
    {"id": "title", "component": "Text", "text": "Book a study room", "variant": "h2"},
    {"id": "hint", "component": "Text", "text": "Check the details, then confirm.", "variant": "caption"},
    {"id": "name", "component": "TextField", "label": "Your name", "value": {"path": "/booking/name"}},
    {"id": "date", "component": "TextField", "label": "When", "value": {"path": "/booking/when"}},
    {"id": "people", "component": "TextField", "label": "People", "value": {"path": "/booking/people"}},
    {"id": "room", "component": "TextField", "label": "Room", "value": {"path": "/booking/room"}},
    {"id": "submit", "component": "Button", "child": "submit_label", "variant": "primary",
     "action": {"event": {"name": "submit_booking", "context": {
         "name": {"path": "/booking/name"}, "when": {"path": "/booking/when"},
         "people": {"path": "/booking/people"}, "room": {"path": "/booking/room"}}}}},
    {"id": "submit_label", "component": "Text", "text": "Confirm booking"},
]
BROKEN = [dict(c) for c in FORM]
BROKEN[5] = {"id": "date", "component": "DatePicker", "label": "When", "value": {"path": "/booking/when"}}
BROKEN[6] = {**FORM[6], "placeholder": "e.g. 4"}
DONE = [
    {"id": "root", "component": "Card", "child": "done"},
    {"id": "done", "component": "Column", "children": ["done_title", "done_who", "done_where"]},
    {"id": "done_title", "component": "Text", "text": "You're booked", "variant": "h2"},
    {"id": "done_who", "component": "Text", "text": {"path": "/confirmation/summary"}},
    {"id": "done_where", "component": "Text", "text": {"path": "/confirmation/where"}, "variant": "caption"},
]

# Reply 1 has two mistakes on purpose. Reply 2 is the fix. Reply 3 answers the submit action.
SCRIPT = [
    "\n".join([
        E("createSurface", {"surfaceId": SURFACE, "catalogId": a2ui.BASIC_CATALOG}),
        E("updateComponents", {"surfaceId": SURFACE, "components": BROKEN}),
        E("updateDataModel", {"surfaceId": SURFACE, "path": "/booking",
                               "value": {"name": "", "when": "Tomorrow 14:00-16:00", "people": "4", "room": "B12"}}),
    ]),
    E("updateComponents", {"surfaceId": SURFACE, "components": FORM}),
    E("updateComponents", {"surfaceId": SURFACE, "components": DONE}),
]

SESSIONS: dict = {}


def stream_validated(model, messages, validator, errors: list):
    """Stream model output; forward each valid line at once; collect errors in `errors`."""
    buffer = ""

    def take(line):
        number, msg, parse_error = a2ui.parse_jsonl(line)[0] if line.strip() else (0, None, None)
        if parse_error:
            errors.append(parse_error)
        elif msg is not None:
            problems = validator.check(msg)
            if problems:
                errors.extend(problems)
                return None
            return msg
        return None

    for chunk in model.stream(messages):
        buffer += chunk
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            msg = take(line)
            if msg:
                yield msg
    msg = take(buffer)
    if msg:
        yield msg


def run(prompt: str):
    model, validator = get_model(SCRIPT), a2ui.Validator()
    SESSIONS["current"] = (model, validator)
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
    for attempt in range(3):
        errors: list = []
        yield from stream_validated(model, messages, validator, errors)
        if not errors:
            return
        yield {"type": "trace", "text": f"validator rejected {len(errors)} problem(s): {'; '.join(errors)}"}
        messages += [{"role": "assistant", "content": "(previous output)"},
                     {"role": "user", "content": "Fix these A2UI errors and resend only the corrected envelopes:\n"
                      + "\n".join(errors)}]
    yield {"type": "trace", "text": "gave up after 3 attempts"}


def on_action(body: dict):
    action = a2ui.parse_action(body)
    ctx = action["context"]
    yield {"type": "trace", "text": f"action {action['name']} context={json.dumps(ctx, ensure_ascii=False)}"}
    room = ROOMS.get(ctx.get("room", ""))
    people = int(ctx.get("people") or 0)
    if action["name"] != "submit_booking" or not room or not ctx.get("name") or people > room["seats"]:
        yield a2ui.update_data_model(SURFACE, "/booking/name", ctx.get("name") or "")
        yield {"type": "trace", "text": "rejected by the server: needs a name, a known room and enough seats"}
        return
    model, validator = SESSIONS["current"]
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"The user submitted: {json.dumps(ctx)}. Show a confirmation surface."}]
    yield a2ui.update_data_model(SURFACE, "/confirmation", {   # data from the server, not the model
        "summary": f"{ctx['name']}, {people} people, {ctx['when']}", "where": f"{room['name']} — {room['where']}"})
    yield from stream_validated(model, messages, validator, [])


def handle(name: str, body: dict):
    if name == "run":
        return run(body.get("prompt", PROMPT))
    if name == "action":
        return on_action(body)
    raise ValueError(f"unknown api {name}")


DEMO_STEPS = [
    {"fill": "label.c-field:has-text('Your name') input", "value": "Alex"},
    {"screenshot": "demo_before.png"},
    {"click": "button[data-action='submit_booking']"},
]
