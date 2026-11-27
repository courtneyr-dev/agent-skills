# Sources: hosting-account-lifecycle

| Title | Location | Version or retrieved | Rights |
| --- | --- | --- | --- |
| WHM API 1 createacct | https://api.docs.cpanel.net/specifications/whm.openapi/account-creation/accounts-createacct | 2026-11-25 | Public docs; cite, don't copy |
| WHM API 1 suspendacct | https://api.docs.cpanel.net/specifications/whm.openapi/suspensions/accounts-suspendacct | 2026-11-25 | Public docs; cite, don't copy |
| WHM API 1 unsuspendacct | https://api.docs.cpanel.net/specifications/whm.openapi/suspensions/accounts-unsuspendacct | 2026-11-25 | Public docs; cite, don't copy |
| WHM API 1 removeacct | https://api.docs.cpanel.net/specifications/whm.openapi/account-management/accounts-removeacct | 2026-11-25 | Public docs; cite, don't copy |
| WHM API 1 listaccts | https://api.docs.cpanel.net/specifications/whm.openapi/account-management/accounts-listaccts | 2026-11-25 | Public docs; cite, don't copy |
| WHM API 1 changepackage | https://api.docs.cpanel.net/specifications/whm.openapi/account-management/accounts-changepackage | 2026-11-25 | Public docs; cite, don't copy |
| factory-rig leases (fencing epochs, `LeaseStore`) | skills/factory-rig/scripts/factory_rig/lease.py | agent-skills, read 2026-11-25 | agent-skills (MIT); imported, not copied |
| factory-rig receipts (`ReceiptStore`, `idempotency_key`) | skills/factory-rig/scripts/factory_rig/receipts.py | agent-skills, read 2026-11-25 | agent-skills (MIT); imported, not copied |
| factory-rig canonical JSON, sha and atomic write | skills/factory-rig/scripts/factory_rig/canon.py | agent-skills, read 2026-11-25 | agent-skills (MIT); imported, not copied |
| company-fleets acceptance matrix (`company-fleets/acceptance/matrix.json`), `recovery` row: retries, interruptions and callbacks preserve state without duplicate work | project requirements (not published) | 2026-11-25 | Project requirement; row cited, not copied |
| Synthetic fixtures (Fixture Co, tenant-a, tenant-b) | skills/company-fleets/fleets/hosting/fixtures/account-lifecycle/ | 2026-11-25 | Synthetic; no real customer, domain or provider data |

## Notes

- The fake panel mirrors WHM API 1 function names and the parameters this skill uses (`username`, `domain`, `plan`, `user`, `reason`, `pkg`). It doesn't model WHM's full parameter list, response metadata or username length rules.
- `changepackage` exists in the adapter, but no lifecycle action calls it yet. A package-change action would need its own row in the transition table.
- The ownership names (`_hosting-verify.<domain>` TXT, `/.well-known/hosting-verify.txt`) are this skill's convention, not a WHM or ACME standard.
