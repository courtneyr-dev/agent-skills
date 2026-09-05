---
name: lmk
description: "Use when the user says 'LMK when you're done', 'let me know', 'notify me', 'ping me when you're done', or says you're stepping away and wants a phone push when the work finishes."
---

# lmk — Pushover push when the task finishes

## Overview

An end-of-task delivery requirement, not a separate task: complete and verify the requested work first, then send exactly one notification. The push is a heads-up — the conversation always carries the complete result.

## Sending

```bash
~/.claude/skills/lmk/scripts/lmk-notify.sh "Short task title" "One to three short lines: what finished and the outcome"
```

Credentials load from the macOS Keychain inside the script. Never inline them in commands, output, or this file.

Priority is normal by default. `-p -1` quiet — only when the user asked for quiet delivery. `-p 1` high — only for a genuinely important alert. `-p 2` emergency — only when the user explicitly requested an emergency alert.

## Message content

- Title names the task; the message says what finished and its outcome, so the push identifies which task it belongs to.
- Keep it generic: no URLs, email addresses, contact names, file paths, document names, payment details, health information, or credentials — unless the user explicitly asked for that exact detail in the push.
- Final outcome only. No progress pushes unless you explicitly asked for them.

## Verifying delivery

- Sent = script exits 0 and prints JSON containing `"status":1`. Note the returned `request` id in the conversation for troubleshooting.
- `"status":0` = not sent: report the `errors` array in the conversation.
- Any other failure (network error, missing credentials) = not sent: report it plainly. Never claim the push was sent without seeing `"status":1`.
- Exit 2 = credentials missing from the Keychain (service `pushover-lmk`, accounts `user_key` and `app_token`). Ask the user to re-add them there; never store them in git-tracked files.
