# 04 · json-render: one JSON spec, a catalog, patches and two renderers

json-render ([github.com/vercel-labs/json-render](https://github.com/vercel-labs/json-render)) describes a UI as a JSON **spec**: a flat element map plus a state object. A **catalog** defines what may appear; a renderer per target draws it.

```json
{"root": "page",
 "elements": {"page": {"type": "Column", "children": ["kpi"]},
              "kpi":  {"type": "Metric", "props": {"label": "Revenue", "value": {"$state": "/revenue"}}}},
 "state": {"revenue": "$1,632"}}
```

* `{"$state": "/pointer"}` binds a prop to state, so data can change without touching the layout.
* The spec can be sent whole, or streamed as JSONL RFC 6902 patches against an empty spec. A flat map streams well: each element is self-contained, and a missing child is a placeholder until it lands.
* The same spec can be drawn by more than one renderer. These codelabs use the shared DOM catalog and a terminal renderer.

These codelabs implement the spec format directly in dependency-free Python and JavaScript, so every step is visible. The shapes follow the library: flat elements, `$state` bindings, JSONL patch streams, named actions.

## The four codelabs

| Mode | Codelab | What the model writes | Update path |
|---|---|---|---|
| static | [1_static](1_static/README.md) | a view name and two sentences | registry spec + app data; one state patch |
| declarative | [2_declarative](2_declarative/README.md) | JSONL patches, streamed | page repaints after every line |
| open-ended | [3_open_ended](3_open_ended/README.md) | a spec whose types are HTML tags with inline CSS | escaped markup in a sandbox |
| mixed | [4_mixed](4_mixed/README.md) | catalog spec + one `GeneratedView` | patches from an action; terminal renderer too |

The scenario is a campus coffee cart's weekly sales.

## The shared code

`jsonrender.py` resolves bindings and applies patch lines:

```python
def resolve(spec: dict) -> dict:
    """A copy of the spec with every $state binding replaced by its value."""
```

```python
def apply_line(spec: dict, line: str) -> dict:
    """Apply one JSONL patch line to the spec."""
    return apply_patch(spec, [json.loads(line)])
```

`json-render.mjs` is the browser half. It resolves `$state` and renders the element map with the shared catalog:

```js
      props[k] = v && typeof v === "object" && "$state" in v ? read(spec.state, v.$state) : v;
```

`client.mjs` keeps one spec per page and changes it by whole replacement (`spec` events) or by one operation (`patch` events).

## Run

```bash
python -m pytest -q 04_json_render
```

```bash
python run_all.py 04_json_render
```
