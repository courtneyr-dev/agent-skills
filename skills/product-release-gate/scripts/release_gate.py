#!/usr/bin/env python3
"""Packaging gate for an extension, theme, integration, SDK or SaaS release candidate.

Stages run in a fixed order. Compatibility runs first and, when it fails, the gate stops there: an
incompatible host or API version is refused before any packaging stage is considered. Every later
stage reports its own errors. The gate never approves; a ready candidate goes to the human approval
owner named in the output.

Adapters, each found beside this skill in the rig and reported as blocked when absent:
  release-engineering/scripts/semver_check.py and changelog_check.py (magnus919/agent-skills)
  company-fleets/scripts/fleetlib (handoff validation and stale-evidence checks, over factory-rig)

Subcommands:
  compat  --matrix M                  compatibility stage only
  gate    --candidate C               every stage; paths inside C are relative to C's directory

Exit: 0 compatible / ready for human approval, 1 refused or blocked, 2 invalid input.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS_ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SEMVER = os.path.join(SKILLS_ROOT, "release-engineering", "scripts", "semver_check.py")
CHANGELOG = os.path.join(SKILLS_ROOT, "release-engineering", "scripts", "changelog_check.py")
FLEETLIB = os.path.join(SKILLS_ROOT, "company-fleets", "scripts")
CHECKLISTS = os.path.join(HERE, "..", "references", "marketplace-checklists.json")

API_CHANGES = ("none", "additive", "breaking")
CHANNELS = ("stable", "beta", "nightly")
BLOCKING_SEVERITIES = ("critical", "high")
APPROVAL_OWNER = "human:release-owner"


class InvalidInput(Exception):
    pass


def err(code: str, message: str) -> Dict[str, str]:
    return {"code": code, "message": message}


# ---- boundary ----

def load(path: str, schema: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise InvalidInput("cannot read %s: %s" % (path, exc))
    if not isinstance(doc, dict) or doc.get("schema") != schema:
        raise InvalidInput("%s is not schema %s" % (path, schema))
    return doc


def need(doc: Dict[str, Any], where: str, fields: Dict[str, type]) -> None:
    for field, kind in fields.items():
        if not isinstance(doc.get(field), kind):
            raise InvalidInput("%s needs %s (%s)" % (where, field, kind.__name__))


def parse_matrix(path: str) -> Dict[str, Any]:
    m = load(path, "compat-matrix.v1")
    need(m, path, {"product": dict, "declares": dict, "platform_facts": dict, "tests": list})
    need(m["product"], path + " product", {"id": str, "platform": str, "version": str})
    need(m["declares"], path + " declares", {"hosts": dict, "apis": dict})
    need(m["platform_facts"], path + " platform_facts", {"source": dict, "host_versions": dict, "api_versions_served": dict})
    for host, rng in m["declares"]["hosts"].items():
        if not (isinstance(rng, dict) and isinstance(rng.get("min"), str) and isinstance(rng.get("max"), str)):
            raise InvalidInput("%s declares.hosts.%s needs min and max strings" % (path, host))
    for t in m["tests"]:
        if not (isinstance(t, dict) and all(isinstance(t.get(k), str) for k in ("host", "version", "result"))):
            raise InvalidInput("%s tests need host, version and result strings" % path)
        if t["result"] not in ("pass", "fail"):
            raise InvalidInput("%s test result must be pass or fail, got %s" % (path, t["result"]))
    return m


def parse_candidate(path: str) -> Dict[str, Any]:
    c = load(path, "release-candidate.v1")
    need(c, path, {"product": dict, "public_api_change": str, "channel": str, "distribution": str,
                   "compat_matrix": str, "changelog": str, "sbom": str, "license_policy": dict,
                   "vulnerabilities": list, "support_boundary": str, "evidence": dict})
    need(c["product"], path + " product", {"id": str, "platform": str, "version": str, "previous_version": str})
    need(c["license_policy"], path + " license_policy", {"allowed": list})
    need(c["evidence"], path + " evidence", {"handoff": str, "contract": str, "base": str})
    if c["public_api_change"] not in API_CHANGES:
        raise InvalidInput("%s public_api_change must be one of %s" % (path, ", ".join(API_CHANGES)))
    if c["channel"] not in CHANNELS:
        raise InvalidInput("%s channel must be one of %s" % (path, ", ".join(CHANNELS)))
    if c["distribution"] not in ("marketplace", "direct"):
        raise InvalidInput("%s distribution must be marketplace or direct" % path)
    return c


# ---- stages (pure where possible) ----

def vkey(v: str) -> Tuple[int, ...]:
    return tuple(int(p) for p in re.split(r"[.-]", v) if p.isdigit())


def compatibility(m: Dict[str, Any], product: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    errors = []
    facts = m["platform_facts"]
    src = facts["source"]
    if not (src.get("ref") and src.get("revision") and src.get("retrieved")):
        errors.append(err("platform-facts-unsourced", "platform_facts.source needs ref, revision and retrieved"))
    if product is not None:
        for field in ("id", "platform", "version"):
            if m["product"][field] != product[field]:
                errors.append(err("matrix-product-mismatch", "compatibility matrix is for %s %s, candidate is %s"
                                  % (field, m["product"][field], product[field])))
    results: Dict[Tuple[str, str], List[str]] = {}
    for t in m["tests"]:
        results.setdefault((t["host"], t["version"]), []).append(t["result"])
    if not m["declares"]["hosts"]:
        errors.append(err("no-hosts-declared", "the matrix declares no host; every product runs on something that must be tested"))
    for host, rng in sorted(m["declares"]["hosts"].items()):
        known = facts["host_versions"].get(host)
        if not known:
            errors.append(err("host-unknown", "no platform facts for host %s" % host))
            continue
        for bound in ("min", "max"):
            if rng[bound] not in known:
                errors.append(err("declared-version-unknown", "%s %s %s is not a known %s version" % (host, bound, rng[bound], host)))
        lo, hi = vkey(rng["min"]), vkey(rng["max"])
        if lo > hi:
            errors.append(err("declared-range-inverted", "%s min %s is above max %s" % (host, rng["min"], rng["max"])))
            continue
        in_range = [v for v in known if lo <= vkey(v) <= hi]
        if not any(results.get((host, v)) == ["pass"] for v in in_range):
            errors.append(err("host-untested", "no %s version in %s-%s has a passing test" % (host, rng["min"], rng["max"])))
        for version in sorted(known, key=vkey):
            if not lo <= vkey(version) <= hi:
                continue
            got = results.get((host, version), [])
            if "fail" in got:
                errors.append(err("incompatible-host", "%s %s is inside the declared range %s-%s and its test failed"
                                  % (host, version, rng["min"], rng["max"])))
            elif not got:
                errors.append(err("untested-host-version", "%s %s is inside the declared range %s-%s and has no test result"
                                  % (host, version, rng["min"], rng["max"])))
    for api, version in sorted(m["declares"]["apis"].items()):
        served = facts["api_versions_served"].get(api)
        if served is None:
            errors.append(err("api-unknown", "no platform facts for API %s" % api))
        elif version not in served:
            errors.append(err("api-version-not-served", "%s version %s is not among the versions served (%s)"
                              % (api, version, ", ".join(served))))
    return errors


def run_json(argv: List[str]) -> Tuple[int, Any]:
    p = subprocess.run([sys.executable] + argv, capture_output=True, text=True)
    try:
        return p.returncode, json.loads(p.stdout)
    except ValueError:
        return p.returncode, {"raw": (p.stdout + p.stderr)[:400]}


def semver(c: Dict[str, Any]) -> List[Dict[str, str]]:
    prod = c["product"]
    code, cur = run_json([SEMVER, "--check", prod["version"], "--json"])
    if code != 0:
        return [err("version-invalid", "version %s is not SemVer 2.0.0: %s" % (prod["version"], cur.get("reason")))]
    code, prev = run_json([SEMVER, "--check", prod["previous_version"], "--json"])
    if code != 0:
        return [err("version-invalid", "previous_version %s is not SemVer 2.0.0" % prod["previous_version"])]
    _, rel = run_json([SEMVER, "--compare", prod["previous_version"], prod["version"], "--json"])
    errors = []
    if rel.get("relation") != "lt":
        errors.append(err("version-not-increasing", "%s is not greater than %s" % (prod["version"], prod["previous_version"])))
    a, b = prev["parsed"], cur["parsed"]
    if c["public_api_change"] == "breaking":
        ok = b["major"] > a["major"] or (a["major"] == 0 and b["major"] == 0 and b["minor"] > a["minor"])
        if not ok:
            errors.append(err("breaking-change-without-major", "a breaking public API change from %s needs a major bump, got %s"
                              % (prod["previous_version"], prod["version"])))
    elif c["public_api_change"] == "additive" and (b["major"], b["minor"]) == (a["major"], a["minor"]):
        errors.append(err("additive-change-without-minor", "an additive API change needs at least a minor bump"))
    if c["channel"] == "stable" and b["prerelease"]:
        errors.append(err("channel-prerelease-mismatch", "stable channel cannot ship pre-release %s" % prod["version"]))
    if c["channel"] != "stable" and not b["prerelease"]:
        errors.append(err("channel-prerelease-mismatch", "%s channel needs a pre-release version" % c["channel"]))
    return errors


def changelog(c: Dict[str, Any], base: str) -> List[Dict[str, str]]:
    path = os.path.join(base, c["changelog"])
    code, out = run_json([CHANGELOG, path, "--json"])
    errors = [err("changelog-invalid", "line %s: %s" % (p.get("line"), p.get("message"))) for p in out.get("problems", [])]
    if code != 0 and not errors:
        errors.append(err("changelog-invalid", str(out)[:200]))
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        text = ""
    if not re.search(r"^## \[%s\]" % re.escape(c["product"]["version"]), text, re.M):
        errors.append(err("changelog-missing-version", "no changelog entry for %s" % c["product"]["version"]))
    return errors


def supply_chain(c: Dict[str, Any], base: str) -> List[Dict[str, str]]:
    try:
        with open(os.path.join(base, c["sbom"]), encoding="utf-8") as fh:
            sbom = json.load(fh)
    except (OSError, ValueError) as exc:
        return [err("sbom-unreadable", str(exc))]
    if sbom.get("bomFormat") != "CycloneDX" or not isinstance(sbom.get("components"), list):
        return [err("sbom-unreadable", "expected a CycloneDX JSON document with components")]
    allowed = set(c["license_policy"]["allowed"])
    errors, names = [], set()
    for comp in sbom["components"]:
        name = "%s@%s" % (comp.get("name"), comp.get("version"))
        names.add(comp.get("name"))
        ids = [l.get("license", {}).get("id") for l in comp.get("licenses", []) if isinstance(l, dict)]
        ids = [i for i in ids if i]
        if not ids:
            errors.append(err("license-unknown", "%s has no SPDX license id; a human license review decides" % name))
        for i in ids:
            if i not in allowed:
                errors.append(err("license-not-allowed", "%s is %s, not in the allowed list" % (name, i)))
    for v in c["vulnerabilities"]:
        if v.get("component") not in names:
            errors.append(err("vulnerability-unknown-component", "%s names %s, which the SBOM lacks" % (v.get("id"), v.get("component"))))
        if v.get("status") == "open" and v.get("severity") in BLOCKING_SEVERITIES:
            errors.append(err("open-vulnerability", "%s (%s) in %s is open" % (v.get("id"), v.get("severity"), v.get("component"))))
        if v.get("status") == "not-affected" and not v.get("justification"):
            errors.append(err("vex-justification-missing", "%s is marked not-affected without a justification" % v.get("id")))
    return errors


def migration(c: Dict[str, Any]) -> List[Dict[str, str]]:
    mig = c.get("migration")
    if not isinstance(mig, dict) or "schema_from" not in mig or "schema_to" not in mig:
        return [err("migration-undeclared", "declare migration.schema_from and schema_to, equal when the schema does not change")]
    if mig.get("schema_from") == mig.get("schema_to"):
        return []
    errors = []
    if mig.get("up") != "pass":
        errors.append(err("migration-untested", "schema %s to %s has no passing upgrade test" % (mig.get("schema_from"), mig.get("schema_to"))))
    if mig.get("down") != "pass":
        errors.append(err("rollback-untested", "schema %s to %s has no passing rollback test" % (mig.get("schema_from"), mig.get("schema_to"))))
    if not mig.get("data_retention"):
        errors.append(err("retention-undefined", "a schema change needs a data-retention statement for rollback and uninstall"))
    return errors


def marketplace(c: Dict[str, Any]) -> Tuple[List[Dict[str, str]], Optional[str]]:
    """Returns (errors, blocked note)."""
    if c["distribution"] == "direct":
        return [], None
    platform = c["product"]["platform"]
    with open(CHECKLISTS, encoding="utf-8") as fh:
        table = json.load(fh)["platforms"]
    review = c.get("marketplace_review")
    if review and review.get("platform") != platform:
        return [err("marketplace-platform-mismatch", "a %s review does not validate a %s product"
                    % (review.get("platform"), platform))], None
    entry = table.get(platform)
    if entry is None or entry["status"] != "pinned":
        reason = entry["note"] if entry else "no checklist registered for %s" % platform
        return [], "no pinned marketplace checklist for %s: %s" % (platform, reason)
    if not review:
        return [err("marketplace-review-missing", "marketplace distribution needs a %s review" % entry["checklist"])], None
    errors = []
    if review.get("checklist") != entry["checklist"]:
        errors.append(err("marketplace-checklist-mismatch", "%s requires checklist %s, got %s" % (platform, entry["checklist"], review.get("checklist"))))
    if review.get("result") != "pass":
        errors.append(err("marketplace-review-failed", "marketplace review result is %s" % review.get("result")))
    return errors, None


def review_record(path: str) -> Dict[str, str]:
    """The key: value lines of a review file (reviewed-sha256, reviewed-by, verdict)."""
    record: Dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                key, sep, value = line.partition(":")
                if sep and key.strip() in ("reviewed-sha256", "reviewed-by", "verdict"):
                    record.setdefault(key.strip(), value.strip())
    except OSError:
        pass
    return record


def drop_unnamed_hash_clause(message: str) -> str:
    """fleetlib joins stale reasons with '; '. The 'does not name the output hash' reason is reported here as
    review-not-bound-to-output, so remove only that clause and keep the others."""
    head, sep, reasons = message.partition(": ")
    if not message.startswith("stale evidence ") or not sep:
        return message
    kept = [r for r in reasons.split("; ") if not r.startswith("it does not name the output hash")]
    return "%s: %s" % (head, "; ".join(kept)) if kept else ""


def review_errors(handoff: Dict[str, Any], base: str) -> List[Dict[str, str]]:
    """Each evidence file must name the exact output bytes it reviewed, be written by the handoff's reviewer
    (never its producer), and pass. fleetlib checks the hash appears; this adds who reviewed and the verdict."""
    errors = []
    for ev in handoff["evidence"]:
        rec = review_record(os.path.join(base, ev["path"]))
        if rec.get("reviewed-sha256") != ev["about_sha256"]:
            errors.append(err("review-not-bound-to-output", "%s does not name reviewed-sha256 %s for %s"
                              % (ev["path"], ev["about_sha256"][:12], ev["about"])))
        who = rec.get("reviewed-by")
        if who != handoff["reviewer"] or who == handoff["producer"]:
            errors.append(err("review-wrong-reviewer", "%s is reviewed by %r; the handoff reviewer is %s and the producer %s may not review"
                              % (ev["path"], who, handoff["reviewer"], handoff["producer"])))
        if rec.get("verdict") != "pass":
            errors.append(err("review-not-passing", "%s verdict is %r" % (ev["path"], rec.get("verdict"))))
    return errors


def evidence(c: Dict[str, Any], base: str, candidate: str) -> Tuple[List[Dict[str, str]], Optional[str]]:
    if not os.path.isdir(os.path.join(FLEETLIB, "fleetlib")):
        return [], "company-fleets fleetlib not found at %s" % FLEETLIB
    if FLEETLIB not in sys.path:
        sys.path.insert(0, FLEETLIB)
    from fleetlib.handoff import evidence_errors, validate_handoff  # noqa: E402
    ev = c["evidence"]
    try:
        with open(os.path.join(base, ev["handoff"]), encoding="utf-8") as fh:
            handoff = json.load(fh)
        with open(os.path.join(base, ev["contract"]), encoding="utf-8") as fh:
            contract = json.load(fh)
    except (OSError, ValueError) as exc:
        return [err("evidence-unreadable", str(exc))], None
    shape = validate_handoff(handoff)
    if shape:
        return [err("stale-or-invalid-evidence", m) for m in shape], None
    hbase = os.path.join(base, ev["base"])
    errors = [err("stale-or-invalid-evidence", m) for m in map(drop_unnamed_hash_clause, evidence_errors(handoff, contract, hbase)) if m]
    seen = {(e["code"], e["message"]) for e in errors}
    errors += [e for e in review_errors(handoff, hbase) if (e["code"], e["message"]) not in seen]
    outputs = {o["path"] for o in handoff["outputs"]}
    for field, path in (("candidate", candidate), ("compat_matrix", c["compat_matrix"]), ("changelog", c["changelog"]), ("sbom", c["sbom"])):
        if path not in outputs:
            errors.append(err("input-not-hash-bound", "%s %s is not an output of handoff %s, so no review binds it"
                              % (field, path, handoff["handoff_id"])))
    return errors, None


def gate(c: Dict[str, Any], base: str, candidate: str = "candidate-ok.json") -> Dict[str, Any]:
    stages: List[Dict[str, Any]] = []
    m = parse_matrix(os.path.join(base, c["compat_matrix"]))
    compat = compatibility(m, c["product"])
    stages.append({"stage": "compatibility", "status": "fail" if compat else "pass", "errors": compat})
    later: List[Tuple[str, Callable[[], Any]]] = [
        ("semver-and-channel", lambda: semver(c)),
        ("changelog", lambda: changelog(c, base)),
        ("supply-chain", lambda: supply_chain(c, base)),
        ("migration-and-rollback", lambda: migration(c)),
        ("marketplace-policy", lambda: marketplace(c)),
        ("evidence-freshness", lambda: evidence(c, base, candidate)),
    ]
    adapters = {"semver-and-channel": SEMVER, "changelog": CHANGELOG}
    for name, fn in later:
        if compat:
            stages.append({"stage": name, "status": "not-run", "errors": [], "note": "compatibility refused first"})
            continue
        if name in adapters and not os.path.isfile(adapters[name]):
            stages.append({"stage": name, "status": "blocked", "errors": [], "note": "adapter missing: %s" % adapters[name]})
            continue
        out = fn()
        errors, note = out if isinstance(out, tuple) else (out, None)
        status = "fail" if errors else ("blocked" if note else "pass")
        stage = {"stage": name, "status": status, "errors": errors}
        if note:
            stage["note"] = note
        stages.append(stage)
    if any(s["status"] == "fail" for s in stages):
        decision = "refused"
    elif any(s["status"] == "blocked" for s in stages):
        decision = "blocked"
    else:
        decision = "ready-for-human-approval"
    return {"product": c["product"], "channel": c["channel"], "decision": decision, "approval_owner": APPROVAL_OWNER,
            "support_boundary": c["support_boundary"], "stages": stages,
            "not_checked": ["runtime behavior beyond the recorded test results", "legal review of license compatibility",
                            "marketplace reviewer judgment", "whether platform_facts are still current"]}


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(prog="release_gate")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("compat").add_argument("--matrix", required=True)
    sub.add_parser("gate").add_argument("--candidate", required=True)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "compat":
            m = parse_matrix(args.matrix)
            errors = compatibility(m)
            out = {"product": m["product"], "status": "fail" if errors else "pass", "errors": errors}
            print(json.dumps(out, indent=2, sort_keys=True))
            return 1 if errors else 0
        c = parse_candidate(args.candidate)
        result = gate(c, os.path.dirname(os.path.abspath(args.candidate)), os.path.basename(args.candidate))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["decision"] == "ready-for-human-approval" else 1
    except InvalidInput as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
