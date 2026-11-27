---
name: community-operating-kit
description: "Use when a community or open-source program needs its operating kit written, reviewed or completed: charter, onboarding path, governance map, moderation and escalation design, event playbook, contributor journey, measurement plan and improvement loop, for developer and non-developer communities alike. Maps each section to the installed samber community and OSS skills, adds local procedures where non-developer needs exceed them (volunteer care, chapters and ambassadors, plain-language onboarding, non-code recognition), and checks the kit so every governance decision has a human owner, a record and an appeal route, moderation keeps conflicts and appeals, the measurement plan lints clean, and nothing ranks volunteers or turns members into sales leads. Trigger on \"community charter\", \"governance map\", \"community playbook\", \"contributor journey\", \"community operating model\", \"OSPO setup\", \"volunteer program\", \"chapter program\"."
disable-model-invocation: true
---

# community-operating-kit

The community mandate stands apart from DevRel even where it reuses DevRel's skills: members aren't an audience, and their records aren't program data. This skill assembles the kit from installed procedures and checks that the finished kit keeps decisions with named humans.

## Inputs

- The community's purpose, membership and existing records (code of conduct, governance log, funding and sponsor registers), from the record owner.
- The measurement plan JSON for `community-health-measures`.
- Synthetic example: `company-fleets/fleets/community/fixtures/kit/community-a-kit.md`.

## Method

1. Write each section with the skill `references/kit-map.md` names for it. Where the kit map lists a local procedure, use that; samber's collection is written for developer communities.
2. Fill the governance map as a table: Decision | Owner | Record | Review or appeal. Owners are named humans (`human:<title>`). Include funding and sponsorship rows, and state what sponsors can't influence.
3. Design moderation with `developer-community-moderation`, and route every agent-drafted case recommendation through `community-moderation-review`.
4. Lint the measurement plan with `community-health-measures` and link it from the kit.
5. Check the kit until it exits 0:

```bash
python3 scripts/kit_check.py kit.md
```

6. Hand the kit to the record owner for acceptance. Feedback for the product goes as a handoff.v1 record to `human:product-owner`.

## Stopping conditions

- Exit 0: hand off for human acceptance. The check proves the kit is complete and bounded; it doesn't prove the community will adopt it.
- A decision has no willing human owner: leave the row with `human:unassigned` and list it under open decisions. Don't assign it to an agent role.

## Output contract

The kit is one Markdown file with the eight `##` sections. `kit_check.py` prints `{ok, violations[{rule, section, message}], notes}`; exit 0 clean, 1 gaps, 2 invalid input.

| Rule | Refuses |
|---|---|
| `missing-section`, `missing-part` | A missing section, or a section without its load-bearing parts (for example, an onboarding path without first meaningful participation) |
| `governance-table`, `non-human-owner` | A governance map that isn't a table, a decision without a record or review route, or a decision owned by an agent |
| `no-plan`, `plan-<rule>` | No linked measurement plan, or one that fails `community-health-measures` lint |
| `ranking-or-sales` | Leaderboards, top-N lists, ranked volunteers, sales leads, unless the sentence negates them |

## Failure states

- Exit 2: the file is unreadable or has no `##` sections.
- If `community-health-measures` isn't installed beside this skill, the output's `notes` says the plan wasn't linted. Treat that kit as unchecked on measurement.
- Phrase checks confirm a part is named, not that it's good. A human reviewer reads the kit.

## Boundaries

- Never post the kit, message members, recruit volunteers or accept sponsors. External actions are drafts for a human.
- Never put moderation case details, member personal data or individual activity in the kit.
- Participation never becomes sales lead generation.

## References

- `references/kit-map.md`: section to skill map and the local procedures.
- `references/sources.md`: upstream and primary sources with versions and rights.

## Tests

```bash
cd scripts/tests && python3 -W ignore -m unittest -v test_kit_check
```
