---
title: Workshop lab 1, search your notes
replay_requires: python3
replay_budget_seconds: 45
---

# Workshop lab 1: search your notes

SYNTHETIC FIXTURE. This lab belongs to the invented Fixture Co developer workshop. It builds on the quickstart and runs only on 127.0.0.1.

Facilitator note: learners who finished the quickstart start at step 2. Budget 10 minutes, including questions.

## Step 1: start a fresh server

```sh tier=run
python3 fixture-co-notes/server.py --port-file port.txt --max-seconds 60 &
```

## Step 2: add three notes

```sh tier=run
python3 fixture-co-notes/client.py --port-file port.txt add "Buy oat milk"
python3 fixture-co-notes/client.py --port-file port.txt add "Book the workshop room"
python3 fixture-co-notes/client.py --port-file port.txt add "Oat milk recipe"
```

```text expect
created note 1: Buy oat milk
created note 2: Book the workshop room
created note 3: Oat milk recipe
```

## Step 3: search

`--contains` matches titles without regard to case:

```sh tier=run
python3 fixture-co-notes/client.py --port-file port.txt list --contains oat
```

```text expect
1  Buy oat milk
3  Oat milk recipe
```

## Checkpoint

Every learner sees notes 1 and 3. If someone sees nothing, check that their server from step 1 is still running; it stops after 60 seconds.
