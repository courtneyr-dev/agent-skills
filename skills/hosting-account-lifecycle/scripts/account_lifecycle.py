#!/usr/bin/env python3
"""hosting-account-lifecycle: move a hosted account through its lifecycle, recoverably.

One transition table (RULES) owns which action is legal from which state and who must approve it.
Side effects go through a fake WHM-shaped panel adapter. Provisioning reuses factory-rig leases and
receipts, so a retry, a crash between side effects or a duplicate callback never repeats work.

Owner records, never the requester's input, decide each gate: qualify issues the ownership token and
refuses a domain another live account holds, or a subdomain or parent of another tenant's domain;
suspend reads clauses and approvers only from the owner's suspension-policy.json, and an abuse clause
also needs an approved hosting-abuse-response case that names a host of this account's domain (from the
account registry in the state folder), verified against the abuse owner's fixed ledger and consumed
once; export accepts only a hosting-data-migration bundle whose manifest the data owner's ledger, at its
fixed path in the fleet's owner folder, recorded for this tenant. --export-ledger and --abuse-anchors are
refused by name unless they are those fixed ledgers. Callbacks are deduplicated per account.

The state folder (--state-dir) is the account system itself: the registry, the fake panel it drives, the
leases and receipts. A caller who points it elsewhere drives a different panel, not this one's.

Exit codes: 0 ok, 1 refused or check failed, 2 invalid input or usage, 3 blocked by a missing capability.
Python 3.9+ standard library plus the sibling skills factory-rig, hosting-data-migration and
hosting-abuse-response.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import fcntl
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

SKILL_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RIG_SCRIPTS = os.path.normpath(os.path.join(SKILL_DIR, "..", "factory-rig", "scripts"))
if not os.path.isdir(os.path.join(RIG_SCRIPTS, "factory_rig")):
    raise ImportError("hosting-account-lifecycle needs skills/factory-rig beside it (looked in %s)" % RIG_SCRIPTS)
if RIG_SCRIPTS not in sys.path:
    sys.path.insert(0, RIG_SCRIPTS)

from factory_rig import canon  # noqa: E402
from factory_rig.lease import LeaseDenied, LeaseStore, StaleEpoch, process_fingerprint  # noqa: E402
from factory_rig.receipts import STEPS, ReceiptStore, idempotency_key  # noqa: E402

SCRIPT = os.path.abspath(__file__)
DEFAULT_FIXTURES = os.path.normpath(os.path.join(SKILL_DIR, "..", "company-fleets", "fleets", "hosting", "fixtures", "account-lifecycle"))
OWNER_POLICY = os.path.join(DEFAULT_FIXTURES, "suspension-policy.json")
for _sibling in ("hosting-data-migration", "hosting-abuse-response"):
    _path = os.path.normpath(os.path.join(SKILL_DIR, "..", _sibling, "scripts"))
    if _path not in sys.path:
        sys.path.insert(0, _path)
PROFILES = ("affiliate", "reseller", "shared", "managed", "platform", "enterprise")
OWNERSHIP_METHODS = ("dns-txt", "http-file")
CHECK_STATUSES = ("ok", "degraded", "failing")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
EVENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
HUMAN_RE = re.compile(r"^human:[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LEASE_TTL = 600.0

ASSUMPTIONS = [
    "The panel is a fake WHM-shaped adapter; the real cPanel/WHM adapter is blocked (no provider selected, no credentials).",
    "Dates are UTC calendar dates; renewal dates come from billing and this skill does not compute them.",
    "Leases use flock on one host and a %d s TTL; a takeover needs proof the holder process is gone." % LEASE_TTL,
]

# action -> from-states, to-state (None keeps the state), required inputs, authority, waiver-needed-from.
RULES: Dict[str, Dict[str, Any]] = {
    "qualify": {"frm": ("requested",), "to": "qualified", "inputs": ("request",), "authority": None},
    "provision": {"frm": ("qualified",), "to": "provisioned", "inputs": (), "authority": None},
    "verify-ownership": {"frm": ("provisioned",), "to": "ownership-verified", "inputs": ("observed",), "authority": None},
    "configure": {"frm": ("ownership-verified",), "to": "configured", "inputs": ("php_version",), "authority": None},
    "activate": {"frm": ("configured",), "to": "active", "inputs": (), "authority": None},
    "monitor": {"frm": ("active",), "to": "active", "inputs": ("check_result",), "authority": None},
    "renew": {"frm": ("active", "suspended"), "to": None, "inputs": ("until",), "authority": None},
    "suspend": {"frm": ("active",), "to": "suspended", "inputs": (), "authority": "policy+human"},
    "unsuspend": {"frm": ("suspended",), "to": "active", "inputs": (), "authority": "policy+human"},
    "export": {"frm": ("active", "suspended"), "to": "exported", "inputs": ("bundle",), "authority": None},
    "decommission": {"frm": ("exported", "active", "suspended"), "to": "decommissioned", "inputs": (),
                     "authority": "owner-human", "waiver_from": ("active", "suspended")},
}


class Refused(Exception):
    """Exit 1: the action is not allowed, or a check found a violation."""

    def __init__(self, reasons: List[str], **extra: Any):
        super().__init__("; ".join(reasons))
        self.reasons, self.extra = reasons, extra


class InvalidInput(Exception):
    """Exit 2: bad JSON, missing file, schema problem or usage."""


class Blocked(Exception):
    """Exit 3: a capability this skill needs is not available."""


# --------------------------------------------------------------------------- input boundary

def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_doc(path: str, what: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except FileNotFoundError:
        raise InvalidInput("%s file not found: %s" % (what, path))
    except (ValueError, OSError) as exc:
        raise InvalidInput("%s file is not valid JSON: %s (%s)" % (what, path, exc))
    if not isinstance(doc, dict):
        raise InvalidInput("%s file must hold a JSON object: %s" % (what, path))
    return doc


def need(doc: Dict[str, Any], key: str, kind: type, what: str) -> Any:
    val = doc.get(key)
    if not isinstance(val, kind) or isinstance(val, bool) and kind is not bool or (kind is str and not val.strip()):
        raise InvalidInput("%s: %r must be a non-empty %s" % (what, key, kind.__name__))
    return val


def ident(value: str, what: str) -> str:
    if not ID_RE.match(value):
        raise InvalidInput("%s %r must be lowercase letters, digits and hyphens (max 63)" % (what, value))
    return value


def parse_date(value: str, what: str) -> str:
    try:
        if not DATE_RE.match(value):
            raise ValueError(value)
        datetime.date.fromisoformat(value)
    except ValueError:
        raise InvalidInput("%s %r must be a YYYY-MM-DD date" % (what, value))
    return value


def load_request(path: str) -> Dict[str, Any]:
    doc = read_doc(path, "request")
    ident(need(doc, "account_id", str, "request"), "account_id")
    ident(need(doc, "tenant_id", str, "request"), "tenant_id")
    if need(doc, "profile", str, "request") not in PROFILES:
        raise InvalidInput("request: profile %r is not one of %s" % (doc["profile"], ", ".join(PROFILES)))
    need(doc, "domain", str, "request")
    need(doc, "package", str, "request")
    for pkg in need(doc, "packages", list, "request"):
        if not isinstance(pkg, dict):
            raise InvalidInput("request: every packages entry must be an object")
        need(pkg, "id", str, "request package")
        versions = need(pkg, "php_versions", list, "request package")
        if not versions or not all(isinstance(v, str) for v in versions):
            raise InvalidInput("request package %s: php_versions must be a non-empty list of strings" % pkg["id"])
    own = need(doc, "ownership", dict, "request")
    if own.get("method") not in OWNERSHIP_METHODS:
        raise InvalidInput("request: ownership.method must be one of %s" % ", ".join(OWNERSHIP_METHODS))
    parse_date(need(doc, "initial_term_until", str, "request"), "initial_term_until")
    doc["_sha256"] = canon.sha({k: v for k, v in doc.items() if k != "_sha256"})
    return doc


def load_observed(path: str) -> Dict[str, Any]:
    doc = read_doc(path, "observed-answers")
    for rec in need(doc, "records", list, "observed-answers"):
        if not isinstance(rec, dict) or rec.get("kind") not in OWNERSHIP_METHODS or not isinstance(rec.get("name"), str) \
                or not isinstance(rec.get("value"), str):
            raise InvalidInput("observed-answers: each record needs kind (%s), name and value strings" % ", ".join(OWNERSHIP_METHODS))
    return doc


def load_check_result(path: str) -> Dict[str, Any]:
    doc = read_doc(path, "check-result")
    ident(need(doc, "account_id", str, "check-result"), "account_id")
    ident(need(doc, "tenant_id", str, "check-result"), "tenant_id")
    need(doc, "checked_at", str, "check-result")
    if doc.get("status") not in CHECK_STATUSES:
        raise InvalidInput("check-result: status must be one of %s" % ", ".join(CHECK_STATUSES))
    return doc


def load_policy(path: str) -> Dict[str, Any]:
    """Only the owner's policy file counts; a --policy-file pointing anywhere else is refused, not read."""
    if os.path.realpath(path) != os.path.realpath(OWNER_POLICY):
        raise Refused(["policy-not-owner-file: clauses and approvers come only from %s, never from %s" % (OWNER_POLICY, path)])
    doc = read_doc(OWNER_POLICY, "policy")
    for clause in need(doc, "clauses", list, "policy"):
        if not isinstance(clause, dict) or not isinstance(clause.get("id"), str) or not isinstance(clause.get("authorizes"), dict):
            raise InvalidInput("policy: each clause needs an id string and an authorizes object")
        for reasons in clause["authorizes"].values():
            if not isinstance(reasons, list) or not all(isinstance(r, str) for r in reasons):
                raise InvalidInput("policy: clause %s authorizes must map actions to lists of reason strings" % clause["id"])
        if not isinstance(clause.get("approvers"), list) or not all(isinstance(a, str) and HUMAN_RE.match(a) for a in clause["approvers"]):
            raise InvalidInput("policy: clause %s needs an approvers list of human: principals" % clause["id"])
    if not isinstance(doc.get("decommission_approvers"), list) or not all(isinstance(a, str) and HUMAN_RE.match(a) for a in doc["decommission_approvers"]):
        raise InvalidInput("policy: decommission_approvers must list human: principals")
    return doc


