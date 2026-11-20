// The page side shared by the four AG-UI codelabs: a chat column for streamed
// text, a canvas for generated UI, and an AgentSession that keeps the thread.
import { shell } from "../shared/js/page.mjs";
import { AgentSession } from "./agui.mjs";

export function startAgUiPage(config, setup) {
  const page = shell({ tech: "AG-UI", ...config });
  page.stage.innerHTML = `<div class="ag-chat"></div><div class="ag-canvas"></div>`;
  const chat = page.stage.querySelector(".ag-chat");
  const canvas = page.stage.querySelector(".ag-canvas");
  let bubble = null;

  const session = new AgentSession({
    onEvent: (e) => page.log("event", e),
    onText: (text, done) => {
      bubble ??= chat.appendChild(Object.assign(document.createElement("div"), { className: "ag-bubble" }));
      bubble.textContent = text;
      if (done) bubble = null;
    },
  });

  // Every follow-up (a button, a sandbox click, an approval) is just another run on the same thread.
  const send = async (messages) => {
    page.status("running…");
    await session.run(messages);
    page.status(`thread ${session.threadId} · ${session.messages.length} messages`);
    page.done();
  };
  setup({ session, page, canvas, send });
  page.onRun((prompt) => send([{ id: `user_${Date.now()}`, role: "user", content: prompt }]));
  return page;
}
