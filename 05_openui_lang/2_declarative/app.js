import { PRIMITIVES } from "../openui.mjs";
import { startOpenUIPage } from "../client.mjs";

let last = -1;
startOpenUIPage({
  mode: "declarative",
  title: "Compose primitives, stream with forward references",
  blurb: "root arrives first and names parts defined later. Each completed line is parsed; unknown names are placeholders until their line lands.",
  prompt: "Plan a 9-unit evening-friendly spring semester for me",
  onPaint({ statements, pending }) {
    if (pending !== last) console.log(`[genux] ${statements.size} statement(s) parsed, ${pending} placeholder(s) on screen`);
    last = pending;
  },
}, { components: PRIMITIVES });
