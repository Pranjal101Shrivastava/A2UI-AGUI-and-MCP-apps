import { startHarnessPage } from "../client.mjs";

startHarnessPage({
  mode: "open-ended",
  title: "render_html: the agent designs its own report",
  blurb: "The agent writes free HTML for the web surface and a text fallback for the terminal. The button inside asks the harness to re-run the tests.",
  prompt: "The tests in my project fail. Find the bug, fix it, and show me what you did.",
});
