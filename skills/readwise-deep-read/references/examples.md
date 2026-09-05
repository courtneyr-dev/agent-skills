# Examples

## Examples

### Example 1: Morning queue

User: "process these from my morning queue"

```
https://www.youtube.com/watch?v=abc123
https://example.com/article-1
https://example.com/article-2
```

Skill:

1. **Phase 0:** Pre-flight check each URL after save — confirm content scraped
2. **Phase 1:** Run script with all 3 URLs → saves 3 docs with full 18-section notes, writes analysis files
3. **Phase 2:** For each saved doc, fetch html_content, map analysis atoms to verbatim passages, POST 4-6 inline highlights with hierarchical tags
4. **Phase 3:** Print Reader URLs, suggest sync

### Example 2: Single URL deep-read

User: "deep read this: https://www.youtube.com/watch?v=xyz789"

Skill: Same as above with 1 URL. Output: 1 Reader doc with full 18-section notes AND 5-8 inline highlights.

### Example 3: Already-saved doc

User: "add inline highlights to the doc I already saved at https://read.readwise.io/read/01ks188zsaefpj5yd0pk9cyar9"

Skill: Skip Phase 1, jump to Phase 0 pre-flight check, then Phase 2 for that doc_id.

### Example 4: YouTube with missing subtitles

User pastes a YouTube URL → Reader saves but returns empty html_content.

Skill:

1. Phase 0 detects "Unfortunately, Youtube does not provide subtitles" sentinel
2. Falls back to `yt-dlp --write-auto-subs`
3. If still empty, calls `vidiq_video_watch`
4. Saves transcript as a NEW Reader doc via `reader_create_document` with `markdown=<transcript>`
Archives the empty original
6. Proceeds to Phase 2 against the new doc_id

### Example 5: Mixed batch (videos + articles)

User pastes 5 YouTube URLs + 3 article URLs.

Skill:

1. Phase 1 runs the script on all 8 — the script handles both content types with the full template
2. Phase 0 pre-flight checks each saved doc
3. Phase 2 fetches html_content for each scrapeable doc and creates appropriately-scaled inline highlights (substantive videos get 4-5, short tutorial gets 2, articles get 3-4)
4. Any subtitle failures cascade through the fallback hierarchy
5. Phase 3 confirms with Reader URLs