def load_event(path: str) -> Dict[str, Any]:
    doc = read_doc(path, "callback event")
    if not EVENT_RE.match(need(doc, "event_id", str, "callback event")):
        raise InvalidInput("callback event: event_id must be letters, digits, dot, underscore or hyphen (max 64)")
    if need(doc, "type", str, "callback event") != "account.created":
        raise InvalidInput("callback event: only type account.created is supported, got %r" % doc["type"])
    ident(need(doc, "account_id", str, "callback event"), "account_id")
    ident(need(doc, "tenant_id", str, "callback event"), "tenant_id")
    return doc


def export_record(bundle: str, named_ledger: Optional[str] = None) -> Dict[str, Any]:
    """The bundle's manifest hash, artifact hashes and tenant, as the data owner's fixed ledger recorded them."""
    import data_migration as dm
    try:
        ledger = dm.owner_ledger(named_ledger, bundle)
    except dm.Refused as exc:
        raise Refused(["export: %s" % exc])
    manifest_path = os.path.join(bundle, dm.MANIFEST)
    if not os.path.isfile(manifest_path):
        raise Refused(["export: %s is not a hosting-data-migration bundle (no manifest.json)" % bundle])
    manifest = read_doc(manifest_path, "bundle manifest")
    try:
        dm._check_manifest(manifest)
    except dm.InputError as exc:
        raise Refused(["export: %s" % exc])
    for name, art in sorted(manifest["artifacts"].items()):
        path = os.path.join(bundle, name)
        if not os.path.isfile(path) or dm.sha256_file(path) != art["sha256"]:
            raise Refused(["export: bundle artifact %s is missing or differs from its manifest" % name])
    manifest_sha = dm.sha256_file(manifest_path)
    try:
        recorded = [r for r in dm.ledger_records(ledger, "export") if r.get("manifest_sha256") == manifest_sha]
    except dm.Refused as exc:
        raise Refused(["export: %s" % exc])
    if not recorded:
        raise Refused(["export: the bundle's manifest sha256 %s is not in the data owner's ledger %s" % (manifest_sha, ledger)])
    return {"manifest_sha256": manifest_sha, "tenant": recorded[-1].get("tenant"), "bundle": os.path.abspath(bundle),
            "ledger": os.path.abspath(ledger)}


# --------------------------------------------------------------------------- state, locks, panel

