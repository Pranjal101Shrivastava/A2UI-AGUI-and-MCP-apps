import { startA2UIPage } from "../client.mjs";

startA2UIPage({
  mode: "declarative",
  title: "The model writes the surface",
  blurb: "The model emits A2UI JSONL from the basic catalog. Each line is validated and streamed; errors go back to the model.",
  prompt: "I need to book room B12 for 4 people tomorrow afternoon",
});
