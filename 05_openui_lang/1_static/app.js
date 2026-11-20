import { renderComponent as c } from "../../shared/js/catalog.mjs";
import { startOpenUIPage } from "../client.mjs";

// The three pre-built widgets. The program can call nothing else.
const widgets = {
  CourseList: (p, ctx, kids) => c("Column", {}, kids),
  CourseCard: (p, ctx) => {
    const button = c("Button", { label: p.enrolled ? "Enrolled ✓" : "Enroll", action: "enroll", variant: p.enrolled ? "default" : "primary" },
      [], { onAction: () => !p.enrolled && ctx.onAction("enroll", { code: p.code }) });
    button.dataset.code = p.code;
    return c("Card", { title: `${p.code} · ${p.title}` }, [
      c("Row", {}, [c("Metric", { label: "When", value: p.when }), c("Metric", { label: "Units", value: p.units }),
        c("Metric", { label: "Seats left", value: p.seats })]),
      c("Badge", { text: p.seats <= 2 ? "almost full" : "open", tone: p.seats <= 2 ? "warn" : "ok" }),
      button,
    ]);
  },
  ConflictAlert: (p) => c("Badge", { text: p.text, tone: p.tone || "info" }),
};

const components = { CourseList: ["children"], CourseCard: ["code", "title", "units", "when", "seats", "enrolled"],
  ConflictAlert: ["text", "tone"] };

startOpenUIPage({
  mode: "static",
  title: "A tiny language over three pre-built widgets",
  blurb: "The model writes OpenUI Lang, but may only call CourseList, CourseCard and ConflictAlert. Enroll sends new statements that replace two names.",
  prompt: "Which evening courses can I still get into this spring?",
}, { components, widgets });
