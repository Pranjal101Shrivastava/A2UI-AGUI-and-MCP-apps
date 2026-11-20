"""OpenUI Lang, mixed mode: primitives for the plan, one ``HtmlArtifact`` for the week view.

Text, metrics, the course table and the button are catalog primitives. Only
the week grid, which no primitive draws, is an ``HtmlArtifact``. When the user
adds an elective, the model answers with statements that re-assign five
names, including the artifact itself. Everything else stays on screen.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import openui  # noqa: E402
from shared.llm import get_model  # noqa: E402
from stream import program_events  # noqa: E402

PROMPT = "Help me finish my spring plan: I have CMPE 280 and 281"
COMPONENTS = {**openui.PRIMITIVES, **openui.HTML_ARTIFACT}
SYSTEM = ("Answer in OpenUI Lang. Prefer primitives: " + ", ".join(openui.PRIMITIVES)
          + ". Use at most one HtmlArtifact(html, title, height), only for what primitives cannot draw.")


def week(blocks: list[tuple[str, int, str]]) -> str:
    """The model-written week grid (the scripted model's HTML)."""
    cells = "".join(f'<div class="b" style="grid-column:{d + 1};background:{c}">{code}</div>' for code, d, c in blocks)
    return ("<style>.w{display:grid;grid-template-columns:repeat(5,1fr);gap:4px;font:12px system-ui;padding:6px}"
            ".d{color:#667085;text-align:center}.b{grid-row:2;color:#fff;border-radius:8px;padding:18px 4px;"
            "text-align:center;font-weight:600}</style><div class=\"w\">"
            + "".join(f'<div class="d">{d}</div>' for d in ["Mon", "Tue", "Wed", "Thu", "Fri"]) + cells + "</div>")


BASE = [("CMPE 280", 0, "#4f46e5"), ("CMPE 281", 1, "#0f8a5f"), ("CMPE 280", 2, "#4f46e5"), ("CMPE 281", 3, "#0f8a5f")]
art = lambda blocks: f'week = HtmlArtifact({json.dumps(week(blocks))}, "This week", 120)'  # noqa: E731
PLAN = "\n".join([
    "root = Stack([title, top, courses, actions])",
    'title = Text("Spring 2027 · 6 units so far", "h1")',
    'top = Stack([week, side], "row")',
    art(BASE),
    'side = Stack([units, seats], "column")',
    'units = Metric("Units", 6, "-3 to full-time")',
    'seats = Progress("Seats taken in CMPE 281", 93)',
    'courses = Table(["Course", "When"], [["CMPE 280", "Mon/Wed 18:00"], ["CMPE 281", "Tue/Thu 18:00"]])',
    'actions = Stack([add], "row")',
    'add = Button("Add a Friday elective", "add_elective", "primary")',
]) + "\n"
ADD = "\n".join([
    art(BASE + [("CMPE 258", 4, "#b45309")]),
    'units = Metric("Units", 9, "+3 full-time")',
    'courses = Table(["Course", "When"], [["CMPE 280", "Mon/Wed 18:00"], ["CMPE 281", "Tue/Thu 18:00"], ["CMPE 258", "Fri 15:00"]])',
    'title = Text("Spring 2027 · 9 units", "h1")',
    'actions = Badge("Plan complete: no conflicts", "ok")',
]) + "\n"
SCRIPT = [PLAN, ADD]
STATE: dict = {}


def run(prompt: str):
    STATE["model"] = get_model(SCRIPT, delay=0.01)
    STATE["program"] = PLAN

    def check(text):
        tree, errors = openui.check(text, COMPONENTS)
        if text.count("HtmlArtifact(") > 1:
            errors.append("use at most one HtmlArtifact")
        return errors

    yield from program_events(STATE["model"], [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}], check)


def on_action(body: dict):
    yield {"type": "trace", "text": f"action {body['name']}: the model re-assigns only what changes"}
    if body["name"] != "add_elective":
        yield {"type": "end"}
        return
    yield from program_events(STATE["model"], [{"role": "user", "content": "Add a Friday elective."}],
                              lambda text: openui.check(STATE["program"] + text, COMPONENTS)[1])


def handle(name: str, body: dict):
    if name == "run":
        return run(body.get("prompt", PROMPT))
    if name == "action":
        return on_action(body)
    raise ValueError(f"unknown api {name}")


def demo_notes() -> str:
    names = [line.split(" = ")[0] for line in ADD.splitlines()]
    return f"the action re-assigned {len(names)} names ({', '.join(names)}); the other {len(PLAN.splitlines()) - len(names)} statements were reused"


DEMO_STEPS = [{"screenshot": "demo_before.png"}, {"click": "button[data-action='add_elective']"}]
