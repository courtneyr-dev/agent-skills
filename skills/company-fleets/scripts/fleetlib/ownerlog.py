"""The owner path: the only place a gate reads a trusted value from.

A gate never trusts a flag, file, label or field the party being checked supplies. Owner-set values
(a handoff's owner fields, its input labels and hashes, stage acceptances, the human acceptor roster,
pinned policy files and suppression lists, a claims register's sign-off, a send approval) live in one
append-only, hash-chained log per workload instance: <ledger>/owner-log.ndjson, with the factory-rig
lease store in <ledger>/leases and the log's head (entry count and last hash) in <ledger>/owner-head.json.

Where the ledger lives: a gate never takes a ledger path. Each instance has one ledger at a fixed place,
fleets/<fleet>/owner/<instance> under this skill (owner_dir), and the gate derives the instance from the
work it judges (a brief's contract_ref, a contract's task_id, a register's or campaign's id). It refuses
a ledger whose tenant, workload or contract hash differ from that work (read_for).

Lifecycle: the log records its own lease. Entry 1 is `ledger-open`, written by the claim that created the
ledger; `ledger-close`, written on release, ends it. A closed ledger takes no record and no claim. An
open ledger moves to a later epoch only through a `lease-transition` entry, which only open_ledger writes,
and fleet claim refuses any instance that already has a ledger, so a gate ledger never leaves epoch 1.

Write: append() refuses unless the lease is active at the given epoch, the caller presents the token that
the claim returned to the claimant alone, and that epoch is the one the log itself records as current.

Read: read() verifies the chain (seq, prev, hash), the head, one lease identity per log, the lifecycle,
and that every holder the log names is a coordinator of the workload. Any break raises OwnerLogError with
a named reason, and gates refuse on it.

Limit: a same-user process that writes the owner root directly, reads the owner's token, or claims an
instance first is not stopped. See references/authoring-guide.md, "Owner path and its limit".
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import re
import unicodedata
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from factory_rig.canon import atomic_write, sha, sha_file
from factory_rig.contract import contract_hash
from factory_rig.lease import LeaseStore, StaleEpoch

from . import SKILL_DIR
from .handoff import OWNER_FIELDS, Ledger, gate_errors, open_handoff, validate_handoff
from .ownership import ClaimRefused, claim, lease_identity, token_path, workload_coordinators
from .registry import Registry, fleet_of

LOG, HEAD, LOCK = "owner-log.ndjson", "owner-head.json", "owner-log.lock"
GENESIS = "0" * 64
LABELS = ("tenant_id", "classification", "trust", "source_kind")
HUMAN = re.compile(r"^human:[a-z0-9]+(?:-[a-z0-9]+)*$")
INSTANCE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9_-]{0,62}[A-Za-z0-9])?$")
FLEET_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
FLEETS_ROOT = os.path.join(SKILL_DIR, "fleets")  # owner roots are FLEETS_ROOT/<fleet>/owner; tests repoint this in-process


class OwnerLogError(Exception):
    def __init__(self, reason: str, detail: str):
        super().__init__("%s: %s" % (reason, detail))
        self.reason, self.detail = reason, detail


def norm_id(x: Any) -> str:
    """Principal ids compare after NFKC, dropping format characters (zero-width, soft hyphen), trimming and lowercasing."""
    text = unicodedata.normalize("NFKC", str(x or ""))
    return "".join(c for c in text if unicodedata.category(c) != "Cf").strip().lower()


def strict_json(text: str, what: str) -> Any:
    """JSON with NaN, Infinity and overflowing numbers such as 1e400 refused."""
    def refuse(name: str) -> Any:
        raise OwnerLogError("non-finite-number", "%s holds %s; numbers must be finite" % (what, name))

    def finite(token: str) -> float:
        value = float(token)
        return value if math.isfinite(value) else refuse(token)
    try:
        return json.loads(text, parse_constant=refuse, parse_float=finite)
    except ValueError as exc:
        raise OwnerLogError("invalid-json", "%s is not valid JSON: %s" % (what, exc))


def read_text(path: str, what: str) -> str:
    """A file's UTF-8 text; any other encoding is refused by name, not with a traceback."""
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except UnicodeDecodeError as exc:
        raise OwnerLogError("input-not-utf8", "%s %s is not UTF-8 text (%s)" % (what, path, exc.reason))
    except OSError as exc:
        raise OwnerLogError("record-invalid", "cannot read %s %s: %s" % (what, path, exc))


