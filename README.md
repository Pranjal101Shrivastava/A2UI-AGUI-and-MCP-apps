# Generative UI codelabs: A2UI, AG-UI, MCP Apps, json-render, OpenUI Lang and harness integration

Six generative-UI technologies, each shown in four modes: **static**, **declarative**, **open-ended** and **mixed**. That makes 24 runnable codelabs. Each one has a server, a page, offline tests, a code walkthrough, and a recorded execution (wire transcript plus screenshots) produced by running it in a headless browser.

Everything runs offline with the Python standard library and plain browser JavaScript. There is no build step, no npm install and no API key.

## The idea in two decisions

Generative UI turns an agent's output into an interface. Two choices are independent:

1. **What may the model generate?** That is the *mode*:

   | Mode | The model... | The application... | Cost and risk |
   |---|---|---|---|
   | **static** | picks a pre-built component and fills its data | owns every component | smallest output, safest |
   | **declarative** | composes a layout from a catalog of components | validates against the catalog, renders | medium output, validated |
   | **open-ended** | writes markup (HTML, CSS, JS) | sandboxes it and polices behaviour | largest output, needs a sandbox |
   | **mixed** | composes from the catalog, plus *one* free-form region | validates the catalog part, sandboxes the region | the usual recommended default |

2. **How does the UI travel and render?** That is the *format* or *transport*: A2UI and json-render are UI description formats; OpenUI Lang is a compact UI language; AG-UI is an agent ↔ frontend event protocol; MCP Apps lets a third-party host show a tool's UI; a harness is the agent loop that produces all of it.

## The 24 codelabs

