#!/usr/bin/env python3
"""Agency engagement gate: every transition from qualified brief to support handoff carries evidence.

  engagement_gate.py brief   --brief SCOPED.json
  engagement_gate.py stages  --ledger LEDGER.json --contract CONTRACT.json --base DIR
  engagement_gate.py support --runbook RUNBOOK.md
  engagement_gate.py handoff --handoff-id ID --contract CONTRACT.json --base DIR --update UPDATE.json

Every owner-set value (margin policy, rate card, stage acceptances, the human acceptor roster, a handoff's
owner fields and input labels) comes from the owner log of the instance the work names: the brief's
change_control.contract_ref, or the contract's task_id. company-fleets keeps that ledger at one fixed place
(fleets/agency/owner/<instance>), and only the lease holder writes it, through `fleet owner-record`. No flag
or file the caller passes picks the ledger or sets a value, and a ledger whose tenant or contract differ
from the work is refused.

Exit 0 = pass, 1 = blocking findings or a refused handoff, 2 = invalid input, 3 = blocked (company-fleets
or factory-rig not found beside this skill). Hashing, contracts and handoff rules come from factory-rig
and company-fleets; nothing here re-implements them.
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
FLEET_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "..", "company-fleets", "scripts"))

STAGES = ("qualified-brief", "research-requirements", "decisions", "prototype", "implementation",
          "integrated-verification", "migration-rehearsal", "release-recommendation", "support-improvement")
RUNBOOK_SECTIONS = ("Scope of support", "Contacts by role", "Deployment and rollback", "Content freeze",
                    "Known issues", "Operator training", "Warranty and maintenance", "Monitoring and escalation")
SECRET = re.compile(r"(?i)(password\s*[:=]\s*\S|api[_-]?key\s*[:=]\s*\S|secret\s*[:=]\s*\S|BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]{20,})")
OWNER_LIMIT = ("Owner values come only from the owner ledger of the instance the work names, kept at fleets/agency/owner/<instance> in "
               "company-fleets and written under the claim token; a ledger whose tenant or contract differ from the work is refused. "
               "Not stopped: a same-user process that writes the owner root, reads the owner's token, or claims an instance first, "
               "including an instance id it writes into its own brief or contract (company-fleets references/authoring-guide.md, Owner path).")
LIMITS = {
    "brief": ["Margin uses the pinned rate card's cost rates and the estimate's hours; it is a planning figure, not an accounting result.",
              "A margin floor marked hypothesis is not calibrated against this company's history; treat a pass as provisional.", OWNER_LIMIT],
    "stages": ["Checks that each transition has evidence files whose bytes still match and an acceptor other than the producer; it does not judge whether the evidence is good.", OWNER_LIMIT],
    "support": ["Checks that required sections exist, are filled, and hold no obvious secrets; a human support owner reads it for accuracy."],
    "handoff": ["Instruction-like lines in untrusted inputs are flagged and attached; protected fields refuse every worker edit whether or not the scan caught the line.", OWNER_LIMIT],
}


class InputError(Exception):
    pass


def finding(rule, message, blocking=True, where=None):
    out = {"rule": rule, "blocking": blocking, "message": message}
    if where is not None:
        out["where"] = where
    return out


def _refuse_constant(name):
    raise ValueError("%s is not a finite number" % name)


def _finite_float(token):
    value = float(token)
    return value if math.isfinite(value) else _refuse_constant(token)


def load_json(path, what):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh, parse_constant=_refuse_constant, parse_float=_finite_float)
    except (OSError, ValueError) as exc:
        raise InputError("cannot read %s %s: %s" % (what, path, exc))


def need(obj, keys, what):
    if not isinstance(obj, dict):
        raise InputError("%s must be a JSON object" % what)
    missing = [k for k in keys if k not in obj]
    if missing:
        raise InputError("%s is missing: %s" % (what, ", ".join(missing)))


# ------------------------------------------------------------------ brief

BRIEF_KEYS = ("client_id", "tenant_id", "qualification", "outcomes", "scope", "exclusions", "assumptions",
              "acceptance", "estimate", "change_control")
PINS = {"margin-policy": "policy-not-pinned", "rate-card": "rates-not-pinned"}  # owner-log pin name -> rule when absent


def _positive(x):
    return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x) and x > 0


def parse_policy(policy, pinned):
    """The company's margin policy, owned by finance and pinned in the owner log. A brief never sets its own floor."""
    need(policy, ("owner", "margin_floor", "basis", "source"), "pinned margin policy")
    floor = policy["margin_floor"]
    if isinstance(floor, bool) or not isinstance(floor, (int, float)) or not 0 < floor < 1:
        raise InputError("margin policy margin_floor must be a number strictly between 0 and 1; got %r" % (floor,))
    if not re.match(r"^human:[a-z0-9]+(?:-[a-z0-9]+)*$", str(policy["owner"])):
        raise InputError("margin policy owner must be human:<title>")
    if policy["basis"] not in ("hypothesis", "calibrated"):
        raise InputError("margin policy basis must be hypothesis or calibrated")
    if policy["basis"] == "calibrated" and policy.get("calibration_evidence") not in pinned:
        raise InputError("a calibrated margin policy needs calibration_evidence: the name of a pin the owner recorded for the measured delivery history behind the floor")
    return policy


