#!/usr/bin/env python3
"""Assert facts about JSON reports a demo step produced; prints each file's assertions and exits 1 on any miss.

usage: check_json.py FILE [FILE...] -- ASSERTION [ASSERTION...]
  path=VALUE    the dotted path equals the JSON value (true, 0, "text", [])
  path!=VALUE   the dotted path differs from the JSON value
  path~         the path exists and is non-empty or truthy
  path>=N       the number at the path is at least N
List indices are numbers in the path (findings.0.rule). `*.key` collects key across a list or object.
"""
import json
import sys


def get(node, path):
    for part in path.split("."):
        if part == "*":
            continue
        if isinstance(node, list):
            if part.isdigit():
                node = node[int(part)]
            else:
                node = [x.get(part) if isinstance(x, dict) else None for x in node]
        elif isinstance(node, dict):
            if part not in node and all(isinstance(v, dict) for v in node.values()) and node:
                node = [v.get(part) for v in node.values()]
            else:
                node = node[part]
        else:
            raise KeyError(path)
    return node


def check(doc, a):
    for op in ("!=", ">=", "="):
        if op in a:
            path, raw = a.split(op, 1)
            try:
                want = json.loads(raw)
            except ValueError:
                want = raw
            got = get(doc, path)
            ok = {"=": got == want, "!=": got != want, ">=": isinstance(got, (int, float)) and got >= want}[op]
            return ok, "%s %s %s (got %s)" % (path, op, json.dumps(want), json.dumps(got))
    path = a.rstrip("~")
    got = get(doc, path)
    return bool(got), "%s is non-empty (got %s)" % (path, json.dumps(got)[:200])


def main(argv):
    if "--" not in argv:
        print(__doc__)
        return 2
    i = argv.index("--")
    files, asserts = argv[:i], argv[i + 1:]
    failed = 0
    for f in files:
        with open(f, encoding="utf-8") as fh:
            doc = json.load(fh)
        print("# %s" % f.rsplit("/work/", 1)[-1])
        for a in asserts:
            try:
                ok, msg = check(doc, a)
            except (KeyError, IndexError, TypeError) as exc:
                ok, msg = False, "%s: path missing (%s)" % (a, exc)
            failed += not ok
            print("%s %s" % ("PASS" if ok else "FAIL", msg))
    print("result: %s" % ("FAIL" if failed else "PASS"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
