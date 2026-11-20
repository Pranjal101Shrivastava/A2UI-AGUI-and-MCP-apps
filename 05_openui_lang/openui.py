"""OpenUI Lang: a parser and resolver, standard library only.

A program is one statement per line, ``name = expression``:

    root = Stack([title, courses])
    title = Text("Spring plan", "h1")
    courses = Table(["Code", "Units"], [["CMPE 280", 3]])

Expressions are strings, numbers, booleans, ``null``, arrays, references to
other names, and component calls with positional arguments. A reference may
point *forward* to a line that has not arrived yet: while streaming, it is a
placeholder. Assigning a name again replaces it, so an update is just a new
line. ``root`` (or the first statement) is the entry point.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.catalog import validate_props  # noqa: E402
from shared.sandbox import check_html  # noqa: E402

TOKEN = re.compile(r'\s*(?:(?P<str>"(?:[^"\\]|\\.)*")|(?P<num>-?\d+(?:\.\d+)?)|(?P<id>[A-Za-z_]\w*)|(?P<p>[=(),\[\]]))')

# Component -> positional parameter names. "children" holds nodes.
PRIMITIVES = {
    "Stack": ["children", "direction"],
    "Card": ["title", "children"],
    "Text": ["text", "variant"],
    "Metric": ["label", "value", "delta"],
    "Table": ["columns", "rows"],
    "BarChart": ["title", "labels", "values"],
    "Badge": ["text", "tone"],
    "Progress": ["label", "value"],
    "Button": ["label", "action", "variant"],
}
HTML_ARTIFACT = {"HtmlArtifact": ["html", "title", "height"]}


class ParseError(ValueError):
    pass


def tokenize(line: str) -> list[tuple[str, object]]:
    tokens, pos = [], 0
    while pos < len(line.rstrip()):
        m = TOKEN.match(line, pos)
        if not m or m.end() == pos:
            raise ParseError(f"unexpected character at column {pos + 1}: {line[pos:pos + 10]!r}")
        kind = m.lastgroup
        raw = m.group(kind)
        value = json.loads(raw) if kind in ("str", "num") else raw
        if kind == "id" and raw in ("true", "false", "null"):
            kind, value = "lit", {"true": True, "false": False, "null": None}[raw]
        tokens.append((kind, value))
        pos = m.end()
    return tokens


def parse_statement(line: str) -> tuple[str, tuple]:
    tokens = tokenize(line)
    if len(tokens) < 3 or tokens[0][0] != "id" or tokens[1] != ("p", "="):
        raise ParseError("a statement is: name = expression")
    expr, rest = _expr(tokens[2:])
    if rest:
        raise ParseError(f"unexpected {rest[0][1]!r} after the expression")
    return tokens[0][1], expr


def _expr(tokens):
    if not tokens:
        raise ParseError("expression expected")
    (kind, value), rest = tokens[0], tokens[1:]
    if kind in ("str", "num", "lit"):
        return ("lit", value), rest
    if (kind, value) == ("p", "["):
        items, rest = _items(rest, "]")
        return ("list", items), rest
    if kind == "id" and rest[:1] == [("p", "(")]:
        args, rest = _items(rest[1:], ")")
        return ("call", value, args), rest
    if kind == "id":
        return ("ref", value), rest
    raise ParseError(f"unexpected {value!r}")


def _items(tokens, close):
    items = []
    if tokens[:1] == [("p", close)]:
        return items, tokens[1:]
    while True:
        item, tokens = _expr(tokens)
        items.append(item)
        if tokens[:1] == [("p", ",")]:
            tokens = tokens[1:]
        elif tokens[:1] == [("p", close)]:
            return items, tokens[1:]
        else:
            raise ParseError(f"expected ',' or '{close}'")


def parse_program(text: str, partial: bool = False) -> tuple[dict, list[str], list[str]]:
    """Return (statements, order of names, errors). With partial=True an unfinished last line is skipped."""
    statements, order, errors = {}, [], []
    lines = text.split("\n")
    if partial and not text.endswith("\n"):
        lines = lines[:-1]
    for number, line in enumerate(lines, 1):
        if not line.strip() or line.strip().startswith("#"):
            continue
        try:
            name, expr = parse_statement(line)
        except ParseError as exc:
            errors.append(f"line {number}: {exc}")
            continue
        if name not in statements:
            order.append(name)
        statements[name] = expr                      # a later assignment replaces an earlier one
    return statements, order, errors


def resolve(statements: dict, order: list[str], components: dict) -> tuple[dict | None, list[str]]:
    """Turn statements into a tree {type, props, children}. Unknown refs become placeholders."""
    errors: list[str] = []
    if not order:
        return None, errors
    entry = "root" if "root" in statements else order[0]

    def value(expr, stack):
        kind = expr[0]
        if kind == "lit":
            return expr[1]
        if kind == "list":
            return [value(e, stack) for e in expr[1]]
        if kind == "ref":
            name = expr[1]
            if name in stack:
                errors.append(f"cycle through {name!r}")
                return None
            if name not in statements:
                return {"type": "_pending", "name": name}
            return value(statements[name], stack | {name})
        name, args = expr[1], expr[2]
        if name not in components:
            errors.append(f"unknown component {name}; known: {', '.join(sorted(components))}")
            return {"type": "_error", "name": name}
        params = components[name]
        if len(args) > len(params):
            errors.append(f"{name} takes at most {len(params)} arguments, got {len(args)}")
        props = {p: value(a, stack) for p, a in zip(params, args)}
        children = props.pop("children", None) or []
        return {"type": name, "props": props, "children": children if isinstance(children, list) else [children]}

    return value(statements[entry], {entry}), errors


def to_catalog(node):
    """Map OpenUI names onto the shared catalog: Stack -> Row/Column, HtmlArtifact -> GeneratedView."""
    if not isinstance(node, dict) or node.get("type", "").startswith("_"):
        return node
    props = dict(node.get("props", {}))
    kind = node["type"]
    if kind == "Stack":
        kind = "Row" if props.pop("direction", "column") == "row" else "Column"
    elif kind == "HtmlArtifact":
        kind = "GeneratedView"
    return {"type": kind, "props": props, "children": [to_catalog(c) for c in node.get("children", [])]}


def check(text: str, components: dict) -> tuple[dict | None, list[str]]:
    """Parse, resolve and validate a complete program against the shared catalog."""
    statements, order, errors = parse_program(text)
    tree, more = resolve(statements, order, components)
    errors += more

    def walk(node, path):
        if not isinstance(node, dict):
            return
        if node["type"] == "_pending":
            errors.append(f"{path}: {node['name']!r} is never defined")
            return
        if node["type"] in ("_error",):
            return
        if node["type"] in components and node["type"] in PRIMITIVES | HTML_ARTIFACT:
            cat = to_catalog({**node, "children": []})
            errors.extend(f"{path}: {e}" for e in validate_props(cat["type"], cat["props"]))
            if node["type"] == "HtmlArtifact":
                errors.extend(f"{path}: {p}" for p in check_html(node["props"].get("html", "")))
        for i, child in enumerate(node.get("children", [])):
            walk(child, f"{path}/{i}")

    walk(tree, "root")
    return tree, errors
