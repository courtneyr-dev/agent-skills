# YouTube Subtitle Fallback Hierarchy

## YouTube Subtitle Fallback Hierarchy

Apply this cascade when Phase 0 pre-flight check detects missing subtitles:

```
1. yt-dlp --write-auto-subs --skip-download --sub-langs en --sub-format vtt <url>
   (auto-generated captions from YouTube; quality varies but usually serviceable)

2. If still no transcript, use vidIQ MCP tool: vidiq_video_watch
   (returns structured markdown walkthrough; works for most videos)

3. If still no transcript, audio + Whisper:
   yt-dlp -x --audio-format mp3 <url>
   whisper <file>.mp3 --model base
   (free local) OR call OpenAI Whisper API (~$0.006/min)

4. Pass the resulting transcript to reader_create_document with markdown=<transcript>
   — creates a NEW Reader doc with content embedded, bypassing Reader's scrape entirely.
   Note: this generates a new doc_id; archive or delete the empty original.

5. Add unrecoverable URLs to ~/.youtube_processing_queue.json with:
   { "status": "transcript_unavailable",
     "next_retry": "<ISO datetime>",
     "attempts": <N>,
     "backoff_minutes": [5, 30, 240, 1440] }

6. Exponential-backoff retry: 5min → 30min → 4hr → 24hr before giving up
```

**Why this hierarchy:** Reader scrapes once at save time. If subtitles aren't ready yet, the scrape returns the empty sentinel string and Reader doesn't re-scrape automatically. The API also does NOT allow updating an existing doc's `html_content`. So either the content gets injected at save time via `markdown=<transcript>`, or the doc is permanently empty.
