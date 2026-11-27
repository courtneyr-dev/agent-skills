# Ethics and data boundary

The skill drafts ethics and data-management materials. It never grants, assumes or reports approval, and it never collects, stores or analyzes data from real participants.

## What the skill may produce

- A protocol draft: purpose, procedures, risks and benefits, recruitment text, consent and assent language, the non-participation path, data handling.
- A data-management plan: storage location named by a human, retention, access list, de-identification step, destruction.
- A checklist of which review bodies may apply (a university IRB or REB, a district research office, a school principal) for a human to confirm.

## What stops the work

| Situation | Response |
|---|---|
| A plan says ethics approval is granted but cites no approval reference | Reject (`approval-claimed-without-evidence`); the rig cannot grant or assume approval |
| A plan cites an approval reference | Warn (`approval-unconfirmed`); a human checks the approval letter |
| A plan or request already holds participant records | Reject (`participant-data-present`); collection waits for the approved process and the school's student-data policy (edu-student-data-guard) |
| Minors are in scope with no parental consent and child assent process | Reject (`minors-without-assent`) |
| Someone asks the rig to recruit, contact, survey or enroll participants | Decline; draft the materials for the human researcher |

## Rules that apply in U.S. schools

- Federal human-subjects protections: 45 CFR 46 (the Common Rule, 2018 Requirements), with Subpart D for children. https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-A/part-46. U.S. government work, public domain.
- Student education records: FERPA, 34 CFR Part 99. https://www.ecfr.gov/current/title-34/subtitle-A/part-99. U.S. government work, public domain.
- Ethical principles: The Belmont Report (1979). https://www.hhs.gov/ohrp/regulations-and-policy/belmont-report/index.html. U.S. government work, public domain.

These sources are recorded by URL as primary references and were not fetched in the 2026-11-25 build (network use was limited to the paper and citation registries); recheck the URLs before relying on them. The skill does not interpret them as legal advice, and a district or university office decides which apply. State law and district policy can add requirements; Pennsylvania is the parent prompt's initial jurisdiction and still needs a human to confirm the actual school's rules.

## Synthetic data only in the rig

Fixtures and evaluations use synthetic records labeled `SYNTHETIC FIXTURE (Fixture Co)`. A study card derived from a published paper is labeled as derived from a real public paper and holds only what the paper reports in aggregate.
