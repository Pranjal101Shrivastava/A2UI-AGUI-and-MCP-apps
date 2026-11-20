"""The terminal surface: the same harness events, drawn as text."""
import json
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent.parent / "04_json_render")]


def draw(event: dict, components: dict | None = None) -> list[str]:
    t = event["type"]
    if t == "RUN_STARTED":
        return [f"● run started in {event['workspace']}"]
    if t == "TEXT":
        return [f"assistant: {event['text']}"]
    if t == "TOOL_CALL":
        return [f"  → {event['name']}({json.dumps(event['args'], ensure_ascii=False)[:80]})"]
    if t == "TOOL_RESULT":
        return [f"    {'✓' if event['ok'] else '✗'} {event['summary'][:90]}"]
    if t == "UI" and event["kind"] == "component":
        draw_one = (components or {}).get(event["component"])
        return draw_one(event["props"]) if draw_one else [f"  [{event['component']}]"]
    if t == "UI" and event["kind"] == "spec":
        from jsonrender import render_terminal  # the json-render terminal renderer, reused

        return ["  ┌ render_ui"] + ["  │ " + line for line in render_terminal(event["spec"]).splitlines()]
    if t == "UI" and event["kind"] == "html":
        return [f"  ┌ render_html (browser only) · fallback: {event['fallback']}"]
    if t == "PAUSED":
        return [f"  ⏸ waiting for approval: {event['request']}"]
    if t == "RUN_FINISHED":
        return ["● run finished" + (f" ({event['note']})" if event.get("note") else "")]
    return []


def transcript(events: list[dict], components: dict | None = None) -> str:
    return "\n".join(line for e in events for line in draw(e, components))
