---
name: obsid-link-builder
description: "Use when asked to create or normalize shareable obsid.net links for Obsidian notes, convert obsidian:// links, or check the URL encoding of vault and file parameters."
---

# Obsid Link Builder

Create canonical links in this format:

    https://obsid.net/?vault=<ENCODED_VAULT>&file=<ENCODED_FILE_PATH>

## Workflow

1. Gather input in one of these forms:
   - vault + file values
   - existing obsidian://open?vault=...&file=... URL

2. Normalize file separators to '/'.
3. URL-encode vault and file values.
4. Output only the final obsid.net URL unless explanation is requested.

## Default Vault

Default vault name: `your vault`

## CLI Helper

    "$HOME/.claude/skills/obsid-link-builder/scripts/build_obsid_link.sh" \
      --vault "your vault" \
      --file "Sites/Joost.blog/Posts"

    "$HOME/.claude/skills/obsid-link-builder/scripts/build_obsid_link.sh" \
      --obsidian-url "obsidian://open?vault=2nd%20Brain&file=Sites%2FJoost.blog%2FPosts"
