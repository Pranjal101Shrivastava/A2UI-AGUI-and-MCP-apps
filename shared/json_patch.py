"""RFC 6902 JSON Patch: add, replace, remove, test. Used for AG-UI STATE_DELTA and json-render streams."""
from __future__ import annotations

import copy


def _walk(doc, pointer):
    parts = [p.replace("~1", "/").replace("~0", "~") for p in pointer.split("/")[1:]]
    parent = doc
    for part in parts[:-1]:
        parent = parent[int(part)] if isinstance(parent, list) else parent[part]
    return parent, parts[-1]


def apply_patch(doc, ops):
    doc = copy.deepcopy(doc)
    for op in ops:
        if op["path"] == "":
            doc = copy.deepcopy(op["value"])
            continue
        parent, key = _walk(doc, op["path"])
        if isinstance(parent, list):
            index = len(parent) if key == "-" else int(key)
            if op["op"] == "add":
                parent.insert(index, op["value"])
            elif op["op"] == "replace":
                parent[index] = op["value"]
            elif op["op"] == "remove":
                parent.pop(index)
            elif op["op"] == "test" and parent[index] != op["value"]:
                raise ValueError(f"test failed at {op['path']}")
        else:
            if op["op"] in ("add", "replace"):
                parent[key] = op["value"]
            elif op["op"] == "remove":
                del parent[key]
            elif op["op"] == "test" and parent.get(key) != op["value"]:
                raise ValueError(f"test failed at {op['path']}")
    return doc
