"""AG-UI, mixed mode: catalog UI in shared state, one generated region, one frontend tool.

* The itinerary is a catalog tree in ``state.ui`` (declarative, validated).
* One node is a ``GeneratedView``: model-written HTML for the route sketch,
  shown in a sandbox (open-ended, one region only).
* The agent asks for approval through ``confirm_booking``, a tool the
  *frontend* declared in ``RunAgentInput.tools``. The page draws the
  approval card; the answer returns as a ``tool`` message in the next run
  (human in the loop).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import agui  # noqa: E402
from shared.llm import get_model  # noqa: E402
from ui_tree import validate_tree  # noqa: E402

PROMPT = "Plan my Kyoto weekend and book a ryokan if it fits ¥40,000"

ROUTE = """<style>svg{font:12px system-ui;width:100%}.p{fill:none;stroke:#be185d;stroke-width:3;stroke-dasharray:8 6;
animation:m 1.2s linear infinite}@keyframes m{to{stroke-dashoffset:-28}}circle{fill:#4f46e5}</style>
<svg viewBox="0 0 360 150"><path class="p" d="M40 110 C 110 20, 170 20, 200 70 S 290 140, 320 40"/>
<circle cx="40" cy="110" r="7"/><text x="22" y="135">Kyoto Stn</text>
<circle cx="200" cy="70" r="7"/><text x="165" y="98">Gion · Sat</text>
<circle cx="320" cy="40" r="7"/><text x="265" y="22">Fushimi · Mon</text></svg>"""

DAY = lambda title, text: {"type": "Card", "props": {"title": title}, "children": [  # noqa: E731
    {"type": "Text", "props": {"text": text}}]}
UI = {"type": "Column", "children": [
    {"type": "Text", "props": {"text": "Kyoto weekend", "variant": "h1"}},
    {"type": "Row", "children": [
        {"type": "Column", "children": [DAY("Sat", "Kiyomizu-dera, Sannenzaka, Gion."),
                                        DAY("Sun", "Indoor day: Nishiki Market, museum, tea."),
                                        DAY("Mon", "Fushimi Inari at sunrise, Nara deer park.")]},
        {"type": "GeneratedView", "props": {"title": "Route sketch", "html": ROUTE, "height": 190}}]},
    {"type": "Row", "children": [{"type": "Metric", "props": {"label": "Budget used", "value": "¥26,000", "delta": "of ¥40,000"}},
                                 {"type": "Badge", "props": {"text": "hotel: waiting for approval", "tone": "warn"}}]}]}
BOOKING = {"hotel": "Ryokan Sakura, Gion", "nights": 2, "price": "¥36,000", "why": "Walking distance to Saturday's stops."}

SCRIPT = [
    {"content": json.dumps({"ui": UI}), "tool_calls": [{"name": "confirm_booking", "arguments": BOOKING}]},
    {"content": json.dumps([
        {"op": "replace", "path": "/ui/children/2/children/0/props/value", "value": "¥62,000"},
        {"op": "replace", "path": "/ui/children/2/children/1", "value": {"type": "Badge", "props": {
            "text": "Ryokan Sakura booked · 2 nights", "tone": "ok"}}}]), "tool_calls": []},
    {"content": json.dumps([{"op": "replace", "path": "/ui/children/2/children/1", "value": {"type": "Badge", "props": {
        "text": "no hotel booked", "tone": "bad"}}}]), "tool_calls": []},
]
MODELS: dict = {}


def handle(name: str, body: dict):
    if name != "run":
        raise ValueError(f"unknown api {name}")
    run = agui.parse_run_input(body)
    model = MODELS.setdefault(run["threadId"], get_model(SCRIPT))
    yield agui.run_started(run["threadId"], run["runId"])
    last = run["messages"][-1] if run["messages"] else {}

    if last.get("role") == "tool":                         # the user answered the approval card
        answer = json.loads(last["content"])
        if not answer.get("approved"):
            model.complete([])                               # the scripted "approved" reply is skipped
        ops = json.loads(model.complete([{"role": "tool", "content": last["content"]}])["content"])
        state = agui.apply_patch(run["state"], ops)
        problems = validate_tree(state.get("ui"))
        if problems:
            yield agui.run_error("; ".join(problems))
            return
        yield agui.state_delta(ops)
        yield from agui.text_message("Booked. Your budget is updated." if answer.get("approved") else "No hotel booked.")
        yield agui.run_finished(run["threadId"], run["runId"])
        return

    reply = model.complete([{"role": "user", "content": agui.last_user_text(run)}])
    state = json.loads(reply["content"])
    problems = validate_tree(state["ui"])
    if problems:
        yield agui.run_error("; ".join(problems))
        return
    yield agui.state_snapshot(state)
    declared = {t["name"] for t in run["tools"]}
    for call in reply["tool_calls"]:
        if call["name"] not in declared:                     # only tools the frontend offered
            yield agui.run_error(f"{call['name']} was not declared by the frontend")
            return
        yield from agui.tool_call(call["name"], call["arguments"], call["id"])
    yield agui.run_finished(run["threadId"], run["runId"])   # the run ends; the frontend owns the next move


DEMO_STEPS = [{"screenshot": "demo_before.png"}, {"click": "button[data-action='approve']"}]
