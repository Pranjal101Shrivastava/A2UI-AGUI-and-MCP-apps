// The web surface of the harness. Left: the agent's steps. Right: the UI the
// agent asked for. The same events also feed the terminal surface (terminal.py).
import { renderComponent as c, renderElementMap } from "../shared/js/catalog.mjs";
import { shell } from "../shared/js/page.mjs";
import { mountSandbox } from "../shared/js/sandbox.mjs";
import { call } from "../shared/js/transport.mjs";

export function startHarnessPage(config, widgets = {}) {
  const page = shell({ tech: "Harness", ...config });
  page.stage.innerHTML = `<div class="h-grid"><ol class="h-steps"></ol><div class="h-surface"></div></div>`;
  const steps = page.stage.querySelector(".h-steps");
  const surface = page.stage.querySelector(".h-surface");
  const panels = new Map();                         // one panel per component name / kind, replaced on update
  const ctx = { onAction: (name) => act(name) };

  const place = (key, node) => {
    if (panels.has(key)) panels.get(key).replaceWith(node);
    else surface.append(node);
    panels.set(key, node);
  };
  const step = (html) => steps.appendChild(Object.assign(document.createElement("li"), { innerHTML: html }));
  const esc = (s) => String(s).replace(/[&<>]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[ch]);

  function onEvent(e) {
    page.log(e.type, e);
    if (e.type === "TOOL_CALL") step(`<code>${esc(e.name)}</code> <span class="c-muted">${esc(JSON.stringify(e.args)).slice(0, 70)}</span>`);
    if (e.type === "TOOL_RESULT") steps.lastElementChild?.insertAdjacentHTML("beforeend", e.ok ? " ✓" : ` ✗ <span class="c-muted">${esc(e.summary)}</span>`);
    if (e.type === "TEXT") step(`<b>assistant</b> ${esc(e.text)}`);
    if (e.type === "PAUSED") step(`⏸ <i>${esc(e.request)}</i>`);
    if (e.type !== "UI") return;
    if (e.kind === "component") place(e.component, widgets[e.component]?.(e.props, ctx) ?? c("Text", { text: e.component }));
    if (e.kind === "spec") place(e.slot || "spec", renderElementMap(e.spec, ctx));
    if (e.kind === "html") {
      const box = c("Card", { title: e.title || "render_html" }, []);
      mountSandbox(box, e.html, { height: e.height || 260, onMessage: (type, p) => type === "action" && act(p.name) });
      place(e.slot || "html", box);
    }
  }

  async function act(name) {
    page.log("action →", name);
    page.status(`action ${name}…`);
    await call("action", { name }, onEvent);
    page.status(`action ${name} handled`);
    page.done();
  }
  page.onRun(async (prompt) => {
    steps.replaceChildren();
    surface.replaceChildren();
    panels.clear();
    page.status("agent running…");
    await call("run", { prompt }, onEvent);
    page.status("run finished");
    page.done();
  });
  return page;
}
