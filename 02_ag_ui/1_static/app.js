import { renderComponent as c } from "../../shared/js/catalog.mjs";
import { partialJSON } from "../agui.mjs";
import { startAgUiPage } from "../client.mjs";

startAgUiPage({
  mode: "static",
  title: "Tool calls drawn by pre-built components",
  blurb: "The agent only calls show_flight and show_weather. The page owns one renderer per tool and fills it while the arguments stream.",
  prompt: "I fly to Kyoto on Friday on JL 5. What should I expect?",
}, ({ session, canvas, send }) => {
  // The frontend's registry: tool name -> hand-written component. Nothing else can appear.
  const renderers = {
    show_flight: (a) => c("Card", { title: `✈ Flight ${a.flight ?? "…"}` }, [
      c("Row", {}, [c("Metric", { label: "Route", value: a.route ?? "…" }),
        c("Metric", { label: "Departs", value: a.departs ?? "…" }), c("Metric", { label: "Gate", value: a.gate ?? "…" })]),
      c("Badge", { text: a.status ?? "…", tone: a.status === "On time" ? "ok" : "warn" }),
      c("Button", { label: "Refresh status", action: "refresh_flight" }, [], {
        onAction: () => send([{ id: `user_${Date.now()}`, role: "user", content: `Refresh the status of ${a.flight}` }]) }),
    ]),
    show_weather: (a) => c("Card", { title: `☀ ${a.city ?? "…"} forecast` }, [
      c("Row", {}, (a.days ?? []).filter((d) => d && d.day).map((d) =>
        c("Metric", { label: d.day, value: `${d.high ?? "…"}° / ${d.low ?? "…"}°`, delta: d.sky }))),
    ]),
  };
  const cards = new Map(); // one slot per tool *name*, so a refresh replaces the card
  session.onToolCall = (callInfo, phase) => {
    const render = renderers[callInfo.name];
    if (!render) return;
    const args = partialJSON(callInfo.raw) || {};
    const node = render(args);
    if (phase === "end") console.log(`[genux] rendered ${callInfo.name} from ${callInfo.raw.length} streamed chars`);
    if (cards.has(callInfo.name)) cards.get(callInfo.name).replaceWith(node);
    else canvas.append(node);
    cards.set(callInfo.name, node);
  };
});
