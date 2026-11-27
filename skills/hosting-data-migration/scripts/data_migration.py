#!/usr/bin/env python3
"""data_migration: move a hosted site's data safely.

SQLite plus a files folder stand in for a site's database and uploads.

  preflight --app APP.json --target TARGET.json
  export    (--db DB | --seed SQL) --files DIR --out BUNDLE_DIR --tenant ID
  import    --bundle BUNDLE_DIR --db NEW_DB --files-dest DIR --tenant ID
  migrate   (--db DB --backup-dir DIR | --seed SQL) --migration SQL
  rollback  --db DB --backup-dir DIR [--backup NAME]
  roundtrip --seed SQL --files DIR --tenant ID [--workdir DIR] [--tamper database.sql|files.tar]

The owner's ledger is one append-only file at a fixed path in the fleet's owner folder
(company-fleets/fleets/hosting/owner/hosting-data-migration/ledger.ndjson). export records the
manifest's sha256 and tenant; migrate records each backup's database, file hash and content checksum,
and the checksum the migration left. import and rollback trust only what the ledger holds, so a bundle
or backup rewritten and rehashed in place, relabeled to another tenant, or taken from another database is
refused. A --ledger the caller names, or a bundle or backup folder that holds the owner folder, is refused
by name. Migration SQL runs under an authorizer that forbids ATTACH, DETACH and pragmas other than
foreign_keys, so a migration writes only the database it was given.

--seed builds a throwaway database in a temp folder, so one command can rehearse a step from fixtures.
--tamper is a test hook: it appends one byte to a bundle artifact before import to prove the import
refuses it and writes nothing.

Stdout is JSON. Exit 0 ok, 1 refused or a check found a problem, 2 invalid input, 3 blocked by a
missing capability. Python 3.9+ standard library only. The script reads and writes local paths only.
"""
from __future__ import annotations

import argparse
import datetime
import fcntl
import hashlib
import json
import os
import pathlib
import re
import shutil
import sqlite3
import sys
import tarfile
import tempfile
from typing import Any, Dict, List, Optional, Tuple

FORMAT_VERSION = 1
OWNER_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "company-fleets", "fleets",
                                           "hosting", "owner", "hosting-data-migration"))
SQL_FORMAT = "sqlite3-iterdump-sql"
TAR_FORMAT = "tar-pax-sorted-mtime0-owner0"
DB_ARTIFACT, TAR_ARTIFACT, MANIFEST = "database.sql", "files.tar", "manifest.json"
LIMITS = [
    "SQLite and a files folder stand in for the site's database and uploads; engine-specific SQL "
    "(MySQL, PostgreSQL) is not tested.",
    "Databases are assumed idle, in rollback-journal mode, with one writer; take the site into "
    "maintenance mode first.",
    "sqlite_sequence content and file permissions are not part of the checksums.",
]


class InputError(Exception):
    """Invalid input; exit 2."""


class Refused(Exception):
    """The operation refused to proceed; exit 1. Carries a result dict."""

    def __init__(self, reason: str, **extra: Any) -> None:
        super().__init__(reason)
        self.result = dict(extra, verdict="refused", reason=reason)


# ------------------------------------------------------------------ shared

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: str, doc: Any) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")


