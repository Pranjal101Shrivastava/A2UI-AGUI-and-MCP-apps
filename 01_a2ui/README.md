# 01 · A2UI: structure and data as two streams

A2UI (Agent-to-UI, [a2ui.org](https://a2ui.org/)) is a declarative format for agent-generated interfaces. A **surface** is a flat list of components with ids, plus a JSON **data model**. The server sends four kinds of envelope; the client answers with one.

| Direction | Envelope | Purpose |
|---|---|---|
| server → client | `createSurface` | open a surface and name its catalog |
| server → client | `updateComponents` | add or replace components (structure) |
| server → client | `updateDataModel` | write JSON at a path (data) |
| server → client | `deleteSurface` | close a surface |
| client → server | `action` | a button or a sandbox click, with its context resolved from the data model |

The key idea: components *bind* to data with `{"path": "/room/name"}`. The server can change what is on screen by sending data only, without resending structure.

## The four codelabs

| Mode | Codelab | Who writes the components? | What changes after a click? |
|---|---|---|---|
| static | [1_static](1_static/README.md) | a developer (`room_card.jsonl`) | data only (`updateDataModel`) |
| declarative | [2_declarative](2_declarative/README.md) | the model, from the basic catalog, validated line by line | the model writes a new surface |
| open-ended | [3_open_ended](3_open_ended/README.md) | the model, as HTML in one custom `HtmlFrame` component | the model writes new HTML |
| mixed | [4_mixed](4_mixed/README.md) | the model: catalog form plus one `HtmlFrame` map | data only, from plain server code |

All four use the same scenario: booking a library study room.

## The shared protocol code

`a2ui.py` builds the four envelopes:

```python
def create_surface(surface_id: str, catalog_id: str = BASIC_CATALOG) -> dict:
    return {"version": VERSION, "createSurface": {"surfaceId": surface_id, "catalogId": catalog_id}}
...
def update_data_model(surface_id: str, path: str, value) -> dict:
    return {"version": VERSION, "updateDataModel": {"surfaceId": surface_id, "path": path, "value": value}}
```

`a2ui.py` also validates every message the model produces. The `Validator` remembers each surface's catalog and component ids, so it can reject unknown components, missing required props and children that do not exist:

```python
            refs = comp.get("children", []) + ([comp["child"]] if "child" in comp else [])
            errors += [f"{cid}: child {r!r} does not exist" for r in refs if r not in ids]
            if name == "Button" and "event" not in (comp.get("action") or {}):
                errors.append(f"{cid}: Button.action needs an 'event' with a name")
            if name == "HtmlFrame":
                errors += [f"{cid}: {p}" for p in check_html(comp.get("html", ""))]
```

`a2ui.mjs` is the client. A `Surface` keeps components and data apart, resolves bindings, and builds the `action` envelope from the current data:

```js
  resolve(value) {
    return value && typeof value === "object" && "path" in value ? getPath(this.data, value.path) : value;
  }
...
  action(componentId) {
    const event = this.components.get(componentId).action.event;
    const context = Object.fromEntries(Object.entries(event.context || {}).map(([k, v]) => [k, this.resolve(v)]));
```

`client.mjs` is the page code shared by all four modes. Only the agent changes from mode to mode.

## Run

```bash
python serve.py
```

Then open `http://127.0.0.1:8000/01_a2ui/1_static/`. To run the tests and the recorded demos:

```bash
python -m pytest -q 01_a2ui
```

```bash
python run_all.py 01_a2ui
```
