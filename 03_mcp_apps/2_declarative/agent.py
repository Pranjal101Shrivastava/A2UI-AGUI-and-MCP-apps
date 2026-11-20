"""MCP Apps, declarative mode: the server's model writes a catalog spec, a generic view draws it.

``weather_dashboard`` asks the server-side model for an element map built
from the shared catalog. The server validates it (components, props, and
that every button names a known action) before returning it as
``structuredContent``. The view, ``ui://genux/catalog-view.html``, contains
no weather code at all: it renders any valid spec.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import views  # noqa: E402
import weather  # noqa: E402
from mcp import McpServer, result  # noqa: E402
from shared.catalog import prompt_text  # noqa: E402
from shared.llm import get_model, tool  # noqa: E402
from shared.spec import validate_element_map  # noqa: E402

PROMPT = "Give me a weather dashboard for Seattle"
VIEW = "ui://genux/catalog-view.html"
SYSTEM = "Design a dashboard as a JSON element map {root, elements:{id:{type, props, children}}}. " \
         "Buttons may use only the action names you are given. Components:\n" + prompt_text()


def _scripted_spec(city: str, days: int) -> str:
    """What the scripted server-side model answers for a given forecast."""
    rows = weather.forecast(city, days)
    wet = sum(r["sky"] in ("rain", "showers") for r in rows)
    other = 5 if days == 3 else 3
    return json.dumps({"root": "page", "elements": {
        "page": {"type": "Column", "children": ["title", "kpis", "chart", "table", "more"]},
        "title": {"type": "Text", "props": {"text": f"{city} · {days}-day outlook", "variant": "h2"}},
        "kpis": {"type": "Row", "children": ["hi", "lo", "wet"]},
        "hi": {"type": "Metric", "props": {"label": "Warmest", "value": f"{max(r['high'] for r in rows)}°C"}},
        "lo": {"type": "Metric", "props": {"label": "Coldest", "value": f"{min(r['low'] for r in rows)}°C"}},
        "wet": {"type": "Badge", "props": {"text": f"{wet} wet day(s)", "tone": "warn" if wet else "ok"}},
        "chart": {"type": "BarChart", "props": {"title": "Daily high °C", "labels": [r["day"] for r in rows],
                                                 "values": [r["high"] for r in rows]}},
        "table": {"type": "Table", "props": {"columns": ["Day", "Sky", "High", "Low"],
                  "rows": [[r["day"], f"{r['icon']} {r['sky']}", r["high"], r["low"]] for r in rows]}},
        "more": {"type": "Button", "props": {"label": f"Show {other} days", "action": f"show_{other}_days"}},
    }})


SERVER_SCRIPT = [_scripted_spec("Seattle", 3), _scripted_spec("Seattle", 5), _scripted_spec("Seattle", 3)]
SERVER_MODEL = {"model": get_model(SERVER_SCRIPT)}
server = McpServer("weather-declarative")


def weather_dashboard(city: str, days: int = 3) -> dict:
    rows = weather.forecast(city, days)
    actions = {f"show_{n}_days": {"tool": "weather_dashboard", "arguments": {"city": city, "days": n}} for n in (3, 5)}
    reply = SERVER_MODEL["model"].complete([
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Forecast: {json.dumps(rows)}. Action names: {list(actions)}"}])
    spec = json.loads(reply["content"])
    errors = validate_element_map(spec)
    errors += [f"unknown action {el['props']['action']!r}" for el in spec["elements"].values()
               if el["type"] == "Button" and el["props"]["action"] not in actions]
    if errors:
        return {**result("The dashboard spec was invalid: " + "; ".join(errors)), "isError": True}
    return result(weather.as_text(city, rows, "C"), {"spec": spec, "actions": actions})


server.tool("weather_dashboard", "A weather dashboard for a city (Seattle or San Jose).",
            {"properties": {"city": {"type": "string"}, "days": {"type": "integer"}}, "required": ["city"]},
            weather_dashboard, ui=VIEW)
server.resource(VIEW, "catalog_view", lambda: views.build(HERE.parent / "catalog-view.html", with_catalog=True))

HOST_SCRIPT = [{"content": "Here is a dashboard for Seattle.", "tool_calls": [
    {"name": "weather_dashboard", "arguments": {"city": "Seattle"}}]}]
HOST: dict = {}


def chat(body: dict) -> dict:
    if len(body["messages"]) == 1:
        HOST["model"] = get_model(HOST_SCRIPT)
        SERVER_MODEL["model"] = get_model(SERVER_SCRIPT)
    schemas = [tool(t, server.tools[t]["description"], server.tools[t]["inputSchema"]["properties"]) for t in body["tools"]]
    reply = HOST["model"].complete(body["messages"], schemas)
    call = reply["tool_calls"][0] if reply["tool_calls"] else None
    return {"text": reply["content"], "toolCall": call and {"name": call["name"], "arguments": call["arguments"]}}


def handle(name: str, body: dict):
    if name == "mcp":
        return server.handle(body)
    if name == "chat":
        return chat(body)
    raise ValueError(f"unknown api {name}")


DEMO_STEPS = [{"screenshot": "demo_before.png"}, {"frame": "iframe.mcp-frame", "click": "button[data-action='show_5_days']"}]
