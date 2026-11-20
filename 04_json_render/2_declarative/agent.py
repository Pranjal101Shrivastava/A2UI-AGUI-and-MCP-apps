"""json-render, declarative mode: the model streams the spec as JSON Patch lines.

The model writes JSONL: one RFC 6902 operation per line against an empty spec
``{root, elements, state}``. The server applies each line, validates the
partial spec, and forwards the operation at once. The page applies the same
operation and repaints, so the first components appear while the model is
still writing. A button sends the current spec back; the model answers with
more patches against it.
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import cart  # noqa: E402
import jsonrender  # noqa: E402
from shared.catalog import prompt_text  # noqa: E402
from shared.llm import get_model  # noqa: E402

PROMPT = "Build me a dashboard of this week's coffee cart sales"
SYSTEM = ("Write a json-render spec as JSONL RFC 6902 patches against {root:null, elements:{}, state:{}}. "
          "Send /root first, then parents before children, then state. Bind data with {\"$state\": \"/x\"}. "
          "Components:\n" + prompt_text())

L = lambda path, value: json.dumps({"op": "add", "path": path, "value": value}, ensure_ascii=False)  # noqa: E731
S = lambda pointer: {"$state": pointer}  # noqa: E731
DASHBOARD = "\n".join([
    L("/root", "page"),
    L("/elements/page", {"type": "Column", "children": ["title", "kpis", "chart", "items", "reorder"]}),
    L("/elements/title", {"type": "Text", "props": {"text": "Coffee cart · this week", "variant": "h1"}}),
    L("/elements/kpis", {"type": "Row", "children": ["revenue", "cups", "best"]}),
    L("/elements/revenue", {"type": "Metric", "props": {"label": "Revenue", "value": S("/revenue"), "delta": "+18%"}}),
    L("/elements/cups", {"type": "Metric", "props": {"label": "Cups", "value": S("/cups"), "delta": "+11%"}}),
    L("/elements/best", {"type": "Metric", "props": {"label": "Busiest day", "value": "Fri · 104"}}),
    L("/elements/chart", {"type": "BarChart", "props": {"title": "Cups per day", "labels": S("/days"), "values": S("/by_day")}}),
    L("/elements/items", {"type": "Table", "props": {"columns": ["Drink", "Cups", "Price"], "rows": S("/items")}}),
    L("/elements/reorder", {"type": "Button", "props": {"label": "Beans are low: reorder", "action": "reorder", "variant": "primary"}}),
    L("/state/revenue", f"${cart.REVENUE:,.0f}"), L("/state/cups", sum(cart.CUPS)),
    L("/state/days", cart.DAYS), L("/state/by_day", cart.CUPS), L("/state/items", cart.ITEMS),
])
REORDER = "\n".join([
    L("/elements/ordered", {"type": "Badge", "props": {"text": "Ordered 10 kg beans · arrives Thursday", "tone": "ok"}}),
    json.dumps({"op": "replace", "path": "/elements/page/children/4", "value": "ordered"}),
    json.dumps({"op": "remove", "path": "/elements/reorder"}),
])
SCRIPT = [DASHBOARD, REORDER]
STATE: dict = {}


def stream_patches(model, messages, spec):
    """Forward each valid line as soon as it is complete; skip and report invalid ones."""
    buffer, started = "", time.perf_counter()
    lines = []
    for chunk in model.stream(messages):
        buffer += chunk
        *complete, buffer = buffer.split("\n")
        lines += complete
        for line in complete:
            try:
                candidate = jsonrender.apply_line(spec, line)
            except (ValueError, KeyError, IndexError) as exc:
                yield {"type": "trace", "text": f"skipped a line that does not apply: {exc}"}
                continue
            errors = jsonrender.validate(candidate, complete=False)
            if errors:
                yield {"type": "trace", "text": "rejected: " + "; ".join(errors)}
                continue
            spec = candidate
            yield {"type": "patch", "op": json.loads(line), "t": round(time.perf_counter() - started, 3)}
        complete.clear()
    if buffer.strip():
        spec = jsonrender.apply_line(spec, buffer)
        yield {"type": "patch", "op": json.loads(buffer), "t": round(time.perf_counter() - started, 3)}
    final = jsonrender.validate(spec)
    yield {"type": "trace", "text": "final spec valid" if not final else "final spec invalid: " + "; ".join(final)}
    STATE["spec"] = spec


def run(prompt: str):
    STATE["model"] = get_model(SCRIPT, delay=0.012)
    data = {"days": cart.DAYS, "cups": cart.CUPS, "items": cart.ITEMS}
    yield from stream_patches(STATE["model"], [{"role": "system", "content": SYSTEM},
                                               {"role": "user", "content": f"{prompt}\nData: {json.dumps(data)}"}],
                              json.loads(json.dumps(jsonrender.EMPTY)))


def on_action(body: dict):
    yield {"type": "trace", "text": f"action {body['name']}: asking the model for patches against the current spec"}
    if body["name"] != "reorder":
        return
    spec = body.get("spec") or STATE["spec"]       # the page sends the spec it shows
    yield from stream_patches(STATE["model"], [{"role": "system", "content": SYSTEM},
                                               {"role": "user", "content": f"User pressed reorder. Spec: {json.dumps(spec)}"}], spec)


def handle(name: str, body: dict):
    if name == "run":
        return run(body.get("prompt", PROMPT))
    if name == "action":
        return on_action(body)
    raise ValueError(f"unknown api {name}")


def demo_notes() -> str:
    """Why a flat map streams: bytes needed before anything can be drawn."""
    lines = DASHBOARD.splitlines()
    first_paint = sum(len(x) + 1 for x in lines[:3])          # root, page, title
    total = len(DASHBOARD)
    return ("bytes the model must write before the first component can be drawn:\n"
            f"  flat element map, JSONL patches  {first_paint:>5} of {total} ({first_paint / total:.0%})\n"
            f"  one nested JSON tree             {total:>5} of {total} (100%: it parses only when complete)")


DEMO_STEPS = [{"screenshot": "demo_before.png"}, {"click": "button[data-action='reorder']"}]
