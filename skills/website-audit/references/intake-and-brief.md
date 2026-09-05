# Intake and brief

Load at Phase 4. This file owns the conversational half of the audit: what to ask, what to
infer, what blocks, and the shape of the brief the user approves before execution.

## The rule that makes intake feel conversational

Every field the master playbook's framing block needs must end up **filled** — but filled is
not the same as *asked*. Each field resolves one of three ways:

- **Ask** — the answer changes the audit and you cannot get it from the site.
- **Infer** — Phase 2 recon answers it. State it as an assumption for correction. Never ask.
- **Default** — the playbook already supplies a default. Apply it silently; surface it in the brief.

Never emit more than one batch at a time, and never more than about six questions in a batch.
Number them, and give your recommended answer with each so a busy user can reply "1, 3, yes,
rest as proposed."

## Field coverage map

Every field in the playbook's Context, Instructions, and Content-and-Access blocks, and how
intake resolves it. **Nothing here may be dropped.**

| Playbook field | Resolution | Batch |
| :--- | :--- | :--- |
| Role | Default: senior cross-functional website auditor (UX research, IA, interaction design, content design, accessibility, responsive, front-end quality). Replace only if a narrower lens changes the work. | — |
| Background | Ask | 1 |
| Why this audit matters | **Ask — blocking.** No decision, no audit. | 1 |
| Organization or site purpose | Infer from recon, confirm | 1 |
| Primary audiences | Infer, label hypotheses, confirm | 1 |
| Most important user tasks (3–7) | Infer, label hypotheses, confirm | 1 |
| Business / organizational / publishing goals | Infer, confirm | 1 |
| Known constraints (CMS, theme, plugins, budget, timeline, governance, legal, brand, editorial, technical) | Partly infer platform; ask the rest | 2 |
| Action | Fixed by this skill: comprehensive, evidence-based, read-only audit | — |
| Complexity | Default `deep` (full investigation); `quick`/`standard` override | — |
| Required method | Default blank — auditor selects and justifies | — |
| Priority pages or journeys | Ask, seeded from recon | 1 |
| Explicit exclusions | Ask | 2 |
| Required standards | Ask; default WCAG 2.2 Level AA | 2 |
| Definition of done | Default from playbook; confirm in brief | 3 |
| Primary URL | From `$ARGUMENTS` | — |
| Additional domains / environments | Ask | 2 |
| Source material (design system, brand guide, sitemap, repo, prior audit, research) | Ask | 2 |
| Presentation (live / local / staging / files / screenshots / mixed) | Infer live; confirm if anything else is in play | 2 |
| Authenticated roles available | **Ask — blocking if any non-public area is in scope.** | 2 |
| Analytics, search data, support requests, user feedback | Ask — this is the only route to *Measured* and *User-reported* evidence | 2 |
| Comparison sites | Ask; include only when comparison serves a defined decision | 3 |
| Browser / device / assistive-technology constraints | Ask | 3 |
| Project-notes location | Default `$VAULT_DIR/Projects/<site>-audit/`; `--notes` overrides | — |
| Site ownership *(health module)* | **Ask — gates Tier B and Tier C** | 2 |
| Stack detail *(health module)* | Infer CMS from recon; ask the rest only when Tier B is in scope | 2 |
| Intentional choices to not flag *(health module)* | Ask when Tier B is in scope | 2 |
| Third-party scan consent *(health module)* | Ask when the site is non-public, pre-launch, or a client's | 2 |

## Batch 1 — Purpose, audience, tasks

Open by showing what recon already told you, so the user corrects rather than dictates:

> From the site I'm reading this as **[purpose]**, aimed mainly at **[audiences]**, where the
> jobs that matter look like **[task 1], [task 2], [task 3]**. Correct anything I have wrong.

Then ask, at most:

1. **What decision does this audit feed, and by when?** — *blocking.* Everything downstream
   scales to this: a pre-redesign audit, a procurement check, a "why did conversions drop",
   and a quality baseline produce different reports from the same site.
2. **What do you already know or suspect?** Prior audits, complaints, analytics anomalies,
   the thing that made you ask.
3. **Which pages or journeys matter most?** Three to seven. Seed with what recon suggests.
4. **What would make this audit a waste of your time?** Flushes out the unstated constraint —
   "we can't change the theme", "leadership already decided on a rebuild."

## Batch 2 — Scope, evidence, constraints

5. **What is explicitly out of scope?**
6. **Anything beyond the public site** — staging, subdomains, an app, authenticated areas?
   If yes: **do you own or have written authorization to audit it, and are credentials being
   supplied through an authorized channel?** *Blocking.* Never accept a password typed into
   chat; ask for a credential manager, an authorized test account, or drop the area from scope.
7. **Do you have analytics, site-search logs, support tickets, session recordings, or user
   research you can share?** Without these, every claim about user behavior stays *Hypothesis*.
   Say that plainly — it changes what the report can conclude.
