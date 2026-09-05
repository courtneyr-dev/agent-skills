# Severity and evidence

Load at Phase 8 — but apply the **evidence labels from the moment you observe something**,
not retroactively at write-up. A finding whose label is assigned after the fact is a finding
whose label was chosen to suit the conclusion.

---

## Evidence classification

Verbatim from the master playbook, Standing Rule 9. Every conclusion carries exactly one
label. Separate evidence from inference.

| Label | Means |
| :--- | :--- |
| **Observed** | Directly reproduced during the audit. |
| **Measured** | Supported by analytics, field data, automated tests, or other measurements. |
| **Standards-based** | Mapped to an applicable published requirement or pattern. |
| **Heuristic** | Based on an established design or usability principle. |
| **Hypothesis** | Plausible but requires user research, analytics, broader sampling, or stakeholder confirmation. |
| **User-reported** | Supported by supplied feedback, research, support requests, or interviews. |

### Rules that govern the labels

These are not style preferences. Each closes a specific way audits lie.

- **Taste is not a finding** (Rule 10). Every criticism must state the *user consequence*.
  "The hero is dated" is not a finding. "The hero's only call to action sits below the fold on
  the two most common viewport heights" is.
- **Do not claim a mental state without user evidence** (Rule 11). You may not write that users
  are confused, frustrated, reassured, or persuaded unless the label is **User-reported** or
  **Measured**. With **Observed** or **Heuristic**, write *may cause*, *creates a risk*, or
  *requires validation*.
- **Automated scans never establish conformance** (Rule 12). You may write "fails
  SC 1.4.3 on the pricing table" from a scan. You may never write "the site is WCAG 2.2 AA
  conformant." Always state the accessibility-testing depth and its limits.
- **Unobserved is not a pass** (Rule 13). When coverage was limited, write *not observed in the
  sample* and name the sample. An audit that reports silence as success is worse than no audit.
- **No wholesale redesign when a smaller correction resolves the mechanism** (Rule 14).
  Preserve effective patterns, brand character, and implementation constraints.
- **No fashionable patterns without justification** (Rule 15). Explain the benefit *for this
  site's audiences and tasks*, or do not recommend it.

### Upgrading a label

A label is upgraded by evidence, never by confidence. Say what would upgrade it:

> **Hypothesis** — the three-step checkout may be shedding users at step 2.
> *Upgrades to Measured with:* funnel data for the checkout path, any 30-day window.

This turns the report's weakest claims into a research agenda instead of hiding them.

---

## The five axes

_Synced from the master playbook. Edit the playbook, not this file._

Standing Rule 16 requires severity, confidence, evidence strength, scope, and remediation effort to
stay separate. Collapsing them into one number is the most common way an audit misleads: a
cosmetic-but-certain issue and a catastrophic-but-speculative one must not land in the same place.

Score every finding on all five. Never average them.

### Severity — how badly it hurts when it bites

| Level | Test |
| :--- | :--- |
| **Critical** | Blocks a primary task outright, or excludes a category of user entirely. No workaround the affected person can reasonably find. |
| **Major** | The task completes, but at substantial cost — errors, abandonment risk, or a materially worse outcome for some users. |
| **Moderate** | Friction. A workaround exists and most people will find it. |
| **Minor** | Polish. No measurable task impact. |

Severity is about *consequence*, never about how sure you are. A Critical finding you are unsure of
stays Critical with Low confidence.

### Confidence — how sure you are the mechanism is right

**High / Medium / Low.** Anything below High states its reason. Confidence is about your causal
explanation, not about whether the symptom exists.

### Evidence strength — which label, and how much

The Standing Rule 9 label, plus coverage: sample size, viewports, pages, dates. "Observed on 2
breakpoints, 1 page" is evidence strength. "Observed" alone is not.

### Scope — how much it touches

**Sitewide · Section · Template · Single page**, plus who is affected. A defect in a global template
is Sitewide *by mechanism* even when sampled on one page — say which.

### Remediation effort — against the stated constraints

| Level | Test |
| :--- | :--- |
| **Trivial** | Minutes. A setting, a line, a piece of copy. |
| **Contained** | Hours. Bounded, within the current stack, no architectural decision. |
| **Substantial** | Days, or a decision someone must authorise. |
| **Structural** | Requires changing the platform, theme, or information architecture. |

Effort is assessed against the constraints captured at intake, including access. A fix the auditor
cannot reach because they lack credentials is not Trivial for this engagement — quarantine it.

### How the axes drive action

Severity × Scope drives priority. Confidence × Evidence drives whether to act now or validate first.
Effort drives sequencing, and never whether a finding gets reported.

---

---

## Deduplication

One entry per **mechanism**, not per symptom. Fifteen pages with unlabeled form inputs are
one finding scoped Sitewide, with instances listed — not fifteen findings.

Two findings are the same when a single correction resolves both. If one correction fixes
part of each, they are separate findings sharing a remediation.

Merge before scoring. Scoring first and merging after inflates severity by counting the same
mechanism repeatedly.
