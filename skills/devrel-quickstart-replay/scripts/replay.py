#!/usr/bin/env python3
"""Replay a quickstart's runnable blocks in a clean, disposable environment.

A block runs when its fence info string carries tier=run (the docs-code-sample-standards convention)
and its language is sh or bash. A following fence whose info string carries `expect` lists output
lines that step must print; `<placeholder>` inside an expected line matches any non-space text.
Front matter may declare `replay_requires: python3, sh` and `replay_budget_seconds: 60`.

Clean means: a fresh temporary directory, an empty HOME, a four-key environment (nothing inherited),
and on macOS a sandbox-exec profile that denies outbound network except localhost and denies reads
under the invoking user's home. Every process the steps start is killed when the replay ends.

Exit 0: every step ran, every expected line appeared, the budget held.
Exit 1: the replay failed; the JSON report names the step and the reason.
Exit 2: invalid input (missing file, no runnable block, expect before any step, unclosed fence).
"""
import argparse
import hashlib
import json
import os
import pwd
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

VERSION = "1.0.0"
FENCE = re.compile(r"^(`{3,}|~{3,})\s*([^\s`]*)\s*(.*)$")
SHELLS = {"sh", "bash"}
SKIP = {"__pycache__", ".DS_Store", ".git"}
END = "::replay-end::"
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
OUTPUT_CAP = 20000
UNVERIFIED_READER = "unverified: needs an unfamiliar human reader; a replay can't measure it"


class InputError(Exception):
    pass


def parse(text):
    """Return (front matter, steps). A step is {n, line, code, expect}."""
    lines = text.splitlines()
    front, i = {}, 0
    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                for raw in lines[1:j]:
                    key, sep, value = raw.partition(":")
                    if sep:
                        front[key.strip()] = value.strip()
                i = j + 1
                break
    steps = []
    while i < len(lines):
        m = FENCE.match(lines[i].strip())
        if not m:
            i += 1
            continue
        fence, lang, info = m.groups()
        opened = i + 1
        body, i = [], i + 1
        while i < len(lines) and not lines[i].strip().startswith(fence):
            body.append(lines[i])
            i += 1
        if i >= len(lines):
            raise InputError("fence opened at line %d is never closed" % opened)
        i += 1
        attrs = info.split()
        if "tier=run" in attrs:
            if lang not in SHELLS:
                raise InputError("line %d: a tier=run block must be sh or bash, not %r" % (opened, lang or "unlabeled"))
            steps.append({"n": len(steps) + 1, "line": opened, "code": "\n".join(body), "expect": []})
        elif "expect" in attrs:
            if not steps:
                raise InputError("line %d: an expect block comes before any tier=run block" % opened)
            steps[-1]["expect"].extend(x.strip() for x in body if x.strip())
    if not steps:
        raise InputError("no tier=run block found; nothing to replay")
    return front, steps


def pattern(expected):
    parts = re.split(r"<[^<>\s][^<>]*>", expected)
    return re.compile(r"\S+".join(re.escape(p) for p in parts))


def match_in_order(expected, output):
    """Each expected line must match a whole later output line (trimmed) than the one before it."""
    lines, pos, results = output.splitlines(), 0, []
    for exp in expected:
        rx, found = pattern(exp), False
        for k in range(pos, len(lines)):
            if rx.fullmatch(lines[k].strip()):
                found, pos = True, k + 1
                break
        results.append({"expected": exp, "found": found})
    return results


def tree_sha(root):
    h = hashlib.sha256()
    for dirpath, dirnames, filenames in sorted(os.walk(root)):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP)
        for f in sorted(x for x in filenames if x not in SKIP):
            p = os.path.join(dirpath, f)
            with open(p, "rb") as fh:
                h.update(os.path.relpath(p, root).encode() + b"\0" + hashlib.sha256(fh.read()).digest())
    return h.hexdigest()


def complete(text):
    """True when text is one or more whole shell commands: no open heredoc or continuation, and bash parses it."""
    lines = text.split("\n")
    if lines[-1].rstrip().endswith("\\"):
        return False
    pending = []
    for line in lines:
        if pending:
            if line.strip() == pending[0]:
                pending.pop(0)
        else:
            pending.extend(m.group(2) for m in HEREDOC.finditer(line))
    if pending:
        return False
    p = subprocess.run(["/bin/bash", "-n"], input=text + "\n", capture_output=True, text=True)
    return p.returncode == 0 and not p.stderr


