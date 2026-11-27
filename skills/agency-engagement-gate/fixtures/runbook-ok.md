<!-- SYNTHETIC FIXTURE (Fixture Co): a complete support runbook for Client A's donate page. -->
# Client A donate page: support runbook

## Scope of support

The agency supports the donate page template, its three locale catalogs (en, es, ar) and its CSS for 30 days after launch. Payment processing and hosting stay with their own owners.

## Contacts by role

- Support handoff owner (agency): first contact for defects during warranty.
- Client A operator (`human:client-a-operator`): publishes copy changes.
- Language reviewer (`human:language-reviewer`): approves every translation change.

## Deployment and rollback

Deploy by copying the release folder to the host's document root. Roll back by restoring the previous release folder, kept for 30 days.

## Content freeze

No copy or catalog edits from 24 hours before launch until the launch check passes.

## Known issues

None open at handoff. Re-run the keyboard and i18n checks after any template edit.

## Operator training

The operator practiced one copy change and one rollback on staging, with the agency watching.

## Warranty and maintenance

Defects reported within 30 days are fixed at no charge. After that, changes go through a new PM contract.

## Monitoring and escalation

The host's uptime alert goes to the operator. Accessibility or translation defects escalate to the support handoff owner within one business day.
