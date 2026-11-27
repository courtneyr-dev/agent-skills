#!/usr/bin/env python3
"""Does the composed workflow beat a single-agent baseline on the same task? Section 13 asks; this measures.

usage: python3 improvement/baseline.py

Task: demonstration 1 (Client A multilingual page with hosting handoff), same fixture, same real tools.
- Composed: `workflow.run` (lease, one handoff per step, ledger, gate), then a late edit to a reviewed page
  and `workflow.verify`.
- Baseline: one agent runs the same bound tools in order in one folder, accepts its own result, and gets
  the same late edit. It has no ledger, so nothing records what was reviewed.

Reports wall time, tool invocations, registry files read, bytes written, check failures, and which planted
faults each side catches or cannot catch. Writes evidence/integration/improvement/baseline/runs/<stamp>/
and evidence/integration/improvement/baseline.json. Nothing is deleted.
"""
import datetime
import json
import os
import sys
import time

SKILL = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(SKILL, "scripts"))

from fleetlib import workflow as wfl  # noqa: E402
from fleetlib.registry import Registry  # noqa: E402

FIXTURE = os.path.join(SKILL, "demos", "01-agency-multilingual", "fixture.json")
LATE_EDIT = "work/engineering/deliverable/donate.ar.html"


def size(path):
    return sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(path) for f in fs)


def invocations(fx, steps, tools_on):
    n = 0
    for s in steps:
        b = fx.get("tools", {}).get(s["id"]) if tools_on else None
        n += (len(b.get("produce", [])) + 1) if b else 0
    return n


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = os.path.join(SKILL, "evidence", "integration", "improvement", "baseline", "runs", stamp)
    fx = wfl.load_fixture(FIXTURE)
    wf, wsha = wfl.load_workflow("agency-engagement")
    steps, _ = wfl.route(wf, fx["needs"])

    comp = os.path.join(root, "composed")
    reg = Registry(SKILL)
    t0 = time.monotonic()
    rep = wfl.run(reg, wf, wsha, fx, comp)
    comp_wall = time.monotonic() - t0
    with open(os.path.join(comp, LATE_EDIT), "a", encoding="utf-8") as fh:
        fh.write("<!-- late edit after review -->\n")
    ver = wfl.verify(comp)

    base = os.path.join(root, "baseline")
    os.makedirs(base)
    ctx = {"skill": SKILL, "skills": reg.skills_root, "base": base, "python": sys.executable, "fixture_dir": fx["_dir"]}
    t0 = time.monotonic()
    results = []
    for s in steps:
        work = os.path.join(base, "work", s["id"])
        b = fx.get("tools", {}).get(s["id"])
        r = wfl.real_tool(s, b, dict(ctx, work=work)) if b else wfl.fake_tool(s, work, [])
        results.append({"step": s["id"], "ok": r["ok"], "exit": r["exit"], "tool": "real" if b else "fake"})
        with open(os.path.join(base, "log-%s.txt" % s["id"]), "w", encoding="utf-8") as fh:
            fh.write(r["check_text"])
    base_wall = time.monotonic() - t0
    with open(os.path.join(base, LATE_EDIT), "a", encoding="utf-8") as fh:
        fh.write("<!-- late edit after review -->\n")

    refused = {s["step"]: s.get("refused_fields", []) for s in rep["steps"] if s.get("refused_fields")}
    stale = [s["step"] for s in ver["steps"] if not s["ok"]]
    composed = {"status": rep["status"], "handoffs": sum(1 for s in rep["steps"] if s["state"] == "accepted"),
                "tool_invocations": invocations(fx, steps, True), "registry_files_read": len(rep["files_read"]),
                "wall_seconds": round(comp_wall, 2), "bytes_written": size(comp),
                "check_failures": sum(1 for s in rep["steps"] if s["state"] == "check-failed"),
                "protected_field_changes_refused": refused, "late_edit_detected_by_verify": stale}
    baseline = {"status": "self-accepted", "handoffs": 0, "tool_invocations": invocations(fx, steps, True),
                "registry_files_read": 0, "wall_seconds": round(base_wall, 2), "bytes_written": size(base),
                "check_failures": sum(1 for r in results if not r["ok"]),
                "protected_field_changes_refused": "no mechanism: the single agent owns every field, so the document's requests are refused only if the agent's own judgment refuses them, which this deterministic harness cannot measure",
                "late_edit_detected_by_verify": "no mechanism: nothing recorded which bytes were reviewed"}
    overhead = composed["wall_seconds"] - baseline["wall_seconds"]
    verdict = [
        "Content defects: equal. Both sides run the same bound tools with the same checks (%d invocations each), so neither finds a page, catalog, keyboard or restore defect the other misses; check failures %d vs %d." % (
            composed["tool_invocations"], composed["check_failures"], baseline["check_failures"]),
        "Cost: the composed run took %.2f s against %.2f s (%+.2f s, %+.0f%%), read %d registry files against 0, and wrote %d bytes against %d. One run each, composed first, so it also paid cold starts (browser launch, imports): treat the time gap as an upper bound, not a measured per-step cost." % (
            composed["wall_seconds"], baseline["wall_seconds"], overhead, 100.0 * overhead / max(baseline["wall_seconds"], 0.01),
            composed["registry_files_read"], composed["bytes_written"], baseline["bytes_written"]),
        "Governance faults: the composed run refused %d protected-field changes planted by the client document and caught the late edit in %s; the baseline has no mechanism for either." % (
            sum(len(v) for v in refused.values()), ", ".join(stale) or "no step"),
        "Where the baseline wins: a task with one tool and no handoff, owner change or later consumer gets nothing from the ledger, lease and gate, so the composed run is pure overhead there (inferred from the per-step cost above, not measured separately).",
        "Not measured: model cost and latency of real agents, correlated errors between agents, and whether a single model would have refused the document's instructions. Both sides here are deterministic scripts.",
    ]
    out = {"run_on": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "stamp": stamp,
           "command": "python3 improvement/baseline.py", "task": "demonstration 1 fixture (SYNTHETIC Fixture Co, Client A)",
           "runs": os.path.relpath(root, SKILL), "composed": composed, "baseline": baseline, "baseline_steps": results, "verdict": verdict}
    path = os.path.join(SKILL, "evidence", "integration", "improvement", "baseline.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
    print(json.dumps({"composed": composed, "baseline": {k: v for k, v in baseline.items() if not isinstance(v, str) or len(v) < 40}, "verdict": verdict}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
