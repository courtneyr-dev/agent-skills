#!/usr/bin/env python3
"""Fixture Co Notes API sample server. SYNTHETIC FIXTURE: Fixture Co and this API are invented.

Listens on 127.0.0.1 only, on a free port written to --port-file (or a fixed --port), keeps notes in
memory, and stops by itself after --max-seconds so nothing outlives a demo.

Known defect, kept on purpose for the feedback-to-product demonstration: POST /notes with an empty
title returns HTTP 500 instead of a 400 validation error.
"""
import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

NOTES = []
LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body):
        data = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path != "/notes":
            return self._send(404, {"error": "not found"})
        with LOCK:
            return self._send(200, {"notes": list(NOTES)})

    def do_POST(self):
        if self.path != "/notes":
            return self._send(404, {"error": "not found"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            title = body.get("title")
            if title is None:
                return self._send(400, {"error": "title is required"})
            with LOCK:
                note = {"id": len(NOTES) + 1, "title": title, "slug": title.split()[0].lower()}
                NOTES.append(note)
            return self._send(201, note)
        except Exception:
            return self._send(500, {"error": "internal error"})

    def log_message(self, *args):
        pass


def main():
    ap = argparse.ArgumentParser(description="Fixture Co Notes API sample server (synthetic)")
    ap.add_argument("--port", type=int, default=0, help="fixed port; 0 picks a free one")
    ap.add_argument("--port-file", help="write the chosen port here")
    ap.add_argument("--max-seconds", type=float, default=60.0)
    args = ap.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    if args.port_file:
        with open(args.port_file, "w") as fh:
            fh.write(str(server.server_address[1]))
    threading.Timer(args.max_seconds, server.shutdown).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
