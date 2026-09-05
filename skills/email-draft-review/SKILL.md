---
name: email-draft-review
description: "Use when the user says 'draft my email replies', 'handle my inbox', 'triage Gmail', or asks to prepare (never send) replies to the emails that need answers."
---

# Email Draft + Tab Review

Inbox triage → drafts in the user's voice → each draft opened in its own tab for manual send. Modeled on the "draft everything, open for review" pattern; nothing leaves the outbox without the user clicking send.

## Hard rules

1. **Never send.** Use Gmail `create_draft` only. No send calls, ever, even if asked mid-flow — confirm first in a fresh exchange.
2. **Human-voice pass required.** Every draft runs through the anti-slop-git-writing sensibility: no AI-tells, no "I hope this email finds you well", no em-dash overload, no bullet-pointed non-answers. Match the user's register: internal work comms lean formal-corporate; community/external lean warm and direct.
3. **Skip what doesn't need a reply.** Newsletters, notifications, FYI threads get labeled or left alone — say what was skipped and why in one line each.

## Workflow

1. **Triage** — `Gmail:search_threads` for unread + recent inbox (default: last 48h, or the window the user names). Classify each thread: needs-reply / FYI / skip.
2. **Confirm the reply list** — show the needs-reply list (sender, subject, one-line gist) before drafting. the user can strike items.
3. **Draft** — for each confirmed thread, `Gmail:get_thread` for full context, then `Gmail:create_draft` as a reply on that thread. Keep drafts short; answer the actual question; one ask per email.
4. **Open tabs** — collect all draft URLs (`https://mail.google.com/mail/u/0/#drafts` deep links per draft where available), then open them in one batched call via Claude in Chrome (`browser_batch`). Cap at 8 tabs; paginate if more.
5. **Hand off** — one line per draft ("Draft to Bhala re: demo schedule — tab 3"), then stop. the user edits and sends manually.

## Fallbacks

- **Chrome extension not connected:** list the drafts with subjects in chat and note they're waiting in the Drafts folder. Don't skip drafting.
- **Ambiguous thread (needs a decision only the user can make):** don't guess — draft a skeleton with a `[DECISION: x or y?]` marker and flag it in the handoff.
- **Anything involving money, legal, HR, or personnel:** draft nothing; surface the thread and ask.

## Config note

Runs in Claude Code CLI / Cowork (robust MCP config). Requires: Gmail MCP + Claude in Chrome. Not for Desktop Chat's lean config.
