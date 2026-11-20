"""A2UI v0.9 messages: build them, parse them, validate them.

A2UI separates a UI into two streams:

* **structure**: ``updateComponents`` sends a flat list of components, each
  with an ``id``. Containers point at children by id.
* **data**: ``updateDataModel`` writes JSON into the surface's data model.
  Components read it through bindings such as ``{"path": "/room/name"}``.

Four server-to-client envelopes exist: ``createSurface``,
``updateComponents``, ``updateDataModel`` and ``deleteSurface``. The client
answers with an ``action`` envelope when the user presses a button.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.sandbox import check_html  # noqa: E402

VERSION = "v0.9"
BASIC_CATALOG = "https://a2ui.org/specification/v0_9/catalogs/basic/catalog.json"
HTML_ONLY_CATALOG = "genux.local:a2ui/html-only-v1"
BASIC_PLUS_HTML_CATALOG = "genux.local:a2ui/basic-plus-html-v1"

# component -> (required props, optional props). A subset of the basic catalog.
_BASIC = {
    "Text": ({"text"}, {"variant"}),
    "Row": ({"children"}, {"justify", "align"}),
    "Column": ({"children"}, {"justify", "align"}),
    "Card": ({"child"}, set()),
    "Divider": (set(), set()),
    "Button": ({"child", "action"}, {"variant"}),
    "TextField": ({"label"}, {"value"}),
}
_HTML = {"HtmlFrame": ({"html"}, {"height"})}  # a custom component: model-written HTML

CATALOGS = {
    BASIC_CATALOG: _BASIC,
    HTML_ONLY_CATALOG: _HTML,
    BASIC_PLUS_HTML_CATALOG: {**_BASIC, **_HTML},
}
ENVELOPES = ("createSurface", "updateComponents", "updateDataModel", "deleteSurface")


# ---- builders ---------------------------------------------------------------
def create_surface(surface_id: str, catalog_id: str = BASIC_CATALOG) -> dict:
    return {"version": VERSION, "createSurface": {"surfaceId": surface_id, "catalogId": catalog_id}}


def update_components(surface_id: str, components: list[dict]) -> dict:
    return {"version": VERSION, "updateComponents": {"surfaceId": surface_id, "components": components}}


def update_data_model(surface_id: str, path: str, value) -> dict:
    return {"version": VERSION, "updateDataModel": {"surfaceId": surface_id, "path": path, "value": value}}


def delete_surface(surface_id: str) -> dict:
    return {"version": VERSION, "deleteSurface": {"surfaceId": surface_id}}


def parse_jsonl(text: str) -> list[tuple[int, dict | None, str | None]]:
    """Split model output into (line number, message or None, parse error or None)."""
    out = []
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip().strip("`")
        if not line or line.startswith("json"):
            continue
        try:
            out.append((number, json.loads(line), None))
        except json.JSONDecodeError as exc:
            out.append((number, None, f"line {number}: not JSON ({exc.msg})"))
    return out


# ---- validation -------------------------------------------------------------
class Validator:
    """Tracks surfaces across messages, so ids and catalogs can be checked."""

    def __init__(self) -> None:
        self.surfaces: dict[str, dict] = {}  # surfaceId -> {"catalog": id, "ids": set()}

    def check(self, msg: dict) -> list[str]:
        if not isinstance(msg, dict):
            return ["message must be a JSON object"]
        if msg.get("version") != VERSION:
            return [f"version must be {VERSION!r}"]
        keys = [k for k in msg if k in ENVELOPES]
        if len(keys) != 1 or len(msg) != 2:
            return [f"message must have 'version' and exactly one of {', '.join(ENVELOPES)}"]
        kind, body = keys[0], msg[keys[0]]
        sid = body.get("surfaceId")
        if kind == "createSurface":
            if body.get("catalogId") not in CATALOGS:
                return [f"unknown catalogId {body.get('catalogId')!r}"]
            if sid in self.surfaces:
                return [f"surface {sid!r} already exists"]
            self.surfaces[sid] = {"catalog": body["catalogId"], "ids": set()}
            return []
        if sid not in self.surfaces:
            return [f"surface {sid!r} was not created"]
        if kind == "deleteSurface":
            del self.surfaces[sid]
            return []
        if kind == "updateDataModel":
            return [] if str(body.get("path", "")).startswith("/") else ["path must start with '/'"]
        return self._check_components(self.surfaces[sid], body.get("components") or [])

    def _check_components(self, surface: dict, components: list) -> list[str]:
        catalog = CATALOGS[surface["catalog"]]
        errors, ids = [], surface["ids"] | {c.get("id") for c in components if isinstance(c, dict)}
        for comp in components:
            cid, name = comp.get("id"), comp.get("component")
            if not cid or name not in catalog:
                errors.append(f"component {cid!r}: unknown type {name!r}; this catalog allows {', '.join(sorted(catalog))}")
                continue
            required, optional = catalog[name]
            props = set(comp) - {"id", "component"}
            errors += [f"{cid}: {name} needs {p!r}" for p in sorted(required - props)]
            errors += [f"{cid}: {name} has no prop {p!r}" for p in sorted(props - required - optional)]
            refs = comp.get("children", []) + ([comp["child"]] if "child" in comp else [])
            errors += [f"{cid}: child {r!r} does not exist" for r in refs if r not in ids]
            if name == "Button" and "event" not in (comp.get("action") or {}):
                errors.append(f"{cid}: Button.action needs an 'event' with a name")
            if name == "HtmlFrame":
                errors += [f"{cid}: {p}" for p in check_html(comp.get("html", ""))]
        if "root" not in ids:
            errors.append("one component must have id 'root'")
        if not errors:
            surface["ids"] = ids
        return errors


def parse_action(body: dict) -> dict:
    """Read a client action envelope and return its inner object."""
    if body.get("version") != VERSION or "action" not in body:
        raise ValueError("expected {version, action}")
    action = body["action"]
    for key in ("name", "surfaceId", "sourceComponentId"):
        if key not in action:
            raise ValueError(f"action.{key} is missing")
    return action
