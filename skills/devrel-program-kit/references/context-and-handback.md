# Context record and handback

How samber's `developer-relations-kickoff` fits the rig without becoming a second memory system or a second dispatcher.

## The context record

| Question | Answer in this rig |
|---|---|
| What is it | `devrel-context.md`, the kickoff's § 5 artifact. It is the "developer/community program context" shared record the company-fleets cross-fleet handoffs read (`company-fleets/references/handoffs.md`). |
| Where it lives | The tenant's project root, as the kickoff says. For the Fixture Co fixture: `company-fleets/fleets/devrel/fixtures/program/devrel-context.md`. |
| Who owns it | One named human per tenant (`human:head-of-devrel` in the fixture). Agents propose patches; the owner accepts them. One authoritative owner per mutable record. |
| What it doesn't hold | Company facts (read `company-fleets/registry/company.json`), delivery state (the PM layer owns it), community-member personal data, conduct reports or moderation cases, embargoed launches, NDA rates, unpublished pricing. The kickoff's § 6 exclusion list applies. |
| Memory | Kickoff § 6 already says memory derives from the artifact, never the reverse. Agent memory may hold a one-line pointer to the file. It never holds program state. |

## Handback

1. The kickoff's output is a short-list and an ordered chain. Treat it as a proposal.
2. `check_routes.py routes` resolves every name against the installed tree. Unresolved names get a fallback or a recorded blocker.
3. The chain becomes the `stages` of a devrel workload in `company-fleets/fleets/devrel/roles.json`, run through `bin/fleet resolve`. `devrel.program-lead` coordinates inside the workload and never dispatches.
4. Each stage that crosses a role or fleet boundary is a handoff.v1 record. The execution owner is the existing router; the acceptance owner is a named human.
5. Kickoff § 7 routines go to the PM layer as dry-run proposals. Nothing recurring starts from this skill.
6. Kickoff § 5's optional agent-instruction patch needs the record owner's approval first.
