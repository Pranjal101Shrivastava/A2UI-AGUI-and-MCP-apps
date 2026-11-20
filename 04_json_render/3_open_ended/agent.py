"""json-render, open-ended mode: still JSON, but no catalog: element types are HTML tags.

The model may use any layout and any inline CSS, so it can design a poster no
catalog component describes. The vocabulary is open; the structure is not:
the server allows only safe tags and the props ``style``, ``text``, ``action``
and ``label``, and blocks CSS that can load resources. The page builds the
markup itself (escaping text) and shows it in a sandboxed iframe.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import cart  # noqa: E402
import jsonrender  # noqa: E402
from shared.llm import approx_tokens, get_model  # noqa: E402

PROMPT = "Design a poster-style recap of the coffee cart's week"
SYSTEM = ("Write one JSON spec {root, elements:{id:{type, props, children}}}. type is an HTML tag "
          f"({', '.join(sorted(jsonrender.OPEN_TAGS))}). props: style (camelCase CSS object), text, action, label. "
          "No event handlers, no URLs.")

top = max(cart.CUPS)
day = lambda d, c: {"type": "div", "props": {"text": f"{d} {c}", "style": {  # noqa: E731
    "flex": "1", "height": f"{40 + c}px", "display": "flex", "alignItems": "flex-end", "justifyContent": "center",
    "paddingBottom": "6px", "borderRadius": "8px", "font": "600 12px system-ui",
    "background": f"rgba(255,247,237,{0.25 + 0.6 * c / top:.2f})", "color": "#451a03"}}}
POSTER = {"root": "poster", "elements": {
    "poster": {"type": "section", "props": {"style": {
        "background": "linear-gradient(135deg,#78350f,#b45309 60%,#f59e0b)", "color": "#fff7ed", "padding": "22px 24px",
        "borderRadius": "16px", "fontFamily": "Georgia, serif"}},
        "children": ["kicker", "headline", "heat", "line", "quote", "share"]},
    "kicker": {"type": "small", "props": {"text": "WEEK 47 · CAMPUS COFFEE CART", "style": {"letterSpacing": "0.2em", "opacity": "0.8"}}},
    "headline": {"type": "h1", "props": {"text": f"{sum(cart.CUPS)} cups. Friday stole the show.",
                                         "style": {"fontSize": "30px", "margin": "6px 0 14px"}}},
    "heat": {"type": "div", "props": {"style": {"display": "flex", "gap": "6px", "alignItems": "flex-end"}},
             "children": [f"d{i}" for i in range(5)]},
    **{f"d{i}": day(d, c) for i, (d, c) in enumerate(zip(cart.DAYS, cart.CUPS))},
    "line": {"type": "p", "props": {"text": "Latte led with 142 cups; cold brew climbed to 118.", "style": {"marginTop": "14px"}}},
    "quote": {"type": "p", "props": {"text": "“Cold brew before the 10 a.m. lectures is now a ritual.”",
                                     "style": {"fontStyle": "italic", "opacity": "0.85"}}},
    "share": {"type": "button", "props": {"text": "Share this recap", "action": "share_recap", "style": {
        "border": "0", "borderRadius": "99px", "padding": "9px 16px", "background": "#fff7ed", "color": "#78350f",
        "font": "700 13px system-ui", "cursor": "pointer"}}},
}}
UNSAFE = json.loads(json.dumps(POSTER))
UNSAFE["elements"]["share"]["props"]["onclick"] = "fetch('/steal')"
UNSAFE["elements"]["poster"]["props"]["style"]["backgroundImage"] = "url(https://cdn.example.com/beans.jpg)"
SCRIPT = [json.dumps(UNSAFE, ensure_ascii=False), json.dumps(POSTER, ensure_ascii=False)]
STATE: dict = {}


def run(prompt: str):
    STATE["model"] = model = get_model(SCRIPT)
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
    for attempt in range(2):
        spec = json.loads(model.complete(messages)["content"])
        errors = jsonrender.validate_open_spec(spec)
        if not errors:
            yield {"type": "spec", "spec": spec}
            return
        yield {"type": "trace", "text": f"attempt {attempt + 1} rejected: {'; '.join(errors)}"}
        messages.append({"role": "user", "content": "Fix: " + "; ".join(errors)})


def on_action(body: dict):
    yield {"type": "trace", "text": f"action {body['name']} from the sandbox"}
    if body["name"] == "share_recap":
        yield {"type": "patch", "op": {"op": "replace", "path": "/elements/share/props/text", "value": "Link copied ✓"}}


def handle(name: str, body: dict):
    if name == "run":
        return run(body.get("prompt", PROMPT))
    if name == "action":
        return on_action(body)
    raise ValueError(f"unknown api {name}")


def demo_notes() -> str:
    from shared.devserver import load_agent

    static = load_agent(HERE.parent / "1_static")
    declarative = load_agent(HERE.parent / "2_declarative")
    rows = [("static (show_view arguments)", json.dumps(static.SCRIPT[0]["tool_calls"][0]["arguments"])),
            ("declarative (catalog patches)", declarative.DASHBOARD),
            ("open-ended (HTML-tag spec)", SCRIPT[1])]
    return "model output size for one screen (tokens, estimated):\n" + \
        "\n".join(f"  {name:<32} {approx_tokens(text):>5}" for name, text in rows)


DEMO_STEPS = [{"screenshot": "demo_before.png"}, {"frame": "iframe.c-sandbox", "click": "[data-action='share_recap']"}]
