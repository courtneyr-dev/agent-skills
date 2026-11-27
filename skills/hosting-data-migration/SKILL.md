---
name: hosting-data-migration
description: "Move a hosted site's data safely and prove it: an upgrade-compatibility preflight (runtime, database engine and extension versions), a migration rehearsal that backs up first, applies the change in one transaction, checks stated post-conditions and rolls back automatically with checksum proof, and a portable export bundle (SQL dump, deterministic tar, hash manifest) that re-imports into a fresh location for a customer leaving the platform. Use whenever someone plans a schema change, PHP or database upgrade, platform move, site transfer, data export or customer exit, or asks whether a migration can be rolled back."
license: MIT
disable-model-invocation: true
---

# hosting-data-migration

Rehearse a data move before it touches production, and give a departing customer an export they can
verify. SQLite plus a files folder stand in for a site's database and uploads, so the method and its
checks are real while engine-specific SQL stays untested.

## When to use

- Before a runtime or database upgrade: run `preflight` against the target's offer.
- Before a schema change: rehearse it with `migrate` and keep the rollback proof.
- For a platform move or a customer exit: `export`, then prove the bundle with `import` into a fresh
  location (`roundtrip` does both).

## When not to use

- Restores after a failure: use `hosting-restore-exercise`.
- DNS cutover: use `hosting-dns-cert-lifecycle`.
- Account decommission after an export: `hosting-account-lifecycle` records the export manifest hash
  and refuses to decommission without it or a human waiver.
- Production MySQL or PostgreSQL moves: this skill doesn't run them. It produces the rehearsal and the
  checks a human operator runs against the real engine.

## Inputs and prerequisites

- `preflight`: app JSON (`requires.runtimes`, `requires.database`, `requires.extensions`) and target
  JSON (`offers.*`). Ranges look like `>=8.1,<8.5` over dotted integers. Any other key under
  `requires` is invalid input, and a preflight that checks nothing is refused.
- `export` and `roundtrip`: a database (`--db`) or a SQL seed (`--seed`), a files folder and `--tenant`.
- The data owner's ledger, at one fixed path:
  `company-fleets/fleets/hosting/owner/hosting-data-migration/ledger.ndjson`. `export` records the
  manifest's sha256 and tenant; `migrate` records each backup's database path, file hash and content
  checksum, and the checksum a committed migration left. A `--ledger` the caller names is refused
  (`ledger-not-owner-ledger`), and so is a bundle or backup folder that overlaps the owner folder
  (`ledger-inside-artifact`). `migrate --seed` and `roundtrip` keep a private ledger in their own temp
  folder, so their bundles count nowhere else.
- `migrate`: a migration SQL file whose header lines state post-conditions (`-- expect-table:`,
  `-- expect-no-table:`, `-- expect-column: table.col`, `-- expect-rows-unchanged: t1, t2`,
  `-- expect-rows: table=N`); a database with `--backup-dir`, or `--seed` for a throwaway copy. Every
  table that exists before the migration needs a row directive (`expect-rows-unchanged`,
  `expect-rows` or `expect-no-table`), and a comment line that starts like a directive but doesn't
  parse is invalid input. `expect-rows-unchanged` compares the rows' content over the columns that
  existed before, not only the count.
- Python 3.9+. Put the site in maintenance mode so the database is idle.

## Method

1. Run `preflight`. Stop on `incompatible` and hand the reasons to the solutions architect.
2. Run `migrate`. It takes a backup and checks that its content checksum matches, runs every statement
   in one transaction under an authorizer that denies ATTACH, DETACH (so `VACUUM INTO`) and every
   pragma but `foreign_keys`, so a migration writes only its own database, refuses a migration that
   commits on its own, evaluates the post-conditions
   and `PRAGMA integrity_check`, and on any failure restores the backup and proves the content
   checksum equals the pre-migration value.
