# Sources

Confirmed 2026-11-25. Cite these; don't copy their text into the rig.

| Mechanism | Title | Location | Version | Rights |
|---|---|---|---|---|
| Online backup before a change | SQLite Online Backup API; Python `sqlite3.Connection.backup` | https://www.sqlite.org/backup.html ; https://docs.python.org/3/library/sqlite3.html | SQLite 3.x; Python 3.9 to 3.14 | SQLite: public domain. Python docs: PSF License; cite, don't copy |
| SQL text dump | Python `sqlite3.Connection.iterdump` | https://docs.python.org/3/library/sqlite3.html | Python 3.9 to 3.14 | PSF License |
| Deny ATTACH and PRAGMA while loading a bundle | SQLite authorizer callbacks; Python `set_authorizer` (clearing with None needs 3.11, so the script installs an allow-all callback instead) | https://www.sqlite.org/c3ref/set_authorizer.html | SQLite 3.x | Public domain |
| Integrity check after a migration | SQLite `PRAGMA integrity_check` | https://www.sqlite.org/pragma.html#pragma_integrity_check | SQLite 3.x | Public domain |
| Transactional DDL | SQLite transactions (`BEGIN`, `ROLLBACK`) | https://www.sqlite.org/lang_transaction.html | SQLite 3.x | Public domain |
| Safe tar extraction | Python `tarfile` extraction warnings | https://docs.python.org/3/library/tarfile.html#tarfile-extraction-filter | Python 3.9 to 3.14 | PSF License |
| Customer exit requirements | company-fleets requirement S05-019 ("Portable export and exit procedures for customers") | project requirements (not published) | 2026-11-25 | Project requirement, paraphrased in `company-fleets/registry/requirements.json` |
