# Example intake

Worked example for `/website-audit https://riverside-clinic.example deep`. Fictional site.
This is a **tone and shape reference** — how much to ask, how to lead with inference, how to
label assumptions. Do not reuse its content.

---

**Claude, after Phase 2 recon:**

> Read-only audit, public pages only. I won't submit forms, sign in, or change anything.
>
> From the homepage, robots.txt, and a 340-URL sitemap, I'm reading this as a **multi-site
> physiotherapy clinic** whose site exists mainly to get people to **book an appointment**,
> **find a location and its hours**, and **check whether their insurance is accepted**. It's
> WordPress on a block theme, with a third-party booking widget on `/book/`. Correct anything
> I have wrong — I'd rather be corrected now than audit the wrong thing.
>
> ❓ **Q1 — The decision.** What does this audit feed, and by when? A pre-redesign baseline,
> a "bookings dropped" investigation, an accessibility-risk check, and a procurement review
> would each produce a different report from the same site.
> ➡️ *My guess: pre-redesign baseline. Say if it's something sharper.*
>
> ❓ **Q2 — What you already suspect.** Prior audits, complaints, analytics oddities, or the
> thing that prompted this?
> ➡️ *Assuming none unless you say otherwise.*
>
> ❓ **Q3 — Priority journeys.** I'd audit these three end to end: **book an appointment**,
> **find a location's hours and parking**, **verify insurance coverage**. Swap any out?
> ➡️ *Recommend keeping booking first — it's the only one with a conversion point.*
>
> ❓ **Q4 — What would make this a waste of your time?** Constraints I should design
> recommendations around — a theme you can't change, a rebuild already decided, a booking
> vendor you're locked into.
> ➡️ *I'm assuming the booking widget is vendor-controlled and can't be modified, only
> replaced or reconfigured.*

**User:** `1 — bookings fell ~20% after the March redesign. 2 — front desk says people phone
to ask about parking. 3 — keep as proposed. 4 — booking vendor is locked in for 2 years.`

**Claude, batch 2:**

> That reframes it — this is a regression investigation, not a baseline. Two consequences:
> the March redesign becomes the prime suspect, and I'll need to actively look for evidence
> that *disproves* that, or I'll just confirm it.
>
> The parking calls are the most useful thing you've told me. That's **User-reported**
> evidence, the strongest label available without analytics, and it points at the locations
> pages independently of anything I'd have found on my own.
>
> ❓ **Q5 — Analytics.** Funnel data for `/book/`, or site-search logs? Without them, every
> claim about *where* the 20% went stays **Hypothesis**. With them it becomes **Measured**.
> That's the single biggest difference between a report that names the cause and one that
> lists suspects.
> ➡️ *Worth 10 minutes of export if you have GA4.*
>
> ❓ **Q6 — Scope beyond the public site.** Staging, the patient portal, or the old
> pre-March theme? If the portal's in scope I need confirmed authorization and credentials
> through a password manager — not pasted in chat.
> ➡️ *Recommend public site only. The portal is a separate audit.*
>
> ❓ **Q7 — Standards.** Default WCAG 2.2 AA. Any sector requirement — healthcare
> accessibility, a payer contract clause?
> ➡️ *Assuming AA, no sector overlay.*

**Assumptions carried forward, for correction:**

| # | Assumption | Affects | Correct it if… |
|---|---|---|---|
| A1 | Booking is the primary conversion; locations and insurance are supporting | Journey priority and severity scoring | Insurance verification drives more revenue |
| A2 | Booking widget is vendor-controlled, reconfigurable but not modifiable | Which corrections are recommendable | You can inject CSS/JS into it |
| A3 | Mobile is the majority of traffic | Severity of touch-only defects | Desktop dominates |
| A4 | The March redesign is the prime suspect — **held as a hypothesis to disprove, not a conclusion** | What evidence gets sought first | — |
