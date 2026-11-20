import { renderTree } from "../../shared/js/catalog.mjs";
import { startAgUiPage } from "../client.mjs";

startAgUiPage({
  mode: "declarative",
  title: "UI as shared state, edited by JSON Patch",
  blurb: "The agent patches state.ui, a tree of catalog components. Every STATE_DELTA re-renders it; a button sends the state back in the next run.",
  prompt: "Plan a 3-day weekend in Kyoto for me",
}, ({ session, canvas, send }) => {
  const ctx = {
    onAction: (name) => send([{ id: `user_${Date.now()}`, role: "user", content: `[action] ${name}` }]),
  };
  session.onState = (state) => canvas.replaceChildren(renderTree(state.ui, ctx));
  session.onEvent = ((log) => (e) => {
    log(e);
    if (e.type === "CUSTOM" && e.name === "validation_errors") console.log(`[genux] server rejected: ${e.value.join("; ")}`);
  })(session.onEvent);
});
