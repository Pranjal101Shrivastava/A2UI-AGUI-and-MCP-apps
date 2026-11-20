"""OpenUI Lang, declarative mode: the model composes primitives, root first, and streams.

The program starts with ``root`` and names parts that are defined later
(forward references). The page parses after every completed line: unknown
names render as placeholders, then fill in as their lines arrive. An action
returns new statements; each re-assigned name replaces its part of the UI.
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

PROMPT = "Plan a 9-unit evening-friendly spring semester for me"
SYSTEM = ("Answer in OpenUI Lang. Start with root, then define each name. Components: "
          + ", ".join(f"{k}({', '.join(v)})" for k, v in openui.PRIMITIVES.items())
          + f". Courses: {json.dumps(COURSES)}")
PLAN = """root = Stack([title, summary, plan, chart, actions])
title = Text("Spring 2027 · suggested plan", "h1")
summary = Stack([units, evenings, risk], "row")
units = Metric("Units", 9, "full-time")
evenings = Metric("Days on campus", 5)
risk = Badge("CMPE 281 has 2 seats left: enroll soon", "warn")
plan = Table(["Course", "Title", "When", "Seats"], rows)
rows = [["CMPE 280", "Web UI Design and Development", "Mon/Wed 18:00", 12], ["CMPE 281", "Cloud Technologies", "Tue/Thu 18:00", 2], ["CMPE 258", "Deep Learning", "Fri 15:00", 5]]
chart = BarChart("Expected hours per week", ["CMPE 280", "CMPE 281", "CMPE 258"], [9, 8, 10])
actions = Stack([enroll, fridays], "row")
enroll = Button("Enroll in all three", "enroll_all", "primary")
fridays = Button("Keep Fridays free", "avoid_friday")
"""
NO_FRIDAY = """rows = [["CMPE 280", "Web UI Design and Development", "Mon/Wed 18:00", 12], ["CMPE 281", "Cloud Technologies", "Tue/Thu 18:00", 2], ["CMPE 272", "Enterprise Software Platforms", "Mon/Wed 18:00", 9]]
chart = BarChart("Expected hours per week", ["CMPE 280", "CMPE 281", "CMPE 272"], [9, 8, 7])
evenings = Metric("Days on campus", 4, "-1")
risk = Badge("CMPE 272 and CMPE 280 meet at the same time: pick one", "bad")
"""
SCRIPT = [PLAN, NO_FRIDAY]
STATE: dict = {}


def run(prompt: str):
    STATE["model"] = get_model(SCRIPT, delay=0.015)
    STATE["program"] = PLAN
    yield from program_events(STATE["model"], [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                              lambda text: openui.check(text, openui.PRIMITIVES)[1])


def on_action(body: dict):
    yield {"type": "trace", "text": f"action {body['name']}: the model answers with replacement statements"}
    if body["name"] != "avoid_friday":
        yield {"type": "end"}
        return
    yield from program_events(STATE["model"], [{"role": "system", "content": SYSTEM},
                                               {"role": "user", "content": "Keep Fridays free. Re-assign only what changes."}],
                              lambda text: openui.check(STATE["program"] + text, openui.PRIMITIVES)[1])


def handle(name: str, body: dict):
    if name == "run":
        return run(body.get("prompt", PROMPT))
    if name == "action":
        return on_action(body)
    raise ValueError(f"unknown api {name}")


def demo_notes() -> str:
    return "the streamed program:\n" + "\n".join("  " + line[:110] for line in PLAN.splitlines()) + \
        "\nthe action's answer (four re-assigned names):\n" + "\n".join("  " + l[:110] for l in NO_FRIDAY.splitlines())


DEMO_STEPS = [{"screenshot": "demo_before.png"}, {"click": "button[data-action='avoid_friday']"}]
