import { HTML_ARTIFACT } from "../openui.mjs";
import { startOpenUIPage } from "../client.mjs";

startOpenUIPage({
  mode: "open-ended",
  title: "One HtmlArtifact holds the whole UI",
  blurb: "The program is a single statement whose string argument is a complete HTML page. It renders only when the line is complete.",
  prompt: "Show my spring timetable as a weekly calendar",
  onPaint({ statements }) {
    if (statements.size) console.log(`[genux] painted once the line was complete: ${statements.size} statement`);
  },
}, { components: HTML_ARTIFACT });
