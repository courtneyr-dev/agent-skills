# Sources: hosting-service-catalogue

| Title | Location | Version or retrieved | Rights |
| --- | --- | --- | --- |
| Company agent fleets prompt, section 5 Hosting profiles (required coverage per profile; the VPS/dedicated, managed cloud/PaaS and advanced resilience rows become capability sets) | project requirements (not published) (table rows 276-284) | 2026-11-25 | Private prompt; function ids derived, text not copied |
| Function vocabulary derived from that section | skills/hosting-service-catalogue/references/functions.json | 2026-11-25 | agent-skills (MIT); original |
| Operating profiles registry (`responsible_for`, `not_responsible_for`, kind hosting) | skills/company-fleets/registry/profiles.json | agent-skills, read 2026-11-25 | agent-skills (MIT); read only, never edited |
| Synthetic catalogue fixtures (Fixture Co; providers `example-host` and `example-upstream` are invented) | skills/company-fleets/fleets/hosting/fixtures/service-catalogue/ | 2026-11-25 | Synthetic; no real provider data or prices |

## Notes

- The prompt states: "Affiliate, reseller, and operator are different responsibilities. A referral service does not become responsible for infrastructure it cannot control." Rules 2 and 3 encode that sentence for the affiliate and reseller profiles.
- Function ids are the kebab-case form of the prompt's coverage words. Where the prompt lists a phrase (for example "Failure-domain analysis"), the id is `failure-domains`; the mapping is a judgment and `functions.json` is the single place to change it.
- The shared profile's `mail` is optional because the prompt says "mail where offered".
