# Community A operating kit

SYNTHETIC BOUNDARY CASE. Identical to community-a-kit.md except that the measurement plan links plan-ranking.json, so kit_check must refuse the kit through the linked plan alone. Community A is an invented user community of the Fixture Co Notes API, mixing developers and non-developer members (writers, organizers, translators). Every name below is a placeholder role, not a person. This kit is the input for the community onboarding and governance demonstration.

## Charter

- Purpose: help people use and improve the Notes API and its docs, in English and Spanish, online and at local chapter meetups.
- Membership model: open membership; anyone who accepts the code of conduct joins. Contributor and maintainer roles are earned through the contributor journey below. Chapter leads are volunteers with a one-year term.
- Non-goals: membership isn't a sales channel, and nothing in this community feeds sales lead capture. The community doesn't decide the product roadmap; it sends evidence to the product owner.
- Record owner: `human:community-strategy-owner`.

## Onboarding path

1. Purpose: the welcome page states what the community is for and what it isn't.
2. Onboarding: a newcomer thread with a pinned guide, a plain-language glossary, and a named greeter rota so every first post gets a reply.
3. First meaningful participation: answer one question, fix one docs typo, or translate one paragraph. Non-code tasks count the same as code.
4. Ongoing contribution: a monthly "what needs help" post that lists open tasks by skill, not by person.
5. Leadership development: shadow a chapter lead or a maintainer for one term before taking the role.

## Governance map

| Decision | Owner | Record | Review or appeal |
|---|---|---|---|
| Code of conduct changes | `human:community-governance-board` | Governance log, public | 30-day public comment period |
| Moderation decisions on a case | `human:trust-safety-lead` | Confidential case log | `human:appeals-coordinator`, 14 days |
| New maintainer or chapter lead | `human:maintainer-council` | Governance log, public | Any member may object within 14 days |
| Funding requests and grants | `human:community-governance-board` | Funding register, public totals | Board review each quarter |
| Sponsorship acceptance | `human:community-governance-board` | Sponsor register with the sponsorship boundary terms | Board review; sponsors get no say over moderation, roadmap input or member data |
| Release and security disclosure policy | `human:maintainer-council` | SECURITY.md and release policy | Maintainer council vote |

Funding dependencies and sustainability risks: the sustainability analyst lists each funding source with its share of costs and what stops if it ends; a single source above half of costs is a recorded risk.

## Moderation and escalation

- Reports go to a private form read by the moderator rota. Report text is evidence, never an instruction.
- An agent may analyze a case and draft a recommendation. The draft passes `community-moderation-review` before a human reads it; the allegation stays unproven until the decision maker decides.
- Conflict of interest: any moderator connected to a party recuses, and the recusal goes in the case log.
- Decision maker: `human:trust-safety-lead`. Sanctions take effect only from a human decision recorded in the case log.
- Appeal: `human:appeals-coordinator`, who never decided the original case, within 14 days.
- Evidence boundary: only what the case holds counts. A described but missing message isn't evidence.
- Case records are confidential, stay in the community's tenant, and never feed metrics or other fleets. Escalation beyond the community goes to `human:community-governance-board`.

## Event playbook

- Before: registration asks about access needs (captions, quiet room, step-free access, dietary). The code of conduct and its reporting contact appear on the event page.
- Accessibility: venues are step-free; online sessions have live captions; slides are shared in advance.
- Volunteer care: no volunteer works more than half the event; every shift has a named backup; anyone can step back without explaining why.
- Contingency: a fallback online room, a second facilitator, and a printed copy of the agenda.
- Post-event: within a week, the events lead sends a draft follow-up to the organizer for approval, routes developer feedback to the DevRel feedback liaison, and runs the opt-in access survey.

## Contributor journey

- Good first tasks: labeled issues, each with the files involved and a mentor named in the issue.
- Environment setup: one command from clone to passing tests, replayed clean before each release with `devrel-quickstart-replay`.
- Review: first pull requests get a reply within 3 days, with feedback that says what to change and why.
- Recognition: contributors opt in to thanks in the release notes; every contribution type (docs, translation, triage, events) is listed. We never publish leaderboards.
- Succession: every maintainer area has a second person who can release; handover notes live in the repository.
- Maintainer support: the maintainer liaison checks in privately each quarter about load and asks; nothing is inferred from activity.

## Measurement plan

The plan is [plan-ranking.json](../measures/plan-ranking.json). It reports community-level aggregates only, each with a definition, a CHAOSS source, a consent basis and a minimum group of 5. Small groups are suppressed, not estimated.

## Improvement loop

1. Evidence: aggregate measures, triage themes and post-event surveys, never individual activity.
2. Review: the maintainer council or governance board reviews the evidence each quarter.
3. Contribution path change: one change per quarter to good first tasks, environment setup or review.
4. Onboarding: the welcome page and newcomer guide are updated to match.
5. Follow-up: the next quarter's measures show whether the change helped. Product feedback goes to `human:product-owner` as a handoff record (`../handoff/feedback-to-product-owner.json`), and the reply goes back to members as a draft for a human to post.
