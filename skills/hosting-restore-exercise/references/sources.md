# Sources

Confirmed 2026-11-25. Cite these; don't copy their text into the rig.

| Use | Title | Location | Version | Rights |
|---|---|---|---|---|
| Online backup and restore | SQLite Online Backup API; Python `sqlite3.Connection.backup` | https://www.sqlite.org/backup.html ; https://docs.python.org/3/library/sqlite3.html | SQLite 3.x; Python 3.9 to 3.14 | SQLite public domain; PSF License |
| Restores prove backups | Site Reliability Engineering, chapter 26, "Data Integrity: What You Read Is What You Wrote" | https://sre.google/sre-book/data-integrity/ | 2016, online edition | O'Reilly, free online; cite, don't copy |
| Recovery objectives (RTO, RPO) and exercise types | NIST SP 800-34 Rev. 1, Contingency Planning Guide for Federal Information Systems | https://csrc.nist.gov/pubs/sp/800/34/r1/upd1/final | Rev. 1, updated 2010-11-11 | US government work; public domain |
| Evidence freshness gate | company-fleets `fleetlib.handoff` (`open_handoff`, `apply_worker_update`, `validate_handoff`, `evidence_errors`) and factory-rig `canon`, `contract` | `skills/company-fleets/scripts/fleetlib/handoff.py`, `skills/factory-rig/scripts/factory_rig/` | agent-skills, 2026-11-25 | agent-skills (MIT) |
| Readiness record and launch gate | Magnus `production-readiness` | `skills/production-readiness/` (upstream magnus919/agent-skills) | upstream main, pinned by skill-sync | MIT, Magnus Hedemark |
| Post-incident learning record | Magnus `incident-learning` templates | `skills/incident-learning/templates/` | upstream main, pinned by skill-sync | MIT, Magnus Hedemark |
| Targets, measured results and claims kept apart | company-fleets requirements S05-023 to S05-027 | project requirements (not published) | 2026-11-25 | Project requirements, paraphrased in `company-fleets/registry/requirements.json` |
