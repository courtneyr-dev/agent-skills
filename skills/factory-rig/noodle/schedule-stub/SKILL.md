---
name: schedule
description: Factory-rig stub scheduler. Writes an empty orders file. Work reaches Noodle through the router (`frig dispatch` enqueues orders), never through this skill.
schedule: "Never choose work. The router enqueues orders; this stub exists only because Noodle injects one scheduler session on every start."
---

# Schedule (factory-rig stub)

Write exactly `{"orders": []}` to `.noodle/orders-next.json` and stop.

Do not read the backlog, `mise.json`, plans, or any other file. Do not create, reorder, or propose
orders. Do not start other agents. If `.noodle/orders-next.json` cannot be written, say so in one
line and stop.
