# Sources

Provider pages were fetched 2026-11-25 with a plain HTTP client and the default user agent; every
quote in the matrix was checked as an exact substring of the fetched page. The full claim list, with
URLs, lives in `company-fleets/fleets/hosting/benchmark/2026-11-26-matrix.json`. Cite these; don't
copy their text beyond the short quotes the matrix holds.

| Use | Title | Location | Version | Rights |
|---|---|---|---|---|
| Pantheon claims | Pantheon documentation and plan pages (backups, multizone failover, application containers, regions, support, pricing, accessibility statement) | https://docs.pantheon.io/ ; https://pantheon.io/plans/pricing | Retrieved 2026-11-25; some pages show review dates from 2020 | Public docs; cite, don't copy |
| WordPress VIP claims | WordPress VIP documentation and capability pages (database backups, rollbacks, disaster recovery, logs, package definitions, pricing) | https://docs.wpvip.com/ ; https://wpvip.com/pricing/ | Retrieved 2026-11-25 | Public docs; cite, don't copy |
| Acquia claims | Acquia Cloud Platform documentation (backups, availability and disaster recovery, architecture, rollback, monitoring, SLA, compliance) | https://docs.acquia.com/acquia-cloud-platform | Retrieved 2026-11-25; one page (docs.acquia.com/node/56192) returned HTTP 503 | Public docs; cite, don't copy |
| What to record separately, and what not to claim | company-fleets requirements S05-023 to S05-027 | project requirements (not published) | 2026-11-25 | Project requirements, paraphrased in `company-fleets/registry/requirements.json` |
| Availability needs a production window | Site Reliability Engineering, chapter 4, "Service Level Objectives" | https://sre.google/sre-book/service-level-objectives/ | 2016, online edition | O'Reilly, free online; cite, don't copy |
| Measured evidence | `hosting-restore-exercise`, `hosting-tenant-isolation`, `hosting-data-migration` outputs | `company-fleets/fleets/hosting/evidence/*-2026-11-26.json` | 2026-11-26 lab runs | agent-skills (MIT); synthetic |
| Launch gate this backlog feeds | Magnus `production-readiness` | `skills/production-readiness/` (upstream magnus919/agent-skills) | upstream main, pinned by skill-sync | MIT, Magnus Hedemark |

Not fetched: the Pantheon Trust Center (a JavaScript page with no readable text), any provider's
VPAT document itself, and contractual SLA terms that sit in customer contracts.