def split_commands(code):
    """Split a block into whole commands. A remainder bash can't parse stays one command and fails when run."""
    out, buf = [], []
    for line in code.split("\n"):
        buf.append(line)
        text = "\n".join(buf)
        if complete(text):
            if any(x.strip() and not x.strip().startswith("#") for x in buf):
                out.append(text)
            buf = []
    if any(x.strip() for x in buf):
        out.append("\n".join(buf))
    return out


def build_script(steps):
    """One bash run so state carries between steps, with every command's exit status checked on its own:
    set -e misses failures inside && lists and after a doc's own set +e, and pipefail catches pipelines."""
    out = ["set -e -o pipefail"]
    for s in steps:
        out.append("printf '\\n::replay-step %d::\\n'" % s["n"])
        for k, cmd in enumerate(s["commands"], 1):
            out.append("printf '\\n::replay-cmd %d %d::\\n'" % (s["n"], k))
            out.append(cmd)
            out.append('__replay_rc=$?; [ "$__replay_rc" -eq 0 ] || exit "$__replay_rc"')
    out.append("printf '\\n%s\\n'" % END)
    return "\n".join(out) + "\n"


def split_output(output):
    """Map step number to the text it printed, and report the last step and command that started."""
    seg, current, last, cmd = {}, None, 0, 0
    for line in output.splitlines():
        m = re.fullmatch(r"::replay-step (\d+)::", line)
        c = re.fullmatch(r"::replay-cmd (\d+) (\d+)::", line)
        if m:
            current = last = int(m.group(1))
            seg[current], cmd = [], 0
        elif c:
            cmd = int(c.group(2))
        elif line == END:
            current = None
        elif current is not None:
            seg[current].append(line)
    return {k: "\n".join(v) for k, v in seg.items()}, last, cmd, END in output.splitlines()


def clean_env(root):
    return {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": os.path.join(root, "home"),
            "LANG": "C.UTF-8", "TMPDIR": os.path.join(root, "tmp")}


def sandbox(root):
    if sys.platform != "darwin" or not os.path.exists("/usr/bin/sandbox-exec"):
        return [], "none: sandbox-exec is unavailable here, so isolation is the fresh directory and four-key environment only"
    home = pwd.getpwuid(os.getuid()).pw_dir
    profile = ('(version 1)(allow default)(deny network-outbound)'
               '(allow network-outbound (remote ip "localhost:*"))'
               '(deny file-read* (subpath "%s"))(allow file-read* (subpath "%s"))' % (home, os.path.realpath(root)))
    return (["/usr/bin/sandbox-exec", "-p", profile],
            "sandbox-exec: outbound network denied except localhost; reads under the invoking user's home denied")


def kill_group(pgid):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            return
        time.sleep(0.3)


