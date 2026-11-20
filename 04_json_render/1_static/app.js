import { startJsonRenderPage } from "../client.mjs";

startJsonRenderPage({
  mode: "static",
  title: "Pick a pre-built spec, fill its state",
  blurb: "Two developer-written specs bind every number to $state. The model picks one and writes the title and highlight; the server fills the data.",
  prompt: "How did the coffee cart do this week?",
});