def load_json(path: str, what: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        raise InputError("%s not found: %s" % (what, path))
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (ValueError, UnicodeDecodeError) as exc:
        raise InputError("%s is not valid JSON: %s" % (what, exc))
    if not isinstance(doc, dict):
        raise InputError("%s must be a JSON object" % what)
    return doc


def ledger_file() -> str:
    return os.path.join(OWNER_ROOT, "ledger.ndjson")


def _inside(path: str, folder: str) -> bool:
    path, folder = os.path.realpath(path), os.path.realpath(folder)
    return path == folder or path.startswith(folder + os.sep)


def owner_ledger(named: Optional[str], *artifact_dirs: str) -> str:
    """The owner's ledger at its fixed path. A caller-named ledger, or an artifact folder that holds the owner's ledger or
    sits inside the owner folder, is refused by name."""
    fixed = ledger_file()
    if named and os.path.realpath(named) != os.path.realpath(fixed):
        raise Refused("ledger-not-owner-ledger: exports and backups are recorded only in the owner's ledger %s; the caller-named "
                      "%s is refused" % (fixed, named), refusal="ledger-not-owner-ledger")
    for d in artifact_dirs:
        if _inside(fixed, d) or _inside(d, OWNER_ROOT):
            raise Refused("ledger-inside-artifact: the owner's ledger folder %s and the artifact folder %s overlap; the ledger "
                          "stays where only the owner writes" % (OWNER_ROOT, d), refusal="ledger-inside-artifact")
    return fixed


def ledger_append(path: str, record: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    record = dict(record, recorded_at=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    with open(path, "a", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.write(json.dumps(record, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def ledger_records(path: str, kind: str) -> List[Dict[str, Any]]:
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except FileNotFoundError:
        return []
    except UnicodeDecodeError:
        raise Refused("the owner's ledger %s is not UTF-8 text; the owner's record is damaged" % path)
    out = []
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            raise Refused("ledger line %d is not JSON; the owner's record is damaged" % n)
        if isinstance(rec, dict) and rec.get("kind") == kind:
            out.append(rec)
    return out


def need_dir(path: str, what: str) -> None:
    if not os.path.isdir(path):
        raise InputError("%s is not a directory: %s" % (what, path))


def open_ro(path: str) -> sqlite3.Connection:
    if not os.path.isfile(path):
        raise InputError("database not found: %s" % path)
    conn = sqlite3.connect(pathlib.Path(os.path.abspath(path)).as_uri() + "?mode=ro", uri=True)
    try:
        conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
    except sqlite3.DatabaseError:
        conn.close()
        raise InputError("not a SQLite database: %s" % path)
    return conn


def _enc(value: Any) -> List[str]:
    if value is None:
        return ["n"]
    if isinstance(value, bool):
        return ["i", str(int(value))]
    if isinstance(value, int):
        return ["i", str(value)]
    if isinstance(value, float):
        return ["f", repr(value)]
    if isinstance(value, bytes):
        return ["b", value.hex()]
    return ["s", str(value)]


def snapshot(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Row counts and content checksums that do not depend on file layout or row order."""
    tables: Dict[str, Dict[str, Any]] = {}
    names = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND substr(name,1,7) != 'sqlite_' ORDER BY name")]
    for name in names:
        quoted = '"%s"' % name.replace('"', '""')
        cur = conn.execute("SELECT * FROM %s" % quoted)
        cols = [d[0] for d in cur.description]
        rows = sorted(json.dumps([_enc(v) for v in row]) for row in cur)
        h = hashlib.sha256(json.dumps(cols).encode("utf-8") + b"\n")
        for row in rows:
            h.update(row.encode("utf-8") + b"\n")
        tables[name] = {"rows": len(rows), "checksum": h.hexdigest()}
    schema = [list(r) for r in conn.execute(
        "SELECT type, name, sql FROM sqlite_master WHERE substr(name,1,7) != 'sqlite_' ORDER BY type, name")]
    canonical = json.dumps({"schema": schema, "tables": tables}, sort_keys=True)
    return {"tables": tables, "database_checksum": sha256_bytes(canonical.encode("utf-8"))}


def db_snapshot(path: str) -> Dict[str, Any]:
    conn = sqlite3.connect(path)
    try:
        return snapshot(conn)
    finally:
        conn.close()


# --------------------------------------------------------------- preflight

def parse_version(text: str) -> Tuple[int, ...]:
    if not isinstance(text, str) or not re.match(r"^\d+(\.\d+)*$", text.strip()):
        raise InputError("not a dotted-integer version: %r" % (text,))
    return tuple(int(p) for p in text.strip().split("."))


def _cmp(a: Tuple[int, ...], b: Tuple[int, ...]) -> int:
    n = max(len(a), len(b))
    a, b = a + (0,) * (n - len(a)), b + (0,) * (n - len(b))
    return (a > b) - (a < b)


def parse_range(text: str) -> List[Tuple[str, Tuple[int, ...]]]:
    if not isinstance(text, str) or not text.strip():
        raise InputError("empty version range")
    clauses = []
    for part in text.split(","):
        m = re.match(r"^\s*(>=|<=|==|=|>|<)?\s*(\d+(?:\.\d+)*)\s*$", part)
        if not m:
            raise InputError("bad version range clause %r in %r" % (part, text))
        clauses.append(("==" if m.group(1) in (None, "=") else m.group(1), parse_version(m.group(2))))
    return clauses


def in_range(version: str, clauses: List[Tuple[str, Tuple[int, ...]]]) -> bool:
    v = parse_version(version)
    ops = {">=": lambda c: c >= 0, ">": lambda c: c > 0, "<=": lambda c: c <= 0, "<": lambda c: c < 0, "==": lambda c: c == 0}
    return all(ops[op](_cmp(v, bound)) for op, bound in clauses)


def _versions(value: Any, where: str) -> List[str]:
    items = value if isinstance(value, list) else [value]
    if not items or not all(isinstance(i, str) for i in items):
        raise InputError("%s must be a version string or a non-empty list of them" % where)
    for item in items:
        parse_version(item)
    return items


def _section(doc: Dict[str, Any], key: str, where: str) -> Dict[str, Any]:
    value = doc.get(key)
    if not isinstance(value, dict):
        raise InputError("%s needs an object %r" % (where, key))
    return value


def preflight(app_path: str, target_path: str) -> Dict[str, Any]:
    app, target = load_json(app_path, "app file"), load_json(target_path, "target file")
    req, offers = _section(app, "requires", "app file"), _section(target, "offers", "target file")
    unknown = sorted(set(req) - {"runtimes", "database", "extensions"})
    if unknown:
        raise InputError("unknown requirement %s (known: database, extensions, runtimes)" % ", ".join(map(repr, unknown)))
    reasons: List[Dict[str, Any]] = []
    checked = 0
    runtimes_req = req.get("runtimes", {})
    runtimes_off = offers.get("runtimes", {})
    if not isinstance(runtimes_req, dict) or not isinstance(runtimes_off, dict):
        raise InputError("'runtimes' must be an object")
    for name, rng in sorted(runtimes_req.items()):
        clauses, checked = parse_range(rng), checked + 1
        if name not in runtimes_off:
            reasons.append({"kind": "runtime-missing", "name": name, "required": rng, "offered": []})
            continue
        offered = _versions(runtimes_off[name], "offers.runtimes.%s" % name)
        if not any(in_range(v, clauses) for v in offered):
            reasons.append({"kind": "runtime-version", "name": name, "required": rng, "offered": offered})
    db_req = req.get("database")
    if db_req is not None:
        if not isinstance(db_req, dict) or not isinstance(db_req.get("engine"), str):
            raise InputError("requires.database needs an 'engine' string")
        db_off = _section(offers, "database", "target offers")
        if not isinstance(db_off.get("engine"), str):
            raise InputError("offers.database needs an 'engine' string")
        checked += 1
        if db_req["engine"].lower() != db_off["engine"].lower():
            reasons.append({"kind": "database-engine", "name": "database", "required": db_req["engine"], "offered": db_off["engine"]})
        elif "version" in db_req:
            clauses = parse_range(db_req["version"])
            offered = _versions(db_off.get("version"), "offers.database.version")
            if not any(in_range(v, clauses) for v in offered):
                reasons.append({"kind": "database-version", "name": db_req["engine"], "required": db_req["version"], "offered": offered})
    ext_req, ext_off = req.get("extensions", []), offers.get("extensions", [])
    for label, value in (("requires.extensions", ext_req), ("offers.extensions", ext_off)):
        if not isinstance(value, list) or not all(isinstance(e, str) for e in value):
            raise InputError("%s must be a list of strings" % label)
    for ext in sorted(set(ext_req)):
        checked += 1
        if ext not in ext_off:
            reasons.append({"kind": "extension-missing", "name": ext, "required": ext, "offered": []})
    if checked == 0:
        raise Refused("the app requires nothing checkable (no runtimes, database or extensions); a preflight with 0 checks proves nothing",
                      checked=0)
    return {"verdict": "incompatible" if reasons else "compatible", "reasons": reasons, "checked": checked,
            "assumptions": ["Ranges compare dotted integers only; a version with a suffix such as 8.4.0RC1 is rejected as invalid input.",
                            "One offered version that satisfies the range is enough.",
                            LIMITS[0]]}


# ------------------------------------------------------------------ export

def scan_files(root: str) -> List[Tuple[str, str]]:
    """Sorted (relative posix path, 'file' or 'dir'). Refuses symlinks and special files."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        for name, kind in [(d, "dir") for d in dirnames] + [(f, "file") for f in sorted(filenames)]:
            full = os.path.join(dirpath, name)
            mode = os.lstat(full).st_mode
            if os.path.islink(full) or not (os.path.isdir(full) if kind == "dir" else os.path.isfile(full)):
                raise InputError("symlinks and special files cannot be exported: %s" % full)
            out.append((os.path.relpath(full, root).replace(os.sep, "/"), kind))
    return sorted(out)


def make_tar(root: str, entries: List[Tuple[str, str]], dest: str) -> List[Dict[str, Any]]:
    files = []
    with tarfile.open(dest, "w", format=tarfile.PAX_FORMAT) as tar:
        for rel, kind in entries:
            info = tarfile.TarInfo(rel)
            info.mtime, info.uid, info.gid, info.uname, info.gname = 0, 0, 0, "", ""
            full = os.path.join(root, *rel.split("/"))
            if kind == "dir":
                info.type, info.mode = tarfile.DIRTYPE, 0o755
                tar.addfile(info)
            else:
                info.size, info.mode = os.path.getsize(full), 0o644
                with open(full, "rb") as fh:
                    tar.addfile(info, fh)
                files.append({"path": rel, "sha256": sha256_file(full), "size": info.size})
    return files


def build_seed_db(seed: str, dest: str) -> None:
    if not os.path.isfile(seed):
        raise InputError("seed file not found: %s" % seed)
    conn = sqlite3.connect(dest)
    try:
        with open(seed, encoding="utf-8") as fh:
            conn.executescript(fh.read())
        conn.commit()
    except UnicodeDecodeError:
        raise InputError("seed file is not UTF-8 text: %s" % seed)
    except sqlite3.Error as exc:
        raise InputError("seed SQL failed: %s" % exc)
    finally:
        conn.close()


def export_bundle(db: str, files: str, out: str, tenant: Optional[str], ledger: str) -> Dict[str, Any]:
    need_dir(files, "--files")
    if not tenant:
        raise InputError("export needs --tenant: a bundle with no tenant would import into any tenant")
    if os.path.exists(out) and (not os.path.isdir(out) or os.listdir(out)):
        raise InputError("--out must not exist or must be an empty directory: %s" % out)
    entries = scan_files(files)
    conn = open_ro(db)
    try:
        sql = "\n".join(conn.iterdump()) + "\n"
        snap = snapshot(conn)
    finally:
        conn.close()
    stage = tempfile.mkdtemp(prefix="bundle-")
    try:
        sql_bytes = sql.encode("utf-8")
        with open(os.path.join(stage, DB_ARTIFACT), "wb") as fh:
            fh.write(sql_bytes)
        file_list = make_tar(files, entries, os.path.join(stage, TAR_ARTIFACT))
        tar_path = os.path.join(stage, TAR_ARTIFACT)
        manifest = {
            "format_version": FORMAT_VERSION,
            "tenant": tenant,
            "artifacts": {
                DB_ARTIFACT: {"sha256": sha256_bytes(sql_bytes), "size": len(sql_bytes), "format": SQL_FORMAT},
                TAR_ARTIFACT: {"sha256": sha256_file(tar_path), "size": os.path.getsize(tar_path), "format": TAR_FORMAT},
            },
            "tables": snap["tables"],
            "database_checksum": snap["database_checksum"],
            "files": file_list,
            "directories": [rel for rel, kind in entries if kind == "dir"],
            "tool": {"name": "data_migration.py", "python": "%d.%d.%d" % sys.version_info[:3], "sqlite": sqlite3.sqlite_version},
            "limitations": LIMITS,
        }
        write_json(os.path.join(stage, MANIFEST), manifest)
        if os.path.isdir(out):
            os.rmdir(out)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        shutil.move(stage, out)
        stage = ""
    finally:
        if stage:
            shutil.rmtree(stage, ignore_errors=True)
    manifest_sha = sha256_file(os.path.join(out, MANIFEST))
    ledger_append(ledger, {"kind": "export", "tenant": tenant, "manifest_sha256": manifest_sha,
                           "database_checksum": snap["database_checksum"]})
    return {"verdict": "exported", "bundle": out, "tenant": tenant, "manifest_sha256": manifest_sha, "ledger": ledger,
            "database_checksum": snap["database_checksum"], "tables": snap["tables"], "file_count": len(file_list),
            "assumptions": LIMITS}


# ------------------------------------------------------------------ import

def _check_manifest(manifest: Dict[str, Any]) -> None:
    if manifest.get("format_version") != FORMAT_VERSION:
        raise InputError("manifest format_version must be %d" % FORMAT_VERSION)
    arts = manifest.get("artifacts")
    if not isinstance(arts, dict) or not {DB_ARTIFACT, TAR_ARTIFACT} <= set(arts):
        raise InputError("manifest 'artifacts' must describe %s and %s" % (DB_ARTIFACT, TAR_ARTIFACT))
    for name in (DB_ARTIFACT, TAR_ARTIFACT):
        a = arts[name]
        if not (isinstance(a, dict) and isinstance(a.get("sha256"), str) and isinstance(a.get("size"), int)):
            raise InputError("manifest artifact %s needs sha256 and size" % name)
    if not isinstance(manifest.get("tables"), dict) or not isinstance(manifest.get("database_checksum"), str):
        raise InputError("manifest needs 'tables' and 'database_checksum'")
    if not isinstance(manifest.get("files"), list):
        raise InputError("manifest needs a 'files' list")


def _safe_members(tar_path: str) -> List[tarfile.TarInfo]:
    try:
        with tarfile.open(tar_path, "r") as tar:
            members = tar.getmembers()
    except (tarfile.TarError, OSError) as exc:
        raise Refused("files.tar cannot be read: %s" % exc)
    for m in members:
        parts = m.name.split("/")
        if m.name.startswith("/") or ".." in parts or "" in parts or not (m.isfile() or m.isdir()):
            raise Refused("files.tar holds an unsafe entry: %r" % m.name)
    return members


def _authorizer(action: int, arg1: Any, arg2: Any, dbname: Any, source: Any) -> int:
    if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH):
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_PRAGMA and str(arg1).lower() != "foreign_keys":
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def _allow_all(action: int, arg1: Any, arg2: Any, dbname: Any, source: Any) -> int:
    return sqlite3.SQLITE_OK


def import_bundle(bundle: str, db: str, files_dest: str, tenant: Optional[str], ledger: str) -> Dict[str, Any]:
    need_dir(bundle, "--bundle")
    if not tenant:
        raise InputError("import needs --tenant, the tenant the data is going to")
    manifest = load_json(os.path.join(bundle, MANIFEST), "manifest")
    _check_manifest(manifest)
    manifest_sha = sha256_file(os.path.join(bundle, MANIFEST))
    exported = next((r for r in reversed(ledger_records(ledger, "export")) if r.get("manifest_sha256") == manifest_sha), None)
    if exported is None:
        raise Refused("the manifest's sha256 %s matches no export in the owner's ledger; the bundle was edited, relabeled "
                      "or exported elsewhere; nothing was written" % manifest_sha)
    if os.path.exists(db):
        raise Refused("destination database already exists: %s" % db)
    if os.path.exists(files_dest) and (not os.path.isdir(files_dest) or os.listdir(files_dest)):
        raise Refused("files destination exists and is not empty: %s" % files_dest)
    for name, art in sorted(manifest["artifacts"].items()):
        path = os.path.join(bundle, name)
        if name not in (DB_ARTIFACT, TAR_ARTIFACT) or not os.path.isfile(path):
            raise Refused("artifact missing from the bundle: %s" % name)
        if os.path.getsize(path) != art["size"] or sha256_file(path) != art["sha256"]:
            raise Refused("artifact %s does not match the manifest hash; nothing was written" % name)
    if exported.get("tenant") != tenant or manifest.get("tenant") != tenant:
        raise Refused("bundle belongs to %s, not %s" % (exported.get("tenant"), tenant))
    tar_path = os.path.join(bundle, TAR_ARTIFACT)
    members = _safe_members(tar_path)

    stage = tempfile.mkdtemp(prefix="import-")
    try:
        stage_db, stage_files = os.path.join(stage, "restored.sqlite"), os.path.join(stage, "files")
        try:
            with open(os.path.join(bundle, DB_ARTIFACT), encoding="utf-8") as fh:
                sql = fh.read()
        except UnicodeDecodeError:
            raise Refused("database.sql is not UTF-8 text; nothing was written")
        conn = sqlite3.connect(stage_db)
        try:
            conn.set_authorizer(_authorizer)
            conn.executescript(sql)
            conn.set_authorizer(_allow_all)  # set_authorizer(None) only clears it from Python 3.11
            restored = snapshot(conn)
        except sqlite3.Error as exc:
            raise Refused("database.sql was rejected: %s; nothing was written" % exc)
        finally:
            conn.close()
        mismatches = []
        for name in sorted(set(manifest["tables"]) | set(restored["tables"])):
            if manifest["tables"].get(name) != restored["tables"].get(name):
                mismatches.append({"table": name, "manifest": manifest["tables"].get(name), "restored": restored["tables"].get(name)})
        if restored["database_checksum"] != manifest["database_checksum"] and not mismatches:
            mismatches.append({"table": "(schema)", "manifest": manifest["database_checksum"], "restored": restored["database_checksum"]})
        os.makedirs(stage_files)
        with tarfile.open(tar_path, "r") as tar:
            for m in members:
                target = os.path.join(stage_files, *m.name.split("/"))
                if m.isdir():
                    os.makedirs(target, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with open(target, "wb") as out, tar.extractfile(m) as src:
                        shutil.copyfileobj(src, out)
        expected = {f["path"]: f["sha256"] for f in manifest["files"]}
        got = {rel: sha256_file(os.path.join(stage_files, *rel.split("/"))) for rel, kind in scan_files(stage_files) if kind == "file"}
        if got != expected:
            mismatches.append({"table": "(files)", "manifest": sorted(expected), "restored": sorted(got)})
        if mismatches:
            return {"verdict": "mismatch", "mismatches": mismatches, "assumptions": LIMITS}
        os.makedirs(os.path.dirname(os.path.abspath(db)), exist_ok=True)
        os.makedirs(os.path.dirname(os.path.abspath(files_dest)), exist_ok=True)
        shutil.move(stage_db, db)
        if os.path.isdir(files_dest):
            os.rmdir(files_dest)
        shutil.move(stage_files, files_dest)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return {"verdict": "imported", "database_checksum": restored["database_checksum"], "tables": restored["tables"],
            "file_count": len(got), "tenant": exported["tenant"], "manifest_sha256": manifest_sha, "assumptions": LIMITS}


TAMPER_TARGETS = (DB_ARTIFACT, TAR_ARTIFACT)


def roundtrip(seed: str, files: str, tenant: Optional[str], workdir: Optional[str],
              tamper: Optional[str] = None) -> Dict[str, Any]:
    need_dir(files, "--files")
    own = workdir is None
    work = workdir or tempfile.mkdtemp(prefix="roundtrip-")
    try:
        os.makedirs(work, exist_ok=True)
        src_db = os.path.join(work, "source.sqlite")
        build_seed_db(seed, src_db)
        before = db_snapshot(src_db)
        ledger = os.path.join(work, "owner", "ledger.jsonl")
        export_bundle(src_db, files, os.path.join(work, "bundle"), tenant, ledger)
        if tamper:
            with open(os.path.join(work, "bundle", tamper), "ab") as fh:
                fh.write(b"\n")
        new_root = os.path.join(work, "new")
        try:
            res = import_bundle(os.path.join(work, "bundle"), os.path.join(new_root, "restored.sqlite"),
                                os.path.join(new_root, "files"), tenant, ledger)
        except Refused as exc:
            res = exc.result
        if res.get("verdict") != "imported":
            return {"verdict": "fail", "import": res, "tampered": tamper,
                    "nothing_written": not os.path.exists(new_root) or not os.listdir(new_root),
                    "assumptions": LIMITS}
        after = db_snapshot(os.path.join(work, "new", "restored.sqlite"))
        want = {rel: sha256_file(os.path.join(files, *rel.split("/"))) for rel, k in scan_files(files) if k == "file"}
        have = {rel: sha256_file(os.path.join(work, "new", "files", *rel.split("/"))) for rel, k in scan_files(os.path.join(work, "new", "files")) if k == "file"}
        checks = {"database_checksum_equal": before["database_checksum"] == after["database_checksum"],
                  "table_checksums_equal": before["tables"] == after["tables"], "files_equal": want == have}
        return {"verdict": "pass" if all(checks.values()) else "fail", "checks": checks, "tables": after["tables"],
                "database_checksum": after["database_checksum"], "file_count": len(have), "tenant": tenant,
                "assumptions": LIMITS}
    finally:
        if own:
            shutil.rmtree(work, ignore_errors=True)


# --------------------------------------------------------------- migration

DIRECTIVES = {"expect-table", "expect-no-table", "expect-column", "expect-rows-unchanged", "expect-rows"}


def parse_migration(path: str) -> Tuple[List[str], List[Tuple[str, Any]]]:
    if not os.path.isfile(path):
        raise InputError("migration file not found: %s" % path)
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except UnicodeDecodeError:
        raise InputError("migration file is not UTF-8 text: %s" % path)
    expects: List[Tuple[str, Any]] = []
    statements: List[str] = []
    buf = ""
    for number, line in enumerate(lines, 1):
        m = re.match(r"^--\s*(expect-[a-z-]+)\s*:\s*(.+?)\s*$", line)
        if not m and not buf and re.match(r"^--\s*expect", line, re.IGNORECASE):
            raise InputError("line %d looks like a directive but is malformed (lowercase, then a colon): %r" % (number, line))
        if m and not buf:
            kind, arg = m.group(1), m.group(2)
            if kind not in DIRECTIVES:
                raise InputError("unknown directive %r" % kind)
            items = [a.strip() for a in arg.split(",") if a.strip()]
            if not items:
                raise InputError("%s needs an argument" % kind)
            for item in items:
                if kind == "expect-column" and not re.match(r"^\w+\.\w+$", item):
                    raise InputError("expect-column needs table.column, got %r" % item)
                if kind == "expect-rows" and not re.match(r"^\w+=\d+$", item):
                    raise InputError("expect-rows needs table=N, got %r" % item)
                expects.append((kind, item))
            continue
        if not buf and (not line.strip() or line.strip().startswith("--")):
            continue
        buf += line + "\n"
        if sqlite3.complete_statement(buf):
            statements.append(buf.strip())
            buf = ""
    if buf.strip():
        raise InputError("migration ends with an incomplete statement")
    if not statements:
        raise InputError("migration holds no statements")
    if not expects:
        raise InputError("migration states no expect- directive; say what must hold afterward")
    return statements, expects


ROW_DIRECTIVES = {"expect-rows-unchanged", "expect-rows", "expect-no-table"}


def _rows_digest(conn: sqlite3.Connection, table: str, cols: List[str]) -> Optional[str]:
    """Checksum of the table's rows over the given columns, independent of row order. None if a column is gone."""
    quoted = ", ".join('"%s"' % c.replace('"', '""') for c in cols)
    try:
        rows = sorted(json.dumps([_enc(v) for v in r]) for r in conn.execute('SELECT %s FROM "%s"' % (quoted, table.replace('"', '""'))))
    except sqlite3.Error:
        return None
    return sha256_bytes("\n".join(rows).encode("utf-8"))


def _count(conn: sqlite3.Connection, table: str) -> Optional[int]:
    try:
        return conn.execute('SELECT count(*) FROM "%s"' % table.replace('"', '""')).fetchone()[0]
    except sqlite3.Error:
        return None


def evaluate(conn: sqlite3.Connection, expects: List[Tuple[str, Any]], before: Dict[str, Tuple[int, List[str], Optional[str]]]) -> List[Dict[str, Any]]:
    results = []
    for kind, item in expects:
        if kind in ("expect-table", "expect-no-table"):
            exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (item,)).fetchone() is not None
            ok, detail = exists == (kind == "expect-table"), "table %s %s" % (item, "exists" if exists else "is absent")
        elif kind == "expect-column":
            table, col = item.split(".")
            cols = [r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)]
            ok, detail = col in cols, "columns of %s: %s" % (table, cols)
        elif kind == "expect-rows-unchanged":
            now = _count(conn, item)
            cols, digest = before.get(item, (None, None, None))[1:] if item in before else (None, None)
            after = _rows_digest(conn, item, cols) if cols else None
            ok = now is not None and now == before.get(item, (None,))[0] and after is not None and after == digest
            detail = "%s rows before %s, after %s; content over the original columns %s" % (
                item, before.get(item, (None,))[0], now, "unchanged" if ok else "changed")
        else:
            table, want = item.split("=")
            now = _count(conn, table)
            ok, detail = now == int(want), "%s rows expected %s, found %s" % (table, want, now)
        results.append({"directive": kind, "arg": item, "ok": bool(ok), "detail": detail})
    return results


def _next_backup_name(backup_dir: str) -> str:
    seqs = [int(m.group(1)) for f in os.listdir(backup_dir) for m in [re.match(r"^backup-(\d{4})\.sqlite$", f)] if m]
    return "backup-%04d" % (max(seqs) + 1 if seqs else 1)


def take_backup(db: str, backup_dir: str, ledger: str) -> Dict[str, Any]:
    os.makedirs(backup_dir, exist_ok=True)
    name = _next_backup_name(backup_dir)
    path = os.path.join(backup_dir, name + ".sqlite")
    src, dst = sqlite3.connect(db), sqlite3.connect(path)
    try:
        src.backup(dst)
        live = snapshot(src)
    finally:
        dst.close()
        src.close()
    saved = db_snapshot(path)
    if saved["database_checksum"] != live["database_checksum"]:
        os.remove(path)
        raise Refused("backup did not match the database; nothing was changed")
    meta = {"name": name, "file": name + ".sqlite", "file_sha256": sha256_file(path), "db": os.path.realpath(db),
            "content_checksum": saved["database_checksum"], "tables": saved["tables"]}
    write_json(os.path.join(backup_dir, name + ".json"), meta)
    ledger_append(ledger, {"kind": "backup", "db": meta["db"], "backup_dir": os.path.realpath(backup_dir), "name": name,
                           "file_sha256": meta["file_sha256"], "content_checksum": meta["content_checksum"]})
    return meta


def restore_backup(db: str, backup_dir: str, meta: Dict[str, Any]) -> str:
    src, dst = sqlite3.connect(os.path.join(backup_dir, meta["file"])), sqlite3.connect(db)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return db_snapshot(db)["database_checksum"]


def migrate(db: str, migration: str, backup_dir: str, ledger: str) -> Dict[str, Any]:
    if not os.path.isfile(db):
        raise InputError("database not found: %s" % db)
    statements, expects = parse_migration(migration)
    probe = open_ro(db)
    try:
        pre = snapshot(probe)
        before = {}
        for name, info in pre["tables"].items():
            cols = [r[1] for r in probe.execute('PRAGMA table_info("%s")' % name.replace('"', '""'))]
            before[name] = (info["rows"], cols, _rows_digest(probe, name, cols))
    finally:
        probe.close()
    named = {item.split("=")[0] for kind, item in expects if kind in ROW_DIRECTIVES}
    unstated = sorted(set(before) - named)
    if unstated:
        raise Refused("the migration states nothing about the rows of %s; add expect-rows-unchanged, expect-rows or "
                      "expect-no-table for each existing table; nothing was changed" % ", ".join(unstated))
    backup = take_backup(db, backup_dir, ledger)
    reason, failed_at, post = None, None, []
    conn = sqlite3.connect(db, isolation_level=None)
    try:
        conn.execute("BEGIN")
        conn.set_authorizer(_authorizer)  # no ATTACH, DETACH (so no VACUUM INTO) or pragma but foreign_keys: one database only
        try:
            for i, stmt in enumerate(statements, 1):
                try:
                    conn.execute(stmt)
                except (sqlite3.Error, sqlite3.Warning) as exc:
                    reason, failed_at = "statement %d failed: %s" % (i, exc), i
                    break
                if not conn.in_transaction:
                    reason, failed_at = "statement %d ended the transaction; a migration must not COMMIT or ROLLBACK" % i, i
                    break
        finally:
            conn.set_authorizer(_allow_all)  # set_authorizer(None) only clears it from Python 3.11
        if reason is None:
            post = evaluate(conn, expects, before)
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            post.append({"directive": "integrity-check", "arg": "", "ok": integrity == "ok", "detail": integrity})
            failed = [p for p in post if not p["ok"]]
            if failed:
                reason = "post-condition failed: %s %s (%s)" % (failed[0]["directive"], failed[0]["arg"], failed[0]["detail"])
        if reason is None:
            conn.execute("COMMIT")
        elif conn.in_transaction:
            conn.execute("ROLLBACK")
    finally:
        conn.close()
    common = {"backup": {k: backup[k] for k in ("name", "file", "file_sha256", "content_checksum")}, "postconditions": post,
              "pre_checksum": pre["database_checksum"], "statements": len(statements), "assumptions": LIMITS}
    if reason is None:
        post_checksum = db_snapshot(db)["database_checksum"]
        ledger_append(ledger, {"kind": "migrated", "db": os.path.realpath(db), "backup_dir": os.path.realpath(backup_dir),
                               "backup": backup["name"], "post_checksum": post_checksum})
        return dict(common, verdict="migrated", post_checksum=post_checksum)
    restored = restore_backup(db, backup_dir, backup)
    equal = restored == pre["database_checksum"]
    return dict(common, verdict="rolled-back" if equal else "rollback-failed", reason=reason, failed_statement=failed_at,
                restored_checksum=restored, checksums_equal=equal)


def rollback(db: str, backup_dir: str, name: Optional[str], ledger: str) -> Dict[str, Any]:
    if not os.path.isfile(db):
        raise InputError("database not found: %s" % db)
    need_dir(backup_dir, "--backup-dir")
    mine = [r for r in ledger_records(ledger, "backup")
            if r.get("db") == os.path.realpath(db) and r.get("backup_dir") == os.path.realpath(backup_dir)]
    if not mine:
        raise Refused("the owner's ledger holds no backup of %s in %s; a backup taken from another database is never "
                      "restored here; the database was not touched" % (db, backup_dir))
    meta = next((r for r in reversed(mine) if r["name"] == name), None) if name else mine[-1]
    if meta is None:
        raise InputError("no backup %s of this database in the ledger" % name)
    chosen = meta["name"]
    meta = dict(meta, file=chosen + ".sqlite")
    path = os.path.join(backup_dir, meta["file"])
    if not os.path.isfile(path):
        raise InputError("backup file not found: %s" % path)
    if sha256_file(path) != meta.get("file_sha256"):
        raise Refused("backup %s does not match the hash in the owner's ledger; the database was not touched" % chosen)
    before = db_snapshot(db)["database_checksum"]
    left = next((r for r in reversed(ledger_records(ledger, "migrated")) if (r.get("db"), r.get("backup_dir"), r.get("backup"))
                 == (meta["db"], meta["backup_dir"], chosen)), None)
    known = {meta.get("content_checksum")} | ({left.get("post_checksum")} if left else set())
    if before not in known:
        raise Refused("db-changed-since-migration: the database at %s (checksum %s) is neither the one migrating it left nor "
                      "the backup itself, so it is another database or has taken writes since; restoring %s could destroy "
                      "them; the database was not touched" % (db, before, chosen), refusal="db-changed-since-migration")
    restored = restore_backup(db, backup_dir, meta)
    ok = restored == meta.get("content_checksum")
    return {"verdict": "restored" if ok else "rollback-failed", "backup": chosen, "checksum_before": before,
            "restored_checksum": restored, "expected_checksum": meta.get("content_checksum"), "checksums_equal": ok,
            "assumptions": LIMITS}


# -------------------------------------------------------------------- main

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("preflight")
    a.add_argument("--app", required=True)
    a.add_argument("--target", required=True)
    e = sub.add_parser("export")
    e.add_argument("--db")
    e.add_argument("--seed")
    e.add_argument("--files", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--tenant")
    e.add_argument("--ledger", help="refused unless it is the owner's fixed ledger; export finds it itself")
    i = sub.add_parser("import")
    i.add_argument("--bundle", required=True)
    i.add_argument("--db", required=True)
    i.add_argument("--files-dest", required=True)
    i.add_argument("--tenant")
    i.add_argument("--ledger", help="refused unless it is the owner's fixed ledger")
    m = sub.add_parser("migrate")
    m.add_argument("--db")
    m.add_argument("--seed", help="build a throwaway database from this SQL seed and migrate that")
    m.add_argument("--migration", required=True)
    m.add_argument("--backup-dir", help="required with --db; a temp folder with --seed")
    m.add_argument("--ledger", help="refused unless it is the owner's fixed ledger")
    r = sub.add_parser("rollback")
    r.add_argument("--db", required=True)
    r.add_argument("--backup-dir", required=True)
    r.add_argument("--backup")
    r.add_argument("--ledger", help="refused unless it is the owner's fixed ledger")
    t = sub.add_parser("roundtrip")
    t.add_argument("--seed", required=True)
    t.add_argument("--files", required=True)
    t.add_argument("--tenant")
    t.add_argument("--workdir")
    t.add_argument("--tamper", choices=TAMPER_TARGETS,
                   help="test hook: append one byte to this bundle artifact before import, to prove import refuses it")
    return p


def run(args: argparse.Namespace) -> Tuple[Dict[str, Any], int]:
    if args.cmd == "preflight":
        res = preflight(args.app, args.target)
        return res, 0 if res["verdict"] == "compatible" else 1
    if args.cmd == "export":
        if bool(args.db) == bool(args.seed):
            raise InputError("pass exactly one of --db and --seed")
        if args.seed:
            tmp = tempfile.mkdtemp(prefix="seed-")
            try:
                build_seed_db(args.seed, os.path.join(tmp, "seed.sqlite"))
                return export_bundle(os.path.join(tmp, "seed.sqlite"), args.files, args.out, args.tenant,
                                     owner_ledger(args.ledger, args.out)), 0
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        return export_bundle(args.db, args.files, args.out, args.tenant, owner_ledger(args.ledger, args.out)), 0
    if args.cmd == "import":
        res = import_bundle(args.bundle, args.db, args.files_dest, args.tenant, owner_ledger(args.ledger, args.bundle))
        return res, 0 if res["verdict"] == "imported" else 1
    if args.cmd == "migrate":
        if bool(args.db) == bool(args.seed):
            raise InputError("pass exactly one of --db and --seed")
        if args.db:
            if not args.backup_dir:
                raise InputError("--backup-dir is required with --db")
            res = migrate(args.db, args.migration, args.backup_dir, owner_ledger(args.ledger, args.backup_dir))
        else:
            tmp = tempfile.mkdtemp(prefix="migrate-")
            try:
                build_seed_db(args.seed, os.path.join(tmp, "site.sqlite"))
                res = migrate(os.path.join(tmp, "site.sqlite"), args.migration, os.path.join(tmp, "backups"),
                              os.path.join(tmp, "owner", "ledger.jsonl"))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        return res, 0 if res["verdict"] == "migrated" else 1
    if args.cmd == "rollback":
        res = rollback(args.db, args.backup_dir, args.backup, owner_ledger(args.ledger, args.backup_dir))
        return res, 0 if res["verdict"] == "restored" else 1
    res = roundtrip(args.seed, args.files, args.tenant, args.workdir, args.tamper)
    return res, 0 if res["verdict"] == "pass" else 1


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result, code = run(args)
    except InputError as exc:
        print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True))
        return 2
    except Refused as exc:
        print(json.dumps(exc.result, indent=2, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
