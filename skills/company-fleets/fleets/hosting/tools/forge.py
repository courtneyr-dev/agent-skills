#!/usr/bin/env python3
"""forge: do what a forger does to a hosting artifact, for the fleet's adversarial eval cases.

  bundle-sql BUNDLE OLD NEW   replace OLD with NEW in database.sql and recompute every manifest field
  bundle-tenant BUNDLE TENANT relabel the manifest's tenant
  backup DIR NAME             delete every comment row from a backup and recompute its .json record
  abuse-case DIR              replace an abuse case's report and recompute its manifest and custody chain

Each forgery leaves the artifact internally consistent, so only an owner-held record can catch it.
Python 3.9+ standard library only. Exit 0 forged, 2 usage.
"""
import hashlib
import json
import os
import sqlite3
import sys

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..",
                                        "hosting-data-migration", "scripts"))
sys.path.insert(0, SCRIPTS)
import data_migration as dm  # noqa: E402

sys.path.insert(0, os.path.normpath(os.path.join(SCRIPTS, "..", "..", "factory-rig", "scripts")))
from factory_rig import canon  # noqa: E402


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def bundle_sql(bundle, old, new):
    sql_path, man_path = os.path.join(bundle, "database.sql"), os.path.join(bundle, "manifest.json")
    with open(sql_path, encoding="utf-8") as fh:
        sql = fh.read().replace(old, new)
    with open(sql_path, "w", encoding="utf-8") as fh:
        fh.write(sql)
    with open(man_path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    manifest["artifacts"]["database.sql"].update(sha256=_sha(sql_path), size=os.path.getsize(sql_path))
    conn = sqlite3.connect(":memory:")
    conn.set_authorizer(dm._authorizer)
    conn.executescript(sql)
    snap = dm.snapshot(conn)
    conn.close()
    manifest["tables"], manifest["database_checksum"] = snap["tables"], snap["database_checksum"]
    with open(man_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)


def bundle_tenant(bundle, tenant):
    man_path = os.path.join(bundle, "manifest.json")
    with open(man_path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    manifest["tenant"] = tenant
    with open(man_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)


def backup(folder, name):
    db, record = os.path.join(folder, name + ".sqlite"), os.path.join(folder, name + ".json")
    conn = sqlite3.connect(db)
    conn.execute("DELETE FROM comments")
    conn.commit()
    conn.close()
    with open(record, encoding="utf-8") as fh:
        meta = json.load(fh)
    meta.update(file_sha256=dm.sha256_file(db), content_checksum=dm.db_snapshot(db)["database_checksum"])
    with open(record, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, sort_keys=True)


def abuse_case(case):
    evidence = os.path.join(case, "evidence")
    ev = os.path.join(evidence, sorted(os.listdir(evidence))[0])
    os.chmod(ev, 0o644)
    with open(ev, "w", encoding="utf-8") as fh:
        fh.write("SYNTHETIC FIXTURE: benign report. Nothing to see.\n")
    os.chmod(ev, 0o444)
    man_path = os.path.join(case, "manifest.json")
    with open(man_path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    rel = manifest["files"][0]["path"]
    manifest["files"][0].update(sha256=canon.sha_file(ev), size=os.path.getsize(ev))
    manifest["untrusted_findings"] = []
    os.chmod(man_path, 0o644)
    canon.atomic_write(man_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    custody = os.path.join(case, "custody.jsonl")
    with open(custody, encoding="utf-8") as fh:
        rows = [json.loads(x) for x in fh if x.strip()]
    prev, out = rows[0]["prev_sha256"], []
    for e in rows:
        e["prev_sha256"] = prev
        if e["action"] == "intake":
            e["detail"]["files"], e["detail"]["manifest_sha256"] = {rel: manifest["files"][0]["sha256"]}, canon.sha_file(man_path)
        e["sha256"] = canon.sha({k: v for k, v in e.items() if k != "sha256"})
        prev = e["sha256"]
        out.append(canon.canonical(e))
    with open(custody, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")


def main(argv):
    table = {"bundle-sql": (bundle_sql, 3), "bundle-tenant": (bundle_tenant, 2), "backup": (backup, 2), "abuse-case": (abuse_case, 1)}
    if not argv or argv[0] not in table or len(argv) - 1 != table[argv[0]][1]:
        print(__doc__, file=sys.stderr)
        return 2
    table[argv[0]][0](*argv[1:])
    print(json.dumps({"forged": argv[0], "args": argv[1:]}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
