---
name: factory-rig
description: "Use when you run software delivery through a factory or backend (Noodle, PMO Platform, Curia, yysun project-manager, Matt Pocock's implement-spec), coordinate several projects or specialists, check which controller owns a task, gate or merge a worker's candidate, or verify, update or recover the factory integration. Routes one workload to exactly one dispatcher and enforces the ownership, evidence and merge rules. Management methods (flow, program, release) live in the Magnus skills it names."
---

# factory-rig

One router, one dispatcher per workload, one authority per mutable state surface. This skill is the
map; code is in `scripts/factory_rig/`, the registry in `registry/components.json`, the override
register in `registry/overrides.json` (rendered in `references/overrides.md`).

## Pick the workflow

| Situation | Use | Native entry |
|---|---|---|
| Unresolved decisions, "what should we build" | [Matt Pocock's skills](https://github.com/mattpocock/skills) `wayfinder`, then `to-spec`, `to-tickets` | user-invoked skills |
| Accepted spec, implement in an isolated worktree under supervision | **[Noodle](https://github.com/poteto/noodle)** through `frig dispatch` | `bin/frig` |
| Same, tracker already holds delivery state | [yysun `project-manager`](https://github.com/yysun/project-manager) (`.projects`) as state; Noodle or Matt `implement-spec` executes | `<skills-root>/project-manager` |
| Scrum, program, delivery or release ceremonies in Claude | [PMO Platform](https://github.com/cody-hutson/pmo-platform) skills (`ppm-agent`, `pmo-scrum-master`, `pmo-technical-program-manager`, `delivery-engine`, `release-hub`) | **inactive**, see `references/operating-modes.md` |
| Wayfinder-driven tickets on a Linux host | [Curia](https://github.com/alp82/curia) | **blocked-platform** on macOS and arm64 |
| Diagnose flow, plan a program, readiness, release, incident learning | [Magnus skills](https://github.com/magnus919/agent-skills) (`kanban-guru`, `technical-program-management`, `technical-project-management`, `implementation-planning`, `multi-agent-coordination`, `agent-evals-and-observability`, `production-readiness`, `release-engineering`, `verification-methodology`, `incident-learning`) | skills |

Never start two dispatchers on one task. The lease in `frig` is the check; the router is the choice.
`<skills-root>` is the folder that holds this skill.

## Set up

Needs Python 3.9+ and git; yysun-led mode also needs node and the `project-manager` skill as a sibling
folder (or `FRIG_YYSUN_SKILL`); Noodle mode needs a Noodle build at the revision pinned in
`registry/components.json` (on PATH as `noodle`, or `FRIG_NOODLE_BIN`).

1. `cp config/provider-policy.example.json config/provider-policy.json` and set each `real` to the
   absolute path of your `codex` and `claude` binaries. Without this file the shims refuse to launch.
2. Override any default with the variables in `config/frig.example.env` (`FRIG_POLICY`,
   `FRIG_NOODLE_BIN`, `FRIG_YYSUN_SKILL`, `FRIG_UPSTREAM_ROOT`, `CODEX_HOME`).

## Commands (`bin/frig`, Python 3.9+, JSON out)

```bash
FR="$PWD/bin/frig"                            # run from this skill's folder
$FR frontier --ws WS --backend noodle         # what may start, and why the rest may not
$FR dispatch --ws WS --task TASK-ID --owner-pid NOODLE_PID --provider codex --model gpt-6-sol
$FR review   --ws WS --attempt A... --verdict approve --reviewer-provider claude --implementer-provider codex
$FR check    --ws WS --attempt A...           # read-only gate evaluation
$FR complete --ws WS --attempt A...           # the only path that merges
$FR reconcile --ws WS                         # finish interrupted completions from what actually happened
$FR fence --ws WS --task TASK-ID              # stop a holder you cannot otherwise prove is gone
$FR report --ws WS
$FR registry-verify ; $FR drift               # registry shape; upstream moved since the pin?
```

A workspace has `repo/` (integration branch), `.projects/<slug>/` (yysun state), `specs/`, and
`.factory-rig/{config.json,contracts/,reviews/,evidence/,attempts.jsonl,state/}`. `python3 -m
factory_rig.fixture DIR` builds a disposable one. `frig noodle-init` writes `.noodle.toml` and the
project-local Noodle skills.

## Rules that are not negotiable

- **Ownership.** `frig dispatch` takes a lease (logical repo + task id, fencing epoch). Expiry never
  reclaims a lease whose holder is alive; use `fence` and read the history.
- **Authority.** Product priority: the human owner. Open decisions: Wayfinder. Accepted requirement: the
  versioned spec in `specs/`. Delivery state: one tracker per project (yysun `.projects` in
  yysun-led mode). QA and acceptance: the gate. Release authorization: existing release policy.
  A closed issue, a runtime completion event, a passing test and a release approval are four facts.
- **Merge.** Only `frig complete` merges: it re-runs the contract's verify argv in a fresh checkout
  of the candidate, requires a review record naming this task, attempt, contract hash, candidate sha
  and base sha from a different provider than the implementer, requires the integration branch to
  still sit at the base, then fast-forwards and compares trees. Any new commit, moved base, edited
  contract or edited spec voids the approval because each is compared at merge time.
- **Evidence is computed.** yysun accepts fabricated evidence of the right shape; every manifest the
  adapter writes comes from hashes and exit codes it just produced.
- **Permissions.** Noodle launches providers through `bin/codex` and `bin/claude`, which replace its
  hardcoded permission-bypass flags with the rig policy. Never point `[agents.*].path` elsewhere.
- **Budget.** Noodle starts one scheduler LLM session per `start` and one per backlog/mise change.
  The rig's `schedule` stub makes it a no-op; count those sessions. One implementation worker at a
  time (`max_concurrency = 1`).
- **Do not** invent Noodle commands; the control actions the rig sends are in `noodle_control.py`.

## Read next, only when needed

- `references/operating-modes.md`: tracker-led, yysun-led, PMO-native, Noodle, Curia, Matt.
- `references/overrides.md`: every local deviation from upstream, why, where, how it is tested.
- `references/operations.md`: launch, inspect, interrupt, recover, update, roll back.
- `references/agent-permissions.md`: keep background agents from hanging on permission prompts.
- `registry/components.json`: pins, licenses, statuses, evidence, blockers (statuses describe the
  reference install; yours starts unverified).
- `evals/management/`: the graded management scenarios behind the Magnus routing.

## Tests

```bash
cd scripts && python3 -W ignore -m unittest tests.test_core tests.test_flow tests.test_noodle_integration
```

`test_flow` skips without node and `project-manager`; `test_noodle_integration` also skips without the
Noodle build. Each skip names what it needs.
