"""Validate a flat element map, the spec shape used by json-render, MCP Apps views and the harness.

    {"root": "page", "elements": {"page": {"type": "Column", "props": {}, "children": ["kpi"]}, ...}}

Flat maps stream well: each element can arrive on its own, and a missing child
is just a placeholder until it lands.
"""
from __future__ import annotations

from shared.catalog import CATALOG, validate_props
from shared.sandbox import check_html


def validate_element_map(spec: dict, allowed: set[str] | None = None, complete: bool = True) -> list[str]:
    if not isinstance(spec, dict) or not isinstance(spec.get("elements"), dict):
        return ["spec needs an 'elements' object"]
    elements, errors = spec["elements"], []
    if spec.get("root") not in elements and complete:
        errors.append(f"root {spec.get('root')!r} is not an element")
    for eid, el in elements.items():
        if not isinstance(el, dict) or "type" not in el:
            errors.append(f"{eid}: needs a 'type'")
            continue
        errors += [f"{eid}: {e}" for e in validate_props(el["type"], el.get("props", {}), allowed)]
        kids = el.get("children", [])
        if kids and not CATALOG.get(el["type"], {}).get("children"):
            errors.append(f"{eid}: {el['type']} cannot have children")
        if complete:
            errors += [f"{eid}: child {k!r} is missing" for k in kids if k not in elements]
        if el["type"] == "GeneratedView":
            errors += [f"{eid}: {p}" for p in check_html(el.get("props", {}).get("html", ""))]
    return errors
