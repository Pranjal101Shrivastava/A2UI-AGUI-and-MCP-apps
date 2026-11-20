"""Serve every codelab from one local server: python serve.py [port]"""
import sys
import time

from shared import devserver

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
server = devserver.start(port)
print(f"GenUX codelabs on http://127.0.0.1:{server.server_port}/  (Ctrl+C to stop)")
try:
    while True:
        time.sleep(3600)
except KeyboardInterrupt:
    server.shutdown()