def resolve_input(base: str, rel: str) -> str:
    """The real path of an input under base. Refuses a path outside base and a symlink whose target leaves
    the folder the input is named in (the tenant folder), so a link can't give one tenant's name to another's bytes."""
    root = os.path.realpath(base)
    lexical = os.path.normpath(os.path.join(root, str(rel)))
    if not lexical.startswith(root + os.sep):
        raise OwnerLogError("input-outside-base", "input %s is outside the base folder" % rel)
    real = os.path.realpath(lexical)
    if not real.startswith(os.path.dirname(lexical) + os.sep):
        raise OwnerLogError("input-symlink-leaves-folder", "input %s resolves to %s, outside its own folder %s"
                            % (rel, os.path.relpath(real, root), os.path.relpath(os.path.dirname(lexical), root)))
    if not os.path.isfile(real):
        raise OwnerLogError("input-missing", "input %s does not exist under the base folder" % rel)
    return real


# ------------------------------------------------------------------ where an instance's ledger lives

def owner_dir(fleet: str, instance: Any) -> str:
    """The one ledger folder for a fleet's workload instance. Derived, never passed in."""
    if not FLEET_ID.match(str(fleet)):
        raise OwnerLogError("instance-invalid", "fleet %r is not a fleet id" % (fleet,))
    if not isinstance(instance, str) or not INSTANCE.match(instance):
        raise OwnerLogError("instance-invalid", "instance %r is not an instance id (letters, digits, _ and -, up to 64)" % (instance,))
    return os.path.join(FLEETS_ROOT, fleet, "owner", instance)


# ------------------------------------------------------------------ kinds: record in, (subject, body) out

class Ctx:
    def __init__(self, root: str, tenant: str, workload: str, chash: str, base: str, contract: Optional[Dict[str, Any]]):
        self.root, self.tenant, self.workload, self.chash, self.base, self.contract = root, tenant, workload, chash, base, contract


def _need(rec: Any, keys: Tuple[str, ...], what: str) -> None:
    if not isinstance(rec, dict):
        raise OwnerLogError("record-invalid", "%s must be a JSON object" % what)
    missing = [k for k in keys if k not in rec]
    if missing:
        raise OwnerLogError("record-invalid", "%s is missing %s" % (what, ", ".join(missing)))


def _open(rec: Dict[str, Any], ctx: Ctx) -> Tuple[str, Dict[str, Any]]:
    owner = {k: v for k, v in rec.items() if k != "label"}
    owner["contract_hash"] = ctx.chash
    errors = validate_handoff(open_handoff(owner)) if not set(owner) - set(OWNER_FIELDS) else \
        ["fields outside the owner set: " + ", ".join(sorted(set(owner) - set(OWNER_FIELDS)))]
    if errors:
        raise OwnerLogError("owner-record-invalid", "; ".join(errors))
    if owner["tenant_id"] != ctx.tenant:
        raise OwnerLogError("tenant-mismatch", "handoff tenant %s is not the lease's tenant %s" % (owner["tenant_id"], ctx.tenant))
    if owner["workload_id"] != ctx.workload:
        raise OwnerLogError("workload-mismatch", "handoff workload %s is not the lease's workload %s" % (owner["workload_id"], ctx.workload))
    try:
        Ledger(ctx.root).open(owner)
    except ValueError as exc:
        raise OwnerLogError("owner-record-conflict", str(exc))
    return owner["handoff_id"], owner


