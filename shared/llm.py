"""One small model adapter used by every codelab.

Two implementations share one interface:

* ``ScriptedModel`` replays replies written in advance. Every demo and test
  uses it by default, so each codelab runs offline, for free, and gives the
  same output on every machine.
* ``LiveModel`` calls any OpenAI-compatible ``/chat/completions`` endpoint
  with the standard library only. It is used when ``GENUX_LIVE=1`` and an
  ``API_KEY`` (or ``OPENAI_API_KEY``) is set.

A reply is a dict ``{"content": str | None, "tool_calls": [ {id, name, arguments} ]}``.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class ScriptedModel:
    """Returns the next scripted reply on each call. Records every prompt it saw."""

    replies: list
    calls: list = field(default_factory=list)
    chunk_size: int = 24
    delay: float = 0.0  # seconds per chunk, to imitate a model's output speed in streaming demos

    def complete(self, messages: list, tools: list | None = None) -> dict:
        self.calls.append({"messages": messages, "tools": [t["function"]["name"] for t in tools or []]})
        if not self.replies:
            raise RuntimeError("ScriptedModel ran out of replies")
        reply = self.replies.pop(0)
        if isinstance(reply, str):
            reply = {"content": reply, "tool_calls": []}
        reply.setdefault("content", None)
        reply.setdefault("tool_calls", [])
        for i, call in enumerate(reply["tool_calls"]):
            call.setdefault("id", f"call_{len(self.calls)}_{i}")
        return reply

    def stream(self, messages: list) -> Iterator[str]:
        """Yield the next reply's text in small chunks, like a streaming API."""
        text = self.complete(messages)["content"] or ""
        for start in range(0, len(text), self.chunk_size):
            if self.delay:
                time.sleep(self.delay)
            yield text[start:start + self.chunk_size]


class LiveModel:
    """OpenAI-compatible chat completions over urllib. No SDK needed."""

    def __init__(self) -> None:
        self.key = os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY", "")
        self.base = os.environ.get("BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.environ.get("MODEL", "gpt-4.1-mini")

    def _post(self, body: dict) -> dict:
        req = urllib.request.Request(
            f"{self.base}/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())

    def complete(self, messages: list, tools: list | None = None) -> dict:
        body = {"model": self.model, "messages": messages}
        if tools:
            body["tools"] = tools
        msg = self._post(body)["choices"][0]["message"]
        calls = [
            {"id": c["id"], "name": c["function"]["name"], "arguments": json.loads(c["function"]["arguments"] or "{}")}
            for c in msg.get("tool_calls") or []
        ]
        return {"content": msg.get("content"), "tool_calls": calls}

    def stream(self, messages: list) -> Iterator[str]:
        # Kept simple: one request, then chunk the answer. Swap in stream=True for true token streaming.
        text = self.complete(messages)["content"] or ""
        for start in range(0, len(text), 24):
            yield text[start:start + 24]


def get_model(script: list, delay: float = 0.0):
    """Live model when explicitly enabled, otherwise a fresh scripted model."""
    if os.environ.get("GENUX_LIVE") == "1" and (os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY")):
        return LiveModel()
    return ScriptedModel(json.loads(json.dumps(script)), delay=delay)  # deep copy: each run starts from the top


def tool(name: str, description: str, properties: dict, required: list | None = None) -> dict:
    """Build an OpenAI function-calling schema in one line."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required or list(properties)},
        },
    }


def approx_tokens(text: str) -> int:
    """Token estimate. Uses tiktoken when installed, else the common 4-characters rule."""
    try:
        import tiktoken  # type: ignore

        return len(tiktoken.get_encoding("o200k_base").encode(text))
    except Exception:
        return max(1, round(len(text) / 4))
