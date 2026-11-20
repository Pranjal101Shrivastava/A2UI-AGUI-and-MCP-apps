"""One tiny development server for every codelab, standard library only.

* ``GET``  serves files from the repository root, so every page can import
  ``../../shared/js/*.mjs`` with relative paths (the same paths work on a
  static host such as GitHub Pages).
* ``POST <codelab>/api/<name>`` loads ``<codelab>/agent.py`` and calls
  ``handle(name, body)``. A generator becomes a Server-Sent Events stream,
  one ``data:`` line per event. A dict or list becomes one JSON response.

Every request and every event is appended to ``TRANSCRIPT``; the demo
runner prints it as the recorded execution of a codelab.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import threading
import types
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TRANSCRIPT: list[dict] = []
_MODULES: dict[Path, types.ModuleType] = {}
_LOCK = threading.Lock()


def load_agent(codelab_dir: Path) -> types.ModuleType:
    """Import <codelab>/agent.py once, under a unique module name."""
    codelab_dir = codelab_dir.resolve()
    with _LOCK:
        if codelab_dir not in _MODULES:
            name = "agent_" + "_".join(codelab_dir.relative_to(ROOT).parts)
            spec = importlib.util.spec_from_file_location(name, codelab_dir / "agent.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            _MODULES[codelab_dir] = module
        return _MODULES[codelab_dir]


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".mjs": "text/javascript", ".js": "text/javascript"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):  # keep demo output clean
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self):
        path = self.path.split("?")[0].strip("/")
        if "/api/" not in path:
            self.send_error(404)
            return
        codelab, name = path.split("/api/", 1)
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        entry = {"codelab": codelab, "api": name, "body": body, "events": []}
        TRANSCRIPT.append(entry)
        try:
            result = load_agent(ROOT / codelab).handle(name, body)
        except Exception as exc:  # report, do not crash the server
            result = {"error": f"{type(exc).__name__}: {exc}"}
        if isinstance(result, (dict, list)):
            entry["kind"] = "json"
            entry["events"].append(result)
            data = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        entry["kind"] = "sse"
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        try:
            for event in result:
                entry["events"].append(event)
                self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
                self.wfile.flush()
        except Exception as exc:
            error = {"type": "error", "message": f"{type(exc).__name__}: {exc}"}
            entry["events"].append(error)
            self.wfile.write(f"data: {json.dumps(error)}\n\n".encode())


def start(port: int = 0) -> ThreadingHTTPServer:
    """Start in a background thread. Port 0 picks a free port."""
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
