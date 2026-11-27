---
title: Create your first note with the Fixture Co Notes API
replay_requires: python3
replay_budget_seconds: 30
---

# Create your first note with the Fixture Co Notes API

SYNTHETIC FIXTURE. Fixture Co and its Notes API are invented for the company-fleets demonstrations. The sample server runs only on your machine, on 127.0.0.1.

You'll start the sample server, create one note, and read it back. It takes under a minute.

## Before you start

You need Python 3.9 or later. Check your version:

```sh tier=run
python3 --version
```

```text expect
Python 3.<minor>
```

Download the `fixture-co-notes` folder into your working directory.

## Start the sample server

The server picks a free port, writes it to `port.txt`, and stops by itself after 60 seconds:

```sh tier=run
python3 fixture-co-notes/server.py --port-file port.txt --max-seconds 60 &
```

## Create a note

```sh tier=run
python3 fixture-co-notes/client.py --port-file port.txt add "First note"
```

```text expect
created note 1: First note
```

## Read it back

```sh tier=run
python3 fixture-co-notes/client.py --port-file port.txt list
```

```text expect
1  First note
```

You've created and read a note through the API. Next, the workshop lab adds search.
