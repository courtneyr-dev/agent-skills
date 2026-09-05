---
name: readwise-synthesis-pass
description: "Use when the user says 'run the synthesis pass', 'synthesize my vault', 'weekly synthesis', 'do the sweep', or 'connect my notes'. The maker half; vault-hygiene-checker is the checker."
---

Base directory: `~/.claude/skills/readwise-synthesis-pass`

# Readwise Synthesis Pass

## Purpose

Each weekly run advances the vault's synthesis: migrate notes to the Konik conventions,
wire related notes together, and keep MOCs current. You are the **curator/migrator maker**;
`vault-hygiene-checker` is the **checker** that runs after you.

### Division of labor (corrected 2026-06-20)

**There is NO autonomous background maker.** The 2026-06-14 "division of labor" assumed a
"separate background/scheduled process creates Permanent notes off the backlog" — that was
**factually wrong** and is now corrected. Diagnosis 2026-06-20: no scheduled task creates
Permanent notes (`grep "Permanent Notes" ~/.claude/scheduled-tasks/*/SKILL.md` → nothing).
The only synthesis automation is `synthesis-desk-brief`, which is **surface-only** ("you never
write atoms… the user does the actual synthesis"). All Permanent notes that exist were created
by the user + Claude in interactive synthesis passes. The backlog grows (142 items as of
2026-06-20) precisely because **nothing creates except in explicit sessions like this one.**

So this skill **owns creation too** (bounded + resonance-filtered), alongside:

1. **Connection & curation** (PRIMARY) — wire orphans and related notes together (rotating sweep).
2. **MOC currency** — keep MOCs listing the notes that belong in them.
3. **Status migration** — legacy `developing`/`draft` → Konik `seedling/budding/evergreen`.
4. **Gap-fill creation** — create Permanent notes for `pending` backlog rows whose strong
   claims aren't yet captured by an existing Permanent. Bounded: resonance-filter hard (only
   what you can say in one line why it matters), and FIRST check whether an existing Permanent
   already covers the claim (connect, don't duplicate). Don't mass-create — a handful of the
   highest-resonance uncaptured claims per run. After creating, mark the row
   `backlog.py set --doc-id <id> --atoms done --moc done`.
5. **Checker pairing** — always run `vault-hygiene-checker` after.

If a backlog row is already `done`, the note exists: migrate and connect it, don't rewrite it.

Emphasis order (the user's call): **connect & curate first**, then gap-fill-create the strongest
uncaptured claims. (Historically this skill deferred creation to the nonexistent "maker," which
is why the backlog ballooned — don't repeat that.)

## When to trigger

- "run the synthesis pass" / "synthesize my vault" / "weekly synthesis" / "do the sweep"
- "connect my notes" / "what should link to what" / "update my MOCs"
- A weekly cadence (this is a registered loop)

Do NOT trigger for: single-doc deep reads (use `readwise-deep-read`), backlog status
questions (use `synthesis-backlog`), or vault verification only (use `vault-hygiene-checker`).

## Maker/checker discipline (non-negotiable)

This skill is the **maker**. It writes. After it finishes, you MUST run
`vault-hygiene-checker` to independently verify the synthesis (dead/fragile links, dup
imports/titles, MOC orphans, atomicity markers, link annotations). A run is not "done"
until the checker passes. The pair is registered in `Reports/_loop-registry.md`.

**The checker must re-derive, not re-read.** Its evidence comes from the filesystem — does
this file exist, does this link resolve, does this marker appear — never from re-reading the
maker's account of what it did. Whatever just wrote the notes has every reason to believe
they're good. Two corollaries, both learned the hard way in other domains:

- If the reason for passing something is "bounded", "harmless", or "probably fine", that's a
  guess. Check it against the filesystem instead.
- Never pass link B because it resembles link A that already resolved. Resolve B.

## Workflow

### Phase 0 — Plan (deterministic, no writes)

```bash
python3 ~/.claude/skills/readwise-synthesis-pass/sweep.py plan --sweep-size 10
```

Returns JSON with the run's work queue:
- `new_arrivals` — backlog rows logged since the last run (the fresh material)
- `backlog_unsynthesized` — standing backlog rows still needing atoms or a MOC home (the
  true synthesis queue; `counts` breaks it into `backlog_atoms_pending` / `backlog_moc_pending`).
  Rows flagged only `read: no` are comprehension debt, not synthesis work — they are counted
  separately as `backlog_read_only` and no longer inflate this list (2026-08-24: 810 of 819
  "unsynthesized" rows were read-only)
- `sweep_slice` — the rotating slice of older Permanent + Literature notes to revisit
- `orphans` — notes with no inbound AND no outbound links (366+ today; chip away, don't boil the ocean)
- `mocs` — the MOC list

The cursor rotates the sweep each run so coverage moves through the vault over weeks.

**Phase 0b — triage the plan before doing any work.** Read the queue and decide where this
run's effort goes, then say so in the report. The three cases:

- **Sweep slice already clean** (all `budding`+, all annotated links) — Phases 1 and 3 are
  no-ops. Say so and move the run's effort to gap-fill creation. This is common now that the
  vault has converged; don't manufacture edits to look busy.
- **Nothing resonant in the backlog** — if no `pending` row carries a claim you can say in one
  line why it matters, **create nothing.** Do Phases 1–2 only, write the report, run the
  checker, stop. A run that connects and creates zero notes is a valid run.
- **Nothing to do at all** — clean slice, no resonant candidates, MOCs current. Write a
  three-line report saying so, record the run to advance the cursor, and exit. Do NOT proceed
  through the phases out of habit.

### Phase 1 — Connect (primary, uncapped)

For the `sweep_slice` + this run's `new_arrivals` + any orphans that intersect them:
- Read each note. Find notes it SHOULD link to (topical overlap, shared MOC, same source).
- Add connections as annotated wikilinks in a `## Links` section:
  `- [[Target Note]] — because <extends|contrasts|applies-in|evidence-for>`
- Bare `[[wikilinks]]` are allowed only inline in prose with a contextual sentence.
- Prioritize orphans from `orphans` that relate to this run's material; log the rest as
  carried-forward (the rotating cursor will reach them in later weeks).

### Phase 2 — MOCs (primary, uncapped)

For each MOC in `mocs`, add notes that belong under it but aren't listed yet (especially
this run's new/updated notes). Keep MOC sections coherent; flag any MOC that has grown
unwieldy for a future split. Do not invent new MOCs without a clear cluster.

### Phase 2b — Guide pages (check every run, edit only on real change)

Guide pages are curated reader entrances, not MOCs — they cite a small, best-available set.
For each, ask: did this run's material add a source or claim strong enough to change what a
beginner should read first? If yes, update it; if no, write "guide pages: no change" in the
run report. Current guide pages:

- `Projects/<your-wiki>/wiki/<page>.md` — NAR beginner
  entrance. **PUBLISHED — public readers.** Rules: link only published targets (never
  `Projects/Religious Research/` or `Projects/NAR Beginner Entrance/`); every book gets
  an Amazon/Kindle link, every video source a direct watch URL; keep the resource list small
  (replace, don't accumulate). Also close any matching open thread in
  `Projects/NAR Beginner Entrance/open-threads-and-adjacent-work.md` (confirmed 2026-08-16:
  this folder IS included in Obsidian Publish, not private — but it's working/draft notes, not
  a curated citation, so the guide page still must never link it directly; e.g.
  Christerson & Flory full ingest, Wagner primary texts, spiritual-covering concept page).
  After any edit, note in the report that the public copy updates only when the user
  republishes via Obsidian Publish.

### Phase 3 — Status migration (primary)

For the `sweep_slice` + any notes created since last run: migrate `status:
developing`/`draft` → `seedling/budding/evergreen` per the maturity rule in Phase 4. This is
how the vault converges on the Konik vocabulary over weeks.

**Gap-fill creation (this skill owns it — there is no other maker):** for `pending` backlog
rows whose strong claims aren't already captured by an existing Permanent, create the note per
`article_template` conventions, resonance-filtered (only what you can say in one line why it
matters; <2 strong claims → Fleeting). Check existing Permanents FIRST (connect, don't
duplicate). After
creating from a backlog row, mark it:
```bash
python3 ~/.claude/skills/synthesis-backlog/backlog.py set --doc-id <id> --atoms done --moc done
```
Do NOT recreate or rewrite notes for rows already marked `done` — migrate and connect them.

### Phase 4 — Promote / update

- The vault is **mid-migration** to the Konik status vocabulary. Existing notes use
  `status: developing` (122) / `draft` (40); migrate them to `seedling/budding/evergreen`
  as the sweep reaches them. Today's batch is the first migration cohort.
- Status by maturity: `seedling` = new / no inbound links; `budding` = ≥1 inbound + ≥1
  outbound annotated link; `evergreen` = linked from ≥2 Permanent notes **AND tended
  across ≥2 runs** (do NOT mark a note created this run evergreen on link-count alone —
  evergreen means cultivated over time, not just well-connected on day one).
- Update notes flagged stale or newly connected.

### Phase 5 — Report, record, check

1. Write a dated run report to `Reports/synthesis-pass-YYYY-MM-DD.md`:
   notes created/updated, links added, MOCs touched, orphans fixed, and a
   "needs human eyes" section for anything you weren't confident about.
2. Record the run (advances the watermark + rotating cursor + run log):
   ```bash
   python3 ~/.claude/skills/readwise-synthesis-pass/sweep.py record \
     --created N --updated N --links N --mocs N --orphans-fixed N \
     --swept 10 --report "Reports/synthesis-pass-YYYY-MM-DD.md"
   ```
3. **Run `vault-hygiene-checker`** and address anything it flags. Not done until it passes.
4. **Placeholder rule: a run that leaves placeholders isn't done.** If `--fix-reciprocal`
   inserted `⚠️ … annotate the relationship` placeholders — in this run or left over from any
   earlier one — annotating them is part of THIS run, not a follow-up. Grep the vault for the
   placeholder marker before writing the report; the report must state the count remaining,
   and that count must be zero to record the run as complete. (237 placeholders once sat for
   eight days because insertion was treated as done — a half-finished run makes the vault look
   more connected than it is.)

## Konik/Zettel conventions (what you write)

Authoritative source: `~/.claude/skills/readwise-deep-read/article_template.txt` (the V2 LIT/PERMANENT/
FLEETING spec). Key rules:

- **Naming:** Fleeting / Literature / Permanent. Never "Atomic" or "Zettel" as a type
  name — atomicity is a property check, not a type. Set `type:` in YAML accordingly.
- **Literature notes** (`Resources/Literature Notes/`): open with the five Konik triage
  callouts (Lingering Questions, Article Ideas, Cross Reference, Fiction & Worldbuilding,
  Vocabulary); bib capsule; Author's thesis (Adler Q1+Q2); key arguments (≤3); H3 claim
  atoms — each `### <≤10-word present-tense claim>` + `> [!quote] ID:rw_<id>` verbatim +
  where/why; Permanent candidates; processing checklist. YAML: type, status, created,
  source_title, author, citekey, tags (≥5–7 topic tags).
- **Permanent notes** (`Resources/Permanent Notes/`): one declarative present-tense
  **Claim in the user's voice** (never a pasted quote — quotes only in an Evidence block,
  and only if aphoristic); Scope & conditions; `## Links` with ≥1 annotated link; end the
  claim block with `<!-- atomicity: 1 idea ✓ -->`. If "and"/"also" is needed, it's two
  notes. YAML: type, id (timestamp), status (seedling default), created, origin, tags.
- **Atomicity:** one idea per atom and per Permanent claim. Every Permanent candidate block
  ends with `<!-- atomicity: 1 idea ✓ -->`.
- **Link annotations:** every wikilink in a `## Links` section carries an annotation
  explaining the relationship: `- [[Title]] — <why these connect>`. An informative
  free-form annotation (e.g. "the specific bottleneck AI amplifies; generation got cheap
  so review is now the binding constraint") is the goal and is PREFERRED over a bare typed
  keyword. The `extends | contrasts | applies-in | evidence-for` types are a fallback
  vocabulary, not a replacement — **never degrade an existing rich annotation to a bare
  type word.** Bare un-annotated `[[links]]` are what needs fixing; good prose annotations
  are already done.
- **Tags (Konik 7, use only these):** `#xref` (default) · `#bmf` · `#addendum` ·
  `#articleseed` · `#storystem` · `#share` · `#aphorisms`. Annotations with `?` → Lingering
  Questions; one-word definitions → Vocabulary; untagged → `#xref`.
- **Decide, don't ask:** emit committed defaults (which atoms, which tags, whether to
  promote). the user reviews via the run report + Obsidian version history, not a prompt.

## Vault paths

- Readwise sources: `Resources/Readwise/{Books,Articles,Podcasts,Tweets,Snipd}`
- Literature Notes: `Resources/Literature Notes/`  ·  Permanent Notes: `Resources/Permanent Notes/`
- MOCs: `Resources/MOCs/`  ·  Templates: `6. Templates/`
- Backlog (queue): vault-root `_Synthesis Backlog.md` (via `synthesis-backlog/backlog.py`)
- Run reports + loop registry: `Reports/`
- State (watermark + cursor + log): `state.json` beside this skill

## Boundaries

- Does NOT save to Reader or add Reader highlights — that's `readwise-deep-read`.
- Does NOT re-scan the whole vault every run — backlog + rotating sweep only (by design).
- Does NOT invent MOCs or force notes from thin sources — resonance filter governs.
- Never leaves a run unverified — `vault-hygiene-checker` is mandatory after.
- For devotional/liturgical Readwise notes, create Literature notes only if there's a
  genuine analytical claim; otherwise skip (mirrors deep-read's Phase 2 policy).
- **Division of labor (corrected 2026-06-20): there is NO autonomous background maker — this
  skill connects + migrates + checks AND gap-fill-creates (bounded, resonance-filtered).**
  Never rewrite a note for a backlog row already `done` — migrate its status and improve its
  connections instead. Create for still-`pending` rows whose claims aren't already captured by
  an existing Permanent. See the Division of Labor section under Purpose.
