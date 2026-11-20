"""MCP Apps, static mode: a tool whose result is shown by a pre-built view.

``server`` is the MCP server: one tool, ``get_forecast``, linked by
``_meta.ui.resourceUri`` to ``ui://weather/forecast.html``, a view written by
hand. The tool returns text for the model and ``structuredContent`` for the
view. ``chat`` is the host's model: it only picks the tool and its arguments.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import views  # noqa: E402
import weather  # noqa: E402
from mcp import McpServer, result  # noqa: E402
from shared.llm import get_model, tool  # noqa: E402

PROMPT = "What's the weather in Seattle this weekend?"
VIEW = "ui://weather/forecast.html"

server = McpServer("weather-static")


def get_forecast(city: str, days: int = 3, units: str = "C") -> dict:
    rows = weather.forecast(city, days, units)
    return result(weather.as_text(city, rows, units), {"city": city, "units": units, "days": rows})


server.tool("get_forecast", "Forecast for a city (Seattle or San Jose).",
            {"properties": {"city": {"type": "string"}, "days": {"type": "integer"}, "units": {"enum": ["C", "F"]}},
             "required": ["city"]}, get_forecast, ui=VIEW)
server.resource(VIEW, "forecast_view", lambda: views.build(HERE / "forecast.html"))

# The host's model: first turn picks the tool; the second answers the app's ui/message.
HOST_SCRIPT = [
    {"content": "Here is the Seattle forecast.", "tool_calls": [
        {"name": "get_forecast", "arguments": {"city": "Seattle", "days": 3}}]},
    {"content": "Rain on Friday and showers on Saturday: pack a waterproof shell, a warm layer for 7°C mornings, "
                "and shoes that can get wet.", "tool_calls": []},
]
HOST: dict = {}


def chat(body: dict) -> dict:
    if len(body["messages"]) == 1:
        HOST["model"] = get_model(HOST_SCRIPT)                   # a new conversation
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


DEMO_STEPS = [
    {"frame": "iframe.mcp-frame", "click": "#f"},
    {"screenshot": "demo_before.png"},
    {"frame": "iframe.mcp-frame", "click": "#ask"},
]
