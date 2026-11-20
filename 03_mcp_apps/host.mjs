// A minimal MCP Apps host: a chat page that connects to an MCP server, lets its
// model pick a tool, and mounts the tool's ui:// resource in a sandboxed iframe.
// Every message between the app and the server passes through this file.
import { shell } from "../shared/js/page.mjs";
import { call } from "../shared/js/transport.mjs";

class McpClient {
  constructor(log) {
    this.log = log;
    this.nextId = 0;
  }

  async request(method, params = {}) {
    this.log("host → server", `${method} ${JSON.stringify(params).slice(0, 120)}`);
    const response = await call("mcp", { jsonrpc: "2.0", id: ++this.nextId, method, params });
    if (response.error) throw new Error(response.error.message);
    return response.result;
  }

  notify(method, params = {}) {
    this.log("host → server", method);
    return call("mcp", { jsonrpc: "2.0", method, params });
  }
}

// The host decides what the app may load: a CSP built from the resource's declared domains.
export function cspFor(meta) {
  const connect = meta?.ui?.csp?.connectDomains?.join(" ") || "'none'";
  return `default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; ` +
    `connect-src ${connect}; frame-src 'self' about: data:`;
}

const withCsp = (html, csp) =>
  html.replace(/<head>/i, `<head><meta http-equiv="Content-Security-Policy" content="${csp}">`);

export function startHost(config) {
  const page = shell({ tech: "MCP Apps", ...config });
  page.stage.innerHTML = `<div class="ag-chat"></div><div class="mcp-apps"></div>`;
  const chat = page.stage.querySelector(".ag-chat");
  const apps = page.stage.querySelector(".mcp-apps");
  const client = new McpClient(page.log);
  const bridge = (direction, text) => {           // app <-> host traffic, also printed by the demo runner
    page.log(direction, text);
    console.log(`[genux] ${direction.padEnd(12)} ${text}`);
  };
  const messages = [];
  let tools = [];

  const say = (role, text) => {
    const b = document.createElement("div");
    b.className = role === "user" ? "ag-bubble mcp-user" : "ag-bubble";
    b.textContent = text;
    chat.append(b);
    messages.push({ role, content: text });
  };

  async function connect() {
    const init = await client.request("initialize", { protocolVersion: "2025-06-18", clientInfo: { name: "genux-host" },
      capabilities: { extensions: { "io.modelcontextprotocol/ui": { mimeTypes: ["text/html;profile=mcp-app"] } } } });
    await client.notify("notifications/initialized");
    tools = (await client.request("tools/list")).tools;
    page.log("host", `connected to ${init.serverInfo.name}: ${tools.map((t) => t.name).join(", ")}`);
  }

  // One chat turn: the host's model sees only tools the model may use (not app-only ones).
  async function turn(text) {
    say("user", text);
    const modelTools = tools.filter((t) => !(t._meta?.ui?.visibility || ["model"]).every((v) => v === "app"));
    const reply = await call("chat", { messages, tools: modelTools.map((t) => t.name) });
    if (reply.text) say("assistant", reply.text);
    if (!reply.toolCall) return page.done();
    const tool = tools.find((t) => t.name === reply.toolCall.name);
    const result = await client.request("tools/call", { name: tool.name, arguments: reply.toolCall.arguments });
    const uri = tool._meta?.ui?.resourceUri;
    if (!uri) return page.done();                              // a plain tool: text only
    const resource = (await client.request("resources/read", { uri })).contents[0];
    mount(resource, reply.toolCall.arguments, result);
  }

  function mount(resource, args, result) {
    const frame = document.createElement("iframe");
    frame.setAttribute("sandbox", "allow-scripts");              // opaque origin: no cookies, no parent DOM
    frame.className = "c-sandbox mcp-frame";
    const csp = cspFor(resource._meta);
    frame.srcdoc = withCsp(resource.text, csp);
    bridge("host", `mount ${resource.uri} (${resource.mimeType}) in iframe sandbox="allow-scripts"`);
    apps.replaceChildren(frame);

    const toView = (msg) => {
      bridge("host → view", msg.method || `response #${msg.id}`);
      frame.contentWindow.postMessage(msg, "*");
    };
    const respond = (id, result) => toView({ jsonrpc: "2.0", id, result });
    const fail = (id, message) => toView({ jsonrpc: "2.0", id, error: { code: -32000, message } });

    window.addEventListener("message", async (event) => {
      if (event.source !== frame.contentWindow) return;          // only this app
      const msg = event.data;
      if (!msg || msg.jsonrpc !== "2.0" || !msg.method) return;
      bridge("view → host", `${msg.method} ${msg.params ? JSON.stringify(msg.params).slice(0, 90) : ""}`);
      switch (msg.method) {
        case "ui/initialize":
          return respond(msg.id, { protocolVersion: "2026-01-26", hostInfo: { name: "genux-host", version: "1.0.0" },
            hostCapabilities: { serverTools: {}, message: {} }, hostContext: { theme: "light", displayMode: "inline" } });
        case "ui/notifications/initialized":
          toView({ jsonrpc: "2.0", method: "ui/notifications/tool-input", params: { arguments: args } });
          toView({ jsonrpc: "2.0", method: "ui/notifications/tool-result", params: result });
          return setTimeout(() => page.done(), 300);
        case "ui/notifications/size-changed":
          frame.style.height = `${Math.min(900, msg.params.height + 8)}px`;
          return;
        case "tools/call": {                                      // proxied, and only to this server's tools
          if (!tools.some((t) => t.name === msg.params.name)) return fail(msg.id, `unknown tool ${msg.params.name}`);
          try {
            respond(msg.id, await client.request("tools/call", msg.params));
          } catch (err) {
            fail(msg.id, err.message);
          }
          return setTimeout(() => page.done(), 300);
        }
        case "ui/message":                                        // the app adds a user turn to the chat
          respond(msg.id, {});
          return turn(msg.params.content.text);
        default:
          return msg.id !== undefined && fail(msg.id, `method not supported: ${msg.method}`);
      }
    });
  }

  page.onRun(async (prompt) => {
    page.status("running…");
    if (!tools.length) await connect();
    await turn(prompt);
    page.status(`${messages.length} chat messages`);
  });
  return page;
}
