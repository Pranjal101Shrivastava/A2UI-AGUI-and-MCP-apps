"""The two generative UI tools a harness can offer: ``render_ui`` (catalog) and ``render_html`` (open)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness  # noqa: E402
from shared.catalog import prompt_text  # noqa: E402
from shared.llm import tool  # noqa: E402
from shared.sandbox import check_html  # noqa: E402
from shared.spec import validate_element_map  # noqa: E402


def render_ui(s: harness.Session, allowed: set[str] | None = None, max_generated: int = 0) -> harness.Tool:
    """A validated spec tool. Invalid specs come back to the model as an error result."""
    def run(spec: dict, slot: str = "main") -> str:
        errors = validate_element_map(spec, allowed)
        generated = sum(el.get("type") == "GeneratedView" for el in spec.get("elements", {}).values())
        if generated > max_generated:
            errors.append(f"at most {max_generated} GeneratedView element(s) allowed")
        if errors:
            return "error: the spec was not shown: " + "; ".join(errors)
        s.ui_events.append({"type": "UI", "kind": "spec", "slot": slot, "spec": spec})
        return f"shown in slot {slot!r} ({len(spec['elements'])} elements)"

    schema = tool("render_ui", "Show a UI built from catalog components as {root, elements:{id:{type, props, children}}}. "
                  "Components:\n" + prompt_text(allowed),
                  {"spec": {"type": "object"}, "slot": {"type": "string"}}, ["spec"])
    return harness.Tool(schema, run)


def render_html(s: harness.Session) -> harness.Tool:
    """Open-ended: any HTML for the web surface, plus a text fallback for the terminal."""
    def run(html: str, fallback: str, title: str = "render_html") -> str:
        problems = check_html(html)
        if problems:
            return "error: refused by the content policy: " + "; ".join(problems)
        s.ui_events.append({"type": "UI", "kind": "html", "html": html, "fallback": fallback, "title": title})
        return f"shown {len(html)} chars of HTML in a sandbox"

    schema = tool("render_html", "Show self-contained HTML in a sandboxed frame. No URLs. "
                  "Report clicks with genux.send('action', {name}).",
                  {"html": {"type": "string"}, "fallback": {"type": "string"}, "title": {"type": "string"}}, ["html", "fallback"])
    return harness.Tool(schema, run)
