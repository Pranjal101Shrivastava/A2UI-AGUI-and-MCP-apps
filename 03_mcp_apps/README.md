# 03 · MCP Apps: an interface that ships inside a tool result

MCP Apps ([overview](https://modelcontextprotocol.io/extensions/apps/overview), extension id `io.modelcontextprotocol/ui`) lets an MCP server give a tool an interface that a *host* (a chat client you do not control) can show. Three parties, two channels:

```text
MCP server  <── JSON-RPC (tools/call, resources/read) ──>  host  <── JSON-RPC over postMessage ──>  app (sandboxed iframe)
mcp.py + agent.py                                           host.mjs                                 the ui:// resource
```

* The server declares a resource with a `ui://` URI and MIME type `text/html;profile=mcp-app`.
* A tool points at it with `_meta.ui.resourceUri`. Its result carries `content` (text, for the model) and `structuredContent` (data, for the app).
* The host calls the tool, reads the resource, mounts the HTML in a sandboxed iframe with a Content Security Policy, and relays messages: `ui/initialize`, `ui/notifications/tool-input`, `ui/notifications/tool-result`, `tools/call`, `ui/message`, `ui/notifications/size-changed`.
* A tool with `_meta.ui.visibility: ["app"]` may be called by the app but is never offered to the model.

The app never talks to the server directly. Every call passes through the host, which can log it, refuse it or ask the user.

## The four codelabs

| Mode | Codelab | Who writes the app? | Interaction |
|---|---|---|---|
| static | [1_static](1_static/README.md) | a developer: `forecast.html` | °C/°F via `tools/call`, "Ask what to pack" via `ui/message` |
| declarative | [2_declarative](2_declarative/README.md) | the server's model writes a catalog spec; a generic view draws it | buttons map to server-defined tool calls |
| open-ended | [3_open_ended](3_open_ended/README.md) | the server's model writes the whole HTML app | `ui/message` from model-written bridge code |
| mixed | [4_mixed](4_mixed/README.md) | catalog spec + one model-written region in a nested sandbox | an app-only tool, hidden from the model |

## The shared code

`mcp.py` is a minimal MCP server, standard library only. A tool can carry a UI link, and a tool can be app-only:

```python
        if ui:
            meta["ui"] = {"resourceUri": ui}
        if app_only:
            meta.setdefault("ui", {})["visibility"] = ["app"]
```

`host.mjs` is the host. It mounts the resource with a CSP built from what the resource declared, and answers the app's JSON-RPC:

```js
    frame.setAttribute("sandbox", "allow-scripts");              // opaque origin: no cookies, no parent DOM
```

`host.mjs` also proxies the app's tool calls, but only to tools this server listed:

```js
        case "tools/call": {                                      // proxied, and only to this server's tools
          if (!tools.some((t) => t.name === msg.params.name)) return fail(msg.id, `unknown tool ${msg.params.name}`);
```

`app-bridge.js` is the app side of the bridge, inlined by `views.py` into every hand-written view:

```js
    async connect() {
      const init = await request("ui/initialize", { protocolVersion: "2026-01-26",
```

Each codelab's `agent.py` contains two separate roles: `server` (the MCP server) and `chat` (the host's model, which only chooses a tool). In a real deployment they run in different processes owned by different parties.

## Run

```bash
python -m pytest -q 03_mcp_apps
```

```bash
python run_all.py 03_mcp_apps
```