def _intake(rec: Dict[str, Any], ctx: Ctx) -> Tuple[str, Dict[str, Any]]:
    _need(rec, ("handoff_id", "inputs"), "intake record")
    inputs = []
    for i in rec["inputs"]:
        _need(i, ("path",) + LABELS, "intake input")
        if i["classification"] not in ("public", "internal", "confidential", "restricted") or i["trust"] not in ("trusted", "untrusted"):
            raise OwnerLogError("record-invalid", "intake input %s has an unknown classification or trust" % i["path"])
        inputs.append(dict({k: i[k] for k in ("path",) + LABELS}, sha256=sha_file(resolve_input(ctx.base, i["path"]))))
    return rec["handoff_id"], {"handoff_id": rec["handoff_id"], "inputs": inputs, "label": rec.get("label", "")}


def _roster(rec: Dict[str, Any], ctx: Ctx) -> Tuple[str, Dict[str, Any]]:
    _need(rec, ("humans",), "roster")
    humans = sorted({norm_id(h) for h in rec["humans"]})
    bad = [h for h in humans if not HUMAN.match(h)]
    if bad or not humans:
        raise OwnerLogError("record-invalid", "roster humans must be human:<title>; got %s" % (bad or "none"))
    return "stage-acceptors", {"humans": humans, "label": rec.get("label", "")}


def _acceptance(rec: Dict[str, Any], ctx: Ctx) -> Tuple[str, Dict[str, Any]]:
    _need(rec, ("stage", "status", "producer", "accepted_by"), "stage acceptance")
    if ctx.contract is None:
        raise OwnerLogError("record-invalid", "a stage acceptance needs --contract, so it records the spec it was accepted under")
    if rec["status"] not in ("done", "skipped"):
        raise OwnerLogError("record-invalid", "stage acceptance status must be done or skipped")
    if rec["status"] == "skipped" and not str(rec.get("skip_reason", "")).strip():
        raise OwnerLogError("record-invalid", "a skipped stage needs skip_reason")
    root = os.path.realpath(ctx.base)
    evidence = []
    for p in rec.get("evidence", []):
        real = os.path.realpath(os.path.join(root, p))
        if not real.startswith(root + os.sep) or not os.path.isfile(real):
            raise OwnerLogError("record-invalid", "evidence %s is missing or outside the base folder" % p)
        evidence.append({"path": p, "sha256": sha_file(real)})
    body = {"stage": rec["stage"], "status": rec["status"], "producer": norm_id(rec["producer"]), "accepted_by": norm_id(rec["accepted_by"]),
            "evidence": evidence, "spec": dict(ctx.contract["spec"]), "label": rec.get("label", "")}
    if rec["status"] == "skipped":
        body["skip_reason"] = rec["skip_reason"]
    return rec["stage"], body


def _pin(rec: Dict[str, Any], ctx: Ctx) -> Tuple[str, Dict[str, Any]]:
    """A policy, rate card or list, by path and hash. A .json file's content is parsed; any other file is kept as text."""
    _need(rec, ("name", "path"), "pin")
    path = os.path.join(ctx.base, rec["path"])
    text = read_text(path, "pinned file")
    content = strict_json(text, rec["path"]) if str(rec["path"]).endswith(".json") else text
    return rec["name"], {"name": rec["name"], "path": rec["path"], "sha256": sha_file(path), "content": content, "label": rec.get("label", "")}


def _sign_off(rec: Dict[str, Any], ctx: Ctx) -> Tuple[str, Dict[str, Any]]:
    _need(rec, ("register", "signed_off_by", "author", "signed_on"), "claims sign-off")
    reg = strict_json(read_text(os.path.join(ctx.base, rec["register"]), "register"), rec["register"])
    if not isinstance(reg, dict) or not isinstance(reg.get("sources"), list):
        raise OwnerLogError("record-invalid", "register %s has no sources list" % rec["register"])
    signer, author = norm_id(rec["signed_off_by"]), norm_id(rec["author"])
    if not HUMAN.match(signer) or not HUMAN.match(author):
        raise OwnerLogError("record-invalid", "signed_off_by and author must both be human:<title>")
    if signer == author:
        raise OwnerLogError("register-self-signed", "the register's author can't sign it off")
    digest = sha(reg["sources"])
    return digest, {"register": rec["register"], "sources_sha256": digest, "signed_off_by": signer, "author": author,
                    "signed_on": rec["signed_on"], "label": rec.get("label", "")}


