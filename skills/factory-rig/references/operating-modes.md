# Operating modes

A project uses one mode. The mode decides which system owns delivery state and which backend executes. Nothing
migrates silently: switching a project's mode is a decision recorded in its own tracker.

| Mode | Delivery state owner | Executes | Use when | Status on the reference install (macOS, 2026-11-25) |
|---|---|---|---|---|
| Tracker-led | The project's existing tracker (Jira, GitHub, Things) | The router's choice: a Codex run, Noodle, or a subagent | The project already lives in a tracker | Works; factory-rig does not touch the tracker |
| yysun-led | `.projects/<slug>/` (yysun `project-manager`) | Noodle through `frig`, or Matt `implement-spec` | You want contract-based delivery state with evidence manifests | installed-and-verified; live pilot passed 2026-11-25 (run records retained privately) |
| Noodle | Whatever the project's mode says (Noodle never owns state) | Noodle worktree workers, supervised, one at a time | Isolated implementation of an accepted contract | installed-and-verified, live pilot passed |
| PMO-native | PMO's hub-state in `$PMO_WORKSPACE/workspace` | Claude Code sessions started in that workspace | Scrum, program or release ceremonies run in Claude | installed-inactive; partly verified natively, see the `pmo-platform` blocker in `registry/components.json` |
| Curia | GitHub issues (Wayfinder tickets) | Curia agents in containers | Linux host, GitHub-centered Wayfinder flow | blocked-platform |
| Matt-led | Wayfinder map and ticket files | `implement-spec` (explicitly selected) | Spec-driven work with Matt Pocock's own loop | installed-and-verified (stable skills) |

Authority per surface (the rule that settles every dispute):

| Surface | Authority |
|---|---|
| Product priority and consequential decisions | The human owner (or the named product owner) |
| Open decisions and decision history | Wayfinder records |
| Accepted requirements | Versioned accepted spec (`specs/<id>.md`, revision and hash in the contract) |
| Delivery state | One tracker per project |
| QA records | Existing evidence system; yysun `.tests` where adopted |
| Runtime sessions and queues | The assigned backend |
| Acceptance | The gate (`frig complete`) |
| Release authorization | Existing release policy |
| Architecture and recovery knowledge | The project's own notes |

An issue closure, a runtime completion event, a passing test and a release approval are different facts.

## Routing rules

1. One dispatcher per workload. The router picks; `frig dispatch` enforces with a lease.
2. PMO's own gates are readiness evidence only (OVR-PMO-DOD). Release authorization stays with release policy.
3. `chief-of-staff` and `software-factory` are user-invocable only. Do not read them to get around that.
4. Skills that cannot chain automatically get an explicit entry point: the user types the skill name.
5. Wayfinder decides; accepted decisions become spec revisions with stable ids; the contract pins the spec hash.