def parse_estimate(est, rates):
    lines = est.get("lines")
    if not isinstance(lines, list) or not lines:
        raise InputError("brief estimate has no lines; estimate each role's hours")
    for i, line in enumerate(lines):
        if not isinstance(line, dict) or not _positive(line.get("hours")):
            raise InputError("brief estimate line %d has hours %r; hours must be a positive number" % (i + 1, line.get("hours") if isinstance(line, dict) else line))
    if not _positive(est.get("price")):
        raise InputError("brief estimate price must be a positive number")
    for role, rate in rates["cost_per_hour"].items():
        if not _positive(rate):
            raise InputError("rate card cost for %s must be a positive number; the estimate can't be priced" % role)


def check_brief(brief, rates, policy):
    """Pure: a parsed brief, rate card and company margin policy in, (findings, margin summary) out."""
    out = []
    q = brief["qualification"]
    if not str(q.get("decision_owner", "")).startswith("human:"):
        out.append(finding("qualification-incomplete", "qualification.decision_owner must name a human (human:<title>)."))
    if q.get("budget_confirmed") is not True:
        out.append(finding("qualification-incomplete", "qualification.budget_confirmed is not true; qualify the budget before scoping."))
    if not str(q.get("problem", "")).strip():
        out.append(finding("qualification-incomplete", "qualification.problem is empty."))
    for key in ("outcomes", "scope", "exclusions", "assumptions"):
        if not brief[key]:
            out.append(finding("brief-section-empty", "%s is empty; a scoped brief states it explicitly." % key))
    if not brief["acceptance"]:
        out.append(finding("brief-section-empty", "acceptance is empty."))
    for i, a in enumerate(brief["acceptance"]):
        if not str(a.get("criterion", "")).strip() or not str(a.get("evidence", "")).strip():
            out.append(finding("acceptance-without-evidence", "acceptance item %d needs a criterion and the evidence that proves it." % (i + 1)))
    cc = brief["change_control"]
    if cc.get("route") != "pm-contract" or not str(cc.get("contract_ref", "")).strip():
        out.append(finding("change-control-bypass", "change_control must route scope changes through the PM contract (route: pm-contract, contract_ref set)."))
    if "margin_policy" in brief:
        out.append(finding("brief-sets-its-own-floor", "the brief carries margin_policy; the floor comes only from the company margin policy pinned in the owner log. Remove it from the brief."))

    est, cost_rates = brief["estimate"], rates["cost_per_hour"]
    cost = 0.0
    for line in est["lines"]:
        if line["role"] not in cost_rates:
            out.append(finding("unpriced-role", "estimate role %s has no cost rate in the rate card." % line["role"]))
        else:
            cost += float(line["hours"]) * float(cost_rates[line["role"]])
    price, floor = float(est["price"]), float(policy["margin_floor"])
    margin = (price - cost) / price
    summary = {"cost": round(cost, 2), "price": price, "currency": est.get("currency", rates.get("currency")),
               "margin": round(margin, 4), "floor": floor, "basis": policy["basis"], "policy_owner": policy["owner"]}
    if margin < floor:
        out.append(finding("margin-below-floor", "margin %.1f%% is below the %.1f%% company floor; rescope, reprice or get a decision from %s."
                           % (margin * 100, floor * 100, policy["owner"])))
    if policy["basis"] == "hypothesis":
        out.append(finding("margin-floor-is-hypothesis", "the company floor is a hypothesis (%s), not calibrated against delivery history." % policy["source"], blocking=False))
    return out, summary


