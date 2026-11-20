// The page side shared by the OpenUI Lang codelabs. The server streams program
// text; the page re-parses after every completed line and repaints. An action
// returns more lines, and a re-assigned name replaces that part of the UI.
import { shell } from "../shared/js/page.mjs";
import { call } from "../shared/js/transport.mjs";
import { countPending, parseProgram, renderNode, resolve } from "./openui.mjs";

export function startOpenUIPage(config, { components, widgets = {} }) {
  const page = shell({ tech: "OpenUI Lang", ...config });
  page.stage.innerHTML = `<div class="oui-view"></div><details class="oui-src" open><summary>program</summary><pre></pre></details>`;
  const view = page.stage.querySelector(".oui-view");
  const source = page.stage.querySelector(".oui-src pre");
  let program = "";
  let paintedLines = -1;
  const ctx = {
    onAction: (name, context) => act(name, context),
    onSandboxMessage: (type, p) => type === "action" && act(p.name, p.context),
  };

  function paint(partial) {
    const complete = partial ? program.slice(0, program.lastIndexOf("\n") + 1) : program;
    source.textContent = program;
    const lines = complete.split("\n").length;
    if (lines === paintedLines) return;                    // nothing new to parse yet
    paintedLines = lines;
    const { statements, errors } = parseProgram(complete);
    const tree = resolve(statements, components);
    view.replaceChildren(renderNode(tree, ctx, widgets));
    config.onPaint?.({ statements, tree, pending: countPending(tree), errors });
  }

  const onEvent = (e) => {
    if (e.type === "trace") return page.log("trace", e.text);
    if (e.type === "chunk") {
      program += e.text;
      paint(true);
    }
    if (e.type === "end") {
      page.log("program", `${program.split("\n").filter(Boolean).length} lines received`);
      paint(false);
    }
  };
  async function act(name, context = {}) {
    page.log("action →", { name, context });
    page.status(`action ${name}…`);
    if (!program.endsWith("\n")) program += "\n";
    await call("action", { name, context }, onEvent);
    page.status(`action ${name} handled`);
    page.done();
  }
  page.onRun(async (prompt) => {
    program = "";
    paintedLines = -1;
    page.status("streaming…");
    await call("run", { prompt }, onEvent);
    page.status("rendered");
    page.done();
  });
  return page;
}