8. **Standards to hold it to?** Default WCAG 2.2 AA. Ask if a sector rule applies (public
   sector, healthcare, education, EAA/Section 508).
9. **Constraints I should design recommendations around?** CMS and theme (name what recon
   found), budget, timeline, governance, brand, editorial, legal.
10. **Source material?** Design system, brand guide, sitemap, repository access, prior audit.

**Health battery questions.** Ask 11–13 only when they change what runs:

11. **Do you own this site?** Tier A of the health battery runs either way. Tier B — the
    accessibility plugin, SEO plugin, AI visibility, and CMS Site Health dashboards — needs
    admin access. Tier C, clearing caches before measuring performance, needs `--own-site`
    plus your explicit yes here.
    ➡️ *Recommend yes to the cache clear if you own it: a stale CDN cache produces false
    performance findings, and without it I have to label the numbers "cache state unknown."*
12. **Stack details** — CMS and theme (recon suggests [X]), hosting, performance plugin, SEO
    plugin, accessibility plugin, security/CDN layer, object cache, AI visibility tool.
    *Only needed if Tier B is in scope.*
13. **Anything I should record but not flag as a defect?** Inactive plugins kept on purpose,
    scheduled-event warnings that are expected on your host, headers your WAF controls.
    ➡️ *These get marked "intentional — recorded, not actioned." Flagging a deliberate
    decision as a bug costs credibility on the findings that matter.*

**Consent check.** If the site is pre-launch, staging, private, or a client's, say plainly
that the Tier A checks send the URL to eight third-party services (Google, WebAIM, Qualys,
websitecarbon, isitagentready) and get a yes before running them.

## Batch 3 — Output and stop condition

11. **Who reads the report, and what do they need to do with it?** An engineer, an executive,
    and a procurement committee need different artifacts from the same findings.
12. **Comparison sites?** Only if a specific decision depends on the comparison.
13. **Devices, browsers, or assistive technology to prioritize?** Anchor to the site's actual
    traffic if analytics are available; otherwise state the sample you will test.
14. **Definition of done** — present the playbook default and ask whether to tighten it.

## Blocking vs inferable

**Blocking** — stop and ask; proceeding would be unsafe, unauthorized, or would make the work
useless if wrong:

- no URL supplied
- any non-public area in scope without confirmed authorization
- credentials needed but no authorized channel to supply them
- a legal, contractual, or safety constraint hinted at but unstated
- no decision the audit informs — a report nobody acts on is not worth producing

**Inferable** — assume, label, move on. Everything else. Write each as
`Assumption — [statement]. Correct this if wrong; it affects [what].`

## Brief format

Present this once, get one confirmation, then run without re-asking.

```
## Audit brief — <site>

**URL(s)**            <primary + any additional in scope>
**Decision this feeds** <the decision and its deadline>
**Purpose**           <what the site is for>
**Audiences**         <primary audiences>          [confirmed | hypothesis]
**Priority tasks**    <3–7 tasks>                   [confirmed | hypothesis]
**Complexity**        quick | standard | deep
**Standards**         <e.g. WCAG 2.2 AA>
**Evidence available** <analytics / research / support data, or "none — see limits">
**Health battery**    Tier A · Tier B <run|skipped, why> · Tier C cache clear <yes|no>
**Constraints**       <CMS, theme, budget, timeline, governance, brand, legal>
**Notes location**    <path>

### In scope
- …

### Explicitly out of scope
- …

### Assumptions
| # | Assumption | Affects | Correct it if… |
|---|---|---|---|

### Companion skill stack
| Skill | Assignment | Why it earns its place |
|---|---|---|

### Grilling outcome
Accepted: …    Rejected: … (and why)

### Definition of done
- [ ] …
```

## Fallback adversarial checklist

Use when `mattpocock-skills:grilling` is unavailable, errors, or `--no-grill` was passed.
Answer each in writing before intake closes; record the pass in the brief.

1. Is the invocation flow unambiguous — does the user know what happens next at every step?
2. Do the intake questions collect information that **changes the audit**, or information that
   merely looks thorough? Cut anything whose answer changes nothing.
3. Does the skill ask too much before doing anything useful?
4. Does it distinguish **missing evidence** (no analytics → claims stay Hypothesis) from
   **missing preferences** (no stated report audience → pick a default)? These are not the same
   gap and must not be handled the same way.
5. Can routing adapt when the installed skill catalog changes, or is a skill name hardcoded?
6. Is every planned action read-only? Name the riskiest step and say why it cannot mutate.
7. Is the definition of done **testable** — could a second auditor check each line and agree?
8. Do the references load progressively, or does Phase 1 drag the whole playbook into context?
9. Is the report actionable, or long for its own sake? What would you cut?
10. What happens when a phase fails — the site blocks you, a companion errors, a journey is
    unreachable? Each needs a stated fallback, not a stall.
