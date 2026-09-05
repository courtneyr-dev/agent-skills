# Example audit excerpt

Two findings in the required format, plus the limitations style. Fictional. **Tone and rigor
reference** — the point is what each finding refuses to overclaim.

---

### F-03 · Insurance list is an image, so it is unsearchable and unreadable aloud

**What is happening** — `/insurance/` presents 34 accepted payers as a single exported PNG
with `alt="insurance carriers"`. The names exist nowhere in text on the page.

**How it was tested** — `read_page` accessibility tree on `/insurance/`; site search for three
payer names present in the image; page source inspection. Chrome 141, desktop and mobile preset.

**Evidence** — **Observed** and **Standards-based**. The tree exposes one image and no payer
text. Site search for "Aetna" returns zero results while Aetna is visible in the image. Fails
**SC 1.4.5 Images of Text (AA)** and **SC 1.1.1 Non-text Content (A)** — the alt text does not
convey equivalent information. Automated scan depth only for the rest of this template; not a
conformance determination.

**Who it affects** — Screen-reader users get nothing. Everyone using site search or
browser find-in-page gets a false negative. Front-desk staff reported inbound calls about
coverage, which is consistent with this, though the calls were reported about **parking**, so
treating them as evidence *for this finding* would be overreach.

**Correction** — Publish the list as text. A plain `<ul>` is sufficient; a filterable table is
better but not required to clear the criterion. No redesign implicated.

| Severity | Confidence | Evidence | Scope | Effort |
|----------|------------|----------|-------|--------|
| Major | High | Observed + Standards-based | Single page | Trivial |

---

### F-08 · Booking step 2 may be shedding users, but the audit cannot show it

**What is happening** — `/book/` step 2 asks for insurance member ID before showing any
appointment times. Members without their card to hand have no way past it and no "skip"
affordance.

**How it was tested** — Walked steps 1–2 read-only on desktop and mobile. **Did not submit**
the form, so steps 3+ were not observed.

**Evidence** — **Hypothesis.** The mechanism is **Observed** — the field is required and there
is no bypass. That it *causes* the reported 20% booking decline is not. The redesign changed
several things at once and no funnel data was available.

*Upgrades to Measured with:* GA4 funnel for `/book/` step 2 → 3, any 30-day window, split by
device. That single export would confirm or kill this finding.

**Who it affects** — Any prospective patient without their insurance card during booking.
Share unquantified — no analytics supplied.

**Correction** — Make member ID optional at booking and collect it at check-in, or move it
after time selection so abandonment costs the user less. Both are vendor *configuration*, not
modification, so they survive the vendor lock-in noted at intake (A2).

| Severity | Confidence | Evidence | Scope | Effort |
|----------|------------|----------|-------|--------|
| Critical | Low | Hypothesis (mechanism Observed) | Booking flow | Contained |

> Severity Critical, Confidence Low — deliberately not averaged. If real it is the most
> important finding here; the evidence does not yet support acting on it without the funnel
> export. Standing Rule 16.

---

## Limitations, in the required style

- **Booking steps 3+ not audited.** Reaching them requires submitting a form against a live
  production booking system. Out of bounds under read-only. Recommend a staging walkthrough.
- **Accessibility depth:** automated tree inspection plus manual keyboard testing on 6
  templates. **No screen-reader testing and no conformance determination.** Templates outside
  that sample are *not observed*, which is not the same as passing.
- **No analytics, session recordings, or user research supplied.** Every claim about user
  behavior is capped at **Hypothesis**.
- **Patient portal excluded** at intake. Not audited, not cleared.
