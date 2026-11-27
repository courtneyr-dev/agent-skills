"""Coverage report and override register: sync requirement statuses from the fleets' own maps, render
references/coverage-report.md, check registry/overrides.json against the sources ledger, and render
references/company-overrides.md with the license note.

Requirement status precedence, first match wins: the fleet's requirements-map.json, the path table in
the fleet's README, then sources/capability-matrix.json. A named deliverable must exist under the rig
skills root; a map that names a missing file leaves the row assigned with that as its blocker. Partial
delivery is `delivered` with a blocker naming what is missing (the hosting fleet's convention).
"""
from __future__ import annotations

import datetime
import json
import os
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from factory_rig.canon import atomic_write

from .checks import STATE_FIELDS, coverage as fleet_coverage
from .registry import REQUIREMENTS, Registry

OVERRIDES = "registry/overrides.json"
LEDGER = "sources/ledger.json"
MATRIX = "sources/capability-matrix.json"
REPORT = "references/coverage-report.md"
OVERRIDE_DOC = "references/company-overrides.md"
ACCEPTANCE_RESULTS = "evidence/integration/acceptance/results.json"
DEMO_RESULTS = "evidence/integration/demos/results.json"
REQUIRED_OVERRIDES = 14
ROW = re.compile(r"\b(?:S0[3-9]|S1[01]|ED)-[0-9]{3}\b")
INTEGRATOR_ROWS = {
    "ED-056": "Notes outside this repository are the integrator's step, not this build's. Resume: the integrator adds the four linked entries in its own notes location, with that location's existing frontmatter.",
    "ED-057": "Same step as ED-056: the integrator writes the entries in its own notes location and keeps that location's existing frontmatter and records.",
}


def _json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _exists(reg: Registry, rel: Optional[str]) -> bool:
    return bool(rel) and os.path.isfile(os.path.join(reg.skills_root, rel.split("#", 1)[0]))


def _fleet_of_row(row_id: str) -> str:
    return {"S03": "corporate", "S04": "agency", "S05": "hosting", "S06": "product", "S07": "consultancies",
            "S08": "devrel", "S09": "community", "S10": "bcit-education", "S11": "instructional-design"}.get(row_id[:3], "bcit-education")


