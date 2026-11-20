import { startHost } from "../host.mjs";

startHost({
  mode: "static",
  title: "A tool result shown by a pre-built app",
  blurb: "The MCP server links get_forecast to a hand-written ui:// view. The host mounts it in a sandbox and relays JSON-RPC.",
  prompt: "What's the weather in Seattle this weekend?",
});
