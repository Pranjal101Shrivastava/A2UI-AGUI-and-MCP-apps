"""The json-render spec format in Python: state bindings, patch streams, two renderers' worth of checks.

A spec is a flat element map plus a state object:

    {"root": "page",
     "elements": {"page": {"type": "Column", "props": {}, "children": ["kpi"]},
                  "kpi":  {"type": "Metric", "props": {"label": "Revenue", "value": {"$state": "/revenue"}}}},
     "state": {"revenue": "$1,240"}}

A prop written as ``{"$state": "/pointer"}`` reads from ``state``. The model can
send the spec whole, or stream it as JSONL RFC 6902 patches against an empty
spec, so the page can paint before the model finishes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.json_patch import apply_patch  # noqa: E402
from shared.spec import validate_element_map  # noqa: E402

EMPTY = {"root": None, "elements": {}, "state": {}}


def read_pointer(doc, pointer: str):
    for key in [k for k in pointer.split("/") if k]:
        doc = doc[int(key)] if isinstance(doc, list) else doc[key]
    return doc


def bindings(spec: dict) -> list[str]:
    """Every state pointer the spec reads."""
    found = []
    for el in spec["elements"].values():
        for value in el.get("props", {}).values():
            if isinstance(value, dict) and "$state" in value:
                found.append(value["$state"])
    return found


def check_state(spec: dict) -> list[str]:
    errors = []
    for pointer in bindings(spec):
        try:
            read_pointer(spec.get("state", {}), pointer)
        except (KeyError, IndexError, TypeError):
            errors.append(f"state has nothing at {pointer}")
    return errors


def resolve(spec: dict) -> dict:
    """A copy of the spec with every $state binding replaced by its value."""
    out = json.loads(json.dumps(spec))
    for el in out["elements"].values():
        for key, value in list(el.get("props", {}).items()):
            if isinstance(value, dict) and "$state" in value:
                el["props"][key] = read_pointer(spec["state"], value["$state"])
    return out


def apply_line(spec: dict, line: str) -> dict:
    """Apply one JSONL patch line to the spec."""
    return apply_patch(spec, [json.loads(line)])


def validate(spec: dict, complete: bool = True) -> list[str]:
    return validate_element_map(spec, complete=complete) + (check_state(spec) if complete else [])


# ---- a second renderer: the terminal ------------------------------------------------
def render_terminal(spec: dict, width: int = 60) -> str:
    """Draw the same spec as text. Same catalog names, a different component map."""
    spec = resolve(spec)
    lines: list[str] = []

    def walk(eid: str, depth: int) -> None:
        el = spec["elements"][eid]
        p, pad = el.get("props", {}), "  " * depth
        t = el["type"]
        if t == "Text":
            lines.append(pad + (p["text"].upper() if p.get("variant") in ("h1", "h2") else p["text"]))
        elif t == "Metric":
            lines.append(f"{pad}{p['label']}: {p['value']} {p.get('delta', '')}".rstrip())
        elif t == "BarChart":
            top = max(p["values"]) or 1
            lines.append(f"{pad}{p['title']}")
            lines.extend([f"{pad}  {lab:<4} {'█' * round(v / top * 24)} {v}" for lab, v in zip(p["labels"], p["values"])])
        elif t == "Table":
            lines.append((pad + " | ".join(f"{c:<14}" for c in p["columns"])).rstrip())
            lines.extend((pad + " | ".join(f"{str(c):<14}" for c in row)).rstrip() for row in p["rows"])
        elif t == "Badge":
            lines.append(f"{pad}[{p['text']}]")
        elif t == "Button":
            lines.append(f"{pad}< {p['label']} >  (action: {p['action']})")
        elif t == "GeneratedView":
            lines.append(f"{pad}[{p.get('title', 'generated view')}: HTML region, shown only in a browser]")
        elif t == "Card":
            lines.append(pad + "┌─ " + p.get("title", "") + " " + "─" * max(0, width - len(p.get("title", "")) - 4))
        for child in el.get("children", []):
            walk(child, depth + (1 if t == "Card" else 0))

    walk(spec["root"], 0)
    return "\n".join(lines)


# ---- open-ended: an open vocabulary of HTML tags instead of a catalog ---------------
OPEN_TAGS = {"div", "span", "p", "h1", "h2", "h3", "strong", "em", "small", "ul", "li", "button", "section"}
OPEN_PROPS = {"style", "text", "action", "label"}
_CSS_BLOCK = ("url(", "expression(", "javascript:", "@import", "behavior")


def validate_open_spec(spec: dict) -> list[str]:
    """Any layout and any styling, but only safe tags, inline styles and named actions."""
    errors = []
    elements = spec.get("elements", {})
    if spec.get("root") not in elements:
        errors.append("root is not an element")
    for eid, el in elements.items():
        if el.get("type") not in OPEN_TAGS:
            errors.append(f"{eid}: tag <{el.get('type')}> is not allowed")
        props = el.get("props", {})
        errors += [f"{eid}: prop {k!r} is not allowed (on* handlers and attributes are stripped)"
                   for k in props if k not in OPEN_PROPS]
        for name, value in (props.get("style") or {}).items():
            if any(bad in str(value).lower() for bad in _CSS_BLOCK):
                errors.append(f"{eid}: style {name} uses a blocked CSS feature")
        errors += [f"{eid}: child {k!r} is missing" for k in el.get("children", []) if k not in elements]
    return errors
