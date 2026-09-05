# Phase 2 — Reader-native inline highlights (and Phase 2.5 topic tags)

### Phase 2 — Add Reader-native inline highlights

For each saved doc_id from Phase 1 that passed the pre-flight check:

**Step 1: Fetch html_content from Reader**

```bash
source ~/.youtube_api_keys

curl -H "Authorization: Token $READWISE_TOKEN" \
     "https://readwise.io/api/v3/list/?id=<doc_id>&withHtmlContent=true"
```

**Step 2: Read the analysis source**

- **YouTube videos:** Read the on-disk analysis at `~/.youtube_analyses/<video_id>_<title>.md` — the script's `process_video` saves this via `self.save_analysis()`.
- **Articles:** No on-disk analysis exists. `process_article` does NOT call `save_analysis()`, so the only copy of the 18-section deep-read is the `notes` field on the Reader doc itself. Pull it from the v3/list response you already fetched in Phase 0: `jq -r '.results[0].notes'`.

Extract atoms from these sections of the full template:

- 🧰 Action Inbox (H1, H2, H3 tiers within Literature Split Pad)
- 📚 Literature Split Pad (verbatim quotes already extracted)
- 🔖 Atomic Split Pad (Zettel candidates)
- ✅ Logical Validity → Fallacies (named with quotes/locations)
- 🛡️ DARVO Analysis (when present)
- 📝 Summary (for top-level claim highlights)

**Step 3: Map atoms to verbatim paragraph spans**

For **YouTube videos**, html_content has structure:

```html
<p>
  <span data-rw-transcript-version="2" data-rw-start="N.NN">text </span>
  <span data-rw-transcript-version="2" data-rw-start="N.NN">text </span>
  ...
</p>
```

For **articles**, paragraphs are standard `<p>...</p>` blocks.

For each atom, search html_content for the strongest matching passage. Prefer:

- Verbatim quotes already in the Literature Split Pad (these came from the transcript)
- Paragraphs containing the atom's key noun phrases or numeric anchors
- Complete thoughts that stand on their own when extracted

**Extract the candidate fragments programmatically — never retype them.** Split the live
`html_content` into an indexed list of complete elements, then select highlights *by index*:

```bash
~/.venvs/readwise-scripts/bin/python3 - "$JSON" <<'PY'
import json, re, sys
d = json.load(open(sys.argv[1]))['results'][0]
paras = re.findall(r'<p(?:\s[^>]*)?>.*?</p>', d['html_content'], re.S)
for i, p in enumerate(paras):
    print(f"[{i}] {p[:120]}")
PY
```

**Use exactly this pattern — `<p(?:\s[^>]*)?>`, not `<p[^>]*>`.** The `(?:\s...)` requires a
whitespace character or an immediate `>` after the `p`, so it matches `<p>` and
`<p class="...">` but cannot match `<path`. A bare `<p[^>]*>` matches `<path d="M0,0 L10,10 ...">`
inside any inline SVG chart, and because the closing `</p>` it then hunts for belongs to the
next *real* paragraph, one `<path>` swallows the whole SVG plus that paragraph into a single
multi-kilobyte pseudo-element. That poisons the index twice: you get a fake entry made of
coordinate data, and a real paragraph vanishes from the list — so every index after it shifts
and any highlight selected by index anchors to the wrong text. Measured on real article HTML,
2026-08-22. (The older `<p>.*?</p>` form has the opposite bug: it silently skips every
paragraph carrying attributes. The pattern above is the only one that handles both.)

Then print `repr(paras[i])` for the ones you picked and pass that exact string through. The
fragment you send must originate from Reader's own bytes — if you compose it from the scraped
source, the browser, or memory, it will not match.

**Step 4: POST inline highlights via the Readwise MCP tool**

Use `mcp__readwise__reader_create_highlight`. The raw `/api/v3/highlight/` URL is NOT a valid Readwise endpoint (returns 404).

```
mcp__readwise__reader_create_highlight(
  document_id="<doc_id>",
  html_content="<verbatim complete <p>...</p> from html_content>",
  tags=["atom/literature/h1", "<additional hierarchical tags>"],
  note="Optional context from analysis"
)
```

The tool returns `{"id": "<highlight_id>", "location": "<offset>", "url": "..."}`. A non-null `location` (e.g. `"36,37"`) confirms Reader matched the fragment to a real position in the doc.

**On `Text not found in document`, the fragment is wrong — not the paragraph.** Do not pick a
different paragraph to dodge the error, and do not conclude that a class of text is
un-highlightable. Re-extract that same paragraph per Step 3 and resend. Confirmed causes, all
of which vanish when the string comes from Reader's bytes:

- **Attribute stripping.** Reader drops `class`/`id` from the source markup. Fragments carrying
  `<p class="wp-block-paragraph">` from a Firecrawl scrape never match.
- **Smart punctuation.** Reader normalizes `'` → `’` (U+2019) and `"` → `”`/`“`. Typing the
  ASCII form fails; so does writing a literal `’` escape, which is sent as six characters.
  The MCP transport carries U+2019 correctly — this is verified, not assumed.
- **Trailing whitespace.** Many paragraphs end `...text.  </p>` with two spaces. Preserve them.
- **Entity escapes.** `&#39;`, `&amp;`, `&gt;&gt;` appear literally in stored HTML.

Parallelize the calls — each highlight is independent. 4 highlights = 4 concurrent MCP invocations.

**Target counts per doc:**

- Substantive long-form (45+ min podcasts, deep articles): 4-6 highlights
- Short tutorial videos (<10 min): 2 highlights
- Procedural/factual content (release notes, RC announcements): 1-2 highlights
- Fallacy-flagged content: include 1 highlight per major fallacy with `#fallacy/<slug>` tag

Each highlight should be a complete element (full `<p>...</p>`) rather than partial text — Reader's anchoring is more reliable that way.

### Phase 2.5 — Topic tags (MANDATORY, easy to forget)

Every saved doc MUST get **document-level topic tags** before it's "done". This is the step
most easily skipped — especially on **article** saves (videos often get tags in the save
payload; articles saved with only `url/location/category` come out untagged). Per the Reader
tag policy (`reader_tag_policy`): **topic tags only** — never dated, pipeline-state
(`deep-read`, `deepread-batch`, `lean`, `full`), single-letter, or source-format
(`youtube`, `video`, `article`, `podcast`, `transcript`) tags. Derive 3–6 topic tags from the
analysis's YAML `tags:` (strip any format/pipeline ones). Apply with
`reader_add_tags_to_document`. **Do NOT use a batch/pipeline tag** like `deepread-batch`.