def owner_entries(fr, instance, expect):
    """The verified owner ledger of the instance the work names, or a blocking finding naming why it can't be used."""
    try:
        return fr["ownerlog"].read_for("agency", instance, expect, fr["registry"]), None
    except fr["ownerlog"].OwnerLogError as exc:
        return (None, None), finding(exc.reason, exc.detail)


def cmd_brief(a, fr):
    brief = load_json(a.brief, "brief")
    need(brief, BRIEF_KEYS, "brief")
    need(brief["estimate"], ("lines", "price"), "brief.estimate")
    with open(a.brief, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    (_, entries), broken = owner_entries(fr, brief["change_control"].get("contract_ref") if isinstance(brief["change_control"], dict) else None,
                                         {"tenant": brief["tenant_id"]})
    if broken:
        return {"findings": [broken], "brief_sha256": digest, "limits": LIMITS["brief"]}
    pins = {name: fr["ownerlog"].effective(entries, "pin", name) for name in PINS}
    missing = [finding(rule, "the owner log has no %s pin; the contract owner pins it with fleet owner-record --kind pin." % name)
               for name, rule in sorted(PINS.items()) if pins[name] is None]
    if missing:
        return {"findings": missing, "brief_sha256": digest, "limits": LIMITS["brief"]}
    rates = pins["rate-card"]["body"]["content"]
    need(rates, ("cost_per_hour",), "pinned rate card")
    policy = parse_policy(pins["margin-policy"]["body"]["content"], {e["subject"] for e in entries if e["kind"] == "pin"})
    parse_estimate(brief["estimate"], rates)
    findings, margin = check_brief(brief, rates, policy)
    margin["pinned"] = {name: {"path": e["body"]["path"], "sha256": e["body"]["sha256"], "owner_log_seq": e["seq"]} for name, e in sorted(pins.items())}
    return {"findings": findings, "margin": margin, "brief_sha256": digest, "limits": LIMITS["brief"]}


# ------------------------------------------------------------------ stages

def norm_id(x):
    """Same normalization as the owner log: NFKC, format characters (zero-width, soft hyphen) dropped, trimmed, lowercased."""
    text = unicodedata.normalize("NFKC", str(x or ""))
    return "".join(c for c in text if unicodedata.category(c) != "Cf").strip().lower()


def inside(base, rel):
    root = os.path.realpath(base)
    real = os.path.realpath(os.path.join(base, str(rel)))
    return real.startswith(root + os.sep)


def check_stages(ledger, contract, base, fr, entries):
    """A done or skipped stage counts only when the owner log holds the contract owner's acceptance for it: producer,
    acceptor (a registered role, or a human on the owner's roster), status and the evidence hashes accepted. The entries
    come from the ledger of this exact contract (read_for refuses any other), so every acceptance is under its hash.
    The worker's ledger must agree with it; acceptance files the worker writes count for nothing."""
    sha_file, roles, ol = fr["sha_file"], fr["roles"], fr["ownerlog"]
    out = [finding("contract-invalid", e) for e in fr["validate_contract"](contract)]
    spec = contract.get("spec", {})
    roster = ol.effective(entries, "roster", "stage-acceptors")
    humans = set(roster["body"]["humans"]) if roster else set()
    if not inside(base, ledger["brief"]):
        out.append(finding("evidence-outside-base", "the ledger's brief %s is outside --base." % ledger["brief"]))
    elif not os.path.isfile(os.path.join(base, ledger["brief"])):
        out.append(finding("evidence-missing", "brief %s is missing" % ledger["brief"]))
    elif sha_file(os.path.join(base, ledger["brief"])) != spec.get("sha256"):
        out.append(finding("scope-changed", "the brief no longer matches the contract's spec hash; return the scope change through the PM contract (factory-rig) and reissue the contract before any stage advances."))
    names = [s.get("stage") for s in ledger["stages"]]
    if names != list(STAGES):
        out.append(finding("stage-order", "stages must be exactly, in order: %s" % ", ".join(STAGES)))
        return out, None, []
    current, open_seen, accepted_by = None, False, []
    for s in ledger["stages"]:
        st, name = s.get("status"), s["stage"]
        if st not in ("done", "skipped", "pending"):
            out.append(finding("stage-order", "stage %s has status %r" % (name, st), where=name))
            continue
        if st == "pending":
            open_seen = True
            current = current or name
            continue
        if open_seen:
            out.append(finding("stage-skipped-ahead", "stage %s is %s after an earlier stage is still pending." % (name, st), where=name))
        producer = norm_id(s.get("producer"))
        if not producer:
            out.append(finding("stage-unattributed", "stage %s names no producer, so acceptance can't be checked for independence." % name, where=name))
        if s.get("acceptance"):
            out.append(finding("acceptance-not-from-owner-log", "stage %s points to acceptance file %s; only the contract owner's record in the owner log accepts a stage. Remove the pointer."
                               % (name, s["acceptance"]), where=name))
        rec = ol.effective(entries, "stage-acceptance", name)
        if rec is None:
            out.append(finding("stage-unaccepted", "stage %s has no acceptance in the owner log; the contract owner records it with fleet owner-record --kind stage-acceptance." % name, where=name))
            continue
        acc = rec["body"]
        acceptor, made_by = acc["accepted_by"], acc["producer"]
        accepted_by.append({"stage": name, "accepted_by": acceptor, "producer": made_by, "owner_log_seq": rec["seq"], "label": acc.get("label", "")})
        if made_by not in roles:
            out.append(finding("producer-unknown", "stage %s producer %s is not a registered role." % (name, made_by), where=name))
        if acc["status"] != st or (producer and made_by != producer):
            out.append(finding("acceptance-mismatch", "stage %s: the owner's acceptance records status %s and producer %s; the ledger says %s and %s."
                               % (name, acc["status"], made_by, st, producer or "nobody"), where=name))
        if acceptor.startswith("human:") and acceptor not in humans:
            out.append(finding("acceptor-not-on-roster", "stage %s is accepted by %s, who is not on the owner's human acceptor roster." % (name, acceptor), where=name))
        elif not acceptor.startswith("human:") and acceptor not in roles:
            out.append(finding("acceptor-unknown", "stage %s is accepted by %r, which is neither a rostered human nor a registered role." % (name, acceptor), where=name))
        if acceptor == made_by:
            out.append(finding("self-acceptance", "stage %s is accepted by its own producer %s." % (name, made_by), where=name))
        if acc["status"] == "skipped":
            if not str(acc.get("skip_reason", "")).strip() or not acceptor.startswith("human:"):
                out.append(finding("skip-without-reason", "stage %s is skipped without a reason accepted by a human." % name, where=name))
            continue
        accepted = {(e["path"], e["sha256"]) for e in acc["evidence"]}
        if not accepted:
            out.append(finding("evidence-missing", "stage %s is done with no accepted evidence." % name, where=name))
        for ev in s.get("evidence", []):
            if (ev.get("path"), ev.get("sha256")) not in accepted:
                out.append(finding("evidence-not-accepted", "stage %s evidence %s at this hash is not in the owner's acceptance; the acceptor must accept it again." % (name, ev.get("path")), where=name))
        for path, digest in sorted(accepted):
            if not inside(base, path):
                out.append(finding("evidence-outside-base", "stage %s evidence %s is outside --base." % (name, path), where=name))
                continue
            p = os.path.join(base, path)
            if not os.path.isfile(p):
                out.append(finding("evidence-missing", "stage %s evidence %s is missing." % (name, path), where=name))
                continue
            if sha_file(p) != digest:
                out.append(finding("evidence-stale", "stage %s evidence %s changed after it was accepted." % (name, path), where=name))
            if p.endswith(".json"):
                try:
                    with open(p, encoding="utf-8") as fh:
                        doc = json.load(fh)
                except ValueError:
                    doc = None
                if isinstance(doc, dict) and "handoff_id" in doc and norm_id(doc.get("producer")) not in ("", made_by):
                    out.append(finding("producer-contradicted", "stage %s says %s produced it, but handoff %s names %s." % (name, made_by, doc["handoff_id"], doc.get("producer")), where=name))
    return out, current, accepted_by


def cmd_stages(a, fr):
    ledger = load_json(a.ledger, "ledger")
    need(ledger, ("brief", "stages"), "ledger")
    contract = load_json(a.contract, "contract")
    (_, entries), broken = owner_entries(fr, contract.get("task_id") if isinstance(contract, dict) else None, {"contract_hash": fr["contract_hash"](contract)})
    if broken:
        return {"findings": [broken], "current_stage": None, "limits": LIMITS["stages"]}
    findings, current, accepted = check_stages(ledger, contract, a.base, fr, entries)
    return {"findings": findings, "current_stage": current, "stages": [(s.get("stage"), s.get("status")) for s in ledger["stages"]],
            "label": ledger.get("label", ""), "acceptances": accepted, "limits": LIMITS["stages"]}


# ------------------------------------------------------------------ support runbook

def check_runbook(text):
    out = []
    heads = {}
    for m in re.finditer(r"(?m)^##\s+(.+?)\s*$", text):
        heads[m.group(1).strip().lower()] = m.end()
    for sec in RUNBOOK_SECTIONS:
        start = heads.get(sec.lower())
        if start is None:
            out.append(finding("runbook-section-missing", "the support runbook has no '## %s' section." % sec, where=sec))
            continue
        body = re.split(r"(?m)^##\s", text[start:], maxsplit=1)[0]
        if not re.search(r"\w", body):
            out.append(finding("runbook-section-empty", "'## %s' is empty." % sec, where=sec))
    for n, line in enumerate(text.splitlines(), 1):
        if SECRET.search(line):
            out.append(finding("secret-in-runbook", "line %d looks like a credential; reference the vault entry instead." % n, where=n))
    return out


def cmd_support(a):
    try:
        with open(a.runbook, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        raise InputError("cannot read runbook %s: %s" % (a.runbook, exc))
    return {"findings": check_runbook(text), "sections_required": list(RUNBOOK_SECTIONS), "limits": LIMITS["support"]}


# ------------------------------------------------------------------ handoff

UPDATE_SHAPED = ("summary", "assumptions", "unresolved_decisions", "inputs", "outputs", "evidence", "label")


LABELS = ("tenant_id", "classification", "trust", "source_kind")


def build_update(spec, base, contract_sha, fr, intake):
    """Turn a worker's update (paths only) into a handoff.v1 worker update with hashes. Input labels and hashes come
    from the owner's intake in the owner log, never from the worker; an input the owner didn't list is refused, and
    so is one whose bytes changed since the intake or that is a symlink leaving its folder."""
    def full(rel):
        if not inside(base, rel):
            raise InputError("path %s is outside --base" % rel)
        p = os.path.join(base, rel)
        if not os.path.isfile(p):
            raise InputError("file %s does not exist under %s" % (rel, base))
        return p
    owner_labels = {i["path"]: i for i in intake["inputs"]}
    update, sources, problems = {}, [], []
    for key in ("summary", "assumptions", "unresolved_decisions"):
        if key in spec:
            update[key] = spec[key]
    update["inputs"] = []
    for i in spec.get("inputs", []):
        item = {"path": i} if isinstance(i, str) else dict(i)
        path = item.get("path")
        if path not in owner_labels:
            problems.append(finding("input-not-in-intake", "input %s is not in the owner's intake record, so it has no owner-set tenant or classification; it can't enter this handoff." % path))
            continue
        label = owner_labels[path]
        differs = [k for k in LABELS if k in item and item[k] != label[k]]
        if differs:
            problems.append(finding("input-label-disagrees", "input %s: the worker set %s, which differ from the owner's intake record; the owner's labels stand." % (path, ", ".join(differs))))
            continue
        try:
            with open(fr["ownerlog"].resolve_input(base, path), "rb") as fh:
                raw = fh.read()
        except fr["ownerlog"].OwnerLogError as exc:
            problems.append(finding(exc.reason, exc.detail))
            continue
        if hashlib.sha256(raw).hexdigest() != label["sha256"]:
            problems.append(finding("input-changed-since-intake", "input %s no longer matches the bytes the owner's intake recorded; the owner records a new intake." % path))
            continue
        text = raw.decode("utf-8", "replace")
        entry = fr["describe_source"](text, path, label["tenant_id"], label["classification"], label["source_kind"])
        entry.update(trust=label["trust"], sha256=label["sha256"])
        update["inputs"].append(entry)
        if label["trust"] == "untrusted":
            sources.append((path, text))
    update["outputs"] = [{"path": o["path"], "sha256": fr["sha_file"](full(o["path"])), "artifact_type": o["artifact_type"]}
                         for o in spec.get("outputs", [])]
    update["evidence"] = [{"path": e["path"], "sha256": fr["sha_file"](full(e["path"])), "about": e["about"],
                           "about_sha256": fr["sha_file"](full(e["about"])), "contract_hash": contract_sha}
                          for e in spec.get("evidence", [])]
    for key, value in spec.items():  # anything else is a protected-field attempt; guarded_update refuses it
        if key not in UPDATE_SHAPED:
            update[key] = value
    return update, sources, problems


def cmd_handoff(a, fr):
    contract = load_json(a.contract, "contract")
    spec = load_json(a.update, "worker update")
    current = fr["contract_hash"](contract)
    ol = fr["ownerlog"]
    (root, entries), broken = owner_entries(fr, contract.get("task_id") if isinstance(contract, dict) else None, {"contract_hash": current})
    if broken:
        return {"findings": [broken], "status": "refused", "limits": LIMITS["handoff"]}
    opened_e = ol.effective(entries, "open", a.handoff_id)
    if opened_e is None:
        return {"findings": [finding("handoff-not-opened", "the owner log has no open record for %s; the contract owner opens it with fleet owner-record --kind open." % a.handoff_id)],
                "status": "refused", "limits": LIMITS["handoff"]}
    owner = opened_e["body"]
    intake_e = ol.effective(entries, "intake", a.handoff_id)
    intake = intake_e["body"] if intake_e else {"inputs": []}
    ledger = fr["Ledger"](root)
    opened = {"opened": os.path.join(ledger.opened, a.handoff_id + ".json")}
    if ledger.opened_record(a.handoff_id) != owner:
        return {"findings": [finding("owner-record-conflict", "opened/%s.json differs from the owner log's open record; the owner log stands." % a.handoff_id)],
                "status": "refused", "paths": opened, "limits": LIMITS["handoff"]}
    h = fr["open_handoff"](owner)
    update, sources, problems = build_update(spec, a.base, current, fr, intake)
    if problems:
        return {"findings": problems, "status": "refused", "paths": opened, "limits": LIMITS["handoff"]}
    new, refused, scan = fr["guarded_update"](h, update, sources)
    receipt = ledger.submit(new)
    errors = list(receipt.get("errors", []))
    if not errors:
        errors = ol.submission_errors(new, entries, contract, a.base)
    paths = {"opened": os.path.join(ledger.opened, new["handoff_id"] + ".json")}
    if receipt["status"] in ("recorded", "duplicate"):
        paths["submitted"] = os.path.join(ledger.submitted, receipt["key"] + ".json")
    return {"findings": [finding("handoff-invalid", e) for e in errors], "status": receipt["status"],
            "idempotency_key": new["idempotency_key"], "next_consumer": new["next_consumer"], "paths": paths,
            "refused_fields": refused, "untrusted_findings": scan, "limits": LIMITS["handoff"]}


def fleet_tools():
    """Import factory-rig and company-fleets helpers, or return None when they are not beside this skill."""
    if not os.path.isdir(os.path.join(FLEET_SCRIPTS, "fleetlib")):
        return None
    sys.path.insert(0, FLEET_SCRIPTS)
    try:
        import fleetlib  # noqa: F401  (adds factory-rig to sys.path)
        from factory_rig.canon import sha_file
        from factory_rig.contract import contract_hash, validate_contract
        from fleetlib import ownerlog
        from fleetlib.handoff import Ledger, open_handoff
        from fleetlib.registry import Registry, fleet_file
        from fleetlib.untrusted import describe_source, guarded_update
    except ImportError:
        return None
    reg, roles = Registry(), set()
    for fleet in reg.fleet_dirs():
        try:
            roles |= {r["id"] for r in reg.load(fleet_file(fleet, "roles")).get("roles", [])}
        except (OSError, ValueError):
            continue
    return {"sha_file": sha_file, "contract_hash": contract_hash, "validate_contract": validate_contract,
            "Ledger": Ledger, "open_handoff": open_handoff, "describe_source": describe_source, "guarded_update": guarded_update,
            "ownerlog": ownerlog, "registry": reg, "roles": roles}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Agency engagement gate.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("brief")
    b.add_argument("--brief", required=True, help="the scoped brief; its tenant_id and change_control.contract_ref name the owner ledger")
    s = sub.add_parser("stages")
    s.add_argument("--ledger", required=True, help="the worker's stage ledger JSON; acceptances come from the contract's owner ledger")
    s.add_argument("--contract", required=True)
    s.add_argument("--base", required=True)
    r = sub.add_parser("support")
    r.add_argument("--runbook", required=True)
    h = sub.add_parser("handoff")
    for flag in ("--handoff-id", "--contract", "--base", "--update"):
        h.add_argument(flag, required=True)
    try:
        a = ap.parse_args(argv)
    except SystemExit as exc:
        if exc.code not in (0, None):
            print(json.dumps({"error": "usage: engagement_gate.py brief|stages|support|handoff with the required options"}, indent=2))
            return 2
        raise
    try:
        if a.cmd == "support":
            result = cmd_support(a)
        else:
            fr = fleet_tools()
            if fr is None:
                print(json.dumps({"ok": False, "status": "blocked", "reason": "company-fleets and factory-rig must sit beside this skill (looked in %s)" % FLEET_SCRIPTS}, indent=2))
                return 3
            result = {"brief": cmd_brief, "stages": cmd_stages, "handoff": cmd_handoff}[a.cmd](a, fr)
    except (InputError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"error": "%s: %s" % (type(exc).__name__, exc) if not isinstance(exc, InputError) else str(exc)}, indent=2, sort_keys=True))
        return 2
    result["ok"] = not any(f["blocking"] for f in result["findings"])
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
