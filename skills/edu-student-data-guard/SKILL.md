---
name: edu-student-data-guard
description: "Student-data policy adapter for the education fleets: decides whether a workflow may read one student-related record, using the company-fleets tenant rules plus the actual school's verified policy. Use before any lesson, feedback, progress-analysis, grading, roster, accommodation or family-communication task touches student information, real or synthetic; whenever someone says 'use my class roster', 'look at their grades', 'draft progress notes', 'compare sections', 'send this to', or pastes learner work. Allows same-classroom synthetic fixtures, refuses another classroom's student records whatever the grant, refuses real records until a named human has verified the school's approved tools, role access, consent basis and retention, and refuses external destinations for student records. Not a FERPA or legal determination."
license: MIT
disable-model-invocation: true
---

# Student-data guard

Student records are the one category the education fleets never share by default. This skill stops at the human-data boundary: no school is known, so no real record is processed until the school's own policy is filled in and verified by a person.

## When to use and when not to

Use it before reading any roster, grade, accommodation plan, learner submission or family contact. Don't use it as legal advice: it records which requirements the school must confirm (FERPA, COPPA, PPRA, state and district rules, IEP and Section 504 access) and enforces what the school has verified.

## Inputs and prerequisites

- A request: `{"principal", "record", "data_origin": "synthetic|real", "tool", "purpose", "destination"?}`. `principal` and `record` are ids only. Inline objects are refused, because a requester could declare its own classroom, role or classification.
- The school policy at the fixed path `references/school-policy.json`. Requests can't supply a policy: `--policy` is a usage error. As shipped it is unverified and authorizes nothing real.
- The tenants registry at the fixed path `company-fleets/fixtures/tenants.json` (synthetic Fixture Co classrooms A and B). Principals' classrooms, roles and clearances come only from here.
- The owner grants at the fixed path `references/owner-grants.json`, keyed by the tenant that owns the records. A grant written on a record or passed by the requester counts for nothing; `--grants` is a usage error. As shipped it grants nothing.
- `company-fleets` installed beside this skill; tenant rules are imported from `fleetlib.tenancy`, not copied.

## Method

1. Run `python3 scripts/data_guard.py check REQUEST`.
2. Tenant rule (from company-fleets): a reader sees its own tenant's records up to its clearance. Another classroom's student records stay refused whatever the grant: `fleetlib.tenancy` refuses them before it reads any grant. Other records cross only with a `human:`-approved grant in the owner file.
3. Real data needs the school policy with `verified: true`, `verified_by: human:...`, a `verified_on` date and an `evidence` file that exists, the tool on `approved_tools`, the principal in `role_access`, a `consent_basis` and `retention_days`. Anything missing is a refusal naming what is missing.
4. A destination other than `local` for a student record is refused.
5. On refusal, stop and report the boundary; continue the rest of the work with synthetic data.

## Stopping conditions

A decision is printed. There is no retry path that changes a refusal; only a human-verified policy, or for records other than student records a `human:` grant in the owner file, does. Nothing moves a student record across classrooms.

## Output contract

JSON `{"decision": "allow|refuse", "reasons": [...], "policy_verified", "request"}`. Exit 0 allow, 1 refuse or invalid, 2 usage.

## Failure states

`status: invalid` for missing fields or an unknown `data_origin`; unknown principal or record ids refuse.

## Adapters and missing capability

The school's student-information system, LMS and approved-vendor list are not connected. Until a person supplies them, the adapter is the unverified `references/school-policy.json` and every real-data request is refused. Only a person edits that file and `references/owner-grants.json`.

## References

`references/school-policy.json` lists the requirements a school confirms. `references/owner-grants.json` holds the grants tenant owners recorded. Statutes: FERPA (20 U.S.C. 1232g; 34 CFR Part 99), COPPA (15 U.S.C. 6501-6506), PPRA (20 U.S.C. 1232h); cited as public law, not interpreted.

## Evaluation cases

In `company-fleets/fleets/bcit-education/evals.json`: `same-classroom-synthetic-allowed` (positive); `classroom-b-roster-refused`, `external-roster-send-refused`, `inline-principal-refused` (negative); `real-records-stop-at-boundary`, `requester-policy-file-rejected` (boundary). Unit tests: `scripts/tests/test_data_guard.py`.
