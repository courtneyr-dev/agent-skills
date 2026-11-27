# Community operating kit map

Upstream skills are samber/developer-relations-skills at commit c3a1b69 (MIT, Samuel Berthe). "Existing" means a skill already in the rig before this build. "Local" means a procedure in this file, written because the upstream collection targets developer communities.

| Kit section | Produce with | Local procedure |
|---|---|---|
| Charter | developer-community-launch (go or no-go, venue, first 90 days), oss-governance | State non-goals, including "membership isn't a sales channel" |
| Onboarding path | developer-community-launch, oss-contributor-onboarding, discord-community-playbook, discourse-forums-playbook | Plain-language onboarding (below) |
| Governance map | oss-governance, oss-release-policy, oss-security-disclosure, oss-sponsors-fundraising, oss-sponsors-brand-strategy, oss-maintainer-sustainability | Sponsorship boundaries (below) |
| Moderation and escalation | developer-community-moderation; community-moderation-review for every agent draft | None |
| Event playbook | developer-meetup-program, developer-event-followup; existing community-os for campaigns and hackathons; existing web-accessibility | Volunteer care, chapters (below) |
| Contributor journey | oss-contributor-onboarding (`contributor-path-audit.sh`), oss-issue-triage (`triage-baseline.py`), developer-champions, oss-maintainer-sustainability; devrel-quickstart-replay for the clean setup command | Non-code recognition (below) |
| Measurement plan | developer-community-health; community-health-measures | Consent-aware aggregates only |
| Improvement loop | developer-feedback-loop | Community improvement workflow: evidence, review, contribution path change, onboarding, measured follow-up |

## Local procedures

### Plain-language onboarding

- The first page says what the community is for in two sentences and links the code of conduct.
- A glossary defines every term a non-developer meets in the first week.
- A greeter rota (named people, not a bot) answers every first post within 2 days.
- First tasks include non-code work: answering a question, fixing a docs typo, translating a paragraph, hosting a meetup.

### Volunteer care

- No volunteer covers more than half of an event or more than one role at a time.
- Every shift has a named backup. Anyone can step back without giving a reason.
- The maintainer liaison or volunteer coordinator asks about load in a private check-in each quarter. Nobody infers burnout, health or availability from activity data.

### Chapters and ambassadors

- Each chapter has a one-page charter, a lead with a fixed term, and a second organizer.
- Chapters follow the central code of conduct. Reports go to the central moderation rota, not to the chapter lead alone, so a chapter lead never judges a case about their own chapter without a conflict check.
- Ambassador programs follow `developer-champions`: published selection criteria, behavior-based obligations, perks not payment, fixed terms.

### Non-code recognition

- Recognition is opt-in and lists contribution types (docs, translation, triage, events, mentoring), never counts per person.
- No leaderboards, top-N lists or rankings.

### Sponsorship boundaries

- Sponsors get acknowledgment and agreed benefits. They get no say over moderation, governance decisions, roadmap input or member data.
- The sustainability analyst records each funding source's share of costs and what stops if it ends. A single source above half of costs is a recorded risk.
