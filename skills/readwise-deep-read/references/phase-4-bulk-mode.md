# Phase 4 — Bulk mode (multi-doc inbox processing)

### Phase 4 — Bulk mode (multi-doc inbox processing)

For processing multiple already-saved docs at once (morning inbox triage, batch-archive workflows). This jumps to Phase 2 for each doc, then bulk-archives.

**1. List the target location**

```bash
source ~/.youtube_api_keys
curl -s -H "Authorization: Token $READWISE_TOKEN" \
     "https://readwise.io/api/v3/list/?location=new&pageSize=100" \
  | jq '.results | map({id, title, category, has_deep_read: ((.notes // "") | contains("Refactor Appendix"))})'
```

**2. Phase 0 per doc — ESSENTIAL in bulk mode**

For each doc, check `html_content` for the no-subtitles sentinel (`<p>Unfortunately, Youtube does not provide subtitles for this video</p>`, ~71 bytes) BEFORE attempting Phase 2. The deep-read pipeline has two independent transcript fetches: the Python script's local yt-dlp (feeds Claude analysis → notes) and Reader's own scrape at v3/save time (produces html_content). These succeed independently — script can produce a full analysis while Reader's scrape returns the sentinel. The doc looks "complete" in the inbox (rich notes, master-DB highlights), but Phase 2 anchors will fail because there's no html_content to match against. Skip Phase 2 for these docs and flag for the YouTube subtitle fallback hierarchy below.

**3. Atom extraction handles H3 OR H4 headings**

The deep-read template produces atom headings at H3 OR H4 inside the Literature Split Pad depending on Claude's render — both are valid. Walk both levels: `re.split(r"\n(?=####?\s)", literature_pad_section)`.

**4. Decode HTML entities before string matching**

Reader stores `html_content` with entities literal: `weren&#39;t`, `&gt;&gt;`, `&amp;`. Run `html.unescape()` on both sides before any substring comparison, or every apostrophe and chevron in transcripts breaks the match.

**5. Strip `<span>` tags for YouTube transcripts**

YouTube transcript html: one `<p>` containing many timestamped `<span>` chunks. The verbatim text needs span-stripping (`re.sub(r"<[^>]+>", " ", p)`) before matching against analysis quotes — but the POST to `reader_create_highlight` MUST use the original `<p>` with spans intact (Reader anchors by exact bytes).

**6. Word-overlap fallback for video transcripts**

Verbatim matching fails for YouTube content. Claude's "verbatim quote" in the analysis silently drops filler words ("I would say", "you know") when rendering transcript content — it's actually a clean paraphrase. For articles, verbatim matching usually works; for videos, fall back to word-overlap scoring: tokenize the atom's quote + claim heading (stripping stopwords), score each `<p>` by shared content tokens, return the best-scoring paragraph above threshold (default: ≥3 shared content tokens AND ≥30% of quote tokens matched). Tune downward only if you accept lower-confidence anchors.

**7. Bulk archive via `reader_move_documents`**

```
mcp__readwise__reader_move_documents(
  document_ids=["<id1>", "<id2>", ...],
  location="archive"
)
```

Single call handles up to 50 docs. Rate-limited 20/min (shared with `reader_bulk_edit_document_metadata`). For >50 docs, batch into multiple calls with sleeps.

**8. Skip cleanly when no Literature Split Pad exists**

Manually-saved docs (Raycast, browser extension, RSS) lack the deep-read template entirely. Don't force a fallback — record "no analysis" and archive per user intent. The skill is anchored on the analysis structure; without it, there's nothing to map.

**9. For docs flagged in Phase 0 (no html_content)**

Apply the **HARD RULE from Phase 0**: never accept a transcript-less doc in the inbox. Recover the transcript via the fallback hierarchy and re-create the doc with the transcript embedded (`/api/v3/save/` with `html=`, or `reader_create_document` with `markdown=`), then archive the empty original. If the cascade fully fails, queue it (`status: transcript_unavailable`, backoff) for the daily retry launchd AND archive the empty doc out of the inbox. Master-DB-only highlights on a sentinel doc are **not** an acceptable end state — that was the old policy and is superseded. Confirmed working end-to-end 2026-06-10 (CLI/MCP video ZR6U4TN8-Cw: yt-dlp recovered 12K-word transcript → new doc 01ktskpygwqphvg89bhm0jyb33 with inline highlights → empty original archived).
