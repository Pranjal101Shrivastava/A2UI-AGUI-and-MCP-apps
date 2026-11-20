"""Validate a nested UI tree ``{type, props, children}`` against the shared catalog."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.catalog import CATALOG, validate_props  # noqa: E402
from shared.sandbox import check_html  # noqa: E402


def validate_tree(node, path="/ui", allowed=None) -> list[str]:
    if node is None:
        return []
    if not isinstance(node, dict) or "type" not in node:
        return [f"{path}: a node needs a 'type'"]
    errors = [f"{path}: {e}" for e in validate_props(node["type"], node.get("props", {}), allowed)]
    kids = node.get("children", [])
    if kids and not CATALOG.get(node["type"], {}).get("children"):
        errors.append(f"{path}: {node['type']} cannot have children")
    if node["type"] == "GeneratedView":
        errors += [f"{path}: {p}" for p in check_html(node.get("props", {}).get("html", ""))]
    for i, child in enumerate(kids):
        errors += validate_tree(child, f"{path}/children/{i}", allowed)
    return errors
