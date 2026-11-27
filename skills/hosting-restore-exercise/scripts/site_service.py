#!/usr/bin/env python3
"""site_service: a disposable local stand-in for one hosted site, for restore exercises only.

  site_service.py --db PATH --port-file PATH [--tenant ID]

Serves on 127.0.0.1 with an ephemeral port, written to --port-file once it listens:
  GET  /health  200 {"ok": true, "rows": N, "content_sha256": ...} after PRAGMA quick_check;
                500 {"ok": false, "error": ...} when the database is missing, unreadable or corrupt.
  POST /write   inserts one synthetic post and returns its id.
Each request opens the database read-write without creating it, so a deleted or corrupted file shows
up on the next check instead of being masked by a cached connection or a silently created empty file.
Python 3.9+ standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict


def rows_digest(conn: sqlite3.Connection) -> str:
    """Content checksum shared by the service and the exercise: every post, in id order."""
    h = hashlib.sha256()
    for row in conn.execute("SELECT id, title FROM posts ORDER BY id"):
        h.update(json.dumps(list(row), ensure_ascii=False).encode("utf-8") + b"\n")
    return h.hexdigest()


def open_existing(db: str) -> sqlite3.Connection:
    return sqlite3.connect(pathlib.Path(db).resolve().as_uri() + "?mode=rw", uri=True, timeout=1)


def make_handler(db: str, tenant: str):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: Dict[str, Any]) -> None:
            data = json.dumps(body, sort_keys=True).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802 (http.server naming)
            if self.path != "/health":
                self._send(404, {"ok": False, "error": "not found"})
                return
            try:
                conn = open_existing(db)
                try:
                    check = conn.execute("PRAGMA quick_check").fetchone()[0]
                    if check != "ok":
                        raise sqlite3.DatabaseError("quick_check: %s" % check)
                    rows = conn.execute("SELECT count(*) FROM posts").fetchone()[0]
                    digest = rows_digest(conn)
                finally:
                    conn.close()
            except sqlite3.Error as exc:
                self._send(500, {"ok": False, "tenant": tenant, "error": str(exc)})
                return
            self._send(200, {"ok": True, "tenant": tenant, "rows": rows, "content_sha256": digest})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/write":
                self._send(404, {"ok": False, "error": "not found"})
                return
            try:
                conn = open_existing(db)
                try:
                    with conn:
                        cur = conn.execute("INSERT INTO posts (title) VALUES (?)", ("synthetic write",))
                    new_id = cur.lastrowid
                finally:
                    conn.close()
            except sqlite3.Error as exc:
                self._send(500, {"ok": False, "error": str(exc)})
                return
            self._send(200, {"ok": True, "id": new_id})

        def log_message(self, *args: Any) -> None:
            pass

    return Handler


def main() -> int:
    ap = argparse.ArgumentParser(prog="site_service")
    ap.add_argument("--db", required=True)
    ap.add_argument("--port-file", required=True)
    ap.add_argument("--tenant", default="tenant-a")
    args = ap.parse_args()
    server = HTTPServer(("127.0.0.1", 0), make_handler(args.db, args.tenant))
    tmp = args.port_file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"port": server.server_address[1], "pid": os.getpid()}, fh)
    os.replace(tmp, args.port_file)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
