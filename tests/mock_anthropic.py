"""A fake Anthropic Messages endpoint that plays a fixed script, to test the Claude agent loop
without an API key."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

SCRIPT = [
    [("get_mission", {})],
    [("test_drop", {"heading": 0, "altitude": 90, "speed": 60, "x": -400, "y": -120}),     # two calls in one turn
     ("test_drop", {"heading": 180, "altitude": 90, "speed": 60, "x": 400, "y": 120})],
    [("compare", {"drag": 0.035, "wind_speed": 8, "wind_dir": 90, "shear": 0.2, "veer": 0, "updraft": 5})],
    [("begin_operation", {})],
    None,                                                                                  # text only: must be nudged
    [("declare_done", {})],
]
SEEN = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):       # Models API lookup: this fake model reports no capabilities
        out = json.dumps({"id": "claude-opus-5-5", "type": "model", "display_name": "mock", "created_at": "2026-01-01T00:00:00Z"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SEEN.append({"path": self.path, "body": body, "beta": self.headers.get("anthropic-beta")})
        turns = [m for m in body["messages"] if m["role"] == "assistant"]
        step = len(turns)
        item = SCRIPT[step] if step < len(SCRIPT) else None
        content = [{"type": "thinking", "thinking": f"plan for step {step}", "signature": f"sig{step}"}]
        if item is None:
            content.append({"type": "text", "text": "Let me think about the next step."})
            stop = "end_turn"
        else:
            content += [{"type": "tool_use", "id": f"toolu_{step}_{i}", "name": n, "input": a} for i, (n, a) in enumerate(item)]
            stop = "tool_use"
        out = json.dumps({"id": f"msg_{step}", "type": "message", "role": "assistant", "model": body["model"],
                          "content": content, "stop_reason": stop, "stop_sequence": None,
                          "usage": {"input_tokens": 100, "output_tokens": 20, "cache_read_input_tokens": 50,
                                    "cache_creation_input_tokens": 10}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


def start() -> tuple[HTTPServer, str]:
    SEEN.clear()
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"
