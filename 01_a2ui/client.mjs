// The page side shared by the four A2UI codelabs. Each mode differs in what the
// agent generates; the client is the same: route envelopes, render, send actions.
import { shell } from "../shared/js/page.mjs";
import { call } from "../shared/js/transport.mjs";
import { SurfaceHost } from "./a2ui.mjs";

export function startA2UIPage(config) {
  const page = shell({ tech: "A2UI", ...config });

  const onMessage = (msg) => {
    if (msg.type === "trace") return page.log("trace", msg.text);
    page.log("server → client", msg);
    host.handle(msg);
  };

  const host = new SurfaceHost(page.stage, async (actionMessage) => {
    page.log("client → server", actionMessage);
    page.status(`action ${actionMessage.action.name}…`);
    await call("action", actionMessage, onMessage);
    page.status(`action ${actionMessage.action.name} handled`);
    page.done();
  });

  page.onRun(async (prompt) => {
    page.status("running…");
    host.surfaces.clear();
    await call("run", { prompt }, onMessage);
    page.status("rendered");
    page.done();
  });
  return page;
}
