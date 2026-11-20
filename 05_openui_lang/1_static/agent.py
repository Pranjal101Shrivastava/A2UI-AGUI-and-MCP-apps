"""OpenUI Lang, static mode: the language, but only three pre-built widgets.

The model writes a short OpenUI Lang program, yet the only components it may
call are ``CourseList``, ``CourseCard`` and ``ConflictAlert``. Their renderers
are hand-written in ``app.js``. The server checks every card against the
registrar's data. The "Enroll" button inside a card is handled by server
code, which answers with new statements: re-assigning ``cloud`` and ``note``
replaces exactly those two parts of the screen.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import openui  # noqa: E402
from courses import COURSES  # noqa: E402
from shared.llm import get_model  # noqa: E402
from stream import program_events  # noqa: E402

PROMPT = "Which evening courses can I still get into this spring?"
WIDGETS = {"CourseList": ["children"], "CourseCard": ["code", "title", "units", "when", "seats", "enrolled"],
           "ConflictAlert": ["text", "tone"]}
SYSTEM = ("Answer with OpenUI Lang, one statement per line. You may only use: "
          + ", ".join(f"{k}({', '.join(v)})" for k, v in WIDGETS.items()) + f". Courses: {json.dumps(COURSES)}")

card = lambda name, code, enrolled=False: (  # noqa: E731
    f'{name} = CourseCard("{code}", "{COURSES[code]["title"]}", {COURSES[code]["units"]}, '
    f'"{COURSES[code]["when"]}", {COURSES[code]["seats"]}, {"true" if enrolled else "false"})')
SCRIPT = ["\n".join([
    "root = CourseList([web, cloud, note])",
    card("web", "CMPE 280"),
    card("cloud", "CMPE 281"),
    'note = ConflictAlert("No time conflicts between these two · 6 units", "ok")',
])]
NAMES = {"CMPE 280": "web", "CMPE 281": "cloud"}


def check(text: str) -> list[str]:
    statements, order, errors = openui.parse_program(text)
    tree, more = openui.resolve(statements, order, WIDGETS)
    errors += more

    def walk(node):
        if node.get("type") == "CourseCard":
            p = node["props"]
            truth = COURSES.get(p["code"])
            if not truth or any(p[k] != truth[k] for k in ("title", "units", "when", "seats")):
                errors.append(f"CourseCard {p['code']} does not match the registrar's data")
        for child in node.get("children", []):
            walk(child)

    walk(tree or {})
    return errors


def run(prompt: str):
    for code in NAMES:
        COURSES[code]["seats"] = {"CMPE 280": 12, "CMPE 281": 2}[code]   # reset the demo data
    yield from program_events(get_model(SCRIPT, delay=0.02), [{"role": "system", "content": SYSTEM},
                                                               {"role": "user", "content": prompt}], check)


def on_action(body: dict):
    code = body.get("context", {}).get("code")
    yield {"type": "trace", "text": f"action {body['name']} {code}: server code writes the new statements"}
    if body["name"] != "enroll" or code not in NAMES or COURSES[code]["seats"] < 1:
        yield {"type": "chunk", "text": 'note = ConflictAlert("That section is full", "bad")\n'}
    else:
        COURSES[code]["seats"] -= 1
        yield {"type": "chunk", "text": card(NAMES[code], code, enrolled=True) + "\n"}
        yield {"type": "chunk", "text": f'note = ConflictAlert("Enrolled in {code} · {COURSES[code]["seats"]} seat(s) left", "ok")\n'}
    yield {"type": "end"}


def handle(name: str, body: dict):
    if name == "run":
        return run(body.get("prompt", PROMPT))
    if name == "action":
        return on_action(body)
    raise ValueError(f"unknown api {name}")


DEMO_STEPS = [{"screenshot": "demo_before.png"}, {"click": "button[data-code='CMPE 281']"}]
