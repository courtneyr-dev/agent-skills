# Audit playbook

Load at Phase 7. Derived from the master playbook, kept canonically at
`$VAULT_DIR/Areas/Website UX Audits/website-ux-navigation-design-audit-master-prompt.md`.

## Standing rules — reread these at Phase 9

Preserved from the source. These govern the whole audit and outrank any companion skill.

1. **Whole task.** Not a homepage review, visual critique, automated scan, accessibility
   checklist, or list of opinions. Do not silently scope down.
2. **Intent over wording.** Read the task through the purpose, stakes, audiences, and
   decisions captured at intake.
3. **Reasonable calls on ambiguity.** State material assumptions and reduce confidence
   accordingly. Ask only when the gap would materially change scope, create risk, require
   authorization, or prevent a responsible test.
4. **Recommend, don't survey.** When a choice is required, make one and say why. Alternatives
   only when their tradeoffs materially affect the decision.
5. **Audit only.** No editing the site, implementing fixes, changing content, creating
   accounts, submitting forms, publishing, or adjacent work. Mention worthwhile adjacent work
   without doing it.
6. **Investigate to the definition of done**, not to the first plausible explanation. Test
   initial findings, competing explanations, and meaningful edge cases.
7. **Mechanism first, then proof.** What is happening · how you tested it · what evidence
   supports it · who it affects · what correction would address it.
8. **Concise at sentence and section level**, even when the audit is comprehensive. No
   ceremonial preambles, no restating the assignment. Tables and grouped findings over repetition.
9. **Separate evidence from inference.** Label every conclusion — see
   `severity-and-evidence.md`.
10. **No taste as finding.** State the user consequence of every criticism.
11. **No unevidenced mental states.** See `severity-and-evidence.md`.
12. **No conformance claims from scans.** State accessibility-testing depth and its limits.
13. **Unobserved ≠ pass.** Say "not observed in the sample."
14. **No wholesale redesign** when a smaller correction resolves the mechanism.
15. **No fashionable patterns** without a benefit argued for this site's audiences and tasks.
16. **Five axes stay separate** — severity, confidence, evidence strength, scope, effort.
17. **Respect access controls.** No bypassing authentication, paywalls, rate limits, or robots
    protections. Blocked areas are recorded limitations.
18. **Protect privacy.** Do not expose personal data encountered during testing. Redact
    sensitive information from evidence.
19. **Reread this prompt before claiming done.** Flag anything missed, assumed, left untested,
    or contradicted.

## Method selection

The source leaves method open by default so the auditor selects and justifies it. Whatever you
choose, **state it and its limits in the report**. Anchor the audit to the priority journeys
from intake — the site is a system people use to complete tasks, not a collection of screens.

Work each priority journey end to end before auditing pages in isolation. A journey walk
surfaces mechanism; a page sweep surfaces symptoms.

---

## Coverage modules

_Synced from the master playbook. Edit the playbook, not this file._

Work the modules against the priority journeys, not as a page-by-page sweep. A journey walk surfaces
mechanism; a page sweep surfaces symptoms. A module with nothing to report says "no findings" — an
unexamined module says "not covered."

### 1. Information architecture and navigation

Whether the structure matches what visitors came to do, rather than how the organisation is
arranged internally. Label vocabulary — the organisation's words or the visitor's. Breadth and depth
of the top level. Whether a parent item is a destination, a disclosure, or a dead link. Whether
every page has a route in that isn't search. Orphans. Duplicate destinations. URL readability, since
a URL is read before it is clicked.

### 2. Interaction design and controls

Every control's states — default, hover, focus, active, disabled, loading, error, empty. Whether a
control's role matches its markup. Destructive actions and their confirmations. Whether feedback
follows action. Disclosure patterns that depend on hover alone.

### 3. Content design

Whether the page answers the question its visitor arrived with, in its first screen. Headline claims
and whether the page substantiates them. Reading level against audience. Stale content presented as
current — dated announcements, past events, expired calls to action. Link text that makes sense out
of context. Whether the organisation's internal vocabulary leaks into visitor-facing copy.

### 4. Accessibility

Testing depth must be stated, and **no conformance claim may be made from any depth short of a full
manual audit** (Standing Rule 12).

At minimum: keyboard reachability of every interactive control, at every breakpoint — a control
hidden at one width may be the only route to a menu at that width. Focus order and focus visibility.
Bypass mechanisms — skip links, landmarks. Heading hierarchy without level skips. Accessible names
and roles on custom controls. Zoom and reflow. Target sizes. Colour contrast. Text alternatives.
Motion and `prefers-reduced-motion`. Media alternatives — captions and transcripts.

Test each breakpoint independently. Responsive CSS routinely produces different accessibility
outcomes at different widths, and a pass at one width proves nothing about the other.

