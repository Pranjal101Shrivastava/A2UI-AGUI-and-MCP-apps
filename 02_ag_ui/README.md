# 02 · AG-UI: one event stream between agent and page

AG-UI ([docs.ag-ui.com](https://docs.ag-ui.com/)) is a protocol for the connection between an agent and a frontend. It does not describe UI. It carries typed events over a stream (Server-Sent Events here), and any UI format can ride on it.

| Event family | Events | Used for |
|---|---|---|
| lifecycle | `RUN_STARTED`, `RUN_FINISHED`, `RUN_ERROR`, `STEP_STARTED`, `STEP_FINISHED` | one run of the agent |
| text | `TEXT_MESSAGE_START`, `TEXT_MESSAGE_CONTENT`, `TEXT_MESSAGE_END` | streamed assistant text |
| tools | `TOOL_CALL_START`, `TOOL_CALL_ARGS`, `TOOL_CALL_END`, `TOOL_CALL_RESULT` | tool calls, with arguments streamed |
| state | `STATE_SNAPSHOT`, `STATE_DELTA` (RFC 6902 JSON Patch) | state shared by agent and page |
| other | `CUSTOM` | anything application-specific |

The page starts a run by POSTing a `RunAgentInput`: `threadId`, `runId`, `messages`, `state`, `tools`, `context`. Every follow-up, whether a button, an approval or a new prompt, is another run on the same thread.

## The four codelabs

| Mode | Codelab | Where the UI comes from | AG-UI feature it shows |
|---|---|---|---|
| static | [1_static](1_static/README.md) | pre-built components keyed by tool name | streamed `TOOL_CALL_ARGS`, partial JSON |
| declarative | [2_declarative](2_declarative/README.md) | a catalog tree in `state.ui` | `STATE_SNAPSHOT` / `STATE_DELTA`, state round trip |
| open-ended | [3_open_ended](3_open_ended/README.md) | model HTML in a `render_html` tool call | policy check before streaming |
| mixed | [4_mixed](4_mixed/README.md) | catalog state, one `GeneratedView`, a frontend tool | human in the loop with a frontend tool |

The scenario is a weekend trip to Kyoto.

## The shared protocol code

`agui.py` builds events. A tool call becomes START, a series of ARGS deltas, and END, as a model produces it:

```python
def tool_call(name: str, args: dict, call_id: str | None = None, chunk: int = 40):
    """A tool call whose JSON arguments stream in pieces, as a model produces them."""
    cid = call_id or _id("call")
    raw = json.dumps(args, ensure_ascii=False)
    yield {"type": "TOOL_CALL_START", "toolCallId": cid, "toolCallName": name}
```

`agui.py` also checks the pairing rules every run must follow; the tests use it:

```python
    if not events or events[0]["type"] != "RUN_STARTED":
        errors.append("first event must be RUN_STARTED")
```

`agui.mjs` is the client. `AgentSession` keeps the thread's messages and state across runs and dispatches each event by type:

```js
        case "STATE_SNAPSHOT": this.state = e.snapshot; this.onState?.(this.state); break;
        case "STATE_DELTA": this.state = applyPatch(this.state, e.delta); this.onState?.(this.state); break;
```

## Run

```bash
python -m pytest -q 02_ag_ui
```

```bash
python run_all.py 02_ag_ui
```
