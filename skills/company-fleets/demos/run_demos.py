#!/usr/bin/env python3
"""Rerun the six end-to-end demonstrations and check each against demos/demos.json.

usage: python3 demos/run_demos.py [DEMO_ID ...]

Each run writes to evidence/integration/demos/<id>/runs/<UTC stamp>/ (ledger, work, evidence, chain.json,
run.json, verify.json) and points evidence/integration/demos/<id>/latest.txt at it. Nothing is deleted.
The summary goes to evidence/integration/demos/results.json. Exit 0 when every selected demo passes.
"""
import datetime
import json
import os
import subprocess
import sys

SKILL = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FLEET = os.path.join(SKILL, "bin", "fleet")
OUT = os.path.join(SKILL, "evidence", "integration", "demos")


def fleet(*args):
    proc = subprocess.run([FLEET] + list(args), capture_output=True, text=True, cwd=SKILL, timeout=1800)
    try:
        return proc.returncode, json.loads(proc.stdout)
    except ValueError:
        return proc.returncode, {"error": proc.stdout[-2000:] + proc.stderr[-2000:]}


def judge(demo, run):
    """Every expectation the manifest states, as (ok, message)."""
    exp, steps = demo["expect"], {s["step"]: s for s in run.get("steps", [])}
    out = [(run.get("status") == exp["status"], "status %s (expected %s)" % (run.get("status"), exp["status"]))]
    if "stopped_at" in exp:
        out.append((run.get("stopped_at") == exp["stopped_at"], "stopped at %s (expected %s)" % (run.get("stopped_at"), exp["stopped_at"])))
    for step, state in exp.get("states", {}).items():
        got = steps.get(step, {}).get("state")
        out.append((got == state, "step %s is %s (expected %s)" % (step, got, state)))
    for step, fields in exp.get("refused", {}).items():
        got = sorted(steps.get(step, {}).get("refused_fields", []))
        out.append((set(fields) <= set(got), "step %s refused %s (expected at least %s)" % (step, got, fields)))
    for step, cats in exp.get("findings", {}).items():
        got = sorted({f["category"] for f in steps.get(step, {}).get("untrusted_findings", [])})
        out.append((set(cats) <= set(got), "step %s flagged %s (expected at least %s)" % (step, got, cats)))
    return out


def main(argv):
    with open(os.path.join(SKILL, "demos", "demos.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    chosen = [d for d in manifest["demos"] if not argv or d["id"] in argv]
    results = []
    for demo in chosen:
        rel = os.path.join(demo["id"], "runs", stamp)
        base = os.path.join(OUT, rel)
        os.makedirs(base)
        code, run = fleet("workflow", "run", demo["workflow"], "--fixture", demo["fixture"], "--out", base)
        with open(os.path.join(base, "run.json"), "w", encoding="utf-8") as fh:
            json.dump(run, fh, indent=2, sort_keys=True)
        vcode, ver = fleet("workflow", "verify", "--out", base) if "steps" in run else (1, {"ok": False})
        with open(os.path.join(base, "verify.json"), "w", encoding="utf-8") as fh:
            json.dump(ver, fh, indent=2, sort_keys=True)
        checks = judge(demo, run) + [(ver.get("ok") is True, "every accepted handoff re-verifies now (%s checked)" % ver.get("checked"))]
        status = "blocked" if run.get("status") == "blocked" else ("pass" if all(ok for ok, _ in checks) else "fail")
        tools = {}
        for s in run.get("steps", []):
            if s.get("tool"):
                tools[s["tool"]] = tools.get(s["tool"], 0) + 1
        loaded = run.get("fleets_loaded", [])
        results.append({"id": demo["id"], "title": demo["title"], "status": status, "workflow": demo["workflow"],
                        "run": os.path.relpath(base, SKILL), "chain_status": run.get("status"), "stopped_at": run.get("stopped_at"),
                        "steps_by_tool": tools, "fleets_loaded": loaded,
                        "depends_on_moving_fleet": sorted(set(loaded) & set(manifest["moving_at_build"]["fleets"])),
                        "checks": [{"ok": ok, "check": msg} for ok, msg in checks], "human_boundary": demo["human_boundary"]})
        with open(os.path.join(OUT, demo["id"], "latest.txt"), "w", encoding="utf-8") as fh:
            fh.write(rel + "\n")
        print("%-26s %-7s %s" % (demo["id"], status, "; ".join(m for ok, m in checks if not ok) or "all checks met"))
    summary = {"run_on": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "stamp": stamp,
               "command": "python3 demos/run_demos.py " + " ".join(argv), "label": manifest["label"], "demos": results}
    path = os.path.join(OUT, "results.json")
    if argv and os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            old = {d["id"]: d for d in json.load(fh)["demos"]}
        old.update({d["id"]: d for d in results})
        summary["demos"] = [old[d["id"]] for d in manifest["demos"] if d["id"] in old]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True)
    return 0 if all(r["status"] == "pass" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