class Ctx:
    """One state directory: accounts, fake panel, ledger, leases, receipts and callbacks."""

    def __init__(self, state_dir: str, actor: str = "skill:hosting-account-lifecycle", panel: str = "fake"):
        if panel != "fake":
            raise Blocked("the %s panel adapter is not implemented: no provider is selected, no credentials exist, "
                          "and this skill makes no network calls. Use --panel fake." % panel)
        self.dir, self.actor = os.path.abspath(state_dir), actor

    def path(self, *parts: str) -> str:
        return os.path.join(self.dir, *parts)

    def get(self, account_id: str) -> Optional[Dict[str, Any]]:
        try:
            return canon.read_json(self.path("accounts", account_id + ".json"))
        except ValueError:
            raise InvalidInput("account file for %s is not valid JSON" % account_id)

    def require(self, account_id: str) -> Dict[str, Any]:
        acct = self.get(account_id)
        if acct is None:
            raise Refused(["no account %s in %s; qualify it first" % (account_id, self.dir)])
        return acct

    def put(self, acct: Dict[str, Any]) -> None:
        canon.atomic_write(self.path("accounts", acct["account_id"] + ".json"), json.dumps(acct, indent=2, sort_keys=True) + "\n")

    @contextlib.contextmanager
    def lock(self, name: str) -> Iterator[None]:
        os.makedirs(self.path("locks"), exist_ok=True)
        fd = os.open(self.path("locks", name + ".lock"), os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def panel(self) -> "FakePanel":
        return FakePanel(self)


class FakePanel:
    """WHM API 1 shaped fake. Function names follow api.docs.cpanel.net; every call lands in panel-calls.jsonl."""

    def __init__(self, ctx: Ctx):
        self.state_path, self.log_path = ctx.path("panel.json"), ctx.path("panel-calls.jsonl")

    def _call(self, fn: str, **params: Any) -> Dict[str, Any]:
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"fn": fn, "params": params, "at": now(), "pid": os.getpid()}, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return canon.read_json(self.state_path, {"accounts": {}})

    def _save(self, doc: Dict[str, Any]) -> None:
        canon.atomic_write(self.state_path, json.dumps(doc, indent=2, sort_keys=True) + "\n")

    def _existing(self, doc: Dict[str, Any], user: str, fn: str) -> Dict[str, Any]:
        if user not in doc["accounts"]:
            raise Refused(["panel %s failed: no account %s" % (fn, user)])
        return doc["accounts"][user]

    def listaccts(self) -> Dict[str, Dict[str, Any]]:
        return self._call("listaccts")["accounts"]

    def createacct(self, username: str, domain: str, plan: str) -> None:
        doc = self._call("createacct", username=username, domain=domain, plan=plan)
        if username in doc["accounts"]:
            raise Refused(["panel createacct failed: account %s already exists" % username])
        doc["accounts"][username] = {"domain": domain, "plan": plan, "suspended": False, "suspend_reason": None}
        self._save(doc)

    def suspendacct(self, user: str, reason: str) -> None:
        doc = self._call("suspendacct", user=user, reason=reason)
        self._existing(doc, user, "suspendacct").update({"suspended": True, "suspend_reason": reason})
        self._save(doc)

    def unsuspendacct(self, user: str) -> None:
        doc = self._call("unsuspendacct", user=user)
        self._existing(doc, user, "unsuspendacct").update({"suspended": False, "suspend_reason": None})
        self._save(doc)

    def removeacct(self, user: str) -> None:
        doc = self._call("removeacct", user=user)
        self._existing(doc, user, "removeacct")
        del doc["accounts"][user]
        self._save(doc)

    def changepackage(self, user: str, pkg: str) -> None:
        doc = self._call("changepackage", user=user, pkg=pkg)
        self._existing(doc, user, "changepackage")["plan"] = pkg
        self._save(doc)


def panel_call_count(state_dir: str, fn: str) -> int:
    path = os.path.join(state_dir, "panel-calls.jsonl")
    if not os.path.exists(path):
        return 0
    with open(path, "r", encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip() and json.loads(line)["fn"] == fn)


def ledger_entries(state_dir: str) -> List[Dict[str, Any]]:
    path = os.path.join(state_dir, "entitlements.jsonl")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


# --------------------------------------------------------------------------- the transition engine

def approver_reasons(flag: str, value: Optional[str], prefix: str = "authority") -> List[str]:
    if not value:
        return ["%s: %s needs human:<slug>" % (prefix, flag)]
    if "." in value:
        return ["%s: %s %s is a role id; a human must approve" % (prefix, flag, value)]
    if not HUMAN_RE.match(value):
        return ["%s: %s %r must look like human:<slug>" % (prefix, flag, value)]
    return []


def abuse_case_reasons(acct: Dict[str, Any], inp: Dict[str, Any]) -> List[str]:
    """An abuse suspension executes an approval hosting-abuse-response recorded, once, for a host of this account; it
    never stands on its own. Every check verify runs applies, the abuse owner's fixed ledger included."""
    import abuse_case
    case = inp.get("abuse_case")
    if not case:
        return ["authority: this clause suspends only on an approved hosting-abuse-response case; pass --abuse-case"]
    if not os.path.isdir(case):
        return ["authority: abuse case %s is not a folder" % case]
    try:
        abuse_case.owner_ledger(case, inp.get("abuse_anchors"))
        state = abuse_case.verify_case(case)
    except abuse_case.Refusal as exc:
        return ["authority: %s: %s" % (exc.payload["refusal"], exc.payload["detail"])]
    except abuse_case.Invalid as exc:
        return ["authority: abuse case %s is unreadable: %s" % (case, exc)]
    if state["verdict"] != "intact":
        return ["authority: abuse case failed verification: %s" % "; ".join(state["problems"])]
    last = [e for e in abuse_case._read_custody(abuse_case._paths(case)["custody"]) if isinstance(e, dict)][-1]
    manifest = read_doc(abuse_case._paths(case)["manifest"], "abuse case manifest")
    detail = last.get("detail", {})
    reasons = []
    if last.get("state") != "approved-for-human-execution" or detail.get("action") != "suspend":
        reasons.append("authority: abuse case %s is %s, not an approved suspension" % (manifest.get("case_id"), last.get("state")))
    if manifest.get("tenant_id") != acct["tenant_id"]:
        reasons.append("authority: abuse case is about %s, not this account's tenant %s" % (manifest.get("tenant_id"), acct["tenant_id"]))
    if detail.get("approved_by") != inp.get("approved_by"):
        reasons.append("authority: the abuse case was approved by %s, not %s" % (detail.get("approved_by"), inp.get("approved_by")))
    hosts = manifest.get("hosts") if isinstance(manifest.get("hosts"), list) else []
    if not any(isinstance(h, str) and abuse_case.host_under(h, acct["domain"]) for h in hosts):
        reasons.append("authority: case-not-for-this-account: abuse case %s names hosts %s; account %s holds %s in the account "
                       "registry, and the case names none of its hosts" % (manifest.get("case_id"), hosts, acct["account_id"], acct["domain"]))
    used = abuse_case.consumed(str(manifest.get("case_id")))
    if used is not None:
        reasons.append("authority: case-consumed: abuse case %s already executed (%s); one approval executes once"
                       % (manifest.get("case_id"), json.dumps(used, sort_keys=True)))
    return reasons


