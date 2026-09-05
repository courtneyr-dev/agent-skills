---
name: readwise-methods-review
description: "Use when the user says 'weekly methods review', 'run the methods review', 'readwise prompting review', or 'what did I read that changes how I work'; writes to Projects/Readwise Prompting Methods Review/."
---

# Readwise methods review

## What this is for

One question, asked of a week of reading: **does anything here change how the user works with models?**

Not "does it discuss AI." Most reading corpora are mostly domain material with a minority of AI commentary, and most of that commentary is forecasting rather than method. Judge each item against what you would actually do differently on Monday.

The baseline to beat is high. You already use structured task prompts, standing instructions, investigation loops, adversarial subagents, project notes, and persistent vault knowledge. "Be specific in your prompts" is not a finding.

## Access — decided, don't re-derive

**Use the Readwise MCP server** (`mcp2.readwise.io`, OAuth). This was settled 2026-07-25:

- `@readwise/cli` is **not installed** and there is **no `READWISE_TOKEN`** in the environment, shell profile, or `~/.config/`. The `readwise-cli` skill documents a path that does not work on this machine.
- Browser automation is strictly worse — MCP returns complete document bodies.
- Re-check the environment each run in case a token appears, but expect MCP. **Never print or store credential values.**

## Workflow

### Phase 0 — window and fetch

```bash
python3 ~/.claude/skills/readwise-methods-review/triage.py window
```

Prints the local window, the `updated_after` value to pass to the API, and the output filename. Then fetch both locations, saving each raw response:

- `reader_list_documents(location="new", updated_after=<from above>, limit=100)`
- `reader_list_documents(location="archive", updated_after=<from above>, limit=100)` — **paginate**, archive runs 100+/week. Follow `nextPageCursor` until null.

Request explicit `response_fields` including `saved_at`, `last_moved_at`, `word_count`, `category`, `author`, `summary`, `tags`. Omitting the field list returns everything including bodies and blows the response limit.

Large responses get auto-persisted to a file path in the tool result. Feed those paths straight to triage.

### Phase 1 — triage (deterministic)

```bash
python3 ~/.claude/skills/readwise-methods-review/triage.py triage <dump1.json> <dump2.json> ...
```

Emits the coverage receipt, the out-of-window list, inaccessible and thin items, and a source-inventory table with blank Decision/Rationale columns. **The script owns the arithmetic. Don't redo it by hand.**

Three gotchas it encodes, all learned the hard way:

1. **`updated_after` filters on `updated_at`**, which fires on any metadata touch — a tag edit pulls in month-old items. The script applies the real rule: in-window if `saved_at` **or** `last_moved_at` falls inside. State this rule in every review, along with its limit: **it does not capture "read but not moved."** `first_opened_at` is null for most items and `reading_progress` is 0 almost everywhere, so read-state is not usable.
2. **Every YouTube save appears twice** — one `video` record and one `article` record (the transcript), same title, different ids, from the deep-read pipeline. ~13 pairs/week. The script keeps the one with text.
3. **Videos and podcasts have `word_count: null`**, so thinness can't be screened for them by word count.

### Phase 2 — select candidates and read them fully

Pick the items plausibly carrying a method and **retrieve their complete bodies** with `reader_get_document_details`. Typically 8–12 of ~100.

Where to look, in rough order of past yield: engineering postmortems and security writeups · maintainer workflow posts · agent/harness design · explicitly-labelled prompt and context engineering · testing and code review · research and documentation workflow.

**The 2026-07-25 finding on this:** the assumption that the best material hides in unlabelled sources was *half* right. Two of the three strongest findings came from a hosting operator's security pipeline and a PHP maintainer's bug-mining session — but the single densest source was an explicit context-engineering post from Anthropic. Read the labelled sources too; they're just no longer sufficient.

### Phase 3 — evaluate

Score each retained finding 1–5 on **novelty** (vs. your documented approach), **evidence**, **utility**, **specificity** (can it become a concrete behavior, instruction, test, or skill?), and **adoption cost**. Then assign one of: **adopt now** · **test next** · **bank for later** · **do not adopt**.

The total is not the decision. Explain any recommendation that diverges from the score.

### Phase 4 — write

To `$VAULT_DIR/Projects/Readwise Prompting Methods Review/`:

- `weekly-review-YYYY-MM-DD.md` (window end date) with ten sections: coverage receipt · executive findings · recommended changes · prompt improvements · skill opportunities · workflow and method improvements · experiments · ideas reviewed but not adopted · source inventory · assumptions, gaps, open threads
- one topic note per substantial retained theme — never for a passing mention
- update `index.md`: review period, links, cumulative adopted methods, open experiments, latest review date

Match the vault's conventions from `Projects/<your-wiki>/wiki/` — YAML frontmatter with title/type/created/updated/sources/tags/related, full-path wikilinks, prose over bullet-dumps.

### Phase 5 — verify

```bash
python3 ~/.claude/skills/vault-hygiene-checker/check_vault.py \
  --scope "Projects/Readwise Prompting Methods Review" --days 1
```

Expect zero dead wikilinks. Two flags are known false positives on this folder: "not registered in any MOC" (these are project notes, registered in `index.md`) and a title-overlap hit on `index`.

## Non-negotiables

**Attribution.** Name the actual author. Reader's `author` field is often just a domain (`youtube.com`, `pluralistic.net`) — dig into the content for the real name and say so when you infer it. Never write a source's claim in the user's voice.

**The `notes` field is a trap.** Archived items carry full deep-read analyses written by `readwise-deep-read`, including "Permanent Candidates" written *in the user's voice* and Action Items assigned to WordPress teams no source mentions. Excellent for triage. **Never quote it as the author.** Only `> [!quote]` blocks inside it are verbatim.

**Label the four registers separately, every time:** author-stated claim · demonstrated evidence · reviewer inference · reviewer recommendation.

**Quote minimally.** Enough words to support the finding, never long passages.

**Don't inflate.** A finding that restates something you already does is "already covered," not a finding — unless it adds a meaningful variation, limitation, or implementation detail.

**Bias checks to run on every retained finding:** survivorship (does the source report only what worked?) · vendor interest · self-reported metrics presented as audited · false precision (invented numbers that sound empirical) · anecdote generalized to a rule · newer/more-complex assumed better. Prefer the simplest method that reaches the needed reliability.

**Never claim complete coverage** unless the inventory, pagination, retrieval results, and inaccessible-item accounting support it. Full-text is normally retrieved for ~10% of items; say so plainly and name the item most likely to have been a miss.

## Boundaries

- Inbox and Archive only. `later`, `shortlist`, and `feed` are out of scope — say so in the receipt rather than silently omitting them.
- Does not save to Reader, add highlights, or move documents. Read-only against Readwise.
- Does not write Permanent notes — economic, governance, and theological material goes to `readwise-synthesis-pass`, not here.
- Does not edit `~/.claude/CLAUDE.md` or skills as part of the review. Findings *recommend* changes; applying them is a separate, approved step.

## History

- **2026-07-25** — first run, and the source of everything above. 123 items returned, 122 in window, 108 unique, 10 full-text, 8 retained findings. The method was frozen into this skill the same day, per the freeze-the-session rule in `credit-routing`.