| Technology | static | declarative | open-ended | mixed |
|---|---|---|---|---|
| [01 · A2UI](01_a2ui/README.md) — book a study room | [pre-built surface, data-only updates](01_a2ui/1_static/README.md) | [model writes JSONL, line validation, correction loop](01_a2ui/2_declarative/README.md) | [custom `HtmlFrame` catalog, content policy](01_a2ui/3_open_ended/README.md) | [catalog form + sandboxed map driving the data model](01_a2ui/4_mixed/README.md) |
| [02 · AG-UI](02_ag_ui/README.md) — plan a Kyoto weekend | [tool-call renderers, streamed args](02_ag_ui/1_static/README.md) | [UI in shared state, JSON Patch deltas](02_ag_ui/2_declarative/README.md) | [`render_html` streamed after a policy check](02_ag_ui/3_open_ended/README.md) | [state UI + generated region + frontend-tool approval](02_ag_ui/4_mixed/README.md) |
| [03 · MCP Apps](03_mcp_apps/README.md) — weather in a host | [hand-written `ui://` app, host bridge](03_mcp_apps/1_static/README.md) | [server model's catalog spec, generic app](03_mcp_apps/2_declarative/README.md) | [server model writes the whole app](03_mcp_apps/3_open_ended/README.md) | [nested sandbox, app-only tool](03_mcp_apps/4_mixed/README.md) |
| [04 · json-render](04_json_render/README.md) — coffee cart sales | [registry specs, `$state` from app data](04_json_render/1_static/README.md) | [JSONL patch stream, first paint at 18%](04_json_render/2_declarative/README.md) | [open HTML-tag vocabulary, escaped builder](04_json_render/3_open_ended/README.md) | [`GeneratedView` heat map, patches, terminal renderer](04_json_render/4_mixed/README.md) |
| [05 · OpenUI Lang](05_openui_lang/README.md) — semester planner | [three pre-built widgets, statement updates](05_openui_lang/1_static/README.md) | [primitives, forward references, streaming](05_openui_lang/2_declarative/README.md) | [one `HtmlArtifact` statement](05_openui_lang/3_open_ended/README.md) | [primitives + one artifact, re-assigned names](05_openui_lang/4_mixed/README.md) |
| [06 · Harness](06_harness/README.md) — a coding agent fixes a bug | [`show_*` panels with real test data](06_harness/1_static/README.md) | [`render_ui`, errors as tool results](06_harness/2_declarative/README.md) | [`render_html` + terminal fallback](06_harness/3_open_ended/README.md) | [review card, generated diff, approval gate](06_harness/4_mixed/README.md) |

Read across a row to see one technology move from static to mixed. Read down a column to see one mode expressed in six technologies. [`index.html`](index.html) is a web page with the same grid, linking to every live page.

## Quick start

Python 3.10 or newer. Nothing to install for the codelabs themselves.

```bash
python serve.py
```

Open `http://127.0.0.1:8000/` and pick a codelab. Each page runs its prompt against the local server and shows a wire log of every message.

Run the offline tests (42 tests; they need `pytest`):

```bash
python -m pip install -r requirements.txt
```

```bash
python -m pytest -q
```

Re-record every execution (needs Playwright's Chromium: `python -m playwright install chromium`):

```bash
python run_all.py
```

Check that every code snippet in the READMEs exists in the file it names:

```bash
python check_snippets.py
```

## How execution is shown

Every codelab has a `demo.py`. It starts the server, opens the page in headless Chromium, performs the clicks a user would, and writes three files:

* `output.txt`: the wire transcript, with every request and every event or message, plus browser console lines and notes such as token comparisons. `run_all.py` copies it into the codelab's README under **Execution**.
* `demo.png` (and `demo_before.png`): screenshots before and after the interaction.
* `recording.json`: the same responses. When a page is opened from a static host with no server (for example GitHub Pages), `shared/js/transport.mjs` replays this recording instead, and the page shows "replaying a recorded run".

All 24 pages were checked both ways: live against `serve.py` and in replay mode from a plain static file server.

## What the measurements show

Model output for one screen, in tokens (estimated as characters / 4), from the recorded runs:

| Technology | static | declarative | open-ended |
|---|---:|---:|---:|
| A2UI | 32 | 300 | 407 |
| json-render | 42 | 433 | 704 |
| OpenUI Lang | 72 | 196 | 516 |

* Static is cheapest because the model writes data, not structure.
* OpenUI Lang's declarative program is less than half the size of json-render's for a comparable screen.
* Open-ended output is always the largest, and in OpenUI Lang one long escaped string also removes the benefit of streaming.
* Flat element maps stream: the json-render dashboard paints after 18% of its bytes, while a nested JSON tree can only be parsed at 100%.

These are illustrative counts for the scripted replies in this repository, not a benchmark of any model.

## The shared runtime

`shared/` holds the parts every codelab uses, so each codelab can focus on its protocol.

`shared/llm.py`: one model interface. `ScriptedModel` replays written replies (used by every demo and test). `LiveModel` calls any OpenAI-compatible endpoint when you opt in:

```python
def get_model(script: list, delay: float = 0.0):
    """Live model when explicitly enabled, otherwise a fresh scripted model."""
    if os.environ.get("GENUX_LIVE") == "1" and (os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY")):
        return LiveModel()
```

`shared/catalog.py`: one catalog definition used three ways: as prompt text, as a validator, and (in `shared/js/catalog.mjs`) as the renderers:

```python
def validate_props(component: str, props: dict, allowed: set[str] | None = None) -> list[str]:
    """Return a list of human-readable errors. An empty list means valid."""
```

Model-written HTML passes two layers. On the server, `shared/sandbox.py` refuses HTML that reaches for the network, navigates or reads storage.

In the browser, `shared/js/sandbox.mjs` mounts it in an iframe with an opaque origin and a no-network Content Security Policy, and accepts only allowed message types from that exact frame:

```js
    if (event.source !== frame.contentWindow) return;        // only this frame
    const msg = event.data || {};
    if (msg.source !== "genux-sandbox" || !ALLOWED_TYPES.has(msg.type)) return;
```

`shared/devserver.py`: one standard-library server. `POST <codelab>/api/<name>` calls that codelab's `agent.handle(name, body)`; a generator becomes a Server-Sent Events stream:

```python
            for event in result:
                entry["events"].append(event)
                self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
                self.wfile.flush()
```

## Using a real model

The recorded runs use scripted replies so they are repeatable and free. To try a live OpenAI-compatible model instead:

```bash
GENUX_LIVE=1 API_KEY=your-key MODEL=gpt-4.1-mini python serve.py
```

The prompts in each `agent.py` describe the catalog and rules to the model, and every model output still goes through the same validators and sandboxes. The recorded outputs in this repository were not produced with a live model, and a live model will not follow the scripted correction steps exactly.

## Repository layout

```text
shared/                 model adapter, catalog, sandbox, JSON Patch, spec validator, dev server, demo runner
  js/                   catalog renderers, sandbox, transport (with replay), page shell, JSON Patch
01_a2ui/                a2ui.py / a2ui.mjs (envelopes, validator, surface) + 4 codelabs
02_ag_ui/               agui.py / agui.mjs (events, RunAgentInput, session) + 4 codelabs
03_mcp_apps/            mcp.py (server), host.mjs (host + bridge), app-bridge.js + 4 codelabs
04_json_render/         jsonrender.py / json-render.mjs (spec, $state, patches, terminal renderer) + 4 codelabs
05_openui_lang/         openui.py / openui.mjs (tokenizer, parser, resolver) + 4 codelabs
06_harness/             harness.py (agent loop), ui_tools.py, terminal.py, toy_project/ + 4 codelabs
  N_mode/               agent.py, app.js, index.html, demo.py, README.md, output.txt, recording.json, demo*.png
serve.py  run_all.py  check_snippets.py  index.html
```

## Credits

The course structure follows the generative UI section of [dlmastery/simple-coding-harness](https://github.com/dlmastery/simple-coding-harness/tree/main/genui) (MIT): the static, declarative, open-ended and hybrid progression, and the same set of technologies. The code here is a separate, dependency-free implementation organised as a technology × mode grid. Protocol details follow the public A2UI v0.9, AG-UI, MCP Apps (`io.modelcontextprotocol/ui`), json-render and OpenUI Lang documentation.
