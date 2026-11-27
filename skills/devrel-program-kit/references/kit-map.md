# Developer-program operating kit

Each kit section, the installed skill that produces it, and what proves it. Upstream skills are samber/developer-relations-skills at commit c3a1b69 (MIT, Samuel Berthe) unless noted. "Existing" means a skill already in the rig before this build.

| Kit section | Produce with | Proof |
|---|---|---|
| Program strategy, business alignment, non-goals | devrel-strategy, developer-first-gtm; existing devrel-engine | check_program `no-non-goals` |
| Audience research and segments | developer-segmentation, developer-survey-design, developer-journey-map | Segment `evidence` field; "assumption to test" until research runs |
| Team structure, staffing, budget | devrel-team-structure, devrel-hiring, devrel-budget-allocation | check_program `invented-budget`; figures come from the owner |
| Developer journey and onboarding friction | developer-journey-map, developer-quickstart-guide (friction log) | Replay of the quickstart; friction log from real readers stays unverified until a session runs |
| Quickstart, tutorials, how-tos | developer-quickstart-guide, developer-tutorial, developer-how-to-guide, developer-troubleshooting-docs | devrel-quickstart-replay evidence per page |
| Sample apps and code samples | docs-code-sample-standards (`sample-audit.py`), devrel-quickstart-replay | Lint plus clean replay |
| Reference docs, structure, versioning, localization | developer-docs-structure-audit, docs-versioning-strategy, docs-localization-strategy, docs-site-platform-selection | Partial: api-reference-quality lives in the uninstalled developer-platform-skills |
| Talks, CFPs, demos | conference-cfp-submission, tech-talk-outline, developer-live-demo-design (`demo-checkpoints.sh`) | Demo script replayed clean; no acceptance claimed without a source |
| Workshops and office hours | developer-workshop-program, developer-office-hours-program, devrel-webinar-program | Workshop lab replayed clean |
| Events: planning, accessibility, rehearsal, contingency, follow-up, reuse | developer-meetup-program, devrel-field-events, developer-booth-playbook, developer-event-sponsorship, developer-event-followup, devrel-content-calendar; existing community-os for hackathons; existing web-accessibility | Accessibility and rehearsal stay human-verified; hackathon coverage is partial |
| Feedback to product to developers | developer-feedback-loop, devrel-quickstart-replay (repro), handoff.v1 to `human:product-owner` | Replayed repro plus a handoff record; replies stay drafts |
| Metrics, instrumentation, attribution, exec reporting | devrel-metrics, devrel-analytics, devrel-exec-reporting | check_program `reach-headline`, `causal-revenue`, `fabrication-risk` |
| Program retrospective | devrel-exec-reporting; existing incident-learning for the learning-record format | Observation, hypothesis, adjustment, verification |
| OSS and community counterpart | oss-governance, oss-contributor-onboarding, developer-community-health | Hands to the community fleet; community records stay there |

## Content and demo chain

Sample app, then quickstart, then workshop lab, then demo, then feedback repro. Every runnable link has a `devrel-quickstart-replay` report in the fleet's evidence folder. Human usability stays `unverified` until a session with unfamiliar readers is on record.
