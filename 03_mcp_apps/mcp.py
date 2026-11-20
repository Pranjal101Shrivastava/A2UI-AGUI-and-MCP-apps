"""A minimal MCP server with the MCP Apps extension, standard library only.

MCP is JSON-RPC 2.0. This server answers ``initialize``, ``tools/list``,
``tools/call``, ``resources/list`` and ``resources/read``. The MCP Apps
extension adds two things:

* a resource whose MIME type is ``text/html;profile=mcp-app`` and whose URI
  starts with ``ui://``: the app's HTML;
* ``_meta.ui.resourceUri`` on a tool: "when this tool runs, show that app".

A tool with ``_meta.ui.visibility == ["app"]`` is callable by the app but is
hidden from the model.
"""
from __future__ import annotations

from typing import Callable

APP_MIME = "text/html;profile=mcp-app"
PROTOCOL = "2025-06-18"
UI_EXTENSION = "io.modelcontextprotocol/ui"


class McpServer:
    def __init__(self, name: str, version: str = "1.0.0") -> None:
        self.info = {"name": name, "version": version}
        self.tools: dict[str, dict] = {}
        self.resources: dict[str, dict] = {}

    def tool(self, name: str, description: str, schema: dict, handler: Callable, ui: str | None = None,
             app_only: bool = False) -> None:
        meta = {}
        if ui:
            meta["ui"] = {"resourceUri": ui}
        if app_only:
            meta.setdefault("ui", {})["visibility"] = ["app"]
        self.tools[name] = {"name": name, "description": description,
                            "inputSchema": {"type": "object", **schema}, "_meta": meta, "handler": handler}

    def resource(self, uri: str, name: str, read: Callable[[], str], csp: dict | None = None) -> None:
        self.resources[uri] = {"uri": uri, "name": name, "mimeType": APP_MIME, "read": read,
                               "_meta": {"ui": {"csp": csp or {"connectDomains": [], "resourceDomains": []},
                                                "prefersBorder": True}}}

    # ---- JSON-RPC ------------------------------------------------------------
    def handle(self, rpc: dict) -> dict:
        method, params, rid = rpc.get("method"), rpc.get("params") or {}, rpc.get("id")
        if rid is None:  # a notification: no response object
            return {}
        try:
            result = self._dispatch(method, params)
        except KeyError as exc:
            return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32602, "message": f"unknown {exc}"}}
        except Exception as exc:  # a tool error is still a JSON-RPC answer
            return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32000, "message": str(exc)}}
        return {"jsonrpc": "2.0", "id": rid, "result": result}

    def _dispatch(self, method: str, params: dict) -> dict:
        if method == "initialize":
            return {"protocolVersion": PROTOCOL, "serverInfo": self.info,
                    "capabilities": {"tools": {}, "resources": {}, "extensions": {UI_EXTENSION: {}}}}
        if method == "notifications/initialized":
            return {}
        if method == "tools/list":
            return {"tools": [{k: v for k, v in t.items() if k != "handler"} for t in self.tools.values()]}
        if method == "tools/call":
            tool = self.tools[params["name"]]
            return tool["handler"](**(params.get("arguments") or {}))
        if method == "resources/list":
            return {"resources": [{k: v for k, v in r.items() if k != "read"} for r in self.resources.values()]}
        if method == "resources/read":
            r = self.resources[params["uri"]]
            return {"contents": [{"uri": r["uri"], "mimeType": r["mimeType"], "text": r["read"](), "_meta": r["_meta"]}]}
        raise KeyError(f"method {method}")


def result(text: str, structured: dict | None = None) -> dict:
    """A CallToolResult: text for any host, structured content for the app."""
    out = {"content": [{"type": "text", "text": text}]}
    if structured is not None:
        out["structuredContent"] = structured
    return out
