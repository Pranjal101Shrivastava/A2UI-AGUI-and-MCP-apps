// POST to the codelab's agent and read the answer.
//
// * text/event-stream: each `data:` line is parsed and handed to onEvent as it arrives.
// * application/json: the whole object is handed to onEvent once.
//
// When no server answers (the page is opened from a static host), the call is
// served from ./recording.json, which the demo runner wrote from a real run.
// The page code is the same in both cases; only the source of events changes.
let recording = null;
const used = new Set();
export const mode = { replay: false, onReplay: null };

async function replay(api, body, onEvent) {
  if (!mode.replay) {
    mode.replay = true;
    mode.onReplay?.();
  }
  recording ??= await fetch("recording.json").then((r) => r.json());
  const index = recording.findIndex(
    (entry, i) => !used.has(i) && entry.api === api && (entry.method ?? "") === (body?.method ?? ""),
  );
  if (index < 0) throw new Error(`no recorded response for ${api}`);
  used.add(index);
  const entry = recording[index];
  if (entry.json !== undefined) {
    onEvent(entry.json);
    return entry.json;
  }
  for (const event of entry.events) {
    await new Promise((r) => setTimeout(r, 25));
    onEvent(event);
  }
  return entry.events;
}

export async function call(api, body, onEvent = () => {}) {
  let response;
  if (!mode.replay) {
    try {
      response = await fetch(`api/${api}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body ?? {}),
      });
    } catch {
      response = null;
    }
  }
  if (!response || !response.ok) return replay(api, body, onEvent);

  if (!(response.headers.get("Content-Type") || "").includes("event-stream")) {
    const json = await response.json();
    onEvent(json);
    return json;
  }
  const events = [];
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let cut;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const frame = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      const data = frame.split("\n").filter((l) => l.startsWith("data: ")).map((l) => l.slice(6)).join("\n");
      if (!data) continue;
      const event = JSON.parse(data);
      events.push(event);
      onEvent(event);
    }
  }
  return events;
}
