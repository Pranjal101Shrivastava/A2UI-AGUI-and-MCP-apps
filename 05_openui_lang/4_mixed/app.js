import { HTML_ARTIFACT, PRIMITIVES } from "../openui.mjs";
import { startOpenUIPage } from "../client.mjs";

startOpenUIPage({
  mode: "mixed",
  title: "Primitives for the plan, one HtmlArtifact for the week",
  blurb: "Everything is a catalog primitive except the week grid. Adding an elective re-assigns five names, including the artifact.",
  prompt: "Help me finish my spring plan: I have CMPE 280 and 281",
}, { components: { ...PRIMITIVES, ...HTML_ARTIFACT } });
