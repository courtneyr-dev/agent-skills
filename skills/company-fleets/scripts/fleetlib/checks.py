"""Registry validation (schema plus cross-record rules) and the coverage report."""
from __future__ import annotations

import os
from collections import Counter, defaultdict
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from .registry import COMPANY, FLEET_KINDS, FLEETS, PROFILES, REQUIREMENTS, Registry, fleet_file, fleet_of
from .schema import Schemas

# A state on the left needs a retained evidence path; "reference-only" is never "installed".
EVIDENCE_CLAIMS = {"installed": {"installed"}, "activated": {"activated"}, "behavioral": {"verified", "failed"}}
STATE_FIELDS = ("coverage", "installed", "activated", "behavioral")


class Rec(NamedTuple):
    fleet: str
    file: str
    rec: Dict[str, Any]
    valid: bool


class Report:
    def __init__(self) -> None:
        self.errors: List[Dict[str, str]] = []
        self.warnings: List[Dict[str, str]] = []

    @staticmethod
    def _issue(file: str, message: str, refs: Tuple[str, ...]) -> Dict[str, Any]:
        """`fleets` names every fleet the issue touches, so `validate --fleet F` also shows F's breakage of others."""
        own = (file.split("/")[1],) if file.startswith("fleets/") else ()
        return {"file": file, "message": message, "fleets": sorted(set(own + refs))}

    def error(self, file: str, message: str, refs: Tuple[str, ...] = ()) -> None:
        self.errors.append(self._issue(file, message, refs))

    def warn(self, file: str, message: str) -> None:
        self.warnings.append(self._issue(file, message, ()))


class Index:
    def __init__(self) -> None:
        self.fleets: List[str] = []
        self.profiles: Dict[str, Dict[str, Any]] = {}
        self.roles: Dict[str, Rec] = {}
        self.workloads: Dict[str, Rec] = {}
        self.skills: Dict[str, Rec] = {}
        self.evals: Dict[str, Rec] = {}
        self.requirements: List[Dict[str, Any]] = []


def _load(reg: Registry, rep: Report, schemas: Schemas, rel: str, ref: str) -> Any:
    try:
        data = reg.load(rel)
    except FileNotFoundError:
        rep.error(rel, "file is missing")
        return None
    except ValueError as exc:
        rep.error(rel, "invalid JSON: %s" % exc)
        return None
    for message in schemas.validate(data, ref):
        rep.error(rel, message)
    return data


def _records(data: Any, key: str, ref: str, schemas: Schemas) -> List[Tuple[Dict[str, Any], bool]]:
    if not (isinstance(data, dict) and isinstance(data.get(key), list)):
        return []
    return [(r, not schemas.validate(r, ref)) for r in data[key] if isinstance(r, dict) and isinstance(r.get("id"), str)]


def _todo_strings(node: Any) -> int:
    if isinstance(node, str):
        return int(node.startswith("TODO"))
    if isinstance(node, dict):
        return sum(_todo_strings(v) for v in node.values())
    if isinstance(node, list):
        return sum(_todo_strings(v) for v in node)
    return 0


def _check_evidence_path(reg: Registry, rep: Report, file: str, fleet: str, owner: str, what: str, ev: str) -> None:
    home = "fleets/%s/evidence/" % fleet
    if not ev.startswith(home):
        rep.error(file, "%s %s evidence %s must sit under %s" % (owner, what, ev, home))
    elif not reg.exists(ev):
        rep.error(file, "%s %s evidence %s does not exist" % (owner, what, ev))