def _readme_rows(reg: Registry, fleet: str) -> Dict[str, Dict[str, Optional[str]]]:
    """Rows from a README table whose first cell names requirement ids. A backticked path that exists is the
    deliverable; a row that says blocker or partial (any case) keeps its whole note, minus the path, as the blocker."""
    path = reg.path("fleets/%s/README.md" % fleet)
    out: Dict[str, Dict[str, Optional[str]]] = {}
    if not os.path.isfile(path):
        return out
    for line in open(path, encoding="utf-8"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or not ROW.search(cells[0]):
            continue
        text = " | ".join(cells[1:])
        paths = [p for p in re.findall(r"`([^`\s]+)`", text) if _exists(reg, p)]
        partial = re.search(r"\b(blocker|partial)\b", text, re.I)
        for rid in ROW.findall(cells[0]):
            out[rid] = {"deliverable": paths[0] if paths else "company-fleets/fleets/%s/README.md" % fleet,
                        "blocker": re.sub(r"`[^`]*`\s*", "", text).strip() if partial else None, "note": text}
    return out


def _matrix_row(reg: Registry, row: Dict[str, Any], roles_count: Dict[str, int]) -> Dict[str, Optional[str]]:
    if row["disposition"] == "blocker":
        return {"status": "blocked", "deliverable": None, "blocker": "%s Resume: %s" % (row["blocker"], row.get("resume", ""))}
    if row.get("local_skill") == "company-fleets":
        roles = "company-fleets/fleets/%s/roles.json" % row["fleet"]
        if roles_count.get(row["fleet"], 0):
            return {"status": "delivered", "deliverable": roles, "blocker": None}
        return {"status": "blocked", "deliverable": None, "blocker": "fleets/%s/roles.json has no roles yet" % row["fleet"]}
    for skill in [row.get("local_skill")] + list(row.get("skills", [])):
        if skill and _exists(reg, "%s/SKILL.md" % skill):
            return {"status": "delivered", "deliverable": "%s/SKILL.md" % skill, "blocker": None}
    return {"status": "assigned", "deliverable": None, "blocker": "The capability matrix names %s, none installed" % (row.get("skills") or row.get("local_skill"))}


def proposals(reg: Registry) -> Dict[str, Dict[str, Any]]:
    """Every row's proposed status, deliverable, blocker and provenance, before the existence check."""
    roles_count = {f: len(_json(reg.path("fleets/%s/roles.json" % f))["roles"]) for f in reg.fleet_dirs()}
    out: Dict[str, Dict[str, Any]] = {}
    for row in _json(reg.path(MATRIX))["rows"]:
        out[row["requirement"]] = dict(_matrix_row(reg, row, roles_count), source=MATRIX)
    for fleet in reg.fleet_dirs():
        for rid, r in _readme_rows(reg, fleet).items():
            out[rid] = {"status": "delivered", "deliverable": r["deliverable"], "blocker": r["blocker"],
                        "source": "fleets/%s/README.md" % fleet}
        mp = reg.path("fleets/%s/requirements-map.json" % fleet)
        if os.path.isfile(mp):
            doc = _json(mp)
            for r in (doc["rows"] if isinstance(doc, dict) else doc):
                out[r["id"]] = {"status": r["status"], "deliverable": r.get("deliverable"), "blocker": r.get("blocker"),
                                "source": "fleets/%s/requirements-map.json" % fleet}
    for rid, blocker in INTEGRATOR_ROWS.items():
        if out.get(rid, {}).get("status") in (None, "assigned", "unassigned"):
            out[rid] = {"status": "blocked", "deliverable": None, "blocker": blocker, "source": "integration (coverage.py)"}
    return out


def sync_requirements(reg: Registry) -> Dict[str, Any]:
    """Apply proposals to registry/requirements.json. Idempotent: a second run changes nothing."""
    path = reg.path(REQUIREMENTS)
    doc = _json(path)
    props = proposals(reg)
    changed, refused = 0, []
    for row in doc["rows"]:
        p = props.get(row["id"])
        if p is None:
            continue
        new = {"status": p["status"], "deliverable": p["deliverable"], "blocker": p["blocker"]}
        if new["deliverable"] and not _exists(reg, new["deliverable"]):
            refused.append({"id": row["id"], "source": p["source"], "missing": new["deliverable"]})
            new = {"status": "assigned", "deliverable": None,
                   "blocker": "%s names %s, which does not exist" % (p["source"], new["deliverable"])}
        if new["status"] == "delivered" and not new["deliverable"]:
            new["status"] = "assigned"
        if any(row[k] != v for k, v in new.items()):
            row.update(new)
            changed += 1
    atomic_write(path, json.dumps(doc, indent=2) + "\n")
    return {"rows": len(doc["rows"]), "changed": changed, "missing_deliverables": refused}


# ---- overrides ---------------------------------------------------------------------------------------

def check_overrides(reg: Registry) -> Dict[str, Any]:
    doc = _json(reg.path(OVERRIDES))
    repos = {r["id"]: r for r in _json(reg.path(LEDGER))["repos"]}
    errors, drift = [], []
    fields = ("id", "requirement", "upstream", "reason", "implementation", "precedence", "scope", "evidence", "owner", "retire_when")
    for o in doc["overrides"]:
        for f in fields:
            if not o.get(f):
                errors.append("%s lacks %s" % (o.get("id"), f))
        for u in o.get("upstream", []):
            led = repos.get(u["repo"])
            if led is None:
                errors.append("%s cites %s, which the sources ledger does not record" % (o["id"], u["repo"]))
            elif led["revision"] != u["revision"]:
                drift.append({"override": o["id"], "repo": u["repo"], "pinned": u["revision"], "ledger": led["revision"],
                              "action": "Upstream moved: rerun the evals named in this override's evidence, then re-pin the revision."})
        for p in o.get("implementation", []) + o.get("evidence", []):
            if not _exists(reg, p):
                errors.append("%s names %s, which does not exist under the rig skills root" % (o["id"], p))
    if len(doc["overrides"]) != REQUIRED_OVERRIDES:
        errors.append("%d overrides recorded; section 14 requires %d" % (len(doc["overrides"]), REQUIRED_OVERRIDES))
    return {"ok": not errors and not drift, "overrides": len(doc["overrides"]), "errors": errors, "drift": drift}


def _licenses(reg: Registry) -> List[str]:
    repos = _json(reg.path(LEDGER))["repos"]
    by = Counter(r["license"]["spdx"] for r in repos)
    share = [r for r in repos if r["license"].get("share_alike")]
    restricted = [r for r in repos if r["license"]["spdx"] in ("NOASSERTION", "BUSL-1.1")]
    lines = ["## Licenses and share-alike obligations", "",
             "The combined library is not MIT. The sources ledger (`sources/ledger.json`) records %d upstream repositories under %d licenses: %s. "
             "Original rig skills (company-fleets, the fleet skills, factory-rig) are published under MIT in agent-skills." % (
                 len(repos), len(by), ", ".join("%s (%d)" % (k, v) for k, v in sorted(by.items(), key=lambda x: (-x[1], x[0])))), "",
             "Share-alike or copyleft sources: material adapted from these keeps their license and attribution, so a local adapter that copies their text inherits it.", ""]
    lines += ["- `%s` at `%s`: %s. %s" % (r["id"], r["revision"][:12], r["license"]["spdx"], r["license"].get("note") or r["license"]["holder"]) for r in share]
    lines += ["", "Not redistributable as is:", ""]
    lines += ["- `%s` at `%s`: %s. %s" % (r["id"], r["revision"][:12], r["license"]["spdx"], r["license"].get("note") or r["license"]["holder"]) for r in restricted]
    lines += ["", "Keep each upstream LICENSE and NOTICE file with its installed directory; skill-sync copies whole directories."]
    return lines


def render_overrides(reg: Registry) -> str:
    doc = _json(reg.path(OVERRIDES))
    chk = check_overrides(reg)
    out = ["# Company override register", "",
           "Every local adaptation of an upstream skill source, as section 14 of the project requirements asks. "
           "The record is `registry/overrides.json`; this page is rendered from it by `bin/fleet overrides --write`. "
           "Factory-rig's own register (`../../factory-rig/references/overrides.md`) covers the delivery layer.", "",
           "Check status at render time: %d overrides, %d errors, %d drifted upstream pins. "
           "A drifted pin means the ledger moved past the revision the override was checked against; rerun that override's evidence and re-pin." % (
               chk["overrides"], len(chk["errors"]), len(chk["drift"])), ""]
    for o in doc["overrides"]:
        out += ["## %s: %s" % (o["id"], o["requirement"].rstrip(".")), "",
                "- Upstream: " + "; ".join("`%s` at `%s` (%s)" % (u["repo"], u["revision"][:12], u["path"]) for u in o["upstream"]),
                "- Reason: " + o["reason"],
                "- Implementation: " + ", ".join("`%s`" % p for p in o["implementation"]),
                "- Precedence: " + o["precedence"],
                "- Scope: " + o["scope"],
                "- Evidence: " + ", ".join("`%s`" % p for p in o["evidence"]),
                "- Owner: " + o["owner"],
                "- Retire when: " + o["retire_when"], ""]
    out += _licenses(reg)
    return "\n".join(out) + "\n"


# ---- coverage report --------------------------------------------------------------------------------

def _states_line(states: Dict[str, Dict[str, int]]) -> List[str]:
    return ["; ".join("%s %d" % (k, v) for k, v in sorted(states[f].items())) or "none" for f in STATE_FIELDS]


def render_report(reg: Registry) -> str:
    cov = fleet_coverage(Registry(reg.root, reg.skills_root))
    rows = _json(reg.path(REQUIREMENTS))["rows"]
    props = proposals(reg)
    status = Counter(r["status"] for r in rows)
    partial = sum(1 for r in rows if r["status"] == "delivered" and r["blocker"])
    uncovered = [r["id"] for r in rows if not (r["deliverable"] or r["blocker"])]
    today = datetime.date.today().isoformat()
    out = ["# Company-fleets coverage report", "",
           "Generated %s by `bin/fleet coverage --sync --write` from `registry/requirements.json`, the fleet records and the integration evidence. "
           "Coverage, installation, activation and behavioral verification are four separate states: a delivered row means a deliverable exists, not that it was activated or verified." % today, "",
           "## Requirement rows", "",
           "- Rows: %d (ids S03 to S11 and ED)" % len(rows),
           "- Delivered with a deliverable: %d, of which %d also name a blocker for the part still missing" % (status["delivered"], partial),
           "- Blocked with an explicit blocker: %d" % status["blocked"],
           "- Assigned without a deliverable: %d" % status["assigned"],
           "- Unassigned: %d" % status["unassigned"],
           "- Rows with neither a deliverable nor a blocker: %d%s" % (len(uncovered), (" (" + ", ".join(uncovered) + ")") if uncovered else ""),
           "- Mapped by: " + "; ".join("%s %d" % (k, v) for k, v in sorted(Counter(props.get(r["id"], {}).get("source", "none") for r in rows).items())), "",
           "## Four states per fleet", "",
           "Role and skill counts from the fleet records (`bin/fleet coverage`). Registry errors at render time: %d." % cov["registry_errors"], ""]
    out += ["| Fleet | Roles | Role coverage | Role installed | Role activated | Role behavioral | Skills | Skill behavioral | Eval outcomes |",
            "|---|---|---|---|---|---|---|---|---|"]
    for f in cov["fleets"]:
        rc, ri, ra, rb = _states_line(f["role_states"])
        out.append("| %s | %d | %s | %s | %s | %s | %d | %s | %s |" % (
            f["fleet"], f["roles"], rc, ri, ra, rb, f["skills_registered"], _states_line(f["skill_states"])[3],
            "; ".join("%s %d" % kv for kv in sorted(f["eval_outcomes"].items()))))
    out += ["", "No role or skill records `activated`: activation means the router selected it in a real session, and no session log was recorded as evidence.", ""]
    acc = reg.path(ACCEPTANCE_RESULTS)
    if os.path.isfile(acc):
        a = _json(acc)
        out += ["## Acceptance matrix", "",
                "From `%s` (run %s): %s. Each row lists its command and evidence file there." % (
                    ACCEPTANCE_RESULTS, a["run_on"], ", ".join("%s %d" % kv for kv in sorted(Counter(r["status"] for r in a["rows"]).items()))), ""]
        out += ["- `%s` %s: %s" % (r["id"], r["status"], r["test"]) for r in a["rows"]]
        out.append("")
    dem = reg.path(DEMO_RESULTS)
    if os.path.isfile(dem):
        d = _json(dem)
        out += ["## Demonstrations", "", "From `%s` (run %s)." % (DEMO_RESULTS, d["run_on"]), ""]
        out += ["- `%s` %s: %s" % (x["id"], x["status"], x["title"]) for x in d["demos"]]
        out.append("")
    out += ["## Sections 12 to 15", "",
            "- Section 12 workflows: %d templates in `workflows/`, checked with `bin/fleet workflow check` and run with `bin/fleet workflow run`." % len([f for f in os.listdir(reg.path("workflows")) if f.endswith(".json")]),
            "- Section 13 compounding improvement: records in `improvement/records/`, gate `bin/fleet improve gate`.",
            "- Section 14 override register: `registry/overrides.json`, rendered in `references/company-overrides.md`.",
            "- Section 15 deliverables: this report.", ""]
    out += ["## Rows by section", ""]
    section = None
    for r in rows:
        if r["source_section"] != section:
            section = r["source_section"]
            out += ["", "### " + section, "", "| Row | Status | Deliverable | Blocker or missing part | Mapped by |", "|---|---|---|---|---|"]
        cell = lambda v: (v or "").replace("|", "/").replace("\n", " ")
        out.append("| %s | %s | %s | %s | %s |" % (r["id"], r["status"], ("`%s`" % r["deliverable"]) if r["deliverable"] else "",
                                                 cell(r["blocker"]), props.get(r["id"], {}).get("source", "none")))
    return "\n".join(out) + "\n"


def write(reg: Registry, rel: str, text: str) -> str:
    atomic_write(reg.path(rel), text)
    return rel
