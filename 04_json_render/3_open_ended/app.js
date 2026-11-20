import { mountSandbox } from "../../shared/js/sandbox.mjs";
import { startJsonRenderPage } from "../client.mjs";
import { buildHtml } from "../open-html.mjs";

startJsonRenderPage({
  mode: "open-ended",
  title: "Still JSON, but the vocabulary is open",
  blurb: "Element types are HTML tags with inline CSS, so the model can design anything. The page builds escaped markup from the spec and sandboxes it.",
  prompt: "Design a poster-style recap of the coffee cart's week",
}, {
  draw(spec, stage, ctx) {
    if (!spec.root) return;
    const box = document.createElement("div");
    box.className = "c-generated";
    stage.replaceChildren(box);
    mountSandbox(box, buildHtml(spec), { height: 380, onMessage: ctx.onSandboxMessage });
  },
});
