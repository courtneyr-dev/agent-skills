# Sources

| Source | Location | Version | Rights | What this skill takes from it |
|---|---|---|---|---|
| developer-relations-kickoff (§ 3 routing, § 5 context artifact, § 6 memory, § 7 routines) | `~/.claude/skills/developer-relations-kickoff/` (upstream `samber/developer-relations-skills`) | commit c3a1b6912791539567727723baf626b4fec5ac7a (2026-11-08) | MIT, copyright 2026 Samuel Berthe | The router this skill adapts and the context-record format. Cited, not copied. |
| devrel-metrics, devrel-exec-reporting | same repository | same commit | MIT, copyright 2026 Samuel Berthe | Metric tiers from reach to business impact, attribution rules, vanity-metric cuts. |
| Route inventory of the installed collection | `check_routes.py scan` over the 93 installed skills, 2026-11-25 | 136 distinct `samber/<collection>@<skill>` references, 93 installed and 43 unresolved: 42 in collections the rig doesn't install (30 `samber/developer-platform-skills`, 11 `samber/dev-event-organizer-skills`, 1 `samber/cc-skills@substack-ghostwriting`) and 1 drift (`samber/developer-relations-skills@substack-playbook`, named by devto-playbook and medium-playbook but absent from the tree) | n/a | The fallbacks in `fallbacks.json`. |
| Prompt section 8, lines 407 to 417 | project requirements (not published) | Research baseline 2026-11-25 | Operator's private brief | Router handback, context mapping, no fabricated quotes or acceptances, reach versus usefulness, cautious revenue claims. |
