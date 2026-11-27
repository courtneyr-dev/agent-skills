#!/usr/bin/env python3
"""isolation_check: test the boundaries between hosted tenants.

  records       --fixture F [--principal ID]     allow/deny matrix through fleetlib.tenancy.can_read
  audit append  --log F --entry JSON             append to a hash-chained JSONL audit trail
  audit verify  --log F [--anchor SHA]           find the first edited, deleted, inserted or reordered line
  secrets scan  --path DIR --manifest M.json     known secret values and named patterns in build output
  secrets scan  --record-for P.json              the owner's scan of the preview's own build folder
  sandbox-build --src DIR --other-tenant DIR --script FILE [--control] [--record-for P.json]
                                                 run an untrusted build in a no-network local container,
                                                 then the harness's own probe in an identical one
  record-dependencies --preview P.json           findings from the preview's package-lock.json and the
                                                 owner's advisories.json
  approve       --preview P.json --by human:SLUG a listed human approves the preview
  promote       --preview P.json [--policy POL.json]   preview-to-production gate

A preview names its build_output_dir and source_dir (folders beside the preview file); its content hash
covers its text fields and every file in both folders. The owner records live at one fixed place,
company-fleets/fleets/hosting/owner/hosting-tenant-isolation/records/<preview_id>/, written once by the
commands above against that hash: the scan covers exactly the preview's build folder with the owner's
secrets manifest; the sandbox verdict comes from the harness's probe, never from the build script's own
output; the dependency findings come from the lockfile in the preview's source folder. A --records path,
a scan of another folder, a sandbox of another source and a --report are refused by name. promote reads
only those records, re-scans the preview's own text for secrets, and ignores every result field the
builder put in the preview. records honors a cross-tenant grant only when the record's tenant owner,
listed in tenant-owners.json, approved it, and never for a credential or backup category, however it is
spelled.

Stdout is JSON. Exit 0 ok, 1 refused or violation found, 2 invalid input, 3 blocked by a missing capability.
Python 3.9+, standard library only. Never writes into the skill folder or fixtures.
"""
from __future__ import annotations

import argparse
import datetime
import fcntl
import json
import os
import re
import subprocess
import sys
import unicodedata
import uuid
from typing import Any, Dict, List, Optional, Tuple

SKILL_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RIG_SKILLS = os.path.normpath(os.path.join(SKILL_DIR, ".."))
FACTORY_RIG_SCRIPTS = os.path.join(RIG_SKILLS, "factory-rig", "scripts")
FLEETS_SCRIPTS = os.path.join(RIG_SKILLS, "company-fleets", "scripts")
for _folder, _pkg in ((FACTORY_RIG_SCRIPTS, "factory_rig"), (FLEETS_SCRIPTS, "fleetlib")):
    if not os.path.isdir(os.path.join(_folder, _pkg)):
        raise ImportError("hosting-tenant-isolation needs %s (looked in %s)" % (_pkg, _folder))
    if _folder not in sys.path:
        sys.path.insert(0, _folder)

from factory_rig import canon  # noqa: E402
from fleetlib import tenancy, untrusted  # noqa: E402

GENESIS = "0" * 64
HEADER_PREFIX = "SYNTHETIC FIXTURE:"
SENSITIVE = tenancy.LEVEL["confidential"]
SEVERITY = {"low": 0, "medium": 1, "high": 2, "critical": 3}
IMAGE = "alpine:latest"
LABEL_KEY = "hosting-isolation"
CONTROL_SECRET = "FIXTURE_DB_PASSWORD=fx_demo_ControlSyntheticValue001"
MAX_SCAN_BYTES = 8 * 1024 * 1024
DOCKER_TIMEOUT = 90
OWNER_FILES = os.path.join(RIG_SKILLS, "company-fleets", "fleets", "hosting", "fixtures", "tenant-isolation")
OWNER_POLICY = os.path.join(OWNER_FILES, "promotion-policy.json")
OWNER_MANIFEST = os.path.join(OWNER_FILES, "secrets-manifest.json")
TENANT_OWNERS = os.path.join(OWNER_FILES, "tenant-owners.json")
ADVISORIES = os.path.join(OWNER_FILES, "advisories.json")
OWNER_ROOT = os.path.join(RIG_SKILLS, "company-fleets", "fleets", "hosting", "owner", "hosting-tenant-isolation")
PROBE_SCRIPT = os.path.join(SKILL_DIR, "scripts", "sandbox_probe.sh")
LOCKFILE = "package-lock.json"
NEVER_GRANTED = re.compile(r"(?<![a-z])(?:credential|backup)")
SUBJECT_FIELDS = ("preview_id", "tenant_id", "produced_by", "build_output", "commit_message", "build_output_dir", "source_dir")
RECORD_KINDS = ("scan", "sandbox", "dependencies", "approval")
CLAIM_FIELDS = ("secrets_scan", "sandbox", "dependency_report", "approved_by")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


class Invalid(Exception):
    """Bad input: exit 2."""


class Blocked(Exception):
    """A required capability is missing: exit 3."""


class Refusal(Exception):
    """A named refusal: exit 1."""

    def __init__(self, refusal: str, detail: str) -> None:
        super().__init__(detail)
        self.payload = {"verdict": "refused", "refusal": refusal, "detail": detail}


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # usage errors are invalid input, reported as JSON
        _emit({"error": message})
        raise SystemExit(2)


