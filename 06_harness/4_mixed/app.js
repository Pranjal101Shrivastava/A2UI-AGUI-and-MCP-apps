import { startHarnessPage } from "../client.mjs";

startHarnessPage({
  mode: "mixed",
  title: "Review card, generated diff, approval gate",
  blurb: "render_ui shows a catalog review card with one sandboxed diff view. write_file pauses the run until you approve.",
  prompt: "The tests in my project fail. Find the bug, fix it, and show me what you did.",
});
