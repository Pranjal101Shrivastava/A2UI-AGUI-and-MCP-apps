"""A small coding-agent harness with generative UI as one more set of tools.

The loop is the usual one: ask the model, run the tool calls it makes, append
the results, repeat until it answers in text. The tools work on a temporary
copy of ``toy_project/`` and really run its tests. UI tools are ordinary tools
too: their "execution" is to validate the request and emit a UI event. The
same events drive two surfaces: the web page (``client.mjs``) and the terminal
(``terminal.py``).

A tool may *pause* the run (``Pause``): the harness stores the session, emits
an approval request and stops. A later ``resume`` call continues the loop with
the user's answer as the tool result.
"""
from __future__ import annotations

import difflib
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from shared.llm import tool  # noqa: E402

SYSTEM = "You are a coding agent. Use tools to inspect the project, fix failing tests, and show the user your progress."


class Pause(Exception):
    """Raised by a tool that needs the user's answer before it can finish."""

    def __init__(self, request: dict):
        super().__init__("paused for approval")
        self.request = request


@dataclass
class Tool:
    schema: dict
    run: Callable[..., str]


@dataclass
class Session:
    model: object
    workspace: Path
    tools: dict = field(default_factory=dict)
    messages: list = field(default_factory=list)
    last_tests: dict = field(default_factory=dict)
    changes: dict = field(default_factory=dict)         # path -> (before, after)
    pending: dict | None = None                          # a paused tool call
    ui_events: list = field(default_factory=list)        # filled by UI tools during a step


def new_workspace() -> Path:
    path = Path(tempfile.mkdtemp(prefix="genux-harness-"))
    shutil.copytree(HERE / "toy_project", path, dirs_exist_ok=True)
    return path


# ---- the coding tools ----------------------------------------------------------------
def coding_tools(s: Session) -> dict[str, Tool]:
    def list_files() -> str:
        return "\n".join(sorted(p.name for p in s.workspace.iterdir() if p.suffix == ".py"))

    def read_file(path: str) -> str:
        return (s.workspace / Path(path).name).read_text(encoding="utf-8")

    def write_file(path: str, content: str) -> str:
        target = s.workspace / Path(path).name
        before = target.read_text(encoding="utf-8") if target.exists() else ""
        target.write_text(content, encoding="utf-8")
        s.changes[target.name] = (s.changes.get(target.name, (before, ""))[0], content)
        return f"wrote {target.name} ({len(content)} chars)"

    def run_tests() -> str:
        proc = subprocess.run([sys.executable, "-m", "unittest", "-v"], cwd=s.workspace, capture_output=True,
                              text=True, timeout=60)
        out = proc.stderr + proc.stdout
        ran = next((int(line.split()[1]) for line in out.splitlines() if line.startswith("Ran ")), 0)
        failed = out.count("... FAIL") + out.count("... ERROR")
        failures = [line.split(" (")[0] for line in out.splitlines() if line.endswith("FAIL") or line.endswith("ERROR")]
        s.last_tests = {"ran": ran, "passed": ran - failed, "failed": failed, "failures": failures, "ok": proc.returncode == 0}
        head = f"{ran - failed}/{ran} passed" + (f"; failing: {', '.join(failures)}" if failures else "")
        return head + "\n" + out[-1500:]

    return {
        "list_files": Tool(tool("list_files", "List the project's Python files.", {}), list_files),
        "read_file": Tool(tool("read_file", "Read a file.", {"path": {"type": "string"}}), read_file),
        "write_file": Tool(tool("write_file", "Replace a file's content.",
                                {"path": {"type": "string"}, "content": {"type": "string"}}), write_file),
        "run_tests": Tool(tool("run_tests", "Run the unit tests.", {}), run_tests),
    }


def unified_diff(s: Session) -> str:
    out = []
    for name, (before, after) in s.changes.items():
        out += difflib.unified_diff(before.splitlines(), after.splitlines(), f"a/{name}", f"b/{name}", lineterm="")
    return "\n".join(out)


# ---- the loop ------------------------------------------------------------------------
def _short(text: str, n: int = 90) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def step_loop(s: Session, max_steps: int = 12):
    """Run until the model answers in text, a tool pauses, or the step budget ends."""
    schemas = [t.schema for t in s.tools.values()]
    for _ in range(max_steps):
        reply = s.model.complete(s.messages, schemas)
        s.messages.append({"role": "assistant", "content": reply["content"],
                           "tool_calls": [{"id": c["id"], "type": "function", "function": {
                               "name": c["name"], "arguments": json.dumps(c["arguments"])}} for c in reply["tool_calls"]]})
        if reply["content"]:
            yield {"type": "TEXT", "text": reply["content"]}
        if not reply["tool_calls"]:
            yield {"type": "RUN_FINISHED"}
            return
        for call in reply["tool_calls"]:
            yield {"type": "TOOL_CALL", "id": call["id"], "name": call["name"],
                   "args": {k: _short(v if isinstance(v, str) else json.dumps(v), 60) for k, v in call["arguments"].items()}}
            try:
                output = s.tools[call["name"]].run(**call["arguments"])
                ok = not str(output).startswith("error:")
            except Pause as pause:
                s.pending = {"call": call, **pause.request}
                yield from s.ui_events
                s.ui_events.clear()
                yield {"type": "PAUSED", "id": call["id"], "request": pause.request.get("summary", "")}
                return
            except Exception as exc:  # a tool error is a result the model can read
                output, ok = f"error: {type(exc).__name__}: {exc}", False
            yield from s.ui_events
            s.ui_events.clear()
            yield {"type": "TOOL_RESULT", "id": call["id"], "name": call["name"], "ok": ok, "summary": _short(output)}
            s.messages.append({"role": "tool", "tool_call_id": call["id"], "content": str(output)})
    yield {"type": "RUN_FINISHED", "note": "step budget reached"}


def start(s: Session, prompt: str):
    s.messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
    yield {"type": "RUN_STARTED", "workspace": s.workspace.name}
    yield from step_loop(s)


def resume(s: Session, answer: str, finish: Callable[[Session, dict, str], str]):
    """Finish the paused tool call with the user's answer, then continue the loop."""
    pending, s.pending = s.pending, None
    if not pending:
        yield {"type": "TEXT", "text": "Nothing is waiting for approval."}
        return
    output = finish(s, pending, answer)
    yield from s.ui_events
    s.ui_events.clear()
    yield {"type": "TOOL_RESULT", "id": pending["call"]["id"], "name": pending["call"]["name"],
           "ok": answer == "approve", "summary": _short(output)}
    s.messages.append({"role": "tool", "tool_call_id": pending["call"]["id"], "content": output})
    yield from step_loop(s)
