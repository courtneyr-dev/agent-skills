---
title: COUNTEREXAMPLE, a quickstart that only works on its author's machine
replay_requires: python3
replay_budget_seconds: 30
---

# Create your first note (counterexample)

SYNTHETIC FIXTURE AND DELIBERATE COUNTEREXAMPLE. The author had `FIXTURE_NOTES_PORT=8765` exported in their shell profile, so every step passed for them. The page never says so. A clean replay must fail at step 3.

```sh tier=run
python3 --version
```

```sh tier=run
python3 fixture-co-notes/server.py --port 8765 --max-seconds 60 &
```

```sh tier=run
python3 fixture-co-notes/client.py add "First note"
```

```text expect
created note 1: First note
```
