"""json-render, static mode: a registry of pre-built specs; the model picks one and writes the words.

``specs/*.json`` are written by a developer and bind every number to state
with ``{"$state": "/pointer"}``. The model calls ``show_view`` with a view name
and two sentences. The server fills ``state`` from the cart's own data, checks
every binding resolves, and sends the finished spec. Buttons are handled by
plain server code: the registry already has the next screen.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import cart  # noqa: E402
import jsonrender  # noqa: E402
from shared.llm import get_model, tool  # noqa: E402

PROMPT = "How did the coffee cart do this week?"
REGISTRY = {p.stem: json.loads(p.read_text()) for p in sorted((HERE / "specs").glob("*.json"))}
TOOLS = [tool("show_view", "Show one pre-built view.", {
    "view": {"type": "string", "enum": sorted(REGISTRY)},
    "title": {"type": "string"}, "highlight": {"type": "string", "description": "one sentence about the data"}})]
SCRIPT = [{"tool_calls": [{"name": "show_view", "arguments": {
    "view": "sales_overview", "title": "Coffee cart · week 47",
    "highlight": "Friday was the best day yet: 104 cups, driven by cold brew before the 10 a.m. lectures."}}]}]


def finished(view: str, state: dict) -> dict:
    spec = {**json.loads(json.dumps(REGISTRY[view])), "state": state}
    errors = jsonrender.validate(spec)
    if errors:
        raise ValueError("; ".join(errors))
    return {"type": "spec", "spec": spec}


def run(prompt: str):
    reply = get_model(SCRIPT).complete([{"role": "user", "content": prompt}], TOOLS)
    call = reply["tool_calls"][0]
    args = call["arguments"]
    yield {"type": "trace", "text": f"model called show_view({json.dumps(args, ensure_ascii=False)})"}
    if args.get("view") != "sales_overview":
        yield {"type": "trace", "text": "rejected: unknown view"}
        return
    yield finished("sales_overview", cart.sales_state(args["title"], args["highlight"]))


def on_action(body: dict):
    name = body.get("name")
    yield {"type": "trace", "text": f"action {name}: handled by server code, no model call"}
    if name == "show_inventory":
        yield finished("inventory", cart.inventory_state())
    elif name == "reorder_beans":   # one state change, sent as one patch
        yield {"type": "patch", "op": {"op": "replace", "path": "/state/alert", "value": "Ordered 10 kg beans · arrives Thursday"}}
    elif name == "show_sales":
        yield finished("sales_overview", cart.sales_state("Coffee cart · week 47", "Back to the weekly view."))


def handle(name: str, body: dict):
    if name == "run":
        return run(body.get("prompt", PROMPT))
    if name == "action":
        return on_action(body)
    raise ValueError(f"unknown api {name}")


DEMO_STEPS = [{"screenshot": "demo_before.png"}, {"click": "button[data-action='show_inventory']"},
              {"click": "button[data-action='reorder_beans']"}]
