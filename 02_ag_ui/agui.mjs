// The AG-UI client half: start a run, dispatch events by type, keep shared state.
import { call } from "../shared/js/transport.mjs";
import { applyPatch } from "../shared/js/json-patch.mjs";

export { applyPatch };

// Best-effort parse of a JSON prefix: close open strings, arrays and objects.
export function partialJSON(text) {
  const closers = [];
  let inString = false, escaped = false;
  for (const ch of text) {
    if (inString) {
      if (escaped) escaped = false;
      else if (ch === "\\") escaped = true;
      else if (ch === '"') inString = false;
      continue;
    }
    if (ch === '"') inString = true;
    else if (ch === "{") closers.push("}");
    else if (ch === "[") closers.push("]");
    else if (ch === "}" || ch === "]") closers.pop();
  }
  let candidate = text + (inString ? '"' : "");
  for (let i = 0; i < 3; i++) {
    try { return JSON.parse(candidate + [...closers].reverse().join("")); } catch { /* trim and retry */ }
    candidate = candidate.replace(/,?\s*("[^"]*"\s*:?\s*)?[^,{}\[\]]*$/, "");
  }
  return null;
}

// One agent session: thread id, message history and shared state survive across runs.
export class AgentSession {
  constructor({ onEvent, onState, onToolCall, onText }) {
    Object.assign(this, { onEvent, onState, onToolCall, onText });
    this.threadId = `thread_${Math.random().toString(16).slice(2, 10)}`;
    this.messages = [];
    this.state = {};
    this.tools = [];
  }

  async run(newMessages = []) {
    this.messages.push(...newMessages);
    const input = { threadId: this.threadId, runId: `run_${Date.now()}`, messages: this.messages,
      state: this.state, tools: this.tools, context: [], forwardedProps: {} };
    const calls = new Map();
    const texts = new Map();
    await call("run", input, (e) => {
      this.onEvent?.(e);
      switch (e.type) {
        case "TEXT_MESSAGE_START": texts.set(e.messageId, ""); break;
        case "TEXT_MESSAGE_CONTENT": texts.set(e.messageId, texts.get(e.messageId) + e.delta);
          this.onText?.(texts.get(e.messageId), false); break;
        case "TEXT_MESSAGE_END": this.messages.push({ id: e.messageId, role: "assistant", content: texts.get(e.messageId) });
          this.onText?.(texts.get(e.messageId), true); break;
        case "TOOL_CALL_START": calls.set(e.toolCallId, { id: e.toolCallId, name: e.toolCallName, raw: "" });
          this.onToolCall?.(calls.get(e.toolCallId), "start"); break;
        case "TOOL_CALL_ARGS": calls.get(e.toolCallId).raw += e.delta;
          this.onToolCall?.(calls.get(e.toolCallId), "args"); break;
        case "TOOL_CALL_END": {
          const c = calls.get(e.toolCallId);
          this.messages.push({ id: `msg_${c.id}`, role: "assistant",
            toolCalls: [{ id: c.id, type: "function", function: { name: c.name, arguments: c.raw } }] });
          this.onToolCall?.(c, "end");
          break;
        }
        case "STATE_SNAPSHOT": this.state = e.snapshot; this.onState?.(this.state); break;
        case "STATE_DELTA": this.state = applyPatch(this.state, e.delta); this.onState?.(this.state); break;
      }
    });
  }
}
