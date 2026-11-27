---
title: Repro for developer feedback FB-1, an empty title returns HTTP 500
replay_requires: python3
replay_budget_seconds: 30
---

# Repro for FB-1: an empty title returns HTTP 500

SYNTHETIC FIXTURE. An invented piece of developer feedback for the Fixture Co Notes API, turned into a reproducible product issue.

- Feedback channel: workshop office hours (synthetic).
- Reported behavior: creating a note with an empty title prints an internal error.
- Expected behavior: a 400 validation error that names the title field.
- Owner: `human:product-owner` decides the fix. DevRel drafts the reply to the developer; a human sends it.

When this repro stops reproducing, the product owner updates the expected lines to the fixed behavior.

## Start the server

```sh tier=run
python3 fixture-co-notes/server.py --port-file port.txt --max-seconds 60 &
```

## Send an empty title

```sh tier=run
python3 fixture-co-notes/client.py --port-file port.txt add "" || echo "exit status $?"
```

```text expect
error: HTTP 500 internal error
exit status 1
```