def replay(doc, assets, timeout, keep=False):
    with open(doc, "r", encoding="utf-8") as fh:
        text = fh.read()
    front, steps = parse(text)
    for s in steps:
        s["commands"] = split_commands(s["code"])
    budget = front.get("replay_budget_seconds")
    try:
        budget = float(budget) if budget else None
    except ValueError:
        raise InputError("replay_budget_seconds must be a number, got %r" % budget)
    requires = [r.strip() for r in front.get("replay_requires", "").split(",") if r.strip()]
    for a in assets:
        if not os.path.isdir(a):
            raise InputError("asset %s is not a directory" % a)

    root = os.path.realpath(tempfile.mkdtemp(prefix="replay-"))
    work = os.path.join(root, "work")
    for d in ("home", "tmp", "work"):
        os.makedirs(os.path.join(root, d))
    for a in assets:
        shutil.copytree(a, os.path.join(work, os.path.basename(os.path.normpath(a))),
                        ignore=shutil.ignore_patterns(*SKIP))
    env = clean_env(root)
    wrap, isolation = sandbox(root)
    report = {
        "tool": "devrel-quickstart-replay", "version": VERSION, "doc": doc,
        "doc_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "assets": [{"name": os.path.basename(os.path.normpath(a)), "tree_sha256": tree_sha(a)} for a in assets],
        "isolation": {"workdir": "fresh temporary directory, %s after the run" % ("kept" if keep else "removed"),
                      "env_keys": sorted(env), "sandbox": isolation},
        "prerequisites": [], "steps": [], "elapsed_s": 0.0, "budget_s": budget,
    }
    try:
        for r in requires:
            found = subprocess.run(wrap + ["/bin/sh", "-c", 'command -v "$1" >/dev/null', "sh", r],
                                   cwd=work, env=env).returncode == 0
            report["prerequisites"].append({"name": r, "found": found})
        missing = [p["name"] for p in report["prerequisites"] if not p["found"]]
        if missing:
            return finish(report, "declared prerequisite not on the clean PATH: " + ", ".join(missing), steps, {}, 0, False, "")

        script = os.path.join(root, "replay.sh")
        log = os.path.join(root, "output.log")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(build_script(steps))
        start = time.monotonic()
        with open(log, "wb") as out:
            proc = subprocess.Popen(wrap + ["/bin/bash", script], cwd=work, env=env, stdout=out,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            timed_out = False
            try:
                code = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out, code = True, None
            kill_group(proc.pid)
            proc.wait()
        report["elapsed_s"] = round(time.monotonic() - start, 3)
        with open(log, "r", encoding="utf-8", errors="replace") as fh:
            output = fh.read()
        segments, last, cmd, marker = split_output(output)
        completed = marker and code == 0 and not timed_out
        failure = None
        if timed_out:
            failure = "step %d still running after the %ss timeout" % (last, timeout)
        elif not completed:
            failure = "step %d exited %s" % (last, code)
            if last and 0 < cmd <= len(steps[last - 1]["commands"]):
                failure += " at command %d: %s" % (cmd, steps[last - 1]["commands"][cmd - 1].split("\n")[0].strip())
        return finish(report, failure, steps, segments, last, completed, output)
    finally:
        if keep:
            report["isolation"]["kept_at"] = root
        else:
            shutil.rmtree(root, ignore_errors=True)


def finish(report, failure, steps, segments, last, completed, output):
    matched_all = True
    for s in steps:
        ran = completed or s["n"] <= last
        exit_ok = completed or s["n"] < last
        expect = match_in_order(s["expect"], segments.get(s["n"], "")) if ran else \
            [{"expected": e, "found": False} for e in s["expect"]]
        if ran and not all(e["found"] for e in expect):
            matched_all = False
            if failure is None:
                missing = next(e["expected"] for e in expect if not e["found"])
                failure = "step %d (line %d) did not print the expected line %r" % (s["n"], s["line"], missing)
        report["steps"].append({"n": s["n"], "line": s["line"], "ran": ran, "succeeded": ran and exit_ok, "expect": expect})
    budget = report["budget_s"]
    within = report["elapsed_s"] <= budget if budget is not None else None
    if failure is None and within is False:
        failure = "elapsed %.1fs exceeds the declared budget of %ss" % (report["elapsed_s"], budget)
    commands_ok = bool(report["steps"]) and all(s["succeeded"] for s in report["steps"])
    report["criteria"] = {
        "1_commands_succeed_verbatim": commands_ok,
        "2_outputs_match": commands_ok and matched_all,
        "3_no_late_prerequisites": commands_ok and all(p["found"] for p in report["prerequisites"]),
        "4_within_budget": within if within is not None else "no budget declared",
        "5_unfamiliar_reader_success": UNVERIFIED_READER,
    }
    report["ok"] = failure is None
    report["failure"] = failure
    report["output"] = output if len(output) <= OUTPUT_CAP else output[:OUTPUT_CAP] + "\n[truncated]"
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="Replay a quickstart's tier=run blocks in a clean environment.")
    ap.add_argument("doc", help="Markdown quickstart, tutorial, lab or repro")
    ap.add_argument("--asset", action="append", default=[], help="directory copied into the clean workdir (repeatable)")
    ap.add_argument("--timeout", type=float, default=300.0, help="hard stop in seconds (default 300)")
    ap.add_argument("--keep", action="store_true", help="keep the workdir for inspection")
    args = ap.parse_args(argv)
    if not os.path.isfile(args.doc):
        print(json.dumps({"ok": False, "error": "no such file: %s" % args.doc}))
        return 2
    try:
        report = replay(args.doc, args.asset, args.timeout, args.keep)
    except InputError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
