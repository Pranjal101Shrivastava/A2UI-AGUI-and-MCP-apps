import { startA2UIPage } from "../client.mjs";

startA2UIPage({
  mode: "mixed",
  title: "Catalog form plus one sandboxed map",
  blurb: "Basic-catalog components bound to the data model, and one HtmlFrame for the floor plan. Map clicks update the form through the server.",
  prompt: "Help me pick and book a study room for tomorrow 14:00",
});
