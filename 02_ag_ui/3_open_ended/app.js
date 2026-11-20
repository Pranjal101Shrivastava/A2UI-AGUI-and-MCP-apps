import { mountSandbox } from "../../shared/js/sandbox.mjs";
import { partialJSON } from "../agui.mjs";
import { startAgUiPage } from "../client.mjs";

startAgUiPage({
  mode: "open-ended",
  title: "The agent streams a whole HTML page",
  blurb: "No catalog. render_html arguments stream as TOOL_CALL_ARGS; the page sandboxes the HTML when the call ends.",
  prompt: "Make me a beautiful one-page plan for a Kyoto weekend",
}, ({ session, canvas, send }) => {
  const progress = document.createElement("div");
  progress.className = "c-muted";
  session.onToolCall = (callInfo, phase) => {
    if (callInfo.name !== "render_html") return;
    if (phase === "start") canvas.replaceChildren(progress);
    if (phase === "args") progress.textContent = `receiving HTML… ${callInfo.raw.length} chars`;
    if (phase === "end") {
      const { html } = partialJSON(callInfo.raw);
      const box = document.createElement("div");
      box.className = "c-generated";
      canvas.replaceChildren(box);
      mountSandbox(box, html, {
        height: 380,
        onMessage: (type, payload) => {
          if (type === "action") send([{ id: `user_${Date.now()}`, role: "user", content: `[action] ${payload.name}` }]);
        },
      });
      console.log(`[genux] mounted ${html.length} chars of model HTML in a sandbox`);
    }
  };
});
