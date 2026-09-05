---
name: things-obsidian-sync
description: "Use when Things tasks and their linked Obsidian checkboxes in the daily note disagree and need syncing; normally runs from launchd."
license: MIT
---

# Things and Obsidian completion sync

Keeps Things tasks and linked Obsidian checkboxes in agreement.

## Completion policy

- Completing a linked task in Things checks every matching Obsidian checkbox.
- Checking a linked Obsidian task completes the matching Things task.
- Completion wins when the same Things ID appears in more than one note.
- Unchecking a box never reopens a completed Things task.
- A Things or automation read failure stops the run before vault files change.

## Default scope

Each run scans:

- `Review/Daily/YYYY-MM-DD.md` for the requested date, when that note exists.
- Every Markdown note under `Areas/Content Strategy/`.

Add another approved file or folder with a repeatable `--root` argument. Relative paths resolve from the vault root.

## Required task format

```markdown
- [ ] [Task name](things:///show?id=XXX)
- [x] ~~[Task name](things:///show?id=XXX)~~
```

The Things task should contain an `obsidian://` link to its owning note for navigation in the other direction.

## Usage

```bash
# Preview the complete default scope
python3 scripts/sync.py --dry-run

# Run the default completion sync
python3 scripts/sync.py

# Include another approved folder
python3 scripts/sync.py --root "Projects/St. John's UCC"

# Limit which side may change
python3 scripts/sync.py --direction things-to-obsidian
python3 scripts/sync.py --direction obsidian-to-things
```

## Automation

The bundled LaunchAgent runs every 15 minutes and writes logs under this skill's `logs/` directory.

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.things-obsidian-sync.plist
```

Add `/Library/Developer/CommandLineTools/usr/bin/python3` under System Settings, Privacy and Security, Full Disk Access before a background run can read the vault or control Things. The sync stops without changing either system when that access is missing.

## Configuration

The defaults live near the top of `scripts/sync.py`:

```python
OBSIDIAN_VAULT = Path("$VAULT_DIR")
DAILY_NOTES_DIR = OBSIDIAN_VAULT / "Review" / "Daily"
LINKED_NOTE_ROOTS = (
    OBSIDIAN_VAULT / "Areas" / "Content Strategy",
)
```

## Dependencies

- macOS
- Python 3
- Things 3
- Obsidian
