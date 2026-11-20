import { startA2UIPage } from "../client.mjs";

startA2UIPage({
  mode: "static",
  title: "Pick a pre-built room card",
  blurb: "The surface structure is a hand-written template. The model only chooses a room and fills the data model.",
  prompt: "Find me a quiet study room for 4 people tomorrow afternoon",
});
