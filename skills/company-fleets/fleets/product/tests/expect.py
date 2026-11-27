#!/usr/bin/env python3
"""Run one command and check its exit code and output. An eval's argv wraps the real command with this,
so the eval passes exactly when the wrapped command behaved as the case expects.

usage: expect.py --exit N [--contains S]... [--absent S]... -- command args...

"{tmp}" in the command becomes a fresh temporary directory, removed afterwards (disposable stores).
Prints the command, its raw stdout and stderr, then one CHECK line per expectation and a VERDICT.
Exit 0 when every check holds, 1 otherwise, 2 for usage errors.
"""
import argparse
import shutil
import subprocess
import sys
import tempfile


def main(argv):
    if "--" not in argv:
        print("usage: expect.py --exit N [--contains S]... [--absent S]... -- command args...")
        return 2
    split = argv.index("--")
    ap = argparse.ArgumentParser(prog="expect")
    ap.add_argument("--exit", type=int, required=True, dest="code")
    ap.add_argument("--contains", action="append", default=[])
    ap.add_argument("--absent", action="append", default=[])
    opts = ap.parse_args(argv[:split])
    tmp = tempfile.mkdtemp(prefix="fleet-eval-")
    try:
        cmd = [a.replace("{tmp}", tmp) for a in argv[split + 1:]]
        if cmd and cmd[0] == "python3":
            cmd[0] = sys.executable
        p = subprocess.run(cmd, capture_output=True, text=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out = p.stdout + p.stderr
    print("$ " + " ".join(argv[split + 1:]))
    print(p.stdout.rstrip())
    if p.stderr.strip():
        print("stderr:\n" + p.stderr.rstrip())
    print("exit=%d" % p.returncode)
    checks = [("exit == %d" % opts.code, p.returncode == opts.code)]
    checks += [("contains %r" % s, s in out) for s in opts.contains]
    checks += [("absent %r" % s, s not in out) for s in opts.absent]
    for label, ok in checks:
        print("CHECK %s: %s" % (label, "ok" if ok else "FAIL"))
    passed = all(ok for _, ok in checks)
    print("VERDICT %s" % ("pass" if passed else "fail"))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
