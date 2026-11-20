"""MCP Apps, open-ended mode: the server's model writes the entire app.

``design_weather_widget`` asks the server-side model for a complete HTML
document, including its own postMessage JSON-RPC code. The server checks it
against the content policy, retries once with the errors, and stores it as
the content of ``ui://weather/generated.html``. The host then reads that
resource and mounts it like any other MCP App, behind the same sandbox and CSP.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]

import weather  # noqa: E402
from mcp import McpServer, result  # noqa: E402
from shared.llm import get_model, tool  # noqa: E402
from shared.sandbox import check_html  # noqa: E402

PROMPT = "Design me a moody little weather widget for Seattle"
VIEW = "ui://weather/generated.html"
SYSTEM = """Write ONE complete HTML document for an MCP App. Inline CSS and JS only, no external URLs.
Talk to the host with JSON-RPC 2.0 over parent.postMessage: request ui/initialize first, then send the
notification ui/notifications/initialized. Use ui/message to add a user turn to the chat."""

WIDGET = """<!doctype html>
<html><head><meta charset="utf-8"><title>seattle-widget</title>
<style>
 body{margin:0;font:14px system-ui;color:#e8eefc}
 .w{position:relative;overflow:hidden;padding:20px 22px;border-radius:14px;
    background:linear-gradient(170deg,#1e293b,#334155 55%,#475569)}
 .drop{position:absolute;top:-20px;width:2px;height:16px;background:#93c5fd88;animation:fall 0.9s linear infinite}
 @keyframes fall{to{transform:translateY(260px)}}
 .city{font-size:13px;letter-spacing:.2em;text-transform:uppercase;color:#93c5fd}
 .now{font:200 64px/1 system-ui;margin:6px 0} .now small{font-size:20px;color:#cbd5e1}
 .row{display:flex;gap:10px;margin:14px 0}.d{flex:1;background:#ffffff14;border-radius:10px;padding:8px;text-align:center}
 button{position:relative;font:600 13px system-ui;padding:9px 14px;border:0;border-radius:99px;background:#93c5fd;color:#0f172a;cursor:pointer}
</style></head>
<body><div class="w" id="w">
 <div class="city">Seattle · this weekend</div>
 <div class="now">12°<small> rain, 7° tonight</small></div>
 <div class="row"><div class="d">Fri<br>🌧<br>12° / 7°</div><div class="d">Sat<br>🌦<br>14° / 8°</div><div class="d">Sun<br>☁<br>16° / 9°</div></div>
 <button id="outfit">What should I wear?</button>
</div>
<script>
 for (let i = 0; i < 28; i++) {
   const d = document.createElement("i"); d.className = "drop";
   d.style.left = (i * 37 % 100) + "%"; d.style.animationDelay = (i % 9) / 10 + "s";
   document.getElementById("w").prepend(d);
 }
 let id = 0;
 const rpc = (method, params) => parent.postMessage({jsonrpc: "2.0", id: ++id, method, params}, "*");
 const note = (method, params) => parent.postMessage({jsonrpc: "2.0", method, params}, "*");
 addEventListener("message", (e) => {
   if (e.source === parent && e.data && e.data.id === 1 && e.data.result) {
     note("ui/notifications/initialized", {});
     note("ui/notifications/size-changed", {width: 600, height: document.documentElement.scrollHeight});
   }
 });
 rpc("ui/initialize", {protocolVersion: "2026-01-26", appInfo: {name: "seattle-widget", version: "1"}, appCapabilities: {}});
 document.getElementById("outfit").onclick = () =>
   rpc("ui/message", {role: "user", content: {type: "text", text: "What should I wear in Seattle on Saturday?"}});
</script></body></html>"""

# Attempt 1 pulls a web font from a CDN; the policy refuses it and the model retries.
SERVER_SCRIPT = [WIDGET.replace("<style>", '<link rel="stylesheet" href="https://fonts.example.com/inter.css"><style>', 1),
                 WIDGET]
STATE = {"html": "<!doctype html><html><head><title>empty</title></head><body>Nothing generated yet.</body></html>",
         "model": get_model(SERVER_SCRIPT)}
server = McpServer("weather-open-ended")


def design_weather_widget(city: str, mood: str = "") -> dict:
    rows = weather.forecast(city, 3)
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Forecast {json.dumps(rows)}. Mood: {mood}"}]
    rejected = []
    for attempt in range(2):
        html = STATE["model"].complete(messages)["content"]
        problems = check_html(html)
        if not problems:
            STATE["html"] = html                       # becomes the ui:// resource's content
            return result(f"Generated a {len(html)}-character widget for {city}.",
                          {"attempts": attempt + 1, "rejected": rejected})
        rejected.append(problems)
        messages.append({"role": "user", "content": "Rejected by the content policy: " + "; ".join(problems)})
    return {**result("Could not produce HTML that passes the content policy."), "isError": True}


server.tool("design_weather_widget", "Design a custom weather widget for a city.",
            {"properties": {"city": {"type": "string"}, "mood": {"type": "string"}}, "required": ["city"]},
            design_weather_widget, ui=VIEW)
server.resource(VIEW, "generated_widget", lambda: STATE["html"])

HOST_SCRIPT = [
    {"content": "I asked the weather server to design one.", "tool_calls": [
        {"name": "design_weather_widget", "arguments": {"city": "Seattle", "mood": "moody, rainy"}}]},
    {"content": "Saturday has showers and 8-14°C: a light waterproof jacket over a sweater, and boots.", "tool_calls": []},
]
HOST: dict = {}


def chat(body: dict) -> dict:
    if len(body["messages"]) == 1:
        HOST["model"] = get_model(HOST_SCRIPT)
        STATE["model"] = get_model(SERVER_SCRIPT)
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


DEMO_STEPS = [{"screenshot": "demo_before.png"}, {"frame": "iframe.mcp-frame", "click": "#outfit"}]