def _check_states(reg: Registry, rep: Report, file: str, fleet: str, owner: str, v: Dict[str, Any],
                  outcomes: List[str], self_id: str, needs_grader: bool = False) -> None:
    """outcomes: the statuses of the eval cases that target this record. needs_grader (roles): a verified claim
    needs a grader who is neither the builder nor the record; these are warnings, so --strict refuses them."""
    for field, claims in EVIDENCE_CLAIMS.items():
        st = v[field]
        if st["state"] in claims:
            if not st.get("evidence"):
                rep.error(file, "%s claims %s=%s without an evidence path" % (owner, field, st["state"]))
            else:
                _check_evidence_path(reg, rep, file, fleet, owner, field, st["evidence"])
    for field in STATE_FIELDS:
        if v[field]["state"] == "blocked" and "note" not in v[field]:
            rep.error(file, "%s %s is blocked without a note saying why" % (owner, field))
    if v["activated"]["state"] == "activated" and v["installed"]["state"] != "installed":
        rep.error(file, "%s claims activated while installed is %s" % (owner, v["installed"]["state"]))
    needed = {"verified": "pass", "failed": "fail"}.get(v["behavioral"]["state"])
    if needed and needed not in outcomes:
        rep.error(file, "%s claims behavioral=%s but none of its eval cases has outcome %s"
                  % (owner, v["behavioral"]["state"], needed))
    b = v["behavioral"]
    if needs_grader and b["state"] == "verified":
        grader = b.get("grader", "").strip().lower()
        if not grader:
            rep.warn(file, "%s claims behavioral=verified without a grader; record who judged the samples" % owner)
        elif grader == b.get("builder", "").strip().lower():
            rep.warn(file, "%s claims behavioral=verified but its grader is the builder (%s)" % (owner, b["grader"]))
        elif grader == self_id.lower():
            rep.warn(file, "%s claims behavioral=verified but graded itself" % owner)


def build(reg: Registry) -> Tuple[Report, Index]:
    """Load every registry file, check it against its schema, then check the rules between records."""
    S, rep, ix = Schemas(), Report(), Index()
    _load(reg, rep, S, COMPANY, "company.schema.json")
    fleets_doc = _load(reg, rep, S, FLEETS, "files.schema.json#/$defs/fleets")
    profiles_doc = _load(reg, rep, S, PROFILES, "files.schema.json#/$defs/profiles")

    for f, _ in _records(fleets_doc, "fleets", "fleet.schema.json", S):
        if f["id"] in ix.fleets:
            rep.error(FLEETS, "duplicate fleet id %s" % f["id"])
        else:
            ix.fleets.append(f["id"])
    dirs = reg.fleet_dirs()
    for f in ix.fleets:
        if f not in dirs:
            rep.error(FLEETS, "fleet %s has no directory fleets/%s" % (f, f))
    for d in dirs:
        if d not in ix.fleets:
            rep.error("fleets/%s/" % d, "fleets/%s is not registered in %s" % (d, FLEETS))
    for p, _ in _records(profiles_doc, "profiles", "operating-profile.schema.json", S):
        if p["id"] in ix.profiles:
            rep.error(PROFILES, "duplicate profile id %s" % p["id"])
            continue
        ix.profiles[p["id"]] = p
        for f in p.get("fleets", []):
            if f not in ix.fleets:
                rep.error(PROFILES, "profile %s activates unknown fleet %s" % (p["id"], f))

    for f in [x for x in ix.fleets if x in dirs]:
        docs = {}
        for kind in FLEET_KINDS:
            rel = fleet_file(f, kind)
            docs[kind] = _load(reg, rep, S, rel, "files.schema.json#/$defs/" + kind)
            if isinstance(docs[kind], dict) and docs[kind].get("fleet") != f:
                rep.error(rel, "file says fleet %r but sits in fleets/%s" % (docs[kind].get("fleet"), f))
            if _todo_strings(docs[kind]):
                rep.warn(rel, "%d placeholder value(s) still start with TODO" % _todo_strings(docs[kind]))
        for key, kind, ref, idx, prefix in (
                ("roles", "roles", "role.schema.json", ix.roles, f + "."),
                ("workloads", "roles", "workload.schema.json", ix.workloads, f + ".workload."),
                ("skills", "skills", "skill.schema.json", ix.skills, ""),
                ("evals", "evals", "eval.schema.json", ix.evals, f + ".eval.")):
            rel = fleet_file(f, kind)
            for rec, ok in _records(docs[kind], key, ref, S):
                rid = rec["id"]
                if rid in idx:
                    rep.error(rel, "duplicate %s id %s (first registered in %s)" % (key[:-1], rid, idx[rid].file))
                    continue
                idx[rid] = Rec(f, rel, rec, ok)
                if prefix and not rid.startswith(prefix):
                    rep.error(rel, "%s id %s must start with %r" % (key[:-1], rid, prefix))
                if key in ("roles", "skills") and rec.get("fleet") != f:
                    rep.error(rel, "%s %s says fleet %r but sits in fleets/%s" % (key[:-1], rid, rec.get("fleet"), f))

    _check_roles(reg, rep, ix)
    _check_workloads(rep, ix)
    _check_skills(reg, rep, ix)
    _check_evals(reg, rep, ix)
    if os.path.isfile(reg.path(REQUIREMENTS)):
        _check_requirements(reg, rep, S, ix)
    return rep, ix


