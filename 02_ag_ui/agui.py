"""AG-UI events, RunAgentInput, and JSON Patch, with the standard library only.

AG-UI is an event protocol between an agent and a frontend. One run is a
stream of typed events: lifecycle (``RUN_STARTED`` ... ``RUN_FINISHED``),
text (``TEXT_MESSAGE_START/CONTENT/END``), tool calls
(``TOOL_CALL_START/ARGS/END/RESULT``), shared state (``STATE_SNAPSHOT``,
``STATE_DELTA`` as RFC 6902 JSON Patch) and ``CUSTOM``. The frontend starts a
run by POSTing a ``RunAgentInput``: thread id, run id, messages, state, tools.
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.json_patch import apply_patch  # noqa: E402,F401  (STATE_DELTA uses RFC 6902)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ---- events -----------------------------------------------------------------
def run_started(thread_id, run_id):
    return {"type": "RUN_STARTED", "threadId": thread_id, "runId": run_id}


def run_finished(thread_id, run_id):
    return {"type": "RUN_FINISHED", "threadId": thread_id, "runId": run_id}


def run_error(message):
    return {"type": "RUN_ERROR", "message": message}


def step(name, started=True):
    return {"type": "STEP_STARTED" if started else "STEP_FINISHED", "stepName": name}


def text_message(text: str, chunk: int = 18):
    """A whole assistant message as START, CONTENT deltas, END."""
    mid = _id("msg")
    yield {"type": "TEXT_MESSAGE_START", "messageId": mid, "role": "assistant"}
    for i in range(0, len(text), chunk):
        yield {"type": "TEXT_MESSAGE_CONTENT", "messageId": mid, "delta": text[i:i + chunk]}
    yield {"type": "TEXT_MESSAGE_END", "messageId": mid}


def tool_call(name: str, args: dict, call_id: str | None = None, chunk: int = 40):
    """A tool call whose JSON arguments stream in pieces, as a model produces them."""
    cid = call_id or _id("call")
    raw = json.dumps(args, ensure_ascii=False)
    yield {"type": "TOOL_CALL_START", "toolCallId": cid, "toolCallName": name}
    for i in range(0, len(raw), chunk):
        yield {"type": "TOOL_CALL_ARGS", "toolCallId": cid, "delta": raw[i:i + chunk]}
    yield {"type": "TOOL_CALL_END", "toolCallId": cid}


def tool_result(call_id: str, content):
    return {"type": "TOOL_CALL_RESULT", "messageId": _id("msg"), "toolCallId": call_id, "role": "tool",
            "content": content if isinstance(content, str) else json.dumps(content)}


def state_snapshot(state):
    return {"type": "STATE_SNAPSHOT", "snapshot": state}


def state_delta(ops):
    return {"type": "STATE_DELTA", "delta": ops}


def custom(name, value):
    return {"type": "CUSTOM", "name": name, "value": value}


# ---- input ------------------------------------------------------------------
def parse_run_input(body: dict) -> dict:
    """Fill the RunAgentInput defaults the frontend may omit."""
    return {
        "threadId": body.get("threadId") or _id("thread"),
        "runId": body.get("runId") or _id("run"),
        "messages": body.get("messages") or [],
        "state": body.get("state") or {},
        "tools": body.get("tools") or [],
        "context": body.get("context") or [],
        "forwardedProps": body.get("forwardedProps") or {},
    }


def last_user_text(run_input: dict) -> str:
    users = [m for m in run_input["messages"] if m.get("role") == "user"]
    return users[-1]["content"] if users else ""


# ---- a protocol check used by the tests -----------------------------------------
def check_sequence(events: list[dict]) -> list[str]:
    """Lifecycle and pairing rules every run must follow."""
    errors, open_text, open_tools = [], set(), set()
    if not events or events[0]["type"] != "RUN_STARTED":
        errors.append("first event must be RUN_STARTED")
    if events and events[-1]["type"] not in ("RUN_FINISHED", "RUN_ERROR"):
        errors.append("last event must be RUN_FINISHED or RUN_ERROR")
    for e in events:
        t = e["type"]
        if t == "TEXT_MESSAGE_START":
            open_text.add(e["messageId"])
        elif t in ("TEXT_MESSAGE_CONTENT", "TEXT_MESSAGE_END") and e["messageId"] not in open_text:
            errors.append(f"{t} for unknown message {e['messageId']}")
        elif t == "TOOL_CALL_START":
            open_tools.add(e["toolCallId"])
        elif t in ("TOOL_CALL_ARGS", "TOOL_CALL_END") and e["toolCallId"] not in open_tools:
            errors.append(f"{t} for unknown tool call {e['toolCallId']}")
        if t == "TEXT_MESSAGE_END":
            open_text.discard(e["messageId"])
        if t == "TOOL_CALL_END":
            open_tools.discard(e["toolCallId"])
    if open_text or open_tools:
        errors.append("unclosed text message or tool call")
    return errors