def abuse_clause(action: str, inp: Dict[str, Any]) -> bool:
    """True when the chosen clause executes only on an approved abuse case."""
    clause = next((c for c in inp["policy_doc"]["clauses"] if c["id"] == inp.get("policy")), None)
    return clause is not None and action in clause.get("abuse_case_required_for", [])


def consume_abuse_case(ctx: "Ctx", acct: Dict[str, Any], inp: Dict[str, Any]) -> str:
    import abuse_case
    manifest = read_doc(abuse_case._paths(inp["abuse_case"])["manifest"], "abuse case manifest")
    try:
        abuse_case.consume_case(manifest["case_id"], {"account_id": acct["account_id"], "tenant_id": acct["tenant_id"],
                                                      "domain": acct["domain"], "state_dir": ctx.dir})
    except abuse_case.Refusal as exc:
        raise Refused(["authority: %s: %s" % (exc.payload["refusal"], exc.payload["detail"])])
    return manifest["case_id"]


def authority_reasons(rule: Dict[str, Any], action: str, inp: Dict[str, Any], acct: Optional[Dict[str, Any]] = None) -> List[str]:
    kind = rule["authority"]
    if kind is None:
        return []
    reasons = approver_reasons("--approved-by", inp.get("approved_by"))
    if kind == "owner-human":
        if not reasons and inp.get("approved_by") not in inp["policy_doc"]["decommission_approvers"]:
            reasons.append("authority: %s is not a decommission approver in the owner's policy" % inp.get("approved_by"))
    if kind == "policy+human":
        clause_id, reason, doc = inp.get("policy"), inp.get("reason"), inp["policy_doc"]
        if not clause_id:
            reasons.append("authority: %s needs --policy <clause id> from the owner's policy file" % action)
        else:
            clause = next((c for c in doc["clauses"] if c["id"] == clause_id), None)
            if clause is None:
                reasons.append("authority: clause %s is not in the owner's policy file" % clause_id)
            elif not reason or reason not in clause["authorizes"].get(action, []):
                reasons.append("authority: clause %s does not authorize %s for reason %r" % (clause_id, action, reason))
            else:
                if inp.get("approved_by") not in clause["approvers"]:
                    reasons.append("authority: %s is not an approver of clause %s in the owner's policy" % (inp.get("approved_by"), clause_id))
                if action in clause.get("abuse_case_required_for", []) and acct is not None:
                    reasons += abuse_case_reasons(acct, inp)
    return reasons


def check_qualify(acct: Dict[str, Any], inp: Dict[str, Any]) -> List[str]:
    req, reasons = inp["request"], []
    if req["profile"] == "affiliate":
        reasons.append("profile affiliate refers customers and operates no accounts; hand the customer to the provider instead")
    if req["package"] not in [p["id"] for p in req["packages"]]:
        reasons.append("package %s is not in the request's package list" % req["package"])
    return reasons


def ownership_name(method: str, domain: str) -> str:
    return "_hosting-verify." + domain if method == "dns-txt" else "http://%s/.well-known/hosting-verify.txt" % domain


def check_verify(acct: Dict[str, Any], inp: Dict[str, Any]) -> List[str]:
    own, name = acct["ownership"], ownership_name(acct["ownership"]["method"], acct["domain"])
    seen = [r for r in inp["observed"]["records"] if r["kind"] == own["method"] and r["name"] == name]
    if not seen:
        return ["ownership: no observed %s record named %s" % (own["method"], name)]
    if not hmac.compare_digest(seen[0]["value"].encode(), own["expected_token"].encode()):
        return ["ownership: observed token at %s does not match the expected token" % name]
    return []


def check_configure(acct: Dict[str, Any], inp: Dict[str, Any]) -> List[str]:
    supported = acct["package"]["php_versions"]
    if inp["php_version"] not in supported:
        return ["php_version %s is not supported by package %s (supported: %s)" % (inp["php_version"], acct["package"]["id"], ", ".join(supported))]
    return []


def check_monitor(acct: Dict[str, Any], inp: Dict[str, Any]) -> List[str]:
    res = inp["check_result"]
    if (res["account_id"], res["tenant_id"]) != (acct["account_id"], acct["tenant_id"]):
        return ["check result is for %s/%s, not %s/%s" % (res["tenant_id"], res["account_id"], acct["tenant_id"], acct["account_id"])]
    return []


def check_renew(acct: Dict[str, Any], inp: Dict[str, Any]) -> List[str]:
    if inp["until"] <= acct["renewed_until"]:
        return ["renewed_until %s must be later than the current %s" % (inp["until"], acct["renewed_until"])]
    return []


def waiver_reasons(rule: Dict[str, Any], acct: Dict[str, Any], inp: Dict[str, Any]) -> List[str]:
    if acct["state"] not in rule.get("waiver_from", ()):
        return []
    if not inp.get("waiver"):
        return ["waiver: decommissioning from %s needs an export first or --waiver human:<slug>" % acct["state"]]
    reasons = approver_reasons("--waiver", inp["waiver"], "waiver")
    if not reasons and inp["waiver"] not in inp["policy_doc"]["decommission_approvers"]:
        reasons.append("waiver: %s is not a decommission approver in the owner's policy" % inp["waiver"])
    return reasons


def check_export(acct: Dict[str, Any], inp: Dict[str, Any]) -> List[str]:
    if inp["bundle"]["tenant"] != acct["tenant_id"]:
        return ["export: the ledger records this bundle for %s, not %s" % (inp["bundle"]["tenant"], acct["tenant_id"])]
    return []


def check_decommission(acct: Dict[str, Any], inp: Dict[str, Any]) -> List[str]:
    """An export counts only while the bundle and its ledger record still match what export saw."""
    if acct["state"] != "exported":
        return []
    saved = acct.get("export", {})
    try:
        now_rec = export_record(saved.get("bundle", ""))
    except Refused as exc:
        return ["export-changed: %s" % "; ".join(exc.reasons)]
    if (now_rec["manifest_sha256"], now_rec["tenant"]) != (saved.get("manifest_sha256"), acct["tenant_id"]):
        return ["export-changed: the bundle or its ledger record differs from what export recorded"]
    return []


CHECKS: Dict[str, Callable[[Dict[str, Any], Dict[str, Any]], List[str]]] = {
    "qualify": check_qualify, "verify-ownership": check_verify, "configure": check_configure,
    "monitor": check_monitor, "renew": check_renew, "export": check_export, "decommission": check_decommission,
}


def decide(acct: Dict[str, Any], action: str, inp: Dict[str, Any], extra_from: Tuple[str, ...] = ()) -> None:
    """Pure refusal check: raise Refused with every reason, or return."""
    rule, state = RULES[action], acct["state"] if acct else None
    allowed = rule["frm"] + extra_from
    if state not in allowed:
        raise Refused(["%s is not allowed from %s; allowed from: %s" % (action, state or "no account", ", ".join(allowed))],
                      allowed_from=list(allowed), state=state)
    reasons = authority_reasons(rule, action, inp, acct) + waiver_reasons(rule, acct, inp) + CHECKS.get(action, lambda a, i: [])(acct, inp)
    if reasons:
        raise Refused(reasons, state=state)


