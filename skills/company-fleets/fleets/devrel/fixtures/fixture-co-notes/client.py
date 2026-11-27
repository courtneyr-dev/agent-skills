#!/usr/bin/env python3
"""Fixture Co Notes API sample client. SYNTHETIC FIXTURE.

Finds the server from --port-file (waiting up to 5 seconds for it to appear) or from the
FIXTURE_NOTES_PORT environment variable.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request


def port(args):
    if args.port_file:
        for _ in range(50):
            if os.path.exists(args.port_file) and open(args.port_file).read().strip():
                return open(args.port_file).read().strip()
            time.sleep(0.1)
        sys.exit("error: %s never appeared; is the server running?" % args.port_file)
    if os.environ.get("FIXTURE_NOTES_PORT"):
        return os.environ["FIXTURE_NOTES_PORT"]
    print("error: no server address: pass --port-file or set FIXTURE_NOTES_PORT", file=sys.stderr)
    sys.exit(2)


def call(base, method, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(base + "/notes", data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    for attempt in range(20):
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            print("error: HTTP %d %s" % (exc.code, json.loads(exc.read()).get("error", "")))
            sys.exit(1)
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.1)
    sys.exit("error: could not reach %s" % base)


def main():
    ap = argparse.ArgumentParser(description="Fixture Co Notes API sample client (synthetic)")
    ap.add_argument("--port-file")
    sub = ap.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add")
    add.add_argument("title")
    ls = sub.add_parser("list")
    ls.add_argument("--contains", default="")
    args = ap.parse_args()
    base = "http://127.0.0.1:%s" % port(args)
    if args.cmd == "add":
        note = call(base, "POST", {"title": args.title})
        print("created note %d: %s" % (note["id"], note["title"]))
    else:
        for note in call(base, "GET")["notes"]:
            if args.contains.lower() in note["title"].lower():
                print("%d  %s" % (note["id"], note["title"]))


if __name__ == "__main__":
    main()
