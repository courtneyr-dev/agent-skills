<!-- SYNTHETIC FIXTURE (Fixture Co): support runbook for Client A's donate page. Names are role placeholders, not people. -->
# Client A donate page: support runbook

## Scope of support

The agency supports the donate page template (`deliverable/template.html`), its build script, the English, Spanish and Arabic catalogs, and the CSS for 30 days after launch. Payment processing, hosting and the donor database stay with their own owners.

## Contacts by role

- Support handoff owner (agency): first contact for defects during warranty.
- Client A operator (`human:client-a-operator`): publishes copy changes.
- Language reviewer (`human:language-reviewer`): approves every translation before release and after any catalog change.
- Hosting intake owner (`human:hosting-intake-owner`): receives the release folder when Fixture Co also hosts the site.

## Deployment and rollback

1. Run `python3 build.py` in `deliverable/`; it fails if any string is missing from a catalog.
2. Copy the three `donate.*.html` pages, `tokens.css` and `styles.css` to the host's document root.
3. Roll back by restoring the previous release folder, kept for 30 days.

## Content freeze

No copy, catalog or style edits from 24 hours before launch until the launch check passes.

## Known issues

- Amounts show a US dollar sign in every locale. The language reviewer decides the local currency format.
- The Spanish and Arabic catalogs have not had linguistic review; release waits for it.

## Operator training

The operator learns three tasks: change a string in a catalog and rebuild, rerun the keyboard and i18n checks, and roll back. Training happens on staging with the training lead; the session isn't recorded here because it hasn't taken place.

## Warranty and maintenance

Defects reported within 30 days are fixed at no charge. After that, changes go through a new PM contract.

## Monitoring and escalation

The host's uptime alert goes to the operator. Accessibility or translation defects escalate to the support handoff owner within one business day; anything touching donor data escalates to the delivery owner the same day.
