// Mount model-written HTML in a sandboxed iframe.
//
// sandbox="allow-scripts" without allow-same-origin gives the frame an opaque
// origin: no cookies, no storage, no access to this page's DOM. The CSP meta
// tag removes the network. The only way out is postMessage, and the parent
// accepts only messages from this exact frame with an allowed type.
export const CSP =
  "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:; font-src data:";

const BRIDGE = `<script>
  window.genux = {
    send(type, payload) { parent.postMessage({ source: "genux-sandbox", type, payload }, "*"); }
  };
  addEventListener("load", () => genux.send("resize", { height: document.documentElement.scrollHeight }));
</script>`;

export const ALLOWED_TYPES = new Set(["action", "resize", "log"]);

export function wrapHtml(html) {
  return `<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${CSP}">
<style>body{margin:0;font:14px system-ui,sans-serif;color:#1f2430}</style>${BRIDGE}</head>
<body>${html}</body></html>`;
}

export function mountSandbox(container, html, { height = 220, onMessage } = {}) {
  const frame = document.createElement("iframe");
  frame.setAttribute("sandbox", "allow-scripts");
  frame.className = "c-sandbox";
  frame.style.height = `${height}px`;
  frame.srcdoc = wrapHtml(html);
  const listener = (event) => {
    if (event.source !== frame.contentWindow) return;        // only this frame
    const msg = event.data || {};
    if (msg.source !== "genux-sandbox" || !ALLOWED_TYPES.has(msg.type)) return;
    if (msg.type === "resize") frame.style.height = `${Math.min(600, Math.max(height, msg.payload.height))}px`;
    else onMessage?.(msg.type, msg.payload);
  };
  window.addEventListener("message", listener);
  container.append(frame);
  return frame;
}
