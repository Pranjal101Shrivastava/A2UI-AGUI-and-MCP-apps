import { startA2UIPage } from "../client.mjs";

startA2UIPage({
  mode: "open-ended",
  title: "The model writes the HTML",
  blurb: "A custom catalog with one component, HtmlFrame. The model writes the whole floor plan; the page sandboxes it.",
  prompt: "Show me a map of the study rooms so I can pick one",
});