def _send_approval(rec: Dict[str, Any], ctx: Ctx) -> Tuple[str, Dict[str, Any]]:
    """A named human's approval of one staged send, bound to the campaign and recipient-list hashes."""
    _need(rec, ("approved_by", "campaign_sha256", "recipient_sha256", "approved_on", "channel"), "send approval")
    who = norm_id(rec["approved_by"])
    if not HUMAN.match(who):
        raise OwnerLogError("record-invalid", "approved_by must be human:<title>")
    if not all(isinstance(rec[k], str) and SHA256.match(rec[k]) for k in ("campaign_sha256", "recipient_sha256")):
        raise OwnerLogError("record-invalid", "campaign_sha256 and recipient_sha256 must be sha256 hex digests")
    body = {k: rec[k] for k in ("campaign_sha256", "recipient_sha256", "approved_on", "channel")}
    body.update(approved_by=who, label=rec.get("label", ""))
    return "%s:%s" % (rec["campaign_sha256"], rec["recipient_sha256"]), body


# kind -> (prepare, write_once). Write-once kinds keep their first record; the others take the latest per subject.
KINDS: Dict[str, Tuple[Callable[[Dict[str, Any], Ctx], Tuple[str, Dict[str, Any]]], bool]] = {
    "open": (_open, True), "intake": (_intake, True), "roster": (_roster, False), "stage-acceptance": (_acceptance, False),
    "pin": (_pin, False), "claims-sign-off": (_sign_off, False), "send-approval": (_send_approval, True),
}
LIFECYCLE = ("ledger-open", "lease-transition", "ledger-close")


# ------------------------------------------------------------------ read and verify

def _entry_hash(e: Dict[str, Any]) -> str:
    return sha({k: v for k, v in e.items() if k != "hash"})


@contextmanager
def _locked(root: str, mode: int) -> Iterator[None]:
    """flock on <root>/owner-log.lock: exclusive to write, shared to read, so a reader never sees a log line without its head."""
    try:
        fd = os.open(os.path.join(root, LOCK), os.O_CREAT | os.O_RDWR, 0o600)
    except OSError:
        yield  # a read-only checkout: nothing can write here either
        return
    try:
        fcntl.flock(fd, mode)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _read(root: str, reg: Registry) -> List[Dict[str, Any]]:
    path = os.path.join(root, LOG)
    if not os.path.isfile(path):
        raise OwnerLogError("owner-log-missing", "no owner log at %s; the contract owner claims the instance with fleet claim, which writes it" % path)
    try:
        text = read_text(path, "owner log")
    except OwnerLogError as exc:
        raise OwnerLogError("owner-log-broken", exc.detail)
    entries, prev = [], GENESIS
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for n, line in enumerate(lines, 1):
        try:
            e = strict_json(line, "owner log line %d" % n)
        except OwnerLogError:
            raise OwnerLogError("owner-log-broken", "line %d is not a JSON entry" % n)
        if not isinstance(e, dict) or e.get("seq") != n or e.get("prev") != prev or e.get("hash") != _entry_hash(e):
            raise OwnerLogError("owner-log-broken", "entry %d breaks the hash chain (edited, reordered or inserted)" % n)
        prev = e["hash"]
        entries.append(e)
    if not entries:
        raise OwnerLogError("owner-log-missing", "the owner log at %s is empty" % path)
    _check_head(root, entries)
    _check_lifecycle(entries, reg)
    return entries