EXTERNAL = "registry/external-skills.json"  # the one list of upstream skills this repository does not ship


def _check_roles(reg: Registry, rep: Report, ix: Index) -> None:
    coordinators: Dict[str, List[str]] = defaultdict(list)
    external = reg.load(EXTERNAL)["skills"] if reg.exists(EXTERNAL) else {}
    for rid, r in sorted(ix.roles.items()):
        if not r.valid:
            continue
        rec = r.rec
        if rec["kind"] == "coordinator":
            coordinators[r.fleet].append(rid)
        for att in rec["skills"]:
            sid = att["id"]
            srec = ix.skills.get(sid)
            if att.get("blocked_reason", "").startswith("external:") and "install from %s;" % external.get(sid) not in att["blocked_reason"]:
                rep.error(r.file, "%s marks skill %s external, but %s lists %s" % (rid, sid, EXTERNAL, external.get(sid, "no repo for it")))
            if "blocked_reason" in att or reg.skill_installed(sid) or (srec and "blocked_reason" in srec.rec):
                continue
            rep.error(r.file, "%s attaches skill %s: no skills/%s/SKILL.md and it is not marked blocked with a reason"
                      % (rid, sid, sid))
        rel = rec["relations"]
        if rel["acceptor"] == rid:
            rep.error(r.file, "%s accepts its own output; the producer and the acceptor must differ" % rid)
        if rid in rel["reviewers"]:
            rep.error(r.file, "%s reviews its own output; a reviewer must differ from the producer" % rid)
        for p in rel["reviewers"] + [rel["acceptor"]] + rel["escalation"] + rec["handoff"]["next_consumers"]:
            if not p.startswith("human:") and p not in ix.roles:
                rep.error(r.file, "%s names unknown role %s" % (rid, p), (fleet_of(p),))
        for eid in rec["evals"]:
            if eid not in ix.evals:
                rep.error(r.file, "%s lists evaluation case %s, which no fleets/*/evals.json defines" % (rid, eid),
                          (fleet_of(eid),))
        own = [ix.evals[e].rec for e in rec["evals"] if e in ix.evals and ix.evals[e].rec.get("target") == rid]
        if rec["evals"] and not own:
            rep.error(r.file, "none of %s's evaluation cases targets it" % rid)
        _check_states(reg, rep, r.file, r.fleet, rid, rec["verification"], [e["outcome"]["status"] for e in own], rid, True)
    for f, ids in sorted(coordinators.items()):
        if len(ids) > 1:
            rep.error(fleet_file(f, "roles"), "fleet %s has competing coordinators %s; keep one" % (f, ", ".join(ids)))


def _check_workloads(rep: Report, ix: Index) -> None:
    for wid, w in sorted(ix.workloads.items()):
        if not w.valid:
            continue
        rec = w.rec
        for p in rec["profiles"]:
            if p not in ix.profiles:
                rep.error(w.file, "%s names unknown profile %s" % (wid, p))
            elif w.fleet not in ix.profiles[p]["fleets"]:
                rep.error(w.file, "%s lists profile %s, which does not activate fleet %s" % (wid, p, w.fleet))
        extra = rec.get("by_profile", {})
        for p in extra:
            if p not in rec["profiles"]:
                rep.error(w.file, "%s by_profile names %s, which is not in its profiles" % (wid, p))
        for rid in set(rec["roles"]).union(*extra.values()):
            if rid not in ix.roles:
                rep.error(w.file, "%s names unknown role %s" % (wid, rid), (fleet_of(rid),))
        for role_set in [rec["roles"]] + [rec["roles"] + v for v in extra.values()]:
            coords = sorted({x for x in role_set if x in ix.roles and ix.roles[x].rec.get("kind") == "coordinator"})
            if len(coords) > 1:
                rep.error(w.file, "%s has competing coordinators %s; one coordinator per workload" % (wid, ", ".join(coords)))
        base = [x for x in rec["roles"] if x in ix.roles and ix.roles[x].rec.get("kind") == "coordinator"]
        if not base:
            rep.error(w.file, "%s has no coordinator, so no role can claim it; add the %s coordinator" % (wid, w.fleet))
        elif fleet_of(base[0]) != w.fleet:
            rep.error(w.file, "%s is coordinated by %s; a workload's coordinator comes from its own fleet" % (wid, base[0]))


