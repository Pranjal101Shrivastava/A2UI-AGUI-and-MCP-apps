import { startJsonRenderPage } from "../client.mjs";

let firstPaint = null;
let patches = 0;
const started = performance.now();
startJsonRenderPage({
  mode: "declarative",
  title: "The model streams the spec as patches",
  blurb: "Each JSONL line is one RFC 6902 operation on a flat element map. The page repaints after every line, so the dashboard grows while the model writes.",
  prompt: "Build me a dashboard of this week's coffee cart sales",
  onEvent(e, spec) {
    if (e.type !== "patch") return;
    patches += 1;
    const ms = Math.round(performance.now() - started);
    if (firstPaint === null && spec.root && Object.keys(spec.elements).length >= 2) {
      firstPaint = ms;
      console.log(`[genux] first paint after ${patches} patches (${ms} ms since page load)`);
    }
    if (e.op.path === "/state/items") console.log(`[genux] dashboard complete after ${patches} patches (${ms} ms since page load)`);
  },
});
