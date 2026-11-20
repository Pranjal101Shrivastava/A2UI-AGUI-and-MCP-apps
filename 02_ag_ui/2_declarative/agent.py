"""AG-UI, declarative mode: the UI lives in shared state, built by JSON Patch.

The model writes RFC 6902 operations against ``state.ui``, a tree of catalog
components. The server applies each operation to a copy, validates the whole
tree, and only then emits it as a ``STATE_DELTA``. The page re-renders the
tree on every delta. A button starts a new run that carries the current
state back, so the agent edits the UI the user is looking at.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import agui  # noqa: E402
from shared.catalog import prompt_text  # noqa: E402
from shared.llm import get_model  # noqa: E402
from ui_tree import validate_tree  # noqa: E402

PROMPT = "Plan a 3-day weekend in Kyoto for me"
SYSTEM = "You edit the user's screen. Reply with JSON Patch operations (one per line) on the state document; " \
         "state.ui is a tree {type, props, children}. Components:\n" + prompt_text()

card = lambda title, text, badge, tone, *extra: {"type": "Card", "props": {"title": title}, "children": [  # noqa: E731
    {"type": "Text", "props": {"text": text}}, {"type": "Badge", "props": {"text": badge, "tone": tone}}, *extra]}
SAT = card("Sat · Eastern Kyoto", "Kiyomizu-dera at 8:00, Sannenzaka lanes, Gion at dusk.", "sunny 19°", "ok")
SUN = card("Sun · Arashiyama", "Bamboo grove, Tenryu-ji, river walk.", "rain 16°", "warn",
           {"type": "Button", "props": {"label": "Make it an indoor day", "action": "rain_plan", "variant": "primary"}})
MON = card("Mon · Fushimi & Nara", "Fushimi Inari at sunrise, deer park in Nara after lunch.", "cloudy 18°", "info")
SUN_INDOOR = card("Sun · Indoor Kyoto", "Nishiki Market, Kyoto National Museum, a tea ceremony in Gion.", "indoor", "ok")
ops = lambda *items: "\n".join(json.dumps(o) for o in items)  # noqa: E731
SCRIPT = [
    ops({"op": "add", "path": "/ui", "value": {"type": "Column", "children": [
            {"type": "Text", "props": {"text": "Kyoto · 3-day plan", "variant": "h1"}},
            {"type": "Row", "children": []},
            {"type": "Metric", "props": {"label": "Estimated budget", "value": "…"}}]}},
        {"op": "add", "path": "/ui/children/1/children/-", "value": SAT},
        {"op": "add", "path": "/ui/children/1/children/-", "value": {"type": "Map", "props": {"place": "Arashiyama"}}},
        {"op": "add", "path": "/ui/children/1/children/-", "value": MON},
        {"op": "replace", "path": "/ui/children/2/props/value", "value": "¥62,000"}),
    ops({"op": "add", "path": "/ui/children/1/children/1", "value": SUN}),
    ops({"op": "replace", "path": "/ui/children/1/children/1", "value": SUN_INDOOR},
        {"op": "replace", "path": "/ui/children/2/props/value", "value": "¥66,500"}),
]
MODELS: dict = {}


def apply_model_patches(text: str, state: dict, errors: list):
    """Apply, validate, then emit: an operation that breaks the tree never reaches the page."""
    for line in filter(str.strip, text.splitlines()):
        op = json.loads(line)
        try:
            candidate = agui.apply_patch(state, [op])
        except (KeyError, IndexError, ValueError) as exc:
            errors.append(f"{op['path']}: cannot apply ({exc})")
            continue
        problems = validate_tree(candidate.get("ui"))
        if problems:
            errors.extend(problems)
            continue
        state.clear()
        state.update(candidate)
        yield agui.state_delta([op])


def handle(name: str, body: dict):
    if name != "run":
        raise ValueError(f"unknown api {name}")
    run = agui.parse_run_input(body)
    model = MODELS.setdefault(run["threadId"], get_model(SCRIPT))
    state = run["state"]                        # the frontend sends the state it holds
    yield agui.run_started(run["threadId"], run["runId"])
    yield agui.state_snapshot(state)
    messages = [{"role": "system", "content": SYSTEM + "\nCurrent state: " + json.dumps(state)},
                {"role": "user", "content": agui.last_user_text(run)}]
    for attempt in range(2):
        yield agui.step("edit_ui")
        errors: list = []
        yield from apply_model_patches(model.complete(messages)["content"], state, errors)
        yield agui.step("edit_ui", started=False)
        if not errors:
            break
        yield agui.custom("validation_errors", errors)
        messages.append({"role": "user", "content": "These operations were rejected: " + "; ".join(errors)})
    summary = "Plan ready." if "rain_plan" not in agui.last_user_text(run) else "Sunday is now an indoor day."
    yield from agui.text_message(summary)
    yield agui.run_finished(run["threadId"], run["runId"])


DEMO_STEPS = [{"screenshot": "demo_before.png"}, {"click": "button[data-action='rain_plan']"}]