def _emit(obj: Any) -> None:
    sys.stdout.write(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _load_json(path: str, what: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except OSError as exc:
        raise Invalid("cannot read %s %s: %s" % (what, path, exc.strerror))
    except ValueError as exc:
        raise Invalid("%s %s is not valid JSON: %s" % (what, path, exc))


def _need(cond: bool, message: str) -> None:
    if not cond:
        raise Invalid(message)


def _text(v: Any) -> bool:
    return isinstance(v, str) and v.strip() != ""


# ---------------------------------------------------------------- records

def _validate_records(doc: Any) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    _need(isinstance(doc, dict), "records fixture must be a JSON object")
    principals, records = doc.get("principals"), doc.get("records")
    _need(isinstance(principals, list) and principals, "records fixture needs a non-empty principals list")
    _need(isinstance(records, list) and records, "records fixture needs a non-empty records list")
    for kind, items, fields in (("principal", principals, ("id", "tenant_id", "max_classification")),
                                ("record", records, ("id", "tenant_id", "classification", "category"))):
        ids = set()
        for item in items:
            _need(isinstance(item, dict), "every %s must be an object" % kind)
            for f in fields:
                _need(_text(item.get(f)), "%s %r needs a text %s" % (kind, item.get("id"), f))
            _need(item["id"] not in ids, "duplicate %s id %s" % (kind, item["id"]))
            ids.add(item["id"])
    for p in principals:
        _need(p["max_classification"] in tenancy.LEVEL, "principal %s has unknown max_classification" % p["id"])
    for r in records:
        _need(r["classification"] in tenancy.LEVEL, "record %s has unknown classification" % r["id"])
        _need(r.get("approved_abstraction", False) in (True, False), "record %s approved_abstraction must be a boolean" % r["id"])
        grants = r.get("grants", [])
        _need(isinstance(grants, list) and all(isinstance(g, dict) and _text(g.get("tenant_id")) for g in grants),
              "record %s grants must be objects with a tenant_id" % r["id"])
    return principals, records


def never_granted(category: str) -> bool:
    """credential, Credentials, BACKUP-archive, ｃｒｅｄｅｎｔｉａｌ: every spelling of the two categories that never cross."""
    folded = "".join(c for c in unicodedata.normalize("NFKC", category) if unicodedata.category(c) != "Cf").casefold()
    return NEVER_GRANTED.search(folded) is not None


def _owner_grants(record: Dict[str, Any], owners: Dict[str, List[str]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Grants that stand: approved by a listed owner of the record's own tenant, never on credentials or backups."""
    kept, notes = [], []
    for g in record.get("grants", []):
        if never_granted(record["category"]):
            notes.append("grant to %s ignored: %s records never cross tenants" % (g["tenant_id"], record["category"]))
        elif g.get("approved_by") not in owners.get(record["tenant_id"], []):
            notes.append("grant to %s ignored: %s is not a listed owner of %s's data" % (g["tenant_id"], g.get("approved_by"), record["tenant_id"]))
        else:
            kept.append(g)
    return kept, notes


def _human_grant(principal: Dict[str, Any], record: Dict[str, Any]) -> bool:
    return any(g["tenant_id"] == principal["tenant_id"] for g in record.get("grants", []))


def cmd_records(a: argparse.Namespace) -> int:
    principals, records = _validate_records(_load_json(a.fixture, "fixture"))
    owners = _load_json(TENANT_OWNERS, "tenant owners file").get("owners", {})
    notes: Dict[str, List[str]] = {}
    checked = []
    for r in records:
        kept, why = _owner_grants(r, owners)
        notes[r["id"]] = why
        checked.append(dict(r, grants=kept))
    records = checked
    chosen = principals
    if a.principal:
        chosen = [p for p in principals if p["id"] == a.principal]
        _need(chosen, "principal %s is not in the fixture" % a.principal)
    matrix, leaks, authorized = [], [], []
    for p in chosen:
        for r in records:
            allowed, why = tenancy.can_read(p, r, r["grants"])
            cross = r["tenant_id"] != p["tenant_id"]
            sensitive = tenancy.LEVEL[r["classification"]] >= SENSITIVE
            row = {"principal": p["id"], "record": r["id"], "allowed": allowed, "reason": why, "cross_tenant": cross}
            ignored = [n for n in notes[r["id"]] if n.startswith("grant to %s " % p["tenant_id"])]
            if ignored:
                row["note"] = "; ".join(ignored)
            matrix.append(row)
            if allowed and cross and sensitive:
                pair = {"principal": p["id"], "record": r["id"], "classification": r["classification"], "reason": why}
                if _human_grant(p, r):
                    authorized.append(pair)
                else:
                    pair["cause"] = "abstraction-mislabel" if r.get("approved_abstraction") is True else "unexplained-allow"
                    leaks.append(pair)
    lint = [{"rule": "abstraction-mislabel", "record": r["id"],
             "detail": "%s record carries approved_abstraction=true; an abstraction is a separate derived record "
                       "(derived_from set, public or internal), so this label is wrong. Any read it allows is counted "
                       "in leaks." % r["classification"]}
            for r in records if tenancy.LEVEL[r["classification"]] >= SENSITIVE and r.get("approved_abstraction") is True]
    verdict = "leak" if leaks else "mislabel" if lint else "isolated"
    _emit({"verdict": verdict, "principals": len(chosen), "records": len(records), "pairs": len(matrix),
           "allowed": sum(1 for m in matrix if m["allowed"]), "denied": sum(1 for m in matrix if not m["allowed"]),
           "leaks": leaks, "lint": lint, "authorized_cross_tenant": authorized, "matrix": matrix,
           "ignored_grants": [{"record": rid, "detail": n} for rid, ns in sorted(notes.items()) for n in ns],
           "assumptions": ["Reads are decided by fleetlib.tenancy.can_read on records whose grants were first filtered: a "
                           "grant stands only when a listed owner of the record's tenant (tenant-owners.json) approved it, and "
                           "credential and backup records never cross tenants. fleetlib itself accepts any human: grant.",
                           "A cross-tenant read of a public or internal record is not counted as a leak; only "
                           "confidential and restricted records are"]})
    return 0 if verdict == "isolated" else 1


# ---------------------------------------------------------------- audit trail

_AT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_REQUIRED = ("seq", "at", "actor", "action", "tenant_id", "prev_sha256", "sha256")


def _entry_sha(entry: Dict[str, Any]) -> str:
    return canon.sha({k: v for k, v in entry.items() if k != "sha256"})


def _split_log(text: str) -> Tuple[int, List[str]]:
    """Return (header lines skipped, entry lines). A first line starting SYNTHETIC FIXTURE: is a label."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    offset = 1 if lines and lines[0].startswith(HEADER_PREFIX) else 0
    return offset, lines[offset:]


def _shaped(e: Any) -> bool:
    return (isinstance(e, dict) and all(k in e for k in _REQUIRED) and isinstance(e["seq"], int)
            and not isinstance(e["seq"], bool) and isinstance(e["sha256"], str) and isinstance(e["prev_sha256"], str))


def _verify_chain(text: str, anchor: Optional[str] = None) -> Dict[str, Any]:
    offset, lines = _split_log(text)
    entries = []
    for raw in lines:
        try:
            entries.append(json.loads(raw))
        except ValueError:
            entries.append(None)
    prev, bad = GENESIS, None
    for i, e in enumerate(entries):
        reason = detail = None
        if not _shaped(e):
            reason, detail = "malformed", "line is not a complete audit entry"
        elif _entry_sha(e) != e["sha256"]:
            reason, detail = "edited", "sha256 does not match the entry's content"
        elif e["seq"] > i:
            later = any(_shaped(x) and x["seq"] == i for x in entries[i + 1:])
            reason = "reordered" if later else "deleted"
            detail = "expected seq %d, found %d%s" % (i, e["seq"], "; seq %d appears later" % i if later else "")
        elif e["seq"] < i:
            reason, detail = "inserted", "expected seq %d, found duplicate seq %d" % (i, e["seq"])
        elif e["prev_sha256"] != prev:
            reason, detail = "inserted", "prev_sha256 does not match the line before: a line was inserted or an earlier line rewritten"
        if reason:
            bad = {"line": i + 1 + offset, "seq": e.get("seq") if isinstance(e, dict) else None,
                   "reason": reason, "detail": detail}
            break
        prev = e["sha256"]
    head = prev if bad is None else None
    if bad is None and anchor is not None and anchor != prev:
        bad = {"line": len(lines) + offset, "seq": None, "reason": "truncated-or-extended",
               "detail": "head sha256 differs from the anchor; lines were removed from or added to the end"}
    return {"verdict": "intact" if bad is None else "tampered", "entries": len(lines), "head_sha256": head, "first_bad": bad}


def cmd_audit_verify(a: argparse.Namespace) -> int:
    try:
        with open(a.log, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        raise Invalid("cannot read log %s: %s" % (a.log, exc.strerror))
    except UnicodeDecodeError:
        raise Invalid("log %s is not UTF-8 text" % a.log)
    if a.anchor is not None:
        _need(re.fullmatch(r"[0-9a-f]{64}", a.anchor) is not None, "--anchor must be 64 lowercase hex characters")
    result = _verify_chain(text, a.anchor)
    result["assumptions"] = ["Verification needs no secret: the chain proves order and content, not who wrote it",
                             "Without --anchor, removing lines from the end, or rewriting every line after a point with "
                             "recomputed hashes, is not detectable; record head_sha256 somewhere the log writer can't edit"]
    _emit(result)
    return 0 if result["verdict"] == "intact" else 1


def cmd_audit_append(a: argparse.Namespace) -> int:
    try:
        entry = json.loads(a.entry)
    except ValueError as exc:
        raise Invalid("--entry is not valid JSON: %s" % exc)
    _need(isinstance(entry, dict), "--entry must be a JSON object")
    extra = set(entry) - {"actor", "action", "tenant_id", "at", "detail"}
    _need(not extra, "--entry has unknown keys: %s" % ", ".join(sorted(extra)))
    for f in ("actor", "action", "tenant_id"):
        _need(_text(entry.get(f)), "--entry needs a text %s" % f)
    _need("detail" not in entry or isinstance(entry["detail"], str), "--entry detail must be text")
    at = entry.get("at") or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _need(isinstance(at, str) and _AT.match(at) is not None, "--entry at must look like 2026-11-25T09:00:00Z")
    directory = os.path.dirname(os.path.abspath(a.log))
    _need(os.path.isdir(directory), "directory for %s does not exist" % a.log)
    fd = os.open(a.log, os.O_RDWR | os.O_CREAT | os.O_APPEND, 0o644)
    with os.fdopen(fd, "a+", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        try:
            text = fh.read()
        except UnicodeDecodeError:
            raise Invalid("log %s is not UTF-8 text; nothing was appended" % a.log)
        state = _verify_chain(text)
        if state["verdict"] != "intact":
            _emit({"verdict": "refused", "reason": "the existing log fails verification; nothing was appended",
                   "first_bad": state["first_bad"]})
            return 1
        _, lines = _split_log(text)
        new = {"seq": len(lines), "at": at, "actor": entry["actor"], "action": entry["action"],
               "tenant_id": entry["tenant_id"], "prev_sha256": state["head_sha256"]}
        if "detail" in entry:
            new["detail"] = entry["detail"]
        new["sha256"] = _entry_sha(new)
        if text and not text.endswith("\n"):
            fh.write("\n")
        fh.write(canon.canonical(new) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    _emit({"verdict": "appended", "entry": new})
    return 0


# ---------------------------------------------------------------- secrets scan

# (name, regex, source). Sources are documented in references/sources.md.
PATTERNS = [
    ("pem-private-key-header",
     re.compile(rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY(?: BLOCK)?-----"),
     "RFC 7468 section 10 (PKCS #8 PRIVATE KEY label) and OpenSSH key format"),
    ("aws-access-key-id", re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
     "AWS IAM documentation: long-term access key ids are 20 characters starting AKIA"),
    ("github-token", re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,})\b"),
     "GitHub documentation, token formats (ghp_, gho_, ghu_, ghs_, ghr_, github_pat_)"),
    ("fx-demo-synthetic-token", re.compile(rb"\bfx_demo_[A-Za-z0-9]{16,}\b"),
     "hosting fleet fixture convention: fx_demo_ plus 16 or more letters or digits marks a synthetic secret"),
    ("secret-assignment", re.compile(rb"\b[A-Z][A-Z0-9_]*(?:SECRET|PASSWORD|PASSWD|TOKEN|API_KEY|PRIVATE_KEY)[A-Z0-9_]*\s*[=:]\s*['\"]?[^\s'\"]{12,}"),
     "common build-log leak: an environment-style NAME=value whose name says secret, password, token or key"),
]


def _validate_manifest(doc: Any) -> List[Dict[str, str]]:
    _need(isinstance(doc, dict) and isinstance(doc.get("secrets"), list) and doc["secrets"],
          "manifest needs a non-empty secrets list")
    names = set()
    for s in doc["secrets"]:
        _need(isinstance(s, dict) and _text(s.get("name")) and isinstance(s.get("value"), str),
              "every manifest secret needs a name and a value")
        _need(len(s["value"]) >= 8, "secret %s is shorter than 8 characters; a substring match would be noise" % s["name"])
        _need(s["name"] not in names, "duplicate secret name %s" % s["name"])
        names.add(s["name"])
    return doc["secrets"]


def cmd_secrets_scan(a: argparse.Namespace) -> int:
    prev = None
    if a.record_for:
        _records_root(a)
        prev = _preview(a.record_for)
        if a.path and os.path.realpath(a.path) != prev["_build"]:
            raise Refusal("scan-not-preview-content", "an owner scan covers the preview's own build folder %s; --path %s is "
                          "another folder" % (prev["_build"], a.path))
        if a.manifest and os.path.realpath(a.manifest) != os.path.realpath(OWNER_MANIFEST):
            raise Refusal("manifest-not-owner-file", "an owner scan uses the owner's secrets manifest %s; --manifest %s is "
                          "refused" % (OWNER_MANIFEST, a.manifest))
        manifest = _load_json(OWNER_MANIFEST, "owner secrets manifest")
        secrets = _validate_manifest(manifest) if manifest.get("tenant_id") == prev["tenant_id"] else []
        root = prev["_build"]
    else:
        _need(bool(a.path) and bool(a.manifest), "secrets scan needs --path and --manifest, or --record-for PREVIEW")
        _need(os.path.isdir(a.path), "--path %s is not a directory" % a.path)
        secrets = _validate_manifest(_load_json(a.manifest, "manifest"))
        root = os.path.realpath(a.path)
    findings, scanned, skipped = [], 0, []
    for folder, dirs, files in os.walk(root, followlinks=False):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(folder, name)
            rel = os.path.relpath(full, root)
            if os.path.islink(full) or not os.path.isfile(full):
                skipped.append({"file": rel, "why": "symlink or special file; not followed"})
                continue
            if os.path.getsize(full) > MAX_SCAN_BYTES:
                skipped.append({"file": rel, "why": "larger than %d bytes" % MAX_SCAN_BYTES})
                continue
            with open(full, "rb") as fh:
                data = fh.read()
            scanned += 1
            findings += _scan_bytes(data, rel, secrets)
    findings.sort(key=lambda f: (f["file"], f["kind"], f.get("line", 0), f.get("secret", f.get("pattern", ""))))
    verdict = "findings" if findings else "clean"
    out = {"verdict": verdict, "files_scanned": scanned, "skipped": skipped, "findings": findings,
           "assumptions": ["Values are matched as literal substrings; an encoded copy (base64, URL-encoded) is not found",
                           "Findings name the secret and file, never the value"]}
    if prev is not None:
        out["recorded"] = _record(prev, "scan", {"verdict": verdict, "findings": len(findings), "files_scanned": scanned,
                                                 "files": prev["_build_files"]}, "isolation_check secrets scan")
    _emit(out)
    return 1 if findings else 0


def _scan_bytes(data: bytes, rel: str, secrets: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    findings, known = [], set()
    for s in secrets:
        needle = s["value"].encode("utf-8")
        if needle in data:
            known.add(needle)
            findings.append({"kind": "manifest-secret", "secret": s["name"], "file": rel, "count": data.count(needle)})
    for pname, rx, source in PATTERNS:
        for m in rx.finditer(data):
            if any(k in m.group(0) for k in known):
                continue  # already reported by name
            findings.append({"kind": "pattern", "pattern": pname, "file": rel,
                             "line": data.count(b"\n", 0, m.start()) + 1, "source": source})
    return findings


# ---------------------------------------------------------------- sandbox build

def _docker(args: List[str], stdin: Optional[str] = None, timeout: int = DOCKER_TIMEOUT) -> "subprocess.CompletedProcess[str]":
    try:
        return subprocess.run(["docker"] + args, input=stdin, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise Blocked("the docker command is not installed")
    except subprocess.TimeoutExpired:
        raise Blocked("docker did not answer within %ds" % timeout)


def docker_ready() -> Tuple[bool, str]:
    """(True, '') when the daemon answers and the local image exists. Never pulls."""
    try:
        if _docker(["info", "--format", "{{.ServerVersion}}"], timeout=20).returncode != 0:
            return False, "the Docker daemon is not running"
        if _docker(["image", "inspect", IMAGE, "--format", "{{.Id}}"], timeout=20).returncode != 0:
            return False, "image %s is not present locally and this check never pulls" % IMAGE
    except Blocked as exc:
        return False, str(exc)
    return True, ""


def mount_check(src: str) -> None:
    """A trusted probe, run before the untrusted script: can the Docker VM see --src at all? A folder outside the
    paths Docker shares mounts empty, which is a missing capability (exit 3), not a leak and never isolation."""
    if not os.listdir(src):
        return
    proc = _docker(["run", "--rm", "--pull", "never", "--network", "none", "-v", "%s:/src:ro" % src, IMAGE,
                    "sh", "-c", "ls -A /src | head -n 1"], timeout=DOCKER_TIMEOUT)
    if proc.returncode == 0 and not proc.stdout.strip():
        raise Blocked("docker mounts %s empty: the folder is outside the paths Docker shares with its VM; share it or "
                      "run from a shared folder" % src)


def build_docker_cmd(run_id: str, src: str, other: str, control: bool) -> List[str]:
    cmd = ["docker", "run", "--rm", "-i", "--pull", "never"]
    if not control:
        cmd += ["--network", "none"]
    cmd += ["--read-only", "--tmpfs", "/tmp:rw,size=16m", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--pids-limit", "64", "--memory", "128m", "--user", "65534:65534",
            "--label", "%s=%s" % (LABEL_KEY, run_id), "-v", "%s:/src:ro" % src]
    if control:  # deliberately weakened: other tenant mounted, one synthetic secret env var, default bridge network
        cmd += ["-v", "%s:/other:ro" % other, "-e", CONTROL_SECRET]
    return cmd + ["-w", "/tmp", IMAGE, "sh", "-s"]


def _evaluate_probes(p: Dict[str, Any]) -> List[str]:
    failed = []
    if p["src_readable"] is not True or p["tmp_writable"] is not True:
        failed.append("sandbox-not-working")
    if p["read_other"] is not False:
        failed.append("other-tenant-readable")
    if p["secret_env_names"]:
        failed.append("secret-env-visible")
    if p["extra_interfaces"]:
        failed.append("network-interface-present")
    if p["src_writable"] is not False:
        failed.append("src-writable")
    return sorted(failed)


def _parse_probes(stdout: str) -> Optional[Dict[str, Any]]:
    for line in reversed([l for l in stdout.splitlines() if l.strip()]):
        try:
            p = json.loads(line)
        except ValueError:
            continue
        if (isinstance(p, dict) and all(isinstance(p.get(k), bool) for k in ("read_other", "src_writable", "src_readable", "tmp_writable"))
                and all(isinstance(p.get(k), list) and all(isinstance(x, str) for x in p[k])
                        for k in ("secret_env_names", "extra_interfaces"))):
            return p
        return None
    return None


def cmd_sandbox_build(a: argparse.Namespace) -> int:
    for flag, path in (("--src", a.src), ("--other-tenant", a.other_tenant)):
        _need(os.path.isdir(path), "%s %s is not a directory" % (flag, path))
    _need(os.path.isfile(a.script), "--script %s is not a file" % a.script)
    src, other = os.path.realpath(a.src), os.path.realpath(a.other_tenant)
    for path in (src, other):
        _need(":" not in path and "," not in path, "path %s holds a colon or comma, which breaks the docker -v syntax" % path)
    _need(src != other, "--src and --other-tenant must be different folders")
    _need(bool(os.listdir(src)), "--src %s is empty; an empty source proves nothing about the sandbox" % a.src)
    prev = None
    if a.record_for and not a.control:
        _records_root(a)
        prev = _preview(a.record_for)
        if src != prev["_source"]:
            raise Refusal("sandbox-not-preview-source", "an owner sandbox record builds the preview's own source folder %s; "
                          "--src %s is another folder" % (prev["_source"], a.src))
    with open(a.script, "rb") as fh:
        raw = fh.read(1024 * 1024 + 1)
    _need(len(raw) <= 1024 * 1024, "--script is larger than 1 MiB")
    try:
        script = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise Invalid("--script is not UTF-8 text")
    if script.startswith(HEADER_PREFIX):  # the fixture label line is not code
        script = "\n" + script.split("\n", 1)[1] if "\n" in script else ""
    with open(PROBE_SCRIPT, "rb") as fh:
        probe_raw = fh.read()
    ready, why = docker_ready()
    if not ready:
        raise Blocked(why)
    mount_check(src)
    run_id = uuid.uuid4().hex[:12]
    cmd = build_docker_cmd(run_id, src, other, a.control)[1:]
    timed_out = False
    try:  # the untrusted build; its output is recorded by hash and never read as a verdict
        build = _docker(cmd, stdin=script, timeout=DOCKER_TIMEOUT)
    except Blocked:
        timed_out, build = True, None
    if build is not None and build.returncode == 125:
        raise Blocked("docker could not start the container: %s" % build.stderr.strip()[:300])
    try:  # the harness's own probe, in a container started with the same flags, after the build
        proc = _docker(cmd, stdin=probe_raw.decode("utf-8"), timeout=DOCKER_TIMEOUT)
    except Blocked:
        proc = None
    leftover = [c for c in _docker(["ps", "-a", "-q", "--filter", "label=%s=%s" % (LABEL_KEY, run_id)]).stdout.split() if c]
    if leftover:
        _docker(["rm", "-f"] + leftover)
    probes = None if proc is None else _parse_probes(proc.stdout)
    if proc is not None and proc.returncode == 125:
        raise Blocked("docker could not start the probe container: %s" % proc.stderr.strip()[:300])
    failed: List[str] = []
    if timed_out:
        failed.append("build-timeout")
    if probes is None:
        failed.append("probe-output-missing")
    else:
        failed += _evaluate_probes(probes)
    if leftover:
        failed.append("container-not-removed")
    failed = sorted(set(failed))
    if a.control:
        verdict = "leak" if failed else "control-undetected"
    else:
        verdict = "leak" if failed else "isolated"
    note = None
    if verdict == "control-undetected":
        note = "the weakened control passed every probe, so the probes cannot be trusted"
    out = {"verdict": verdict, "control": a.control, "failed_probes": failed, "probes": probes,
           "ephemeral": {"label": "%s=%s" % (LABEL_KEY, run_id), "containers_remaining_after_run": len(leftover)},
           "script_sha256": canon.sha_bytes(raw), "probe_sha256": canon.sha_bytes(probe_raw), "image": IMAGE,
           "build": {"exit": None if build is None else build.returncode, "timed_out": timed_out,
                     "stdout_sha256": None if build is None else canon.sha_bytes(build.stdout.encode("utf-8"))},
           "assumptions": ["The verdict comes from the harness's own probe (scripts/sandbox_probe.sh), run after the build "
                           "in a second container started with the same flags; the build script's output is never read as "
                           "a probe result",
                           "src_readable and tmp_writable must hold so a broken sandbox can't look isolated",
                           "Network is judged from /sys/class/net; no traffic is sent, even in the control",
                           "%s must already be local; the check never pulls" % IMAGE]}
    if note:
        out["note"] = note
    if proc is not None and probes is None:
        out["docker_stderr"] = proc.stderr.strip()[:300]
    if prev is not None:
        out["recorded"] = _record(prev, "sandbox", {"verdict": verdict, "control": False, "failed_probes": failed,
                                                    "script_sha256": out["script_sha256"], "probe_sha256": out["probe_sha256"],
                                                    "source_files": prev["_source_files"]}, "isolation_check sandbox-build")
    _emit(out)
    return 0 if verdict == "isolated" else 1


# ---------------------------------------------------------------- owner records and the promotion gate

def _tree(folder: str, what: str) -> List[List[str]]:
    """[relative path, sha256] for every regular file under folder, sorted. A symlink or special file is invalid input."""
    out = []
    for base, dirs, files in os.walk(folder, followlinks=False):
        for d in dirs:
            _need(not os.path.islink(os.path.join(base, d)), "%s holds a symlinked folder %s" % (what, os.path.join(base, d)))
        for name in files:
            full = os.path.join(base, name)
            _need(os.path.isfile(full) and not os.path.islink(full), "%s holds a symlink or special file %s" % (what, full))
            out.append([os.path.relpath(full, folder).replace(os.sep, "/"), canon.sha_file(full)])
    return sorted(out)


def _preview_dir(prev: Dict[str, Any], base: str, field: str) -> str:
    rel = prev.get(field)
    _need(_text(rel), "preview needs a text %s: the folder, beside the preview file, that holds it" % field)
    parts = rel.replace("\\", "/").split("/")
    _need(not os.path.isabs(rel) and ".." not in parts, "preview %s must be a relative folder without '..': %r" % (field, rel))
    full = os.path.realpath(os.path.join(base, rel))
    _need(os.path.isdir(full), "preview %s %s is not a folder" % (field, full))
    return full


def _preview(path: str) -> Dict[str, Any]:
    prev = _load_json(path, "preview")
    _need(isinstance(prev, dict), "preview must be a JSON object")
    for f in ("preview_id", "tenant_id", "produced_by"):
        _need(_text(prev.get(f)), "preview needs a text %s" % f)
    _need(SLUG.match(prev["preview_id"]) is not None, "preview_id must be a lowercase slug")
    for f in ("build_output", "commit_message"):
        _need(prev.get(f, "") is not None and isinstance(prev.get(f, ""), str), "preview %s must be text" % f)
    base = os.path.dirname(os.path.abspath(path))
    prev["_build"], prev["_source"] = _preview_dir(prev, base, "build_output_dir"), _preview_dir(prev, base, "source_dir")
    prev["_build_files"] = _tree(prev["_build"], "build_output_dir")
    prev["_source_files"] = _tree(prev["_source"], "source_dir")
    _need(bool(prev["_build_files"]), "preview build_output_dir %s holds no files; there is nothing to promote" % prev["_build"])
    return prev


def _subject(prev: Dict[str, Any]) -> str:
    """The preview's content hash: its text fields and every file in its build and source folders."""
    return canon.sha(dict({k: prev.get(k) for k in SUBJECT_FIELDS}, build_files=prev["_build_files"], source_files=prev["_source_files"]))


def records_root() -> str:
    return os.path.join(OWNER_ROOT, "records")


def _records_root(a: argparse.Namespace) -> str:
    named = getattr(a, "records", None)
    if named and os.path.realpath(named) != os.path.realpath(records_root()):
        raise Refusal("records-not-owner-ledger", "owner records live only at %s; the caller-named %s is refused"
                      % (records_root(), named))
    return records_root()


def _record(prev: Dict[str, Any], kind: str, payload: Dict[str, Any], by: str) -> str:
    """Write the owner's record for one check, once. Same content again is a no-op; different content is refused."""
    folder = os.path.join(records_root(), prev["preview_id"])
    os.makedirs(folder, exist_ok=True)
    rec = dict(payload, kind=kind, preview_id=prev["preview_id"], tenant_id=prev["tenant_id"], subject_sha256=_subject(prev),
               recorded_by=by)
    path = os.path.join(folder, kind + ".json")
    tmp = path + ".tmp-%d" % os.getpid()
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    try:
        os.link(tmp, path)
    except FileExistsError:
        if _load_json(path, "owner record") != rec:
            raise Refusal("record-exists", "%s already holds a different %s record for %s" % (records_root(), kind, prev["preview_id"]))
    finally:
        os.unlink(tmp)
    return path


def _owner_policy(a: argparse.Namespace) -> Dict[str, Any]:
    if getattr(a, "policy", None) and os.path.realpath(a.policy) != os.path.realpath(OWNER_POLICY):
        raise Refusal("policy-not-owner-file", "the threshold and approvers come only from %s, never from %s" % (OWNER_POLICY, a.policy))
    doc = _load_json(OWNER_POLICY, "policy")
    _need(isinstance(doc, dict) and doc.get("blocking_severity") in SEVERITY,
          "policy blocking_severity must be one of %s" % ", ".join(sorted(SEVERITY)))
    _need(isinstance(doc.get("approvers"), dict), "policy needs approvers per tenant")
    return doc


def _slug(principal: str) -> str:
    return principal.split(":", 1)[-1].split(".", 1)[-1]


def _lock_packages(path: str) -> Dict[str, str]:
    """package name -> version from an npm package-lock.json (lockfileVersion 2 or 3 'packages' map)."""
    doc = _load_json(path, "lockfile")
    pkgs = doc.get("packages") if isinstance(doc, dict) else None
    _need(isinstance(pkgs, dict), "lockfile %s needs a packages object" % path)
    out = {}
    for key, meta in pkgs.items():
        if not key:
            continue
        _need(key.startswith("node_modules/") and isinstance(meta, dict) and _text(meta.get("version")),
              "lockfile entry %r needs a node_modules/ path and a version" % key)
        out[key.rsplit("node_modules/", 1)[1]] = meta["version"]
    return out


def cmd_record_dependencies(a: argparse.Namespace) -> int:
    _records_root(a)
    if a.report:
        raise Refusal("report-not-from-lockfile", "dependency findings come from the lockfile in the preview's source folder "
                      "matched against the owner's %s; a --report the caller wrote is refused" % ADVISORIES)
    prev = _preview(a.preview)
    lock = os.path.join(prev["_source"], LOCKFILE)
    _need(os.path.isfile(lock), "the preview's source folder %s has no %s to audit" % (prev["_source"], LOCKFILE))
    packages = _lock_packages(lock)
    advisories = _load_json(ADVISORIES, "owner advisories")
    _need(isinstance(advisories, dict) and isinstance(advisories.get("advisories"), list), "owner advisories need an advisories list")
    findings = []
    for adv in advisories["advisories"]:
        _need(isinstance(adv, dict) and adv.get("severity") in SEVERITY and _text(adv.get("package")) and _text(adv.get("id")),
              "every advisory needs an id, a package and a severity of %s" % ", ".join(sorted(SEVERITY)))
        version = packages.get(adv["package"])
        versions = adv.get("versions", "*")
        if version is not None and (versions == "*" or version in versions):
            findings.append({"package": adv["package"], "version": version, "severity": adv["severity"], "id": adv["id"]})
    path = _record(prev, "dependencies", {"findings": sorted(findings, key=lambda f: (f["package"], f["id"])),
                                          "packages": len(packages), "lockfile_sha256": canon.sha_file(lock),
                                          "advisories_sha256": canon.sha_file(ADVISORIES)}, "isolation_check record-dependencies")
    _emit({"verdict": "recorded", "recorded": path, "findings": len(findings), "packages": len(packages)})
    return 0


def cmd_approve(a: argparse.Namespace) -> int:
    _records_root(a)
    prev, policy = _preview(a.preview), _owner_policy(a)
    if a.by not in policy["approvers"].get(prev["tenant_id"], []):
        raise Refusal("approver-not-authorized", "%s is not a promotion approver for %s in %s" % (a.by, prev["tenant_id"], OWNER_POLICY))
    if _slug(a.by) == _slug(prev["produced_by"]):
        raise Refusal("self-approval", "%s produced the preview as %s and cannot approve it" % (a.by, prev["produced_by"]))
    path = _record(prev, "approval", {"approved_by": a.by}, "isolation_check approve")
    _emit({"verdict": "recorded", "recorded": path, "approved_by": a.by, "preview_id": prev["preview_id"]})
    return 0


def cmd_promote(a: argparse.Namespace) -> int:
    records = _records_root(a)
    prev = _preview(a.preview)
    policy = _owner_policy(a)
    blocking, subject = policy["blocking_severity"], _subject(prev)
    reasons: List[str] = []
    checks: Dict[str, str] = {}

    def owned(kind: str) -> Optional[Dict[str, Any]]:
        path = os.path.join(records, prev["preview_id"], kind + ".json")
        if not os.path.isfile(path):
            return None
        rec = _load_json(path, "owner record")
        if not isinstance(rec, dict) or rec.get("subject_sha256") != subject or rec.get("kind") != kind:
            return {"stale": True}
        return rec

    manifest = _load_json(OWNER_MANIFEST, "owner secrets manifest")
    known = _validate_manifest(manifest) if manifest.get("tenant_id") == prev["tenant_id"] else []
    rescan = []
    for ref in ("build_output", "commit_message"):
        rescan += _scan_bytes((prev.get(ref) or "").encode("utf-8"), ref, known)
    scan = owned("scan")
    if rescan:
        checks["secrets_scan"] = "failed"
        reasons.append("the preview's own %s holds %d secret finding(s)" % ("/".join(sorted({f["file"] for f in rescan})), len(rescan)))
    elif scan is None:
        checks["secrets_scan"] = "missing"
        reasons.append("no owner secrets-scan record; an absent measurement is not a clean one")
    elif scan.get("stale") or scan.get("verdict") != "clean" or scan.get("files") != prev["_build_files"] \
            or scan.get("files_scanned") != len(prev["_build_files"]):
        checks["secrets_scan"] = "failed"
        reasons.append("secrets scan record is %s, not a clean scan of every file in the build folder"
                       % ("for different preview content" if scan.get("stale") else scan.get("verdict")))
    else:
        checks["secrets_scan"] = "passed"

    sb = owned("sandbox")
    if sb is None:
        checks["sandbox"] = "missing"
        reasons.append("no owner sandbox record; the build has not been shown isolated")
    elif sb.get("stale") or sb.get("verdict") != "isolated" or sb.get("control") is not False:
        checks["sandbox"] = "failed"
        reasons.append("sandbox record is %s, not isolated" % ("for different preview content" if sb.get("stale") else sb.get("verdict")))
    else:
        checks["sandbox"] = "passed"

    deps = owned("dependencies")
    if deps is None:
        checks["dependencies"] = "missing"
        reasons.append("no owner dependency record")
    elif deps.get("stale"):
        checks["dependencies"] = "failed"
        reasons.append("dependency record is for different preview content")
    else:
        hits = sorted("%s (%s)" % (f["package"], f["severity"]) for f in deps["findings"] if SEVERITY[f["severity"]] >= SEVERITY[blocking])
        checks["dependencies"] = "failed" if hits else "passed"
        if hits:
            reasons.append("dependency findings at or above %s: %s" % (blocking, ", ".join(hits)))

    ok = owned("approval")
    if ok is None:
        checks["approval"] = "missing"
        reasons.append("no approval recorded by an owner-listed human")
    elif ok.get("stale") or ok.get("approved_by") not in policy["approvers"].get(prev["tenant_id"], []) \
            or _slug(ok["approved_by"]) == _slug(prev["produced_by"]):
        checks["approval"] = "failed"
        reasons.append("approval record is stale, unlisted or self-approval")
    else:
        checks["approval"] = "passed"

    findings = []
    for ref in ("build_output", "commit_message"):
        findings += untrusted.scan(prev.get(ref, "") or "", "%s:%s" % (prev["preview_id"], ref))
    decision = "promote" if not reasons else "refuse"
    _emit({"decision": decision, "reasons": reasons, "checks": checks, "preview_id": prev["preview_id"],
           "tenant_id": prev["tenant_id"], "blocking_severity": blocking, "untrusted_findings": findings,
           "secret_findings_in_preview": rescan, "ignored_claims": sorted(f for f in CLAIM_FIELDS if prev.get(f) is not None),
           "assumptions": ["Text in build_output and commit_message is data: it is scanned and attached, and never "
                           "changes the decision",
                           "Scan, sandbox, dependency and approval results come only from the owner records at their fixed "
                           "folder, bound to this preview's content hash (its text and every file in its build and source "
                           "folders); the preview's own result fields are listed as ignored_claims",
                           "A process running as the same OS user can write the owner's records folder or run the owner "
                           "commands under any listed name; only separate OS accounts or signed records stop that"]})
    return 0 if decision == "promote" else 1


# ---------------------------------------------------------------- entry point

def build_parser() -> argparse.ArgumentParser:
    p = Parser(prog="isolation_check", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True, parser_class=Parser)
    r = sub.add_parser("records", help="allow/deny matrix for every principal and record")
    r.add_argument("--fixture", required=True)
    r.add_argument("--principal")
    r.set_defaults(fn=cmd_records)
    au = sub.add_parser("audit", help="hash-chained audit trail").add_subparsers(dest="sub", required=True, parser_class=Parser)
    ap = au.add_parser("append")
    ap.add_argument("--log", required=True)
    ap.add_argument("--entry", required=True)
    ap.set_defaults(fn=cmd_audit_append)
    av = au.add_parser("verify")
    av.add_argument("--log", required=True)
    av.add_argument("--anchor")
    av.set_defaults(fn=cmd_audit_verify)
    se = sub.add_parser("secrets", help="secret exposure").add_subparsers(dest="sub", required=True, parser_class=Parser)
    ss = se.add_parser("scan")
    ss.add_argument("--path", help="the folder to scan; with --record-for it must be the preview's build folder")
    ss.add_argument("--manifest", help="the secrets manifest; with --record-for it must be the owner's")
    ss.add_argument("--record-for", dest="record_for", help="the preview this scan is for; writes an owner record")
    ss.add_argument("--records", help="refused unless it is the owner's fixed records folder")
    ss.set_defaults(fn=cmd_secrets_scan)
    sb = sub.add_parser("sandbox-build", help="untrusted build in a no-network container")
    sb.add_argument("--src", required=True)
    sb.add_argument("--other-tenant", required=True)
    sb.add_argument("--script", required=True)
    sb.add_argument("--control", action="store_true")
    sb.add_argument("--record-for", dest="record_for", help="the preview this build is for; --src must be its source folder")
    sb.add_argument("--records", help="refused unless it is the owner's fixed records folder")
    sb.set_defaults(fn=cmd_sandbox_build)
    rd = sub.add_parser("record-dependencies", help="findings from the preview's lockfile and the owner's advisories")
    rd.add_argument("--preview", required=True)
    rd.add_argument("--report", help="refused: findings come from the preview's own lockfile")
    rd.add_argument("--records", help="refused unless it is the owner's fixed records folder")
    rd.set_defaults(fn=cmd_record_dependencies)
    apv = sub.add_parser("approve", help="an owner-listed human approves a preview")
    apv.add_argument("--preview", required=True)
    apv.add_argument("--records", help="refused unless it is the owner's fixed records folder")
    apv.add_argument("--by", required=True)
    apv.add_argument("--policy", help="optional; must be the owner's promotion-policy.json")
    apv.set_defaults(fn=cmd_approve)
    pr = sub.add_parser("promote", help="preview-to-production gate")
    pr.add_argument("--preview", required=True)
    pr.add_argument("--records", help="refused unless it is the owner's fixed records folder")
    pr.add_argument("--policy", help="optional; must be the owner's promotion-policy.json")
    pr.set_defaults(fn=cmd_promote)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except Invalid as exc:
        _emit({"error": str(exc)})
        return 2
    except Blocked as exc:
        _emit({"blocked": str(exc)})
        return 3
    except Refusal as exc:
        _emit(exc.payload)
        return 1


if __name__ == "__main__":
    sys.exit(main())
