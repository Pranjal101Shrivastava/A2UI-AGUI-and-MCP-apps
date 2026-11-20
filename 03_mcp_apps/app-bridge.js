// The app (view) side of MCP Apps: JSON-RPC 2.0 over postMessage to the host.
// The server inlines this file into every hand-written view it serves.
(() => {
  let next = 0;
  const pending = new Map();
  const handlers = {};
  const request = (method, params) => {
    const id = ++next;
    parent.postMessage({ jsonrpc: "2.0", id, method, params }, "*");
    return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
  };
  const notify = (method, params) => parent.postMessage({ jsonrpc: "2.0", method, params }, "*");
  addEventListener("message", (event) => {
    if (event.source !== parent) return;
    const msg = event.data;
    if (!msg || msg.jsonrpc !== "2.0") return;
    if (msg.id !== undefined && !msg.method) {          // a response to one of our requests
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p?.reject(msg.error); else p?.resolve(msg.result);
      return;
    }
    handlers[msg.method]?.(msg.params || {});           // a notification from the host
  });
  window.mcpApp = {
    request, notify,
    on: (method, fn) => (handlers[method] = fn),
    async connect() {
      const init = await request("ui/initialize", { protocolVersion: "2026-01-26",
        appInfo: { name: document.title || "app", version: "1.0.0" }, appCapabilities: {} });
      notify("ui/notifications/initialized", {});
      return init;
    },
    resized() {
      notify("ui/notifications/size-changed", { width: document.body.scrollWidth, height: document.documentElement.scrollHeight });
    },
    callTool: (name, args) => request("tools/call", { name, arguments: args }),
    say: (text) => request("ui/message", { role: "user", content: { type: "text", text } }),
  };
})();
