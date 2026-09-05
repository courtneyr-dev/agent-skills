# Phase 0 — Pre-flight check

### Phase 0 — Pre-flight check

For each URL, after the script saves and Reader scrapes:

```bash
source ~/.youtube_api_keys
curl -s -H "Authorization: Token $READWISE_TOKEN" \
     "https://readwise.io/api/v3/list/?id=<doc_id>&withHtmlContent=true" \
  | jq -r '.results[0].html_content' \
  | head -c 200
```

**HARD RULE — never accept a transcript-less doc in the inbox.** If `html_content` is empty/null OR its only body text is the no-subtitles sentinel (`Unfortunately,?\s+Youtube\s+does\s+not\s+provide\s+subtitles`, ~71 bytes), the doc is **not acceptable** and must not be left sitting in the inbox (`location=new`). Take these steps, in order, before moving on:

1. **Try to recover the transcript by any means** — run the full YouTube Subtitle Fallback Hierarchy below (yt-dlp `--write-auto-subs` → vidIQ `vidiq_video_watch` → audio + Whisper). Don't stop at the first failure; exhaust the cascade.
2. **If recovered:** create a NEW Reader doc with the transcript embedded (POST to `/api/v3/save/` with `html=<wrapped paragraphs>` — or `reader_create_document` with `markdown=`), carrying over the original `notes`/tags, then **archive the empty original** so the inbox only ever holds docs with real content. Proceed to Phase 2 on the new doc.
3. **If still unrecoverable after the whole cascade:** add it to the retry queue (`~/.youtube_processing_queue.json`, `status: transcript_unavailable`, with exponential backoff) so the daily `com.you.youtube-queue-retry` launchd retries it (most often YouTube simply hasn't finished generating auto-captions for a fresh upload), and **move the empty doc out of the inbox** (archive it) so it isn't mistaken for a completed read. Report the queued URL to the user.

Do NOT proceed to Phase 2 highlights, and do NOT consider the doc "done," until it has a real transcript. Accepting master-DB-only highlights on a sentinel doc is **not** an acceptable resolution — recover the transcript or queue+archive.