def _check_head(root: str, entries: List[Dict[str, Any]]) -> None:
    """The head file holds the count and last hash the last append wrote, so a dropped tail entry or a substituted log shows."""
    try:
        head = strict_json(read_text(os.path.join(root, HEAD), "owner head"), HEAD)
    except OwnerLogError:
        raise OwnerLogError("owner-head-missing", "no readable %s beside the owner log; the log's length can't be confirmed" % HEAD)
    if not isinstance(head, dict) or not isinstance(head.get("count"), int):
        raise OwnerLogError("owner-head-missing", "%s holds no entry count" % HEAD)
    if head["count"] > len(entries):
        raise OwnerLogError("owner-log-truncated", "the head records %d entries but the log holds %d; entries were removed from its end" % (head["count"], len(entries)))
    if head["count"] != len(entries) or head.get("hash") != entries[-1]["hash"]:
        raise OwnerLogError("owner-log-broken", "the log's last entry is not the one its head records (entry %d, %s...)" % (head["count"], str(head.get("hash"))[:12]))


def _check_lifecycle(entries: List[Dict[str, Any]], reg: Registry) -> None:
    first = entries[0]
    if first.get("kind") != "ledger-open":
        raise OwnerLogError("owner-log-broken", "entry 1 is %s, not the ledger-open record the claim writes" % first.get("kind"))
    ident = _ident(first)
    epoch, holder, closed, holders = first["lease"].get("epoch"), first["lease"].get("holder"), False, set()
    for e in entries:
        lease = e.get("lease") or {}
        if _ident(e) != ident:
            raise OwnerLogError("owner-log-broken", "entry %d names lease %s, not the log's lease %s" % (e["seq"], _ident(e), ident))
        if closed:
            raise OwnerLogError("owner-log-broken", "entry %d follows the ledger-close record" % e["seq"])
        if e["seq"] > 1 and e["kind"] == "ledger-open":
            raise OwnerLogError("owner-log-broken", "entry %d opens the ledger a second time" % e["seq"])
        if e["kind"] == "lease-transition":
            body = e.get("body") or {}
            if not isinstance(lease.get("epoch"), int) or lease["epoch"] <= epoch or body.get("from_epoch") != epoch or body.get("to_epoch") != lease["epoch"]:
                raise OwnerLogError("owner-log-broken", "entry %d is a lease transition that doesn't follow epoch %s" % (e["seq"], epoch))
            epoch, holder = lease["epoch"], lease.get("holder")
        elif lease.get("epoch") != epoch or lease.get("holder") != holder:
            raise OwnerLogError("owner-entry-without-lease", "entry %d claims epoch %s held by %s, but the log records epoch %s held by %s"
                                % (e["seq"], lease.get("epoch"), lease.get("holder"), epoch, holder))
        holders.add(holder)
        closed = e["kind"] == "ledger-close"
    try:
        coordinators = workload_coordinators(reg, ident[1])
    except (ClaimRefused, OSError, KeyError, ValueError):
        coordinators = set()
    for h in sorted(holders - coordinators):
        raise OwnerLogError("owner-not-coordinator", "the log names holder %s, not a coordinator of %s" % (h, ident[1]))


def _ident(e: Dict[str, Any]) -> Tuple[Any, Any, Any]:
    lease = e.get("lease") or {}
    return lease.get("tenant"), lease.get("workload"), lease.get("instance")


def read(root: str, reg: Optional[Registry] = None) -> List[Dict[str, Any]]:
    with _locked(root, fcntl.LOCK_SH) if os.path.isdir(root) else _nolock():
        return _read(root, reg or Registry())


@contextmanager
def _nolock() -> Iterator[None]:
    yield