### 5. Responsive and cross-device

The breakpoints the site actually defines, not arbitrary widths. Horizontal overflow. What occupies
the first screen at each. Touch versus pointer behaviour, including any interaction that depends on
hover. Whether device emulation changed a load-time gate — reload after switching.

### 6. Forms and journeys

Each priority journey end to end. Field labelling, grouping, required-field marking, error handling,
and recovery. What the form asks for before it gives anything back. Where a journey hands off to a
third party, and whether the handoff is announced.

**Read-only boundary:** never submit. A journey that cannot be completed without submitting is
audited to the boundary and the remainder recorded as not covered.

### 7. Search and discovery

How people arrive, and whether they arrive at all. Query data against landing pages. Branded versus
non-branded demand — a site can convert superbly for people who know its name and be invisible to
everyone else, and those are different problems with different fixes. Title and description quality
on the pages that draw impressions and lose them. On-site search, if present.

**Check acquisition before diagnosing conversion.** A page nobody reaches cannot have a usability
problem, and a page with a high click-through rate does not have a snippet problem.

### 8. Performance as experienced

Not scores — consequences. Which element delays the thing the visitor came for, at what connection
speed. Layout shift during read. Input delay on the controls of a priority journey. A score is an
input; it becomes a finding only when connected to a user consequence.

### 9. Trust and safety signals

Whether the site looks like what it claims to be at the moments that matter — giving, contact,
handoffs to payment processors, anything asking for personal data. Unannounced domain changes.
Certificate and security posture where a visitor would notice.

Also: **information that should not be public.** Named individuals in contexts they did not choose,
internal operational detail, contact details of people who did not consent. Flag it and hand the
judgment to the organisation — it is theirs to make, not the auditor's (Standing Rule 18).

### 10. Platform-specific — WordPress

Theme-emitted markup versus plugin output versus content. This split is what answers "do we need to
rebuild," and it is usually the most consequential question the audit is asked.

Common sources: theme viewport tags suppressing zoom; theme menu modules emitting non-semantic
toggles and hover-only submenus; missing landmarks and skip links in theme templates; plugin-emitted
heading levels overwhelming a page's outline; auto-generated slugs from title collisions; SEO plugin
present but not configured. Check whether the fix lives in a child theme, a plugin setting, or the
content — and say which, per finding.

### 11. Research and analytics synthesis

Whatever the organisation already has: analytics, search data, support requests, staff observations,
prior audits. **Read the prior work before generating new work** — a recent audit is a baseline to
diff against, not something to duplicate.

Every premise inherited from a prior report is **unverified until checked at the level the claim is
made.** A summary sentence in an earlier document is not evidence. Verify inherited premises before
building findings on them; a false premise repeated confidently is worse than no finding.

### 12. Quality control

Standing Rule 19, executed rather than gestured at. Re-read the playbook. Walk the definition of
done line by line and state which lines are met. List what was missed, assumed, left untested,
contradicted, or represented imperfectly. Confirm no finding carries an evidence label stronger than
what was actually gathered. Confirm nothing performed during the audit mutated the site.

---

---

## Default definition of done

Use this when the per-audit framing does not supply a custom stop condition. Every line must be
checkable by someone who did not run the audit. "Looks thorough" is not a stop condition.

The audit is done when:

1. **Every priority journey has been walked end to end**, at the agreed viewports, and each one's
   drop-off point is named — or "none found" is stated explicitly. A journey that could not be
   completed is recorded with the reason, not omitted.
2. **The lead hypothesis is confirmed or killed**, on evidence, with the evidence named. "Probably"
   is not an outcome. An audit that only confirms its opening theory has not been run.
3. **Every question the framing raised is answered or explicitly declared unanswerable**, with the
   specific missing evidence named.
4. **Every finding carries one evidence label and all five axes**, scored separately.
5. **Every finding states its user consequence.** A finding without one is taste.
6. **Every recommendation is executable within the stated constraints**, or is quarantined into a
   separate list saying what access or authority it needs.
7. **What was not covered is stated** — sample sizes, blocked areas, untested surfaces — using
   "not observed in the sample" rather than silence.
8. **The report has been re-read against this playbook**, and anything missed, assumed, left
   untested, contradicted, or imperfectly represented is flagged in the report itself.

Fewer than eight met is a partial audit, and must say so in its header.

---

---

## Quality control

Standing Rule 19 is the stop condition, not a formality. Before claiming done:

- Reread `SKILL.md` and this file.
- Walk the definition of done line by line. State which lines are met, which are not, and why.
- List what was **missed, assumed, left untested, contradicted, or represented imperfectly.**
- Name every blocked or unreachable area as a limitation with its cause.
- Confirm no finding rests on an evidence label stronger than what you actually have.
- Confirm nothing you did mutated the site.
