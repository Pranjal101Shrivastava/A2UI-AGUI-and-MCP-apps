"""Server-side checks for model-written HTML (open-ended and mixed modes).

The browser sandbox (``shared/js/sandbox.mjs``) is the real boundary: an
iframe with ``sandbox="allow-scripts"`` and a strict Content Security Policy.
This module is the second layer: it refuses HTML that tries to reach the
network or navigate, before the HTML ever leaves the server. A refusal is
returned to the model as a normal error so it can try again.
"""
from __future__ import annotations

import re

# The policy the iframe enforces. No network, no forms, no nested frames.
CSP = "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:; font-src data:"

MAX_HTML_BYTES = 40_000

BLOCKED = [
    (re.compile(r"<script[^>]+src\s*=", re.I), "external <script src> is not allowed"),
    (re.compile(r"https?://", re.I), "network URLs are not allowed"),
    (re.compile(r"\bfetch\s*\(|XMLHttpRequest|WebSocket|EventSource", re.I), "network APIs are not allowed"),
    (re.compile(r"<(iframe|object|embed|form)\b", re.I), "nested frames and forms are not allowed"),
    (re.compile(r"\b(top|parent)\.location|window\.open\s*\(", re.I), "navigation is not allowed"),
    (re.compile(r"document\.cookie|localStorage|sessionStorage", re.I), "storage access is not allowed"),
]


def check_html(html: str) -> list[str]:
    """Return policy violations. An empty list means the HTML may be shown."""
    problems = [message for pattern, message in BLOCKED if pattern.search(html)]
    if len(html.encode()) > MAX_HTML_BYTES:
        problems.append(f"HTML is larger than {MAX_HTML_BYTES} bytes")
    return problems