def _check_skills(reg: Registry, rep: Report, ix: Index) -> None:
    users: Dict[str, set] = defaultdict(set)  # skill id -> roles that attach it
    for rid, r in ix.roles.items():
        if r.valid:
            for att in r.rec["skills"]:
                users[att["id"]].add(rid)
    for sid, s in sorted(ix.skills.items()):
        if not s.valid:
            continue
        rec = s.rec
        testers = {sid} | users[sid]
        for bucket in ("positive", "negative", "boundary"):
            for eid in rec["evals"][bucket]:
                e = ix.evals.get(eid)
                if e is None:
                    rep.error(s.file, "skill %s lists %s case %s, which no evals.json defines" % (sid, bucket, eid),
                              (fleet_of(eid),))
                elif e.valid and e.rec["kind"] != bucket:
                    rep.error(s.file, "skill %s lists %s as %s but the case is %s" % (sid, eid, bucket, e.rec["kind"]))
                elif e.valid and e.rec["target"] not in testers:
                    rep.error(s.file, "skill %s lists %s, which targets %s: neither the skill nor a role that attaches it"
                              % (sid, eid, e.rec["target"]))
        outcomes = [ix.evals[e].rec["outcome"]["status"] for b in rec["evals"].values() for e in b
                    if e in ix.evals and ix.evals[e].valid and ix.evals[e].rec["target"] in testers]
        _check_states(reg, rep, s.file, s.fleet, "skill " + sid, rec["verification"], outcomes, sid)
        installed = reg.skill_installed(sid)
        if rec["verification"]["installed"]["state"] == "installed" and not installed:
            rep.error(s.file, "skill %s claims installed but skills/%s/SKILL.md does not exist" % (sid, sid))
        if installed:
            for sp in rec["scripts"]:
                if not os.path.isfile(os.path.join(reg.skills_root, sid, sp)):
                    rep.error(s.file, "skill %s lists script %s, which does not exist" % (sid, sp))


def _check_evals(reg: Registry, rep: Report, ix: Index) -> None:
    for eid, e in sorted(ix.evals.items()):
        if not e.valid:
            continue
        rec = e.rec
        target = rec["target"]
        if "." in target:
            if target not in ix.roles:
                rep.error(e.file, "%s targets unknown role %s" % (eid, target), (fleet_of(target),))
        elif target not in ix.skills and not reg.skill_installed(target):
            rep.error(e.file, "%s targets unknown skill %s" % (eid, target))
        out = rec["outcome"]
        if out["status"] in ("pass", "fail"):
            if "evidence" not in out:
                rep.error(e.file, "%s reports %s without an evidence path" % (eid, out["status"]))
            else:
                _check_evidence_path(reg, rep, e.file, e.fleet, eid, "outcome", out["evidence"])
        if out["status"] == "blocked" and "note" not in out:
            rep.error(e.file, "%s is blocked without a note saying why" % eid)
        if rec["check"]["method"] == "script" and "argv" not in rec["check"]:
            rep.error(e.file, "%s is a script check without argv" % eid)
        for fx in rec.get("fixtures", []):
            if not reg.exists(fx):
                rep.error(e.file, "%s fixture %s does not exist" % (eid, fx))