3. For a move or exit, run `export`, then `import --tenant T` into an empty location. Import
   refuses a manifest whose sha256 isn't in the ledger (a bundle edited and rehashed, or relabeled),
   takes the tenant from the ledger record, checks every artifact hash before writing, refuses unsafe
   tar paths, loads the SQL with ATTACH (which also covers `VACUUM INTO`) and most PRAGMAs denied, and
   compares table checksums.
4. `rollback --db D --backup-dir B` restores only a backup the ledger records for that database and
   folder, only if its file hash matches the ledger, and only while the database is the one the
   migration left (or already the backup). Another database copied to the same path, or one that has
   taken writes since, is refused (`db-changed-since-migration`) and left untouched.
5. Attach the JSON outputs and the manifest hash to the handoff. The account record keeps the
   manifest hash.

## Stopping conditions

- `compatible`, then `migrated` with every post-condition true, or `pass` on the roundtrip.
- Or a refusal, `rolled-back` or `incompatible`: stop and hand the reasons on. Don't retry a migration
  that failed a post-condition without changing it.

## Output contract

JSON on stdout. `preflight`: `verdict`, `reasons`, `checked`. `migrate`: `verdict` (`migrated`,
`rolled-back`, `rollback-failed`), `pre_checksum`, `post_checksum` or `restored_checksum` and
`checksums_equal`, `postconditions`, `backup`. `export`: the manifest summary. `import`: `verdict`
(`imported` or `refused`) and `reason`. `roundtrip`: `verdict`, `checks`, `tables`, `file_count`.
Every result carries `assumptions`.

## Failure states

- Exit 1: incompatible, refused (`ledger-not-owner-ledger`, `ledger-inside-artifact`,
  `db-changed-since-migration`, a bundle or backup the ledger doesn't hold, tampered or unsafe bundle,
  wrong tenant, existing destination, unstated tables, a preflight with 0 checks), rolled back
  (including an ATTACH denied by the authorizer), or a roundtrip mismatch.
- Exit 2: invalid input (unparseable JSON or range, unknown or malformed directive, no directive,
  unknown requirement key, export without `--tenant`, missing file, both or neither of `--db` and
  `--seed`, a seed or migration file that isn't UTF-8).
- Limit: a process running as the same OS user can rewrite the owner's ledger along with the bundle,
  or run `export` itself. Only separate OS accounts or signed records stop that.
- No exit 3: the script needs no external capability.

## Adapters and missing capability

No database-engine adapter exists for MySQL, MariaDB or PostgreSQL. Without one, run the rehearsal
here on a SQLite copy of the schema, then give the human operator the same post-conditions as a
checklist for the real engine and mark the production result unverified.

## References

`references/sources.md` lists the SQLite and Python documentation each mechanism follows.

## Tests

```bash
cd ~/.claude/skills/hosting-data-migration/scripts && python3 -W ignore -m unittest discover -s tests
```

## Evaluation cases

Fleet cases in `company-fleets/fleets/hosting/evals.json`:
`hosting.eval.data-migration-export-import-roundtrip`, `hosting.eval.data-migration-compatible-preflight`,
`hosting.eval.data-migration-tampered-bundle-refused`, `hosting.eval.data-migration-incompatible-runtime`,
`hosting.eval.data-migration-failed-migration-rolls-back`, `hosting.eval.data-migration-dropped-rows-caught`.

Cases that replay the 2026-11-26 independent review's probes: `hosting.eval.data-migration-rehashed-bundle-refused`, `hosting.eval.data-migration-relabeled-bundle-refused`, `hosting.eval.data-migration-untenanted-export-refused`, `hosting.eval.data-migration-other-site-backup-refused`, `hosting.eval.data-migration-edited-backup-refused`, `hosting.eval.data-migration-content-wipe-caught`, `hosting.eval.data-migration-unstated-tables-refused`, `hosting.eval.data-migration-empty-preflight-refused`.

Cases that replay the hosting re-review's probes: `hosting.eval.data-migration-caller-ledger-refused`, `-attach-in-migration-refused`, `-swapped-database-rollback-refused`.
