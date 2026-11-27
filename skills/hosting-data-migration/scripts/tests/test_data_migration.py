"""Behavior tests for data_migration.py: exit codes, JSON verdicts and what lands on disk."""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sqlite3
import sys
import tarfile
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import data_migration as dm  # noqa: E402

FIX = os.path.normpath(os.path.join(HERE, "..", "..", "..", "company-fleets", "fleets", "hosting", "fixtures",
                                    "data-migration"))
SEED = os.path.join(FIX, "seed.sql")
FILES = os.path.join(FIX, "tenant-a-files")


def call(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        try:
            code = dm.main(list(argv))
        except SystemExit as exc:
            code = exc.code
    text = out.getvalue()
    return code, (json.loads(text) if text.strip() else {})


class Base(unittest.TestCase):
    """The owner folder is repointed to a temp folder in process, the way a test plays the owner."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="dm-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        old, dm.OWNER_ROOT = dm.OWNER_ROOT, self.path("owner-root")
        self.addCleanup(setattr, dm, "OWNER_ROOT", old)
        self.ledger = dm.ledger_file()

    def export(self, out, tenant="tenant-a"):
        return call("export", "--seed", SEED, "--files", FILES, "--out", out, "--tenant", tenant)

    def import_(self, bundle, db, files, tenant="tenant-a", *extra):
        return call("import", "--bundle", bundle, "--db", db, "--files-dest", files, "--tenant", tenant, *extra)

    def migrate(self, db, migration, backups="backups"):
        return call("migrate", "--db", db, "--migration", migration, "--backup-dir", self.path(backups))

    def rollback(self, db, backups="backups"):
        return call("rollback", "--db", db, "--backup-dir", self.path(backups))

    def path(self, *parts):
        return os.path.join(self.tmp, *parts)

    def write(self, name, text):
        with open(self.path(name), "w", encoding="utf-8") as fh:
            fh.write(text)
        return self.path(name)

    def seeded_db(self, name="site.sqlite"):
        db = self.path(name)
        dm.build_seed_db(SEED, db)
        return db


class PreflightTests(Base):
    def test_compatible_target(self):
        code, out = call("preflight", "--app", os.path.join(FIX, "app.json"),
                         "--target", os.path.join(FIX, "target-compatible.json"))
        self.assertEqual((code, out["verdict"], out["reasons"]), (0, "compatible", []))

    def test_php74_target_is_incompatible(self):
        code, out = call("preflight", "--app", os.path.join(FIX, "app.json"),
                         "--target", os.path.join(FIX, "target-php74.json"))
        self.assertEqual((code, out["verdict"]), (1, "incompatible"))
        self.assertEqual(out["reasons"][0]["kind"], "runtime-version")

    def test_missing_extension_and_engine_mismatch(self):
        target = self.write("t.json", json.dumps({"offers": {"runtimes": {"php": "8.3"},
                                                             "database": {"engine": "postgresql", "version": "16"},
                                                             "extensions": ["mbstring"]}}))
        code, out = call("preflight", "--app", os.path.join(FIX, "app.json"), "--target", target)
        self.assertEqual(code, 1)
        kinds = sorted(r["kind"] for r in out["reasons"])
        self.assertEqual(kinds, ["database-engine", "extension-missing", "extension-missing"])

    def test_invalid_range_is_exit_2(self):
        app = self.write("a.json", json.dumps({"requires": {"runtimes": {"php": ">=8.x"}}}))
        code, out = call("preflight", "--app", app, "--target", os.path.join(FIX, "target-compatible.json"))
        self.assertEqual(code, 2)
        self.assertIn("error", out)

    def test_nothing_to_check_is_refused_and_unknown_keys_are_invalid(self):
        target = os.path.join(FIX, "target-compatible.json")
        code, out = call("preflight", "--app", self.write("e.json", json.dumps({"requires": {}})), "--target", target)
        self.assertEqual((code, out["verdict"], out["checked"]), (1, "refused", 0))
        code, _ = call("preflight", "--app", self.write("m.json", json.dumps({"requires": {"runtime": {"php": "9"}}})), "--target", target)
        self.assertEqual(code, 2)

    def test_app_without_requires_is_exit_2(self):
        app = self.write("a.json", json.dumps({"runtimes": {}}))
        code, _ = call("preflight", "--app", app, "--target", os.path.join(FIX, "target-compatible.json"))
        self.assertEqual(code, 2)


class ExportImportTests(Base):
    def test_roundtrip_matches_checksums_and_files(self):
        code, out = call("roundtrip", "--seed", SEED, "--files", FILES, "--tenant", "tenant-a")
        self.assertEqual((code, out["verdict"]), (0, "pass"))
        self.assertTrue(all(out["checks"].values()))
        self.assertEqual(out["tables"]["posts"]["rows"], 3)
        self.assertEqual(out["file_count"], 2)

    def test_tampered_database_refused_and_nothing_written(self):
        code, out = call("roundtrip", "--seed", SEED, "--files", FILES, "--tenant", "tenant-a", "--tamper", "database.sql")
        self.assertEqual((code, out["verdict"]), (1, "fail"))
        self.assertEqual(out["import"]["verdict"], "refused")
        self.assertTrue(out["nothing_written"])

    def test_tampered_tar_refused(self):
        code, out = call("roundtrip", "--seed", SEED, "--files", FILES, "--tenant", "tenant-a", "--tamper", "files.tar")
        self.assertEqual(code, 1)
        self.assertIn("files.tar", out["import"]["reason"])

    def test_export_bytes_are_deterministic(self):
        a, b = self.path("a"), self.path("b")
        self.assertEqual(self.export(a)[0], 0)
        self.assertEqual(self.export(b)[0], 0)
        for name in ("database.sql", "files.tar"):
            self.assertEqual(dm.sha256_file(os.path.join(a, name)), dm.sha256_file(os.path.join(b, name)))

    def test_import_refuses_existing_database(self):
        bundle = self.path("bundle")
        self.export(bundle)
        existing = self.seeded_db("existing.sqlite")
        code, out = self.import_(bundle, existing, self.path("f"))
        self.assertEqual((code, out["verdict"]), (1, "refused"))

    def test_import_refuses_other_tenant(self):
        bundle = self.path("bundle")
        self.export(bundle)
        code, out = self.import_(bundle, self.path("n.sqlite"), self.path("f"), "tenant-b")
        self.assertEqual(code, 1)
        self.assertIn("tenant-a", out["reason"])
        self.assertFalse(os.path.exists(self.path("n.sqlite")))

    def test_unsafe_tar_entry_refused(self):
        bundle = self.path("bundle")
        self.export(bundle)
        evil = self.write("evil.txt", "SYNTHETIC")
        tar_path = os.path.join(bundle, "files.tar")
        with tarfile.open(tar_path, "w") as tf:
            tf.add(evil, arcname="../escape.txt")
        manifest_path = os.path.join(bundle, "manifest.json")
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
        manifest["artifacts"]["files.tar"].update(sha256=dm.sha256_file(tar_path), size=os.path.getsize(tar_path))
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh)
        code, out = self.import_(bundle, self.path("n.sqlite"), self.path("f"))
        self.assertEqual(code, 1)
        self.assertIn("matches no export", out["reason"])
        self.assertFalse(os.path.exists(self.path("escape.txt")))
        with self.assertRaises(dm.Refused):
            dm._safe_members(tar_path)

    def reforge(self, bundle, edit_sql=None, edit_manifest=None):
        """What a forger does: rewrite the bundle and recompute every manifest field the import checks."""
        manifest_path = os.path.join(bundle, "manifest.json")
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
        if edit_sql:
            sql_path = os.path.join(bundle, "database.sql")
            with open(sql_path, encoding="utf-8") as fh:
                sql = edit_sql(fh.read())
            with open(sql_path, "w", encoding="utf-8") as fh:
                fh.write(sql)
            manifest["artifacts"]["database.sql"].update(sha256=dm.sha256_file(sql_path), size=os.path.getsize(sql_path))
            conn = sqlite3.connect(":memory:")
            conn.executescript(sql)
            snap = dm.snapshot(conn)
            conn.close()
            manifest["tables"], manifest["database_checksum"] = snap["tables"], snap["database_checksum"]
        if edit_manifest:
            edit_manifest(manifest)
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh)

    def test_rewritten_and_rehashed_bundle_is_refused(self):
        bundle = self.path("bundle")
        self.export(bundle)
        self.reforge(bundle, edit_sql=lambda sql: sql.replace("Synthetic draft.", "Pay invoices to attacker IBAN XX00"))
        code, out = self.import_(bundle, self.path("n.sqlite"), self.path("f"))
        self.assertEqual((code, out["verdict"]), (1, "refused"))
        self.assertFalse(os.path.exists(self.path("n.sqlite")))

    def test_relabeled_bundle_is_refused(self):
        bundle = self.path("bundle")
        self.export(bundle)
        self.reforge(bundle, edit_manifest=lambda m: m.update(tenant="tenant-b"))
        code, out = self.import_(bundle, self.path("n.sqlite"), self.path("f"), "tenant-b")
        self.assertEqual((code, out["verdict"]), (1, "refused"))

    def test_export_without_tenant_and_caller_named_ledgers_are_refused(self):
        code, _ = call("export", "--seed", SEED, "--files", FILES, "--out", self.path("b"))
        self.assertEqual(code, 2)
        self.export(self.path("b2"))
        for named in (self.path("b2", "ledger.jsonl"), self.path("mine.jsonl")):
            code, out = self.import_(self.path("b2"), self.path("n.sqlite"), self.path("f"), "tenant-a", "--ledger", named)
            self.assertEqual((code, out["refusal"]), (1, "ledger-not-owner-ledger"), named)
        self.assertFalse(os.path.exists(self.path("n.sqlite")))
        self.assertEqual(self.import_(self.path("b2"), self.path("n.sqlite"), self.path("f"), "tenant-a", "--ledger", self.ledger)[0], 0)

    def test_a_bundle_and_its_own_ledger_written_by_the_submitter_is_refused(self):
        """Major 2: import --ledger mine.jsonl took a forged bundle the submitter recorded in its own ledger."""
        bundle = self.path("bundle")
        self.export(bundle)
        self.reforge(bundle, edit_sql=lambda sql: sql.replace("Synthetic draft.", "Forged"))
        mine = self.path("mine.jsonl")
        with open(mine, "w") as fh:
            fh.write(json.dumps({"kind": "export", "tenant": "tenant-a",
                                 "manifest_sha256": dm.sha256_file(os.path.join(bundle, "manifest.json"))}) + "\n")
        code, out = self.import_(bundle, self.path("n.sqlite"), self.path("f"), "tenant-a", "--ledger", mine)
        self.assertEqual((code, out["refusal"]), (1, "ledger-not-owner-ledger"))
        code, out = self.import_(bundle, self.path("n.sqlite"), self.path("f"))
        self.assertEqual((code, out["verdict"]), (1, "refused"))
        self.assertIn("matches no export", out["reason"])

    def test_an_artifact_folder_overlapping_the_owner_folder_is_refused(self):
        code, out = self.export(os.path.join(dm.OWNER_ROOT, "bundle"))
        self.assertEqual((code, out["refusal"]), (1, "ledger-inside-artifact"))
        code, out = self.export(self.tmp)
        self.assertEqual((code, out["refusal"]), (1, "ledger-inside-artifact"))

    def test_vacuum_into_in_a_bundle_writes_nothing_outside(self):
        bundle, escape = self.path("bundle"), self.path("ESCAPED.sqlite")
        self.export(bundle)
        sql_path = os.path.join(bundle, "database.sql")
        with open(sql_path, "a", encoding="utf-8") as fh:
            fh.write("VACUUM INTO '%s';\n" % escape)
        with open(os.path.join(bundle, "manifest.json"), encoding="utf-8") as fh:
            manifest = json.load(fh)
        manifest["artifacts"]["database.sql"].update(sha256=dm.sha256_file(sql_path), size=os.path.getsize(sql_path))
        with open(os.path.join(bundle, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(manifest, fh)
        with open(self.ledger, "a") as fh:  # the owner re-records the edited bundle, so only the authorizer stands in the way
            fh.write(json.dumps({"kind": "export", "tenant": "tenant-a", "manifest_sha256": dm.sha256_file(os.path.join(bundle, "manifest.json"))}) + "\n")
        code, out = self.import_(bundle, self.path("n.sqlite"), self.path("f"))
        self.assertEqual((code, out["verdict"]), (1, "refused"))
        self.assertIn("authorization denied", out["reason"])
        self.assertFalse(os.path.exists(escape))

    def test_empty_database_roundtrip(self):
        seed = self.write("empty.sql", "-- SYNTHETIC FIXTURE: empty schema\nCREATE TABLE t (id INTEGER PRIMARY KEY);\n")
        os.makedirs(self.path("nofiles"))
        code, out = call("roundtrip", "--seed", seed, "--files", self.path("nofiles"), "--tenant", "tenant-a")
        self.assertEqual((code, out["verdict"], out["file_count"]), (0, "pass", 0))

    def test_export_needs_exactly_one_source(self):
        self.assertEqual(call("export", "--files", FILES, "--out", self.path("o"))[0], 2)

    def test_missing_seed_is_exit_2(self):
        code, out = call("roundtrip", "--seed", self.path("nope.sql"), "--files", FILES, "--tenant", "tenant-a")
        self.assertEqual(code, 2)
        self.assertIn("error", out)


class MigrationTests(Base):
    def test_successful_migration_reports_both_checksums(self):
        code, out = call("migrate", "--seed", SEED, "--migration", os.path.join(FIX, "migration-v1-to-v2.sql"))
        self.assertEqual((code, out["verdict"]), (0, "migrated"))
        self.assertNotEqual(out["pre_checksum"], out["post_checksum"])
        self.assertTrue(all(p["ok"] for p in out["postconditions"]))

    def test_failed_statement_rolls_back_to_identical_content(self):
        db = self.seeded_db()
        before = dm.db_snapshot(db)["database_checksum"]
        code, out = self.migrate(db, os.path.join(FIX, "migration-fails-halfway.sql"))
        self.assertEqual((code, out["verdict"], out["failed_statement"]), (1, "rolled-back", 3))
        self.assertTrue(out["checksums_equal"])
        self.assertEqual(dm.db_snapshot(db)["database_checksum"], before)

    def test_silent_row_loss_caught_by_postcondition(self):
        db = self.seeded_db()
        code, out = self.migrate(db, os.path.join(FIX, "migration-drops-rows.sql"))
        self.assertEqual((code, out["verdict"]), (1, "rolled-back"))
        self.assertIn("expect-rows-unchanged posts", out["reason"])
        with sqlite3.connect(db) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM posts").fetchone()[0], 3)

    def test_migration_may_not_commit(self):
        mig = self.write("commit.sql", "-- expect-rows-unchanged: posts, comments\n-- expect-rows: options=2\nUPDATE options SET value='x';\nCOMMIT;\n")
        code, out = call("migrate", "--seed", SEED, "--migration", mig)
        self.assertEqual(code, 1)
        self.assertIn("must not COMMIT", out["reason"])

    def test_rollback_on_request_restores_backup(self):
        db = self.seeded_db()
        before = dm.db_snapshot(db)["database_checksum"]
        self.assertEqual(self.migrate(db, os.path.join(FIX, "migration-v1-to-v2.sql"))[0], 0)
        code, out = self.rollback(db)
        self.assertEqual((code, out["verdict"]), (0, "restored"))
        self.assertEqual(dm.db_snapshot(db)["database_checksum"], before)

    def test_rollback_refuses_edited_backup(self):
        db = self.seeded_db()
        self.migrate(db, os.path.join(FIX, "migration-v1-to-v2.sql"))
        with open(self.path("backups", "backup-0001.sqlite"), "ab") as fh:
            fh.write(b"x")
        code, out = self.rollback(db)
        self.assertEqual((code, out["verdict"]), (1, "refused"))

    def test_edited_backup_with_a_recomputed_record_is_refused(self):
        db = self.seeded_db()
        self.migrate(db, os.path.join(FIX, "migration-v1-to-v2.sql"))
        backup = self.path("backups", "backup-0001.sqlite")
        with sqlite3.connect(backup) as conn:
            conn.execute("DELETE FROM comments")
        record = self.path("backups", "backup-0001.json")
        with open(record) as fh:
            meta = json.load(fh)
        meta.update(file_sha256=dm.sha256_file(backup), content_checksum=dm.db_snapshot(backup)["database_checksum"])
        with open(record, "w") as fh:
            json.dump(meta, fh)
        code, out = self.rollback(db)
        self.assertEqual((code, out["verdict"]), (1, "refused"))
        self.assertIn("owner's ledger", out["reason"])

    def test_another_sites_backup_is_never_restored(self):
        site_a, site_b = self.seeded_db("site-a.sqlite"), self.seeded_db("site-b.sqlite")
        with sqlite3.connect(site_b) as conn:
            conn.execute("UPDATE options SET value = 'Client B (fixture)' WHERE name = 'site_name'")
        before = dm.db_snapshot(site_b)["database_checksum"]
        self.assertEqual(self.migrate(site_a, os.path.join(FIX, "migration-v1-to-v2.sql"), "shared")[0], 0)
        code, out = self.rollback(site_b, "shared")
        self.assertEqual((code, out["verdict"]), (1, "refused"))
        self.assertEqual(dm.db_snapshot(site_b)["database_checksum"], before)

    def test_a_migration_cannot_attach_or_write_another_database(self):
        """Minor 8: ATTACH ... CREATE TABLE o.leak AS SELECT * FROM posts wrote into another database."""
        db, other = self.seeded_db(), self.path("other.sqlite")
        for sql, why in (("ATTACH DATABASE '%s' AS o;\nCREATE TABLE o.leak AS SELECT * FROM posts;\n" % other, "not authorized"),
                         ("VACUUM INTO '%s';\n" % other, "statement 1 failed")):
            mig = self.write("attach.sql", "-- expect-rows-unchanged: posts, comments\n-- expect-rows: options=2\n" + sql)
            code, out = self.migrate(db, mig)
            self.assertEqual((code, out["verdict"], out["failed_statement"]), (1, "rolled-back", 1), sql)
            self.assertIn(why, out["reason"])
            self.assertFalse(os.path.exists(other))
            self.assertTrue(out["checksums_equal"])

    def test_rollback_refuses_a_different_database_at_the_same_path(self):
        """Minor 9: a backup was bound to its database by path only."""
        site_a, site_b = self.seeded_db("site-a.sqlite"), self.seeded_db("site-b.sqlite")
        with sqlite3.connect(site_b) as conn:
            conn.execute("UPDATE options SET value = 'Client B (fixture)' WHERE name = 'site_name'")
        self.assertEqual(self.migrate(site_a, os.path.join(FIX, "migration-v1-to-v2.sql"))[0], 0)
        shutil.copyfile(site_b, site_a)
        before = dm.db_snapshot(site_a)["database_checksum"]
        code, out = self.rollback(site_a)
        self.assertEqual((code, out["refusal"]), (1, "db-changed-since-migration"))
        self.assertEqual(dm.db_snapshot(site_a)["database_checksum"], before)

    def test_rollback_after_a_failed_migration_is_a_no_op_restore(self):
        db = self.seeded_db()
        self.migrate(db, os.path.join(FIX, "migration-fails-halfway.sql"))
        code, out = self.rollback(db)
        self.assertEqual((code, out["verdict"], out["checksums_equal"]), (0, "restored", True))

    def test_non_utf8_migration_and_seed_exit_2_with_a_named_reason(self):
        bad = self.path("bad.sql")
        with open(bad, "wb") as fh:
            fh.write(b"-- expect-table: posts\n\xff\xfe SELECT 1;\n")
        for argv in (("migrate", "--seed", SEED, "--migration", bad), ("roundtrip", "--seed", bad, "--files", FILES, "--tenant", "tenant-a")):
            code, out = call(*argv)
            self.assertEqual(code, 2, argv)
            self.assertIn("not UTF-8", out["error"])

    def test_content_change_with_counts_kept_fails_rows_unchanged(self):
        mig = self.write("wipe.sql", "-- expect-rows-unchanged: posts, comments\n-- expect-rows: options=2\n"
                                     "UPDATE posts SET body = '';\nDELETE FROM comments WHERE id = 3;\n"
                                     "INSERT INTO comments VALUES (99, 1, 'visitor', 'spam');\n")
        code, out = call("migrate", "--seed", SEED, "--migration", mig)
        self.assertEqual((code, out["verdict"]), (1, "rolled-back"))
        self.assertIn("expect-rows-unchanged posts", out["reason"])

    def test_malformed_or_missing_directives_and_unstated_tables(self):
        for text in ("-- expect-rows-unchanged posts, comments\nDELETE FROM posts;\n",
                     "-- Expect-Rows-Unchanged: posts\nDELETE FROM posts;\n",
                     "DELETE FROM posts;\nDELETE FROM comments;\n"):
            self.assertEqual(call("migrate", "--seed", SEED, "--migration", self.write("m.sql", text))[0], 2, text)
        code, out = call("migrate", "--seed", SEED, "--migration", self.write("m.sql", "-- expect-table: posts\nDELETE FROM posts;\n"))
        self.assertEqual((code, out["verdict"]), (1, "refused"))
        self.assertIn("comments, options, posts", out["reason"])

    def test_unknown_directive_is_exit_2(self):
        mig = self.write("bad.sql", "-- expect-magic: posts\nSELECT 1;\n")
        self.assertEqual(call("migrate", "--seed", SEED, "--migration", mig)[0], 2)

    def test_db_and_seed_together_is_exit_2(self):
        code, _ = call("migrate", "--seed", SEED, "--db", self.path("x.sqlite"),
                       "--migration", os.path.join(FIX, "migration-v1-to-v2.sql"))
        self.assertEqual(code, 2)

    def test_db_without_backup_dir_is_exit_2(self):
        db = self.seeded_db()
        self.assertEqual(call("migrate", "--db", db, "--migration", os.path.join(FIX, "migration-v1-to-v2.sql"))[0], 2)


if __name__ == "__main__":
    unittest.main()