def _check_requirements(reg: Registry, rep: Report, S: Schemas, ix: Index) -> None:
    data = _load(reg, rep, S, REQUIREMENTS, "files.schema.json#/$defs/requirements")
    seen = set()
    for row, ok in _records(data, "rows", "requirement.schema.json", S):
        if row["id"] in seen:
            rep.error(REQUIREMENTS, "duplicate requirement id %s" % row["id"])
            continue
        seen.add(row["id"])
        ix.requirements.append(row)
        if not ok:
            continue
        if row["status"] == "delivered" and not row["deliverable"]:
            rep.error(REQUIREMENTS, "%s is delivered without a deliverable path" % row["id"])
        if row["status"] == "blocked" and not row["blocker"]:
            rep.error(REQUIREMENTS, "%s is blocked without a blocker" % row["id"])
        if row["deliverable"] and not os.path.isfile(os.path.join(reg.skills_root, row["deliverable"].split("#", 1)[0])):
            rep.error(REQUIREMENTS, "%s deliverable %s does not exist under the rig skills root" % (row["id"], row["deliverable"]))


def validate(reg: Registry, only_fleet: Optional[str] = None, strict: bool = False) -> Dict[str, Any]:
    """strict turns warnings (TODO placeholders) into errors: the gate before a fleet hands back."""
    rep, ix = build(reg)
    errors, warnings = rep.errors, rep.warnings
    if strict:
        errors, warnings = errors + warnings, []
    if only_fleet:
        errors = [e for e in errors if only_fleet in e["fleets"]]
        warnings = [w for w in warnings if only_fleet in w["fleets"]]
        if only_fleet not in ix.fleets:
            errors.append({"file": FLEETS, "message": "fleet %s is not registered" % only_fleet, "fleets": [only_fleet]})
    return {"ok": not errors, "scope": only_fleet or "all", "strict": strict, "errors": errors, "warnings": warnings,
            "counts": {"fleets": len(ix.fleets), "profiles": len(ix.profiles), "roles": len(ix.roles),
                       "workloads": len(ix.workloads), "skills": len(ix.skills), "evals": len(ix.evals),
                       "requirements": len(ix.requirements)}}


def coverage(reg: Registry) -> Dict[str, Any]:
    """Per-fleet counts with the four states kept apart, plus requirement rows that lack a deliverable or a blocker."""
    rep, ix = build(reg)
    fleets = []
    for f in ix.fleets:
        roles = [r for r in ix.roles.values() if r.fleet == f and r.valid]
        skills = [s for s in ix.skills.values() if s.fleet == f and s.valid]
        evals = [e for e in ix.evals.values() if e.fleet == f and e.valid]
        attached = Counter()
        for r in roles:
            for att in r.rec["skills"]:
                if "blocked_reason" in att or ("blocked_reason" in ix.skills[att["id"]].rec if att["id"] in ix.skills else False):
                    attached["blocked"] += 1
                elif reg.skill_installed(att["id"]):
                    attached["available"] += 1
                else:
                    attached["missing"] += 1
        fleets.append({
            "fleet": f,
            "roles": len(roles),
            "coordinator": next((r.rec["id"] for r in roles if r.rec["kind"] == "coordinator"), None),
            "workloads": sum(1 for w in ix.workloads.values() if w.fleet == f),
            "attached_skills": dict(attached),
            "role_states": {k: dict(Counter(r.rec["verification"][k]["state"] for r in roles)) for k in STATE_FIELDS},
            "skills_registered": len(skills),
            "skill_states": {k: dict(Counter(s.rec["verification"][k]["state"] for s in skills)) for k in STATE_FIELDS},
            "evals": dict(Counter(e.rec["kind"] for e in evals)),
            "eval_outcomes": dict(Counter(e.rec["outcome"]["status"] for e in evals)),
        })
    by_ws: Dict[str, Counter] = defaultdict(Counter)
    uncovered = []
    for row in ix.requirements:
        covered = bool(row.get("deliverable") or row.get("blocker"))
        by_ws[row.get("owner_workstream", "?")]["covered" if covered else "uncovered"] += 1
        if not covered:
            uncovered.append(row["id"])
    return {
        "registry_errors": len(rep.errors),
        "fleets": fleets,
        "requirements": {"rows": len(ix.requirements), "by_workstream": {k: dict(v) for k, v in sorted(by_ws.items())},
                         "uncovered": len(uncovered), "uncovered_ids": uncovered},
    }
