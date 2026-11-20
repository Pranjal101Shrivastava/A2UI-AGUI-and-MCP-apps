# 06 · Harness integration: generative UI inside a coding-agent loop

A coding-agent harness is the loop around a model: send the conversation, run the tool calls it makes, append the results, repeat until it answers in text. These codelabs add generative UI to that loop **as tools**. A UI tool's "execution" is to validate the request and emit a UI event. The same events drive two surfaces: a web page and the terminal.

```text
            ┌──────────── harness.py: step_loop ────────────┐
prompt ──>  model ──> tool calls ──> coding tools (real files, real tests)
              ^                 └──> UI tools ──> UI events ──┬──> web surface   (client.mjs)
              └──── tool results (including UI errors) <─────┘   └──> terminal  (terminal.py)
```

The agent works on a temporary copy of `toy_project/`, a module with an off-by-one bug in `average()`. `run_tests` really runs `python -m unittest`, so the test numbers on screen are real.

## The four codelabs

| Mode | Codelab | UI tools | What it shows |
|---|---|---|---|
| static | [1_static](1_static/README.md) | `show_status`, `show_test_report`, `show_diff` | the model picks a panel; the harness fills it with real data |
| declarative | [2_declarative](2_declarative/README.md) | `render_ui(spec)` | an invalid spec is an error *result*, and the model corrects itself |
| open-ended | [3_open_ended](3_open_ended/README.md) | `render_html(html, fallback)` | free HTML for the web, a required text fallback for the terminal |
| mixed | [4_mixed](4_mixed/README.md) | `render_ui` with one `GeneratedView`, plus a gated `write_file` | the run pauses for approval and resumes on the user's click |

## The shared code

`harness.py`, the loop. A tool error becomes a tool result the model can read; a `Pause` stops the run and keeps the session:

```python
            try:
                output = s.tools[call["name"]].run(**call["arguments"])
                ok = not str(output).startswith("error:")
            except Pause as pause:
                s.pending = {"call": call, **pause.request}
```

`ui_tools.py`, the two generative UI tools any harness can offer:

```python
        if errors:
            return "error: the spec was not shown: " + "; ".join(errors)
        s.ui_events.append({"type": "UI", "kind": "spec", "slot": slot, "spec": spec})
```

`terminal.py` draws the same events as text. For specs it reuses the json-render terminal renderer from theme 04:

```python
        from jsonrender import render_terminal  # the json-render terminal renderer, reused
```

## Run

```bash
python -m pytest -q 06_harness
```

```bash
python run_all.py 06_harness
```
