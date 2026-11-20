"""Offline tests for the four MCP Apps codelabs: the server over JSON-RPC, in process."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE)]

from mcp import APP_MIME  # noqa: E402
from shared.devserver import load_agent  # noqa: E402


def rpc(mode, method, params=None, rid=1):
    return load_agent(HERE / mode).handle("mcp", {"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})


def test_initialize_advertises_the_ui_extension():
    caps = rpc("1_static", "initialize")["result"]["capabilities"]
    assert "io.modelcontextprotocol/ui" in caps["extensions"]


def test_tool_links_to_an_app_resource():
    tool = rpc("1_static", "tools/list")["result"]["tools"][0]
    uri = tool["_meta"]["ui"]["resourceUri"]
    content = rpc("1_static", "resources/read", {"uri": uri})["result"]["contents"][0]
    assert uri.startswith("ui://") and content["mimeType"] == APP_MIME and "mcpApp" in content["text"]


def test_static_result_has_text_for_the_model_and_data_for_the_view():
    res = rpc("1_static", "tools/call", {"name": "get_forecast", "arguments": {"city": "Seattle", "units": "F"}})["result"]
    assert res["content"][0]["text"].startswith("Seattle:") and res["structuredContent"]["days"][0]["high"] == 54


def test_unknown_tool_is_a_json_rpc_error():
    assert rpc("1_static", "tools/call", {"name": "rm_rf", "arguments": {}})["error"]["code"] == -32602


def test_declarative_spec_is_validated_and_actions_are_server_defined():
    agent = load_agent(HERE / "2_declarative")
    agent.chat({"messages": [{"role": "user", "content": "x"}], "tools": ["weather_dashboard"]})  # reset scripted models
    res = rpc("2_declarative", "tools/call", {"name": "weather_dashboard", "arguments": {"city": "Seattle"}})["result"]
    spec, actions = res["structuredContent"]["spec"], res["structuredContent"]["actions"]
    buttons = [e for e in spec["elements"].values() if e["type"] == "Button"]
    assert buttons and all(b["props"]["action"] in actions for b in buttons)


def test_open_ended_retries_after_the_policy_and_serves_the_result_as_the_resource():
    agent = load_agent(HERE / "3_open_ended")
    agent.chat({"messages": [{"role": "user", "content": "x"}], "tools": ["design_weather_widget"]})
    res = rpc("3_open_ended", "tools/call", {"name": "design_weather_widget", "arguments": {"city": "Seattle"}})["result"]
    assert res["structuredContent"]["attempts"] == 2
    html = rpc("3_open_ended", "resources/read", {"uri": "ui://weather/generated.html"})["result"]["contents"][0]["text"]
    assert "ui/initialize" in html and "https://" not in html


def test_mixed_hides_app_only_tools_from_the_model():
    tools = {t["name"]: t for t in rpc("4_mixed", "tools/list")["result"]["tools"]}
    assert tools["refresh_radar"]["_meta"]["ui"]["visibility"] == ["app"]
    agent = load_agent(HERE / "4_mixed")
    reply = agent.chat({"messages": [{"role": "user", "content": "studio"}], "tools": ["weather_studio"]})
    assert reply["toolCall"]["name"] == "weather_studio"
    res = rpc("4_mixed", "tools/call", {"name": "weather_studio", "arguments": {"city": "Seattle"}})["result"]
    kinds = [e["type"] for e in res["structuredContent"]["spec"]["elements"].values()]
    assert kinds.count("GeneratedView") == 1
