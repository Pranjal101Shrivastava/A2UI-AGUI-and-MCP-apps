// The page shell every codelab shares: a header, a prompt bar, the stage the
// generated UI is drawn into, and a wire log that shows every message.
import { mode } from "./transport.mjs";

const short = (value) => {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  return text.length > 220 ? `${text.slice(0, 217)}…` : text;
};

export function shell({ tech, mode: genMode, title, blurb, prompt }) {
  document.title = `${tech} · ${genMode}`;
  document.body.innerHTML = `
    <header class="p-head">
      <a class="p-home" href="../../index.html">GenUX codelabs</a>
      <span class="p-crumb">${tech}</span><span class="p-mode">${genMode}</span>
      <span class="p-replay" hidden>replaying a recorded run (no server)</span>
    </header>
    <main class="p-main">
      <h1 class="p-title">${title}</h1>
      <p class="p-blurb">${blurb}</p>
      <form class="p-prompt"><input name="prompt" value="${prompt.replace(/"/g, "&quot;")}"><button>Run</button></form>
      <div class="p-status">idle</div>
      <div class="p-stage" id="stage"></div>
      <details class="p-log" open><summary>wire log</summary><ol id="log"></ol></details>
    </main>`;
  mode.onReplay = () => (document.querySelector(".p-replay").hidden = false);
  const logList = document.getElementById("log");
  let runs = 0;
  let onRun = null;
  const api = {
    stage: document.getElementById("stage"),
    log(direction, value) {
      const li = document.createElement("li");
      li.innerHTML = `<b>${direction}</b> <code></code>`;
      li.querySelector("code").textContent = short(value);
      logList.append(li);
      li.scrollIntoView({ block: "nearest" });
    },
    status(text) {
      document.querySelector(".p-status").textContent = text;
    },
    done() {
      runs += 1;
      document.body.dataset.done = String(runs); // the demo runner waits on this
    },
    onRun(fn) {
      onRun = fn;
    },
  };
  document.querySelector(".p-prompt").onsubmit = (e) => {
    e.preventDefault();
    onRun?.(e.target.prompt.value);
  };
  queueMicrotask(() => onRun?.(prompt)); // run once on load
  return api;
}