def up_qualify(acct: Dict[str, Any], inp: Dict[str, Any]) -> None:
    req = inp["request"]
    acct.update({
        "domain": normal_domain(req["domain"]), "package": next(p for p in req["packages"] if p["id"] == req["package"]),
        "ownership": {"method": req["ownership"]["method"], "expected_token": "hv-" + secrets.token_hex(16),
                      "issued_by": "the account state's owner at qualify", "verified_at": None},
        "config": {"php_version": None}, "renewed_until": req["initial_term_until"], "request_sha256": req["_sha256"]})


def up_verify(acct: Dict[str, Any], inp: Dict[str, Any]) -> None:
    acct["ownership"]["verified_at"] = now()


def up_configure(acct: Dict[str, Any], inp: Dict[str, Any]) -> None:
    acct["config"]["php_version"] = inp["php_version"]


def up_monitor(acct: Dict[str, Any], inp: Dict[str, Any]) -> None:
    res = inp["check_result"]
    acct["last_check"] = {"status": res["status"], "checked_at": res["checked_at"], "sha256": canon.sha(res)}


def up_renew(acct: Dict[str, Any], inp: Dict[str, Any]) -> None:
    acct["renewed_until"] = inp["until"]


def up_export(acct: Dict[str, Any], inp: Dict[str, Any]) -> None:
    acct["export"] = dict(inp["bundle"])


def up_decommission(acct: Dict[str, Any], inp: Dict[str, Any]) -> None:
    if acct["state"] in RULES["decommission"]["waiver_from"]:
        acct["waiver"] = {"approved_by": inp["waiver"]}


UPDATES: Dict[str, Callable[[Dict[str, Any], Dict[str, Any]], None]] = {
    "qualify": up_qualify, "verify-ownership": up_verify, "configure": up_configure, "monitor": up_monitor,
    "renew": up_renew, "export": up_export, "decommission": up_decommission,
}


def panel_sync(ctx: Ctx, action: str, acct: Dict[str, Any], inp: Dict[str, Any]) -> List[str]:
    """Inspect the panel first and call only when it does not already show the goal."""
    panel, user = ctx.panel(), acct["account_id"]
    row = panel.listaccts().get(user)
    if action == "decommission":
        if row is None:
            return []
        panel.removeacct(user)
        return ["removeacct"]
    if row is None:
        raise Refused(["panel has no account %s; reconcile before %s" % (user, action)])
    want = action == "suspend"
    if row["suspended"] == want:
        return []
    if want:
        panel.suspendacct(user, inp["reason"])
    else:
        panel.unsuspendacct(user)
    return ["suspendacct" if want else "unsuspendacct"]


def history_entry(ctx: Ctx, action: str, frm: Optional[str], to: str, epoch: Optional[int], approved_by: Optional[str] = None) -> Dict[str, Any]:
    entry: Dict[str, Any] = {"action": action, "from": frm, "to": to, "at": now(), "actor": ctx.actor, "epoch": epoch}
    if approved_by:
        entry["approved_by"] = approved_by
    return entry


def new_account(req: Dict[str, Any], ctx: Ctx) -> Dict[str, Any]:
    return {"account_id": req["account_id"], "tenant_id": req["tenant_id"], "profile": req["profile"], "package": None,
            "state": "requested", "history": [history_entry(ctx, "request", None, "requested", None)]}


def normal_domain(domain: str) -> str:
    return domain.strip().lower().rstrip(".")


def related_domains(a: str, b: str) -> bool:
    """One is the other or a subdomain of it: the owner's host map gives a subdomain to its parent's tenant."""
    a, b = normal_domain(a), normal_domain(b)
    return a == b or a.endswith("." + b) or b.endswith("." + a)


def domain_holders(ctx: Ctx, domain: str, account_id: str, tenant_id: str) -> List[str]:
    """Other live accounts in this state (the owner's registry) that hold the domain, or, for another tenant, a parent
    or subdomain of it."""
    held = []
    folder = ctx.path("accounts")
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        other = canon.read_json(os.path.join(folder, name)) if name.endswith(".json") else None
        if not other or other["account_id"] == account_id or other.get("state") == "decommissioned":
            continue
        theirs = str(other.get("domain") or "")
        if normal_domain(theirs) == normal_domain(domain) or (other["tenant_id"] != tenant_id and related_domains(theirs, domain)):
            held.append("%s (%s, %s)" % (other["account_id"], other["tenant_id"], normal_domain(theirs)))
    return held


def apply_action(ctx: Ctx, action: str, account_id: str, inp: Dict[str, Any]) -> Dict[str, Any]:
    rule = RULES[action]

    def current() -> Optional[Dict[str, Any]]:
        acct = ctx.get(account_id)
        return new_account(inp["request"], ctx) if acct is None and action == "qualify" else acct

    decide(current(), action, inp)  # refuse before taking any lock or writing anything
    with ctx.lock("domains"), ctx.lock(account_id):
        acct = current()
        decide(acct, action, inp)  # the state may have moved while we waited for the lock
        if action in ("qualify", "verify-ownership"):
            held = domain_holders(ctx, inp["request"]["domain"] if action == "qualify" else acct["domain"], account_id, acct["tenant_id"])
            if held:
                raise Refused(["domain-held: %s is already held by %s" % (inp["request"]["domain"] if action == "qualify" else acct["domain"],
                                                                       ", ".join(held))])
        consumed = consume_abuse_case(ctx, acct, inp) if action == "suspend" and abuse_clause(action, inp) else None
        calls = panel_sync(ctx, action, acct, inp) if action in ("suspend", "unsuspend", "decommission") else []
        before = acct["state"]
        UPDATES.get(action, lambda a, i: None)(acct, inp)
        acct["state"] = rule["to"] or before
        acct["history"].append(history_entry(ctx, action, before, acct["state"], None, inp.get("approved_by")))
        ctx.put(acct)
    out = {"verdict": "ok", "action": action, "account_id": account_id, "from": before, "to": acct["state"], "panel_calls": calls}
    if consumed:
        out["abuse_case_consumed"] = consumed
    if action == "qualify":
        own = acct["ownership"]
        out["publish"] = {"kind": own["method"], "name": ownership_name(own["method"], acct["domain"]), "value": own["expected_token"],
                          "note": "the token is issued here; a token in the request is ignored"}
    return out


# --------------------------------------------------------------------------- provision: leases, receipts, recovery