def state(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The ledger's identity, contract hash, current epoch and holder, and whether it is closed."""
    first, last_lease = entries[0], [e for e in entries if e["kind"] in ("ledger-open", "lease-transition")][-1]
    tenant, workload, instance = _ident(first)
    return {"tenant": tenant, "workload": workload, "instance": instance, "contract_hash": first["body"].get("contract_hash"),
            "epoch": last_lease["lease"]["epoch"], "holder": last_lease["lease"]["holder"], "closed": entries[-1]["kind"] == "ledger-close"}


def read_for(fleet: str, instance: Any, expect: Dict[str, Any], reg: Optional[Registry] = None) -> Tuple[str, List[Dict[str, Any]]]:
    """The verified ledger of the instance the work names, refused when its tenant, workload or contract hash
    differ from the work's (expect holds any of tenant, workload, contract_hash)."""
    root = owner_dir(fleet, instance)
    if not os.path.isdir(root):
        raise OwnerLogError("owner-log-missing", "instance %s has no owner ledger under fleets/%s/owner; the contract owner claims it with fleet claim" % (instance, fleet))
    entries = read(root, reg)
    st = state(entries)
    differs = ["%s: the ledger has %s, the work names %s" % (k, st[k], v) for k, v in sorted(expect.items()) if st[k] != v]
    if differs:
        raise OwnerLogError("ledger-not-for-this-work", "the owner ledger of instance %s belongs to other work (%s)" % (instance, "; ".join(differs)))
    return root, entries


def effective(entries: List[Dict[str, Any]], kind: str, subject: str, chash: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """The record that stands for (kind, subject[, contract hash]): the first for write-once kinds, else the latest."""
    hits = [e for e in entries if e["kind"] == kind and e["subject"] == subject and (chash is None or e["contract_hash"] == chash)]
    if not hits:
        return None
    return hits[0] if KINDS[kind][1] else hits[-1]


# ------------------------------------------------------------------ write

def _write(root: str, entries: List[Dict[str, Any]], kind: str, subject: str, body: Dict[str, Any], chash: str,
           ident: Tuple[str, str, str], holder: str, epoch: int) -> Dict[str, Any]:
    e = {"seq": len(entries) + 1, "kind": kind, "subject": subject, "body": body, "contract_hash": chash,
         "lease": {"tenant": ident[0], "workload": ident[1], "instance": ident[2], "holder": holder, "epoch": epoch},
         "prev": entries[-1]["hash"] if entries else GENESIS}
    e["hash"] = _entry_hash(e)
    with open(os.path.join(root, LOG), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(e, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    atomic_write(os.path.join(root, HEAD), json.dumps({"count": e["seq"], "hash": e["hash"]}, sort_keys=True) + "\n")
    return e


def open_ledger(root: str, reg: Registry, tenant: str, workload: str, instance: str, role: str, owner_pid: int, chash: str,
                exclusive: bool, store_root: Optional[str] = None, ttl: float = 600.0, label: str = "") -> Dict[str, Any]:
    """Claim the coordinator lease and record it in the log: ledger-open for a new ledger, lease-transition for an
    open one. exclusive (fleet claim, gate ledgers): refuse when the folder exists at all, so an instance gets one
    ledger and a released or copied one can't be claimed again. Returns the lease with its one-time token."""
    coordinators = workload_coordinators(reg, workload)
    if role not in coordinators:
        raise ClaimRefused("%s is not the coordinator of %s (coordinator: %s); it cannot claim or dispatch it"
                           % (role, workload, ", ".join(sorted(coordinators)) or "none"))
    if exclusive:
        os.makedirs(os.path.dirname(root), exist_ok=True)
        try:
            os.mkdir(root)
        except FileExistsError:
            raise OwnerLogError("ledger-exists", "instance %s already has a ledger at %s; an instance gets one ledger, and a closed one takes no new claim" % (instance, root))
    os.makedirs(root, exist_ok=True)
    if os.path.isfile(os.path.join(root, LOG)):
        _claimable(read(root, reg), tenant, workload, instance)
    lease = claim(LeaseStore(store_root or os.path.join(root, "leases")), reg, tenant, workload, instance, role, owner_pid, chash, ttl=ttl)
    with _locked(root, fcntl.LOCK_EX):
        entries = _read(root, reg) if os.path.isfile(os.path.join(root, LOG)) else []
        if entries:
            _claimable(entries, tenant, workload, instance)
            _write(root, entries, "lease-transition", instance, {"from_epoch": state(entries)["epoch"], "to_epoch": lease["epoch"]},
                   state(entries)["contract_hash"], (tenant, workload, instance), lease["attempt_id"], lease["epoch"])
        else:
            _write(root, entries, "ledger-open", instance, {"tenant": tenant, "workload": workload, "instance": instance,
                                                            "contract_hash": chash, "label": label},
                   chash, (tenant, workload, instance), lease["attempt_id"], lease["epoch"])
    return lease


def _claimable(entries: List[Dict[str, Any]], tenant: str, workload: str, instance: str) -> None:
    st = state(entries)
    if (st["tenant"], st["workload"], st["instance"]) != (tenant, workload, instance):
        raise OwnerLogError("lease-mismatch", "this ledger belongs to %s/%s#%s" % (st["tenant"], st["workload"], st["instance"]))
    if st["closed"]:
        raise OwnerLogError("ledger-closed", "the ledger of %s was closed on release; it takes no new claim or record" % instance)


def _authorize(store_root: str, tenant: str, workload: str, instance: str, epoch: int, token: str) -> Dict[str, Any]:
    if not os.path.isdir(store_root):
        raise OwnerLogError("ledger-not-claimed", "no lease store at %s; the contract owner claims the instance with fleet claim" % store_root)
    repo, task = lease_identity(tenant, workload, instance)
    try:
        lease = LeaseStore(store_root).assert_current(repo, task, epoch)
    except StaleEpoch as exc:
        raise OwnerLogError("stale-epoch", str(exc))
    try:
        want = strict_json(read_text(token_path(store_root, tenant, workload, instance), "owner seal"), "owner seal")
    except OwnerLogError:
        want = {}
    if not isinstance(want, dict) or want.get("epoch") != epoch or hashlib.sha256(str(token).strip().encode()).hexdigest() != want.get("sha256"):
        raise OwnerLogError("not-the-lease-holder", "the token doesn't match the one fleet claim gave the holder of epoch %d" % epoch)
    return lease


def _current(root: str, reg: Registry, tenant: str, workload: str, instance: str, epoch: int) -> List[Dict[str, Any]]:
    """The verified log, open, of this lease identity, at exactly the epoch the log records as current."""
    if not os.path.isfile(os.path.join(root, LOG)):
        raise OwnerLogError("ledger-not-claimed", "no owner log at %s; the contract owner claims the instance with fleet claim" % root)
    entries = _read(root, reg)
    _claimable(entries, tenant, workload, instance)
    current = state(entries)["epoch"]
    if epoch < current:
        raise OwnerLogError("stale-epoch", "epoch %d is older than the log's epoch %d" % (epoch, current))
    if epoch > current:
        raise OwnerLogError("epoch-without-transition", "the log records epoch %d as current; epoch %d has no lease transition in it" % (current, epoch))
    return entries


def append(root: str, kind: str, record: Dict[str, Any], tenant: str, workload: str, instance: str, epoch: int, token: str,
           base: str = ".", contract: Optional[Dict[str, Any]] = None, reg: Optional[Registry] = None,
           store_root: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
    """Record one owner value. Returns ("recorded" | "duplicate", entry). Raises OwnerLogError with a named reason."""
    if not isinstance(record, dict):
        raise OwnerLogError("record-invalid", "the record must be a JSON object")
    if kind not in KINDS:
        raise OwnerLogError("record-invalid", "unknown kind %s; one of %s" % (kind, ", ".join(sorted(KINDS))))
    lease = _authorize(store_root or os.path.join(root, "leases"), tenant, workload, instance, epoch, token)
    if contract is not None and contract_hash(contract) != lease["contract_hash"]:
        raise OwnerLogError("contract-mismatch", "the contract hashes to %s but the lease is bound to %s" % (contract_hash(contract)[:12], lease["contract_hash"][:12]))
    reg = reg or Registry()
    with _locked(root, fcntl.LOCK_EX):
        entries = _current(root, reg, tenant, workload, instance, epoch)
        prepare, write_once = KINDS[kind]
        subject, body = prepare(record, Ctx(root, tenant, workload, lease["contract_hash"], base, contract))
        current = effective(entries, kind, subject, lease["contract_hash"])
        if current is not None and current["body"] == body:
            return "duplicate", current
        if current is not None and write_once:
            raise OwnerLogError("%s-conflict" % kind if kind == "intake" else "owner-record-conflict",
                                "the %s record for %s already exists with different values; the first stands" % (kind, subject))
        return "recorded", _write(root, entries, kind, subject, body, lease["contract_hash"], (tenant, workload, instance), lease["attempt_id"], epoch)


def close_ledger(root: str, tenant: str, workload: str, instance: str, epoch: int, token: str, outcome: str,
                 reg: Optional[Registry] = None, store_root: Optional[str] = None) -> Dict[str, Any]:
    """Write ledger-close under the holder's token, then release the lease. Nothing is recorded after it."""
    store_root = store_root or os.path.join(root, "leases")
    lease = _authorize(store_root, tenant, workload, instance, epoch, token)
    with _locked(root, fcntl.LOCK_EX):
        entries = _current(root, reg or Registry(), tenant, workload, instance, epoch)
        _write(root, entries, "ledger-close", instance, {"outcome": outcome}, lease["contract_hash"], (tenant, workload, instance), lease["attempt_id"], epoch)
    repo, task = lease_identity(tenant, workload, instance)
    return LeaseStore(store_root).release(repo, task, epoch, outcome)


# ------------------------------------------------------------------ consumers

def intake_errors(h: Dict[str, Any], intake: Optional[Dict[str, Any]], base: str) -> List[str]:
    """Every handoff input must be in the owner's intake with the same labels and hash, and its bytes must still match."""
    listed = {i["path"]: i for i in (intake or {}).get("inputs", [])}
    errors = []
    for i in h.get("inputs", []):
        ref = i.get("ref")
        rec = listed.get(ref)
        if rec is None:
            errors.append("input %s is not in the owner's intake record" % ref)
            continue
        differs = [k for k in LABELS + ("sha256",) if i.get(k) != rec.get(k)]
        if differs:
            errors.append("input %s: %s differ from the owner's intake record" % (ref, ", ".join(differs)))
        try:
            now = sha_file(resolve_input(base, ref))
        except OwnerLogError as exc:
            errors.append("input %s: %s" % (ref, exc))
            continue
        if now != rec["sha256"]:
            errors.append("input %s changed after the owner's intake recorded it" % ref)
    return errors


def submission_errors(h: Dict[str, Any], entries: List[Dict[str, Any]], contract: Dict[str, Any], base: str) -> List[str]:
    """Owner fields and input labels re-derived from a verified owner log, never from the submitter."""
    hid = h.get("handoff_id") if isinstance(h, dict) else None
    opened = effective(entries, "open", hid) if hid else None
    if opened is None:
        return ["handoff-not-opened: handoff %s has no open record in the owner log" % hid]
    errors = gate_errors(h, opened["body"], contract, base)
    if errors:
        return errors
    intake = effective(entries, "intake", hid)
    return intake_errors(h, intake["body"] if intake else None, base)


def check_submission(h: Any, contract: Dict[str, Any], base: str, reg: Optional[Registry] = None) -> List[str]:
    """The next consumer's gate. The ledger is the one of the instance the contract names (its task_id), and it must
    belong to the handoff's tenant and workload and to this exact contract."""
    if not isinstance(h, dict) or not isinstance(contract, dict):
        return ["handoff-invalid: the handoff and the contract must be JSON objects"]
    try:
        _, entries = read_for(fleet_of(str(h.get("workload_id", ""))), contract.get("task_id"),
                              {"tenant": h.get("tenant_id"), "workload": h.get("workload_id"), "contract_hash": contract_hash(contract)}, reg)
    except OwnerLogError as exc:
        return [str(exc)]
    return submission_errors(h, entries, contract, base)
