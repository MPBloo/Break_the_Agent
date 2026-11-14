"""A fake OpenAI-compatible endpoint that plays a fixed script. Lets us test the LLM agent loop
(tool-call plumbing, error handling, stopping) without any API key."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

SCRIPT = [
    ("get_mission", {}),
    ("test_drop", {"heading": 0, "altitude": 90, "speed": 60, "x": -400, "y": -120}),
    ("compare", {"drag": 0.035, "wind_speed": 8, "wind_dir": 90, "shear": 0.2, "veer": 0, "updraft": 5}),
    ("test_drop", "this is not json"),
    ("begin_operation", {}),
    ("drop", {"target": 1, "heading": 0, "altitude": 90, "speed": 60, "x": 0, "y": 0}),
    None,   # a turn with plain text and no tool call: the loop must nudge
    ("declare_done", {}),
]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        step = sum(1 for m in body["messages"] if m["role"] == "assistant")
        item = SCRIPT[step] if step < len(SCRIPT) else None
        if item is None:
            msg = {"role": "assistant", "content": "Thinking about what to do next."}
        else:
            name, args = item
            msg = {"role": "assistant", "content": f"Calling {name}.", "tool_calls": [{
                "id": f"call_{step}", "type": "function", "extra_content": {"opaque": "must be echoed"},
                "function": {"name": name, "arguments": args if isinstance(args, str) else json.dumps(args)}}]}
        prev = [m for m in body["messages"] if m["role"] == "assistant" and m.get("tool_calls")]
        assert all("extra_content" in m["tool_calls"][0] for m in prev), "assistant messages were not echoed verbatim"
        out = json.dumps({"choices": [{"message": msg}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


def start() -> tuple[HTTPServer, str]:
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"
