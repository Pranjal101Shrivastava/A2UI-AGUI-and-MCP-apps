import { startHarnessPage } from "../client.mjs";

startHarnessPage({
  mode: "declarative",
  title: "render_ui: the agent composes its report",
  blurb: "One tool, render_ui, takes a catalog spec. An invalid spec is refused and the error returns to the model as a tool result.",
  prompt: "The tests in my project fail. Find the bug, fix it, and show me what you did.",
});
