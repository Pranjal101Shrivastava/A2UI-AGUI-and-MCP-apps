"""The shared component catalog.

A catalog is the contract between the model and the page. One definition
serves three uses:

1. ``prompt_text()`` describes the components to the model,
2. ``validate_props()`` checks what the model produced,
3. ``shared/js/catalog.mjs`` holds one renderer per name.

Every format in this repository (A2UI, AG-UI state, MCP Apps, json-render,
OpenUI Lang and the harness ``render_ui`` tool) maps onto these names.
"""
from __future__ import annotations

# name -> {"props": {prop: (type, required)}, "children": bool, "doc": str}
CATALOG: dict[str, dict] = {
    "Card": {"props": {"title": ("string", False)}, "children": True, "doc": "A bordered box with an optional title"},
    "Row": {"props": {"gap": ("string", False)}, "children": True, "doc": "Children side by side"},
    "Column": {"props": {"gap": ("string", False)}, "children": True, "doc": "Children stacked vertically"},
    "Text": {"props": {"text": ("string", True), "variant": ("string", False)}, "children": False,
             "doc": "Text. variant: h1 | h2 | body | muted"},
    "Metric": {"props": {"label": ("string", True), "value": ("any", True), "delta": ("string", False)},
               "children": False, "doc": "A big number with a label and an optional change like +4%"},
    "Table": {"props": {"columns": ("array", True), "rows": ("array", True)}, "children": False,
              "doc": "Header list plus rows of cells"},
    "BarChart": {"props": {"title": ("string", True), "labels": ("array", True), "values": ("array", True)},
                 "children": False, "doc": "One-series bar chart"},
    "Badge": {"props": {"text": ("string", True), "tone": ("string", False)}, "children": False,
              "doc": "A small status pill. tone: ok | warn | bad | info"},
    "Progress": {"props": {"label": ("string", True), "value": ("number", True)}, "children": False,
                 "doc": "A progress bar, value 0-100"},
    "TextField": {"props": {"label": ("string", True), "value": ("any", False), "bind": ("string", False)},
                  "children": False, "doc": "A labelled text input; bind names a data path"},
    "Button": {"props": {"label": ("string", True), "action": ("string", True), "variant": ("string", False)},
               "children": False, "doc": "Sends a named action back to the server. variant: primary | default"},
    "GeneratedView": {"props": {"html": ("string", True), "title": ("string", False), "height": ("number", False)},
                      "children": False,
                      "doc": "Escape hatch: model-written HTML shown in a sandboxed iframe. Use for ONE region only"},
}

TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "any": lambda v: True,
}


def validate_props(component: str, props: dict, allowed: set[str] | None = None) -> list[str]:
    """Return a list of human-readable errors. An empty list means valid."""
    allowed = allowed if allowed is not None else set(CATALOG)
    if component not in CATALOG or component not in allowed:
        return [f"unknown component {component!r}; allowed: {', '.join(sorted(allowed))}"]
    spec = CATALOG[component]["props"]
    errors = []
    for name, (kind, required) in spec.items():
        if name not in props:
            if required:
                errors.append(f"{component}.{name} is required")
            continue
        value = props[name]
        if isinstance(value, dict) and ("path" in value or "$state" in value):
            continue  # a data binding: checked when it resolves
        if not TYPE_CHECKS[kind](value):
            errors.append(f"{component}.{name} must be {kind}, got {type(value).__name__}")
    for name in props:
        if name not in spec:
            errors.append(f"{component} has no prop {name!r}")
    return errors


def prompt_text(allowed: set[str] | None = None) -> str:
    """The catalog as the model sees it: one line per component."""
    lines = []
    for name, spec in CATALOG.items():
        if allowed is not None and name not in allowed:
            continue
        props = ", ".join(f"{p}{'' if req else '?'}: {kind}" for p, (kind, req) in spec["props"].items())
        kids = " (has children)" if spec["children"] else ""
        lines.append(f"- {name}({props}){kids}: {spec['doc']}")
    return "\n".join(lines)