def take_lease(ctx: Ctx, store: LeaseStore, repo: str, task: str, key: str, owner_pid: int) -> Dict[str, Any]:
    """Acquire the provision lease. Every acquire and takeover runs under one flock per account, so no new
    holder can appear between the liveness check and `fence` (fence kills whatever live process holds the lease)."""
    account_id = task.split(":", 1)[1]
    with ctx.lock("takeover-" + account_id):
        for _ in range(3):
            try:
                return store.acquire(repo, task, key, "fake-whm", uuid.uuid4().hex[:12], ctx.dir, owner_pid, ttl=LEASE_TTL)
            except LeaseDenied:
                cur = store.status(repo, task)
                if cur is None or cur["state"] not in ("active", "uncertain"):
                    continue  # released while we looked; acquire again
                fp = process_fingerprint(cur["owner_pid"])
                if fp is not None and fp == cur.get("owner_fingerprint"):
                    raise Refused(["in progress: provision of %s is held by live pid %d (epoch %d); never fence a live holder"
                                   % (account_id, cur["owner_pid"], cur["epoch"])], holder_pid=cur["owner_pid"])
                try:
                    store.fence(repo, task)  # the holder is gone, so this kills nothing; it marks the lease takeover-safe
                except LeaseDenied:
                    continue  # the holder released between our read and the fence
    raise Refused(["in progress: the lease for %s kept changing hands" % account_id])


def provision(ctx: Ctx, account_id: str, owner_pid: int, after_step: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    acct = ctx.require(account_id)
    key = idempotency_key(account_id, "provision", acct["request_sha256"], canon.sha(acct["package"]))
    receipts = ReceiptStore(ctx.path("receipts"))
    rec = receipts.get(key)
    if rec is not None and rec["step"] == "complete":
        return {"verdict": "ok", "status": "already-complete", "account_id": account_id, "receipt_key": key, "receipt_step": "complete",
                "panel_calls": [], "skipped": ["every step: the receipt is complete"]}
    decide(acct, "provision", {}, extra_from=("provisioned",) if rec is not None else ())  # a resumed run may find state already moved
    repo, task = "hosting/" + acct["tenant_id"], "provision:" + account_id
    leases = LeaseStore(ctx.path("leases"))
    epoch = take_lease(ctx, leases, repo, task, key, owner_pid)["epoch"]
    made: List[str] = []
    skipped: List[str] = []

    def guard() -> None:
        leases.assert_current(repo, task, epoch)  # StaleEpoch if a newer holder fenced us

    def reached(step: str) -> None:
        if after_step:
            after_step(step)

    rec = receipts.begin(key, {"task_id": account_id, "account_id": account_id, "tenant_id": acct["tenant_id"],
                               "request_sha256": acct["request_sha256"], "package_sha256": canon.sha(acct["package"])})
    def at_least(step: str) -> bool:
        return STEPS.index(rec["step"]) >= STEPS.index(step)

    if not at_least("integrated"):
        guard()
        if account_id in ctx.panel().listaccts():
            skipped.append("createacct: the panel already lists the account")
        else:
            guard()
            ctx.panel().createacct(account_id, acct["domain"], acct["package"]["id"])
            made.append("createacct")
        guard()
        rec = receipts.advance(key, "integrated", {"observed": "panel lists the account"})
        reached("integrated")
    if not at_least("state_recorded"):
        guard()
        if any(e["receipt_key"] == key for e in ledger_entries(ctx.dir)):
            skipped.append("entitlement: the ledger already has an entry for this receipt")
        else:
            with open(ctx.path("entitlements.jsonl"), "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"receipt_key": key, "account_id": account_id, "tenant_id": acct["tenant_id"],
                                     "package": acct["package"]["id"], "recorded_at": now()}, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            made.append("entitlement")
        guard()
        rec = receipts.advance(key, "state_recorded", {"observed": "ledger has one entry"})
        reached("state_recorded")
    with ctx.lock(account_id):
        acct = ctx.get(account_id)
        if acct["state"] == "qualified":
            guard()
            acct["state"] = "provisioned"
            acct["history"].append(history_entry(ctx, "provision", "qualified", "provisioned", epoch))
            ctx.put(acct)
    guard()
    leases.release(repo, task, epoch, "provisioned")
    rec = receipts.advance(key, "complete")
    return {"verdict": "ok", "status": "completed", "account_id": account_id, "receipt_key": key, "receipt_step": rec["step"],
            "epoch": epoch, "panel_calls": made, "skipped": skipped}


def record_callback(ctx: Ctx, event: Dict[str, Any]) -> Dict[str, Any]:
    acct = ctx.get(event["account_id"])
    if acct is None:
        raise Refused(["callback names unknown account %s" % event["account_id"]])
    if acct["tenant_id"] != event["tenant_id"]:
        raise Refused(["callback tenant %s does not match the account's tenant" % event["tenant_id"]])
    out = {"verdict": "ok", "event_id": event["event_id"], "account_id": acct["account_id"], "account_state": acct["state"]}
    final = ctx.path("callbacks", acct["account_id"], event["event_id"] + ".json")

    def settled() -> Dict[str, Any]:
        stored = (canon.read_json(final) or {}).get("event")
        if stored != event:
            raise Refused(["callback %s was already recorded for %s with a different payload" % (event["event_id"], acct["account_id"])],
                          status="conflict")
        return dict(out, status="duplicate")

    if os.path.exists(final):
        return settled()
    os.makedirs(os.path.dirname(final), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=os.path.dirname(final))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"event": event, "received_at": now()}, indent=2, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        try:
            os.link(tmp, final)  # exclusive create: the loser of a race sees FileExistsError
        except FileExistsError:
            return settled()
    finally:
        os.unlink(tmp)
    return dict(out, status="recorded")


def show(ctx: Ctx, account_id: str) -> Dict[str, Any]:
    acct = ctx.require(account_id)
    shown = json.loads(json.dumps(acct))
    shown["ownership"]["expected_token"] = "[redacted]"
    out: Dict[str, Any] = {"verdict": "ok", "account": shown, "callbacks": [], "provision_receipt": None, "provision_lease": None}
    cdir = ctx.path("callbacks", account_id)
    out["callbacks"] = [name[:-5] for name in sorted(os.listdir(cdir)) if name.endswith(".json")] if os.path.isdir(cdir) else []
    if acct.get("request_sha256") and os.path.isdir(ctx.path("receipts")):
        rec = ReceiptStore(ctx.path("receipts")).get(idempotency_key(account_id, "provision", acct["request_sha256"], canon.sha(acct["package"])))
        out["provision_receipt"] = rec and {"key": rec["key"], "step": rec["step"]}
    if os.path.isdir(ctx.path("leases")):
        cur = LeaseStore(ctx.path("leases")).status("hosting/" + acct["tenant_id"], "provision:" + account_id)
        out["provision_lease"] = cur and {"state": cur["state"], "epoch": cur["epoch"], "owner_pid": cur["owner_pid"]}
    return out


