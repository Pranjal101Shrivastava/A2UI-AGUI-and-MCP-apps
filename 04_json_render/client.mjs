// The page side shared by the json-render codelabs: keep one spec, change it by
// whole replacement ("spec") or by RFC 6902 operation ("patch"), redraw.
import { shell } from "../shared/js/page.mjs";
import { call } from "../shared/js/transport.mjs";
import { EMPTY, applyPatchLine, render } from "./json-render.mjs";

export function startJsonRenderPage(config, { draw } = {}) {
  const page = shell({ tech: "json-render", ...config });
  let spec = structuredClone(EMPTY);
  const ctx = { onAction: (name) => act(name), onSandboxMessage: (type, p) => type === "action" && act(p.name, p) };
  const paint = () => (draw ? draw(spec, page.stage, ctx) : page.stage.replaceChildren(render(spec, ctx)));

  const onEvent = (e) => {
    page.log(e.type, e.type === "patch" ? e.op : e.type === "spec" ? `${Object.keys(e.spec.elements).length} elements` : e);
    if (e.type === "spec") spec = e.spec;
    if (e.type === "patch") spec = applyPatchLine(spec, e.op);
    if (e.type === "spec" || e.type === "patch") paint();
    config.onEvent?.(e, spec);
  };
  async function act(name, payload = {}) {
    page.log("action →", { name, ...payload });
    page.status(`action ${name}…`);
    await call("action", { name, context: payload.context || {}, spec }, onEvent);
    page.status(`action ${name} handled`);
    page.done();
  }
  page.onRun(async (prompt) => {
    spec = structuredClone(EMPTY);
    page.status("running…");
    await call("run", { prompt }, onEvent);
    page.status("rendered");
    page.done();
  });
  return page;
}
