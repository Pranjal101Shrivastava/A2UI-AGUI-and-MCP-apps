"""MCP Apps, mixed mode: a catalog spec with one model-written region, two sandboxes deep.

``weather_studio`` returns a catalog element map (declarative). One element
is a ``GeneratedView`` holding model-written HTML for an animated radar
(open-ended). The view renders the catalog and puts that region in a nested
sandboxed iframe, inside the host's sandbox. The "Refresh radar" button calls
``refresh_radar``, an app-only tool: the view may call it through the host,
but the host never offers it to the model.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import views  # noqa: E402
import weather  # noqa: E402
from mcp import McpServer, result  # noqa: E402
from shared.llm import get_model, tool  # noqa: E402
from shared.spec import validate_element_map  # noqa: E402

PROMPT = "Open the weather studio for Seattle"
VIEW = "ui://genux/catalog-view.html"


def radar(minute: int) -> str:
    """Model-written HTML for the radar region (the scripted model's answer)."""
    return f"""<style>body{{background:#0b1220;margin:0}}svg{{width:100%;height:170px}}
.sweep{{transform-origin:110px 85px;animation:s 3s linear infinite}}@keyframes s{{to{{transform:rotate(360deg)}}}}
.cell{{fill:#38bdf8;opacity:.55;animation:p 2s ease-in-out infinite alternate}}@keyframes p{{to{{opacity:.15}}}}
text{{fill:#94a3b8;font:11px system-ui}}</style>
<svg viewBox="0 0 320 170"><circle cx="110" cy="85" r="70" fill="none" stroke="#1e3a5f"/>
<circle cx="110" cy="85" r="40" fill="none" stroke="#1e3a5f"/>
<path class="sweep" d="M110 85 L180 85 A70 70 0 0 0 160 36 Z" fill="#22d3ee33"/>
<ellipse class="cell" cx="{90 + minute % 30}" cy="60" rx="22" ry="12"/><ellipse class="cell" cx="{130 + minute % 20}" cy="105" rx="16" ry="9"/>
<text x="200" y="40">Seattle radar</text><text x="200" y="58">updated :{minute:02d}</text>
<text x="200" y="76">rain cells moving east</text></svg>"""


def studio_spec(minute: int) -> str:
    rows = weather.forecast("Seattle", 3)
    return json.dumps({"root": "page", "elements": {
        "page": {"type": "Column", "children": ["title", "body", "refresh"]},
        "title": {"type": "Text", "props": {"text": "Seattle weather studio", "variant": "h2"}},
        "body": {"type": "Row", "children": ["left", "radar"]},
        "left": {"type": "Column", "children": ["now", "rain", "days"]},
        "now": {"type": "Metric", "props": {"label": "Now", "value": "12°C", "delta": "-2° vs yesterday"}},
        "rain": {"type": "Progress", "props": {"label": "Chance of rain", "value": 80}},
        "days": {"type": "Table", "props": {"columns": ["Day", "Sky", "High"],
                 "rows": [[r["day"], r["icon"], r["high"]] for r in rows]}},
        "radar": {"type": "GeneratedView", "props": {"title": "Radar", "html": radar(minute), "height": 190}},
        "refresh": {"type": "Button", "props": {"label": "Refresh radar", "action": "refresh_radar", "variant": "primary"}},
    }})


SERVER_SCRIPT = [studio_spec(5), studio_spec(20)]
STATE = {"model": get_model(SERVER_SCRIPT)}
server = McpServer("weather-mixed")


def _studio(city: str, reason: str) -> dict:
    spec = json.loads(STATE["model"].complete([{"role": "user", "content": f"{reason} for {city}"}])["content"])
    errors = validate_element_map(spec)
    if sum(e["type"] == "GeneratedView" for e in spec["elements"].values()) > 1:
        errors.append("at most one GeneratedView")
    if errors:
        return {**result("invalid studio spec: " + "; ".join(errors)), "isError": True}
    actions = {"refresh_radar": {"tool": "refresh_radar", "arguments": {"city": city}}}
    return result(f"Weather studio for {city}: 12°C now, 80% chance of rain.", {"spec": spec, "actions": actions})


server.tool("weather_studio", "Open an interactive weather studio for a city.",
            {"properties": {"city": {"type": "string"}}, "required": ["city"]},
            lambda city: _studio(city, "Build the studio"), ui=VIEW)
server.tool("refresh_radar", "Re-draw the radar region. Called by the app, not the model.",
            {"properties": {"city": {"type": "string"}}, "required": ["city"]},
            lambda city: _studio(city, "Refresh the radar"), app_only=True)
server.resource(VIEW, "catalog_view", lambda: views.build(HERE.parent / "catalog-view.html", with_catalog=True))

HOST_SCRIPT = [{"content": "Opening the studio.", "tool_calls": [{"name": "weather_studio", "arguments": {"city": "Seattle"}}]}]
HOST: dict = {}


def chat(body: dict) -> dict:
    if len(body["messages"]) == 1:
        HOST["model"] = get_model(HOST_SCRIPT)
        STATE["model"] = get_model(SERVER_SCRIPT)
    assert "refresh_radar" not in body["tools"], "the host must not offer app-only tools to the model"
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


DEMO_STEPS = [{"screenshot": "demo_before.png"}, {"frame": "iframe.mcp-frame", "click": "button[data-action='refresh_radar']"}]