# --------------------------------------------------------------------------- scenarios (real files, real processes)

def fresh_workdir(path: Optional[str]) -> Tuple[str, bool]:
    if path is None:
        return tempfile.mkdtemp(prefix="hosting-lifecycle-"), True
    if os.path.exists(path) and (not os.path.isdir(path) or os.listdir(path)):
        raise InvalidInput("--workdir must be absent or empty: %s" % path)
    os.makedirs(path, exist_ok=True)
    return os.path.abspath(path), False


def cli_json(argv: List[str]) -> Tuple[int, Dict[str, Any]]:
    proc = subprocess.run([sys.executable, SCRIPT] + argv, capture_output=True, text=True, timeout=120)
    try:
        return proc.returncode, json.loads(proc.stdout)
    except ValueError:
        return proc.returncode, {"stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}


def full_path(workdir: Optional[str], fixtures: str) -> Dict[str, Any]:
    work, temp = fresh_workdir(workdir)
    fx = lambda name: os.path.join(fixtures, name)  # noqa: E731
    base = ["--state-dir", work]
    acct = ["--account-id", "acct-tenant-a-001"]
    finance = ["--policy", "BILL-7.1", "--approved-by", "human:finance-owner"]
    observed, bundle = os.path.join(work, "observed.json"), os.path.join(work, "export-bundle")
    steps = [
        ("qualify", base + ["--request", fx("request-tenant-a-reseller.json")]),
        ("provision", base + acct),
        ("verify-ownership", base + acct + ["--observed", observed]),
        ("configure", base + acct + ["--php-version", "8.3"]),
        ("activate", base + acct),
        ("monitor", base + acct + ["--check-result", fx("check-result.json")]),
        ("renew", base + acct + ["--until", "2028-11-25"]),
        ("suspend", base + acct + finance + ["--reason", "nonpayment"]),
        ("unsuspend", base + acct + finance + ["--reason", "payment-received"]),
        ("export", base + acct + ["--bundle", bundle]),
        ("decommission", base + acct + ["--approved-by", "human:hosting-operations-owner"]),
    ]
    try:
        trail, verdict = [], "ok"
        for action, args in steps:
            if action == "export":
                export_tenant_bundle(fixtures, work, bundle)
            code, doc = execute([action] + args)
            if action == "qualify" and code == 0:
                with open(observed, "w", encoding="utf-8") as fh:
                    json.dump({"records": [{k: doc["publish"][k] for k in ("kind", "name", "value")}]}, fh)
            trail.append({"action": action, "exit": code, "to": doc.get("to") or doc.get("status")})
            if code != 0:
                verdict = "fail"
                trail[-1]["reasons"] = doc.get("reasons") or doc.get("error")
                break
        final = (Ctx(work).get("acct-tenant-a-001") or {}).get("state")
        left = list(Ctx(work).panel().listaccts())
        return {"verdict": verdict if final == "decommissioned" and not left else "fail", "final_state": final, "steps": trail,
                "panel_accounts_left": left, "createacct_calls": panel_call_count(work, "createacct"),
                "removeacct_calls": panel_call_count(work, "removeacct")}
    finally:
        if temp:
            shutil.rmtree(work, ignore_errors=True)


def export_tenant_bundle(fixtures: str, work: str, bundle: str) -> None:
    """The data owner's export of tenant-a: a hosting-data-migration bundle recorded in its fixed ledger."""
    import data_migration as dm
    seed_dir = os.path.normpath(os.path.join(fixtures, "..", "data-migration"))
    db = os.path.join(work, "tenant-a-site.sqlite")
    dm.build_seed_db(os.path.join(seed_dir, "seed.sql"), db)
    dm.export_bundle(db, os.path.join(seed_dir, "tenant-a-files"), bundle, "tenant-a", dm.owner_ledger(None, bundle))


def recovery_demo(workdir: Optional[str], fixtures: str) -> Dict[str, Any]:
    work, temp = fresh_workdir(workdir)
    fx = lambda name: os.path.join(fixtures, name)  # noqa: E731
    first, second = "acct-tenant-a-001", "acct-tenant-a-002"
    holder: Optional[subprocess.Popen] = None
    try:
        request = load_request(fx("request-tenant-a-reseller.json"))
        second_request = os.path.join(work, "request-second.json")
        raw = read_doc(fx("request-tenant-a-reseller.json"), "request")
        raw.update({"account_id": second, "domain": "client-a-shop.example", "request_id": "req-fixture-0003"})
        with open(second_request, "w", encoding="utf-8") as fh:
            json.dump(raw, fh)
        for req in (fx("request-tenant-a-reseller.json"), second_request):
            code, _ = cli_json(["qualify", "--state-dir", work, "--request", req])
            if code != 0:
                raise InvalidInput("qualify failed for %s in the recovery scenario" % req)
        prov = ["provision", "--state-dir", work, "--account-id", first]
        steps = []
        for name, extra in (("provision-crash-after-integrated", ["--crash-after", "integrated"]), ("provision-rerun", []), ("provision-retry", [])):
            code, doc = cli_json(prov + extra)
            steps.append({"name": name, "exit": code, "status": doc.get("status")})
        callback = ["callback", "--state-dir", work, "--event", fx("callback-account-created.json")]
        results = [cli_json(callback)[1].get("status") for _ in range(2)]
        holder = subprocess.Popen(["sleep", "60"])
        LeaseStore(os.path.join(work, "leases")).acquire("hosting/" + request["tenant_id"], "provision:" + second, "demo", "fake-whm",
                                                         "demo-holder", work, holder.pid, ttl=LEASE_TTL)
        alive = process_fingerprint(holder.pid) is not None
        code, doc = cli_json(["provision", "--state-dir", work, "--account-id", second])
        refused = alive and code == 1 and "in progress" in " ".join(doc.get("reasons", []))
        steps.append({"name": "provision-while-holder-alive", "exit": code, "status": doc.get("verdict")})
        holder.kill()
        holder.wait()
        key = idempotency_key(first, "provision", request["_sha256"], canon.sha(next(p for p in request["packages"] if p["id"] == request["package"])))
        step = ReceiptStore(os.path.join(work, "receipts")).get(key)["step"]
        counts = {"createacct_calls": panel_call_count(work, "createacct"), "entitlement_entries": len(ledger_entries(work)), "receipt_step": step,
                  "callback_results": results, "concurrent_refused": bool(refused)}
        ok = counts == {"createacct_calls": 1, "entitlement_entries": 1, "receipt_step": "complete",
                        "callback_results": ["recorded", "duplicate"], "concurrent_refused": True} \
            and [s["exit"] for s in steps] == [137, 0, 0, 1]
        history = LeaseStore(os.path.join(work, "leases")).history("hosting/" + request["tenant_id"], "provision:" + first)
        counts.update({"verdict": "ok" if ok else "fail", "steps": steps, "lease_history": [{"event": e["event"], "epoch": e["epoch"]} for e in history],
                       "holder_pid_alive_during_refusal": alive, "callback_files": len(os.listdir(os.path.join(work, "callbacks")))})
        return counts
    finally:
        if holder is not None and holder.poll() is None:
            holder.kill()
            holder.wait()
        if temp:
            shutil.rmtree(work, ignore_errors=True)


# --------------------------------------------------------------------------- CLI

class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        raise InvalidInput(message)


def build_parser() -> Parser:
    ap = Parser(prog="account_lifecycle", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True, parser_class=Parser)

    def common(p: argparse.ArgumentParser, account: bool = True) -> argparse.ArgumentParser:
        p.add_argument("--state-dir", required=True)
        if account:
            p.add_argument("--account-id", required=True)
        p.add_argument("--actor", default="skill:hosting-account-lifecycle")
        p.add_argument("--panel", default="fake", choices=["fake", "whm"], help="whm is blocked: no provider, no credentials")
        return p

    common(sub.add_parser("qualify"), account=False).add_argument("--request")
    p = common(sub.add_parser("provision"))
    p.add_argument("--owner-pid", type=int, help="pid recorded as the lease holder (default: this process)")
    p.add_argument("--crash-after", choices=["integrated", "state_recorded"], help="test hook: os._exit(137) right after that step")
    common(sub.add_parser("verify-ownership")).add_argument("--observed")
    common(sub.add_parser("configure")).add_argument("--php-version", dest="php_version")
    common(sub.add_parser("activate"))
    common(sub.add_parser("monitor")).add_argument("--check-result", dest="check_result")
    common(sub.add_parser("renew")).add_argument("--until")
    for name in ("suspend", "unsuspend"):
        p = common(sub.add_parser(name))
        p.add_argument("--policy")
        p.add_argument("--policy-file", dest="policy_file", help="optional; must be the owner's suspension-policy.json")
        p.add_argument("--reason")
        p.add_argument("--approved-by", dest="approved_by")
        p.add_argument("--abuse-case", dest="abuse_case", help="the approved hosting-abuse-response case folder")
        p.add_argument("--abuse-anchors", dest="abuse_anchors", help="refused unless it is the abuse owner's fixed ledger")
    p = common(sub.add_parser("export"))
    p.add_argument("--bundle", help="a hosting-data-migration bundle folder")
    p.add_argument("--export-ledger", dest="export_ledger", help="refused unless it is the data owner's fixed ledger")
    p.add_argument("--manifest", help="refused: a manifest file alone is not an export")
    p = common(sub.add_parser("decommission"))
    p.add_argument("--approved-by", dest="approved_by")
    p.add_argument("--waiver")
    common(sub.add_parser("callback"), account=False).add_argument("--event", required=True)
    common(sub.add_parser("show"))
    for name in ("full-path", "recovery-demo"):
        p = sub.add_parser(name)
        p.add_argument("--workdir", help="fresh directory for scratch state (default: a temp directory removed afterward)")
        p.add_argument("--fixtures", default=DEFAULT_FIXTURES)
    return ap


LOADERS: Dict[str, Callable[[str], Any]] = {"request": load_request, "observed": load_observed, "check_result": load_check_result,
                                           "until": lambda v: parse_date(v, "--until"), "php_version": str}


def gather(action: str, args: argparse.Namespace) -> Dict[str, Any]:
    inp: Dict[str, Any] = {}
    if action == "export":
        if getattr(args, "manifest", None) and not args.bundle:
            raise Refused(["export: a manifest file alone is not an export; pass --bundle (a hosting-data-migration bundle the data owner recorded)"])
        if not args.bundle:
            raise InvalidInput("export needs --bundle")
        inp["bundle"] = export_record(args.bundle, args.export_ledger)
    for name in RULES[action]["inputs"]:
        if name == "bundle":
            continue
        raw = getattr(args, name, None)
        if not raw:
            raise InvalidInput("%s needs --%s" % (action, name.replace("_", "-")))
        inp[name] = LOADERS[name](raw)
    for name in ("approved_by", "waiver", "policy", "reason", "abuse_case", "abuse_anchors"):
        if getattr(args, name, None) is not None:
            inp[name] = getattr(args, name)
    if RULES[action]["authority"] or RULES[action].get("waiver_from"):
        inp["policy_doc"] = load_policy(getattr(args, "policy_file", None) or OWNER_POLICY)
    return inp


def execute(argv: List[str], after_step: Optional[Callable[[str], None]] = None) -> Tuple[int, Dict[str, Any]]:
    try:
        args = build_parser().parse_args(argv)
        if args.cmd == "full-path":
            out = full_path(args.workdir, args.fixtures)
            return (0 if out["verdict"] == "ok" else 1), out
        if args.cmd == "recovery-demo":
            out = recovery_demo(args.workdir, args.fixtures)
            return (0 if out["verdict"] == "ok" else 1), out
        ctx = Ctx(args.state_dir, args.actor, args.panel)
        if args.cmd == "provision":
            account_id = ident(args.account_id, "--account-id")
            crash = args.crash_after

            def hook(step: str) -> None:
                if step == crash:
                    os._exit(137)
                if after_step:
                    after_step(step)

            return 0, provision(ctx, account_id, args.owner_pid or os.getpid(), hook)
        if args.cmd == "callback":
            return 0, record_callback(ctx, load_event(args.event))
        if args.cmd == "show":
            return 0, show(ctx, ident(args.account_id, "--account-id"))
        inp = gather(args.cmd, args)
        account_id = inp["request"]["account_id"] if args.cmd == "qualify" else ident(args.account_id, "--account-id")
        return 0, apply_action(ctx, args.cmd, account_id, inp)
    except Refused as exc:
        return 1, dict(exc.extra, verdict="refused", reasons=exc.reasons)
    except StaleEpoch as exc:
        return 1, {"verdict": "refused", "reasons": ["stale epoch: %s; a newer holder fenced this run" % exc]}
    except InvalidInput as exc:
        return 2, {"error": str(exc)}
    except Blocked as exc:
        return 3, {"blocked": str(exc)}


def main(argv: Optional[List[str]] = None, after_step: Optional[Callable[[str], None]] = None) -> int:
    code, doc = execute(list(sys.argv[1:] if argv is None else argv), after_step)
    if "error" not in doc and "blocked" not in doc:
        doc.setdefault("assumptions", ASSUMPTIONS)
    print(json.dumps(doc, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
