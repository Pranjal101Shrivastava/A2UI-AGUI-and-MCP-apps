"""json-render, mixed mode: a catalog spec with one GeneratedView, actions, and two renderers.

The dashboard is catalog components bound to state. One element, a rush-hour
heat map, is a ``GeneratedView`` whose HTML the model writes, because no
catalog component draws it. A button round-trips to the model, which answers
with patches. The same final spec is also drawn by ``render_terminal``: one
spec, two renderers (the HTML region degrades to a one-line note).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import cart  # noqa: E402
import jsonrender  # noqa: E402
from shared.llm import get_model  # noqa: E402

PROMPT = "When are our rush hours, and what should we prep for tomorrow?"

HOURS = ["8", "9", "10", "11", "12", "13"]
LOAD = [[3, 9, 6, 2, 4, 1], [4, 8, 7, 3, 5, 2], [2, 7, 5, 2, 3, 1], [5, 10, 8, 4, 6, 2], [6, 10, 9, 5, 8, 3]]
def heat_cell(day: str, hour: str, v: int) -> str:
    return f'<div class="c" style="--v:{v / 10}" title="{day} {hour}:00 · {v * 6} cups">{v * 6}</div>'


rows_html = "".join(f'<div class="h">{d}</div>' + "".join(heat_cell(d, h, v) for h, v in zip(HOURS, row))
                    for d, row in zip(cart.DAYS, LOAD))
HEATMAP = f"""<style>.g{{display:grid;grid-template-columns:40px repeat(6,1fr);gap:4px;font:12px system-ui;padding:6px}}
.c{{border-radius:6px;padding:8px 0;text-align:center;color:#fff;background:rgba(79,70,229,calc(.15 + var(--v)*.85))}}
.c:hover{{outline:2px solid #1f2430}} .h{{color:#667085;text-align:center}}</style>
<div class="g"><div></div>{"".join(f'<div class="h">{h}:00</div>' for h in HOURS)}{rows_html}</div>"""

S = lambda p: {"$state": p}  # noqa: E731
SPEC = {"root": "page", "elements": {
    "page": {"type": "Column", "children": ["title", "kpis", "heat", "plan"]},
    "title": {"type": "Text", "props": {"text": "Rush hours · week 47", "variant": "h1"}},
    "kpis": {"type": "Row", "children": ["peak", "cups"]},
    "peak": {"type": "Metric", "props": {"label": "Peak hour", "value": S("/peak"), "delta": "60 cups/h on Thu–Fri"}},
    "cups": {"type": "Metric", "props": {"label": "Cups this week", "value": S("/cups")}},
    "heat": {"type": "GeneratedView", "props": {"title": "Cups per hour (model-drawn)", "html": HEATMAP, "height": 230}},
    "plan": {"type": "Button", "props": {"label": "Plan tomorrow's prep", "action": "plan_prep", "variant": "primary"}},
}, "state": {"peak": "9:00", "cups": sum(cart.CUPS)}}
PREP = [
    {"op": "add", "path": "/elements/prep", "value": {"type": "Card", "props": {"title": "Prep for Friday"}, "children": ["prep_table", "prep_note"]}},
    {"op": "add", "path": "/elements/prep_table", "value": {"type": "Table", "props": {"columns": ["Item", "Amount", "Ready by"],
     "rows": [["Cold brew", "12 L", "7:30"], ["Espresso beans", "2.5 kg", "7:45"], ["Milk", "16 L", "7:45"]]}}},
    {"op": "add", "path": "/elements/prep_note", "value": {"type": "Badge", "props": {"text": "2 staff from 8:45 to 10:15", "tone": "info"}}},
    {"op": "replace", "path": "/elements/page/children/3", "value": "prep"},
    {"op": "remove", "path": "/elements/plan"},
]
SCRIPT = [json.dumps(SPEC, ensure_ascii=False), "\n".join(json.dumps(op, ensure_ascii=False) for op in PREP)]
STATE: dict = {}


def run(prompt: str):
    STATE["model"] = get_model(SCRIPT)
    spec = json.loads(STATE["model"].complete([{"role": "user", "content": prompt}])["content"])
    errors = jsonrender.validate(spec)
    if sum(el["type"] == "GeneratedView" for el in spec["elements"].values()) > 1:
        errors.append("use at most one GeneratedView")
    if errors:
        yield {"type": "trace", "text": "rejected: " + "; ".join(errors)}
        return
    STATE["spec"] = spec
    yield {"type": "spec", "spec": spec}


def on_action(body: dict):
    yield {"type": "trace", "text": f"action {body['name']}: model answers with patches"}
    if body["name"] != "plan_prep":
        return
    spec = STATE["spec"]
    for line in STATE["model"].complete([{"role": "user", "content": "plan_prep"}])["content"].splitlines():
        candidate = jsonrender.apply_line(spec, line)
        if not jsonrender.validate(candidate, complete=False):
            spec = candidate
            yield {"type": "patch", "op": json.loads(line)}
    STATE["spec"] = spec


def handle(name: str, body: dict):
    if name == "run":
        return run(body.get("prompt", PROMPT))
    if name == "action":
        return on_action(body)
    raise ValueError(f"unknown api {name}")


def demo_notes() -> str:
    return "the same final spec, drawn by the terminal renderer (jsonrender.render_terminal):\n" + \
        "\n".join("  " + line for line in jsonrender.render_terminal(STATE["spec"]).splitlines())


DEMO_STEPS = [{"screenshot": "demo_before.png"}, {"click": "button[data-action='plan_prep']"}]
