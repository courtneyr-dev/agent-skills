---
name: edu-learning-progression
description: "Use when someone needs a prerequisite map, curriculum map, learning progression or course sequence: CS from school computing through introductory university study, a BCIT program pathway, or an instructional-design curriculum map for workplace or developer training. Checks the map with a script: no prerequisite cycles, nothing taught before its prerequisites, every concept assessed or flagged, and no university (CS2023) expectation dropped into a K-12 unit without a written bridge. Use it for 'prerequisite graph', 'scope and sequence', 'course sequence', 'learning progression', 'curriculum map', 'what should come before recursion', even when the request only says 'order these topics'. Not for single lessons (cs-classroom-instruction) or standards alignment claims (edu-standards-alignment)."
license: MIT
disable-model-invocation: true
---

# Learning progression

Builds and checks a prerequisite map plus the sequence that teaches it. A map that passes is
coherent. It isn't evidence that learners learn in that order; that needs actual classroom or
workplace evidence collected later.

## When to use and when not to

Use it for a CS progression across grade bands, a BCIT or information-systems program pathway, or
an instructional-design curriculum map with a prerequisite graph.

Don't use it to:
- Apply university curriculum expectations (CS2023) to school learners without a justified bridge. The script refuses it.
- Claim standards alignment. Concepts may cite a registry record by label; alignment status belongs to edu-standards-alignment.
- Treat higher-education research on sequencing as proof for K-12 BCIT or workplace learners.
- Override a district's adopted course sequence. Record the adopted sequence and flag disagreements for faculty review.

## Inputs and prerequisites

- The audience and its grade band or setting, the course or program length, and any adopted sequence.
- Concepts with a band, prerequisites and the tasks that assess them.
- Python 3.9+ for `scripts/progression.py`.

Graph shape:

```json
{"label": "...", "concepts": [
   {"id": "lists", "label": "Lists of values", "band": "9-10", "prereqs": ["variables"],
    "assessed_by": ["unit2-lab:L1"], "prior": false, "bridge": null,
    "source": {"record_id": "csta-k12-2026", "label": "Algorithms and Programming"}}],
 "sequence": [{"unit": "U1", "grade": 9, "concepts": ["lists"]}]}
```

`band` is `PK-2`, `3-5`, `6-8`, `9-10`, `11-12`, `9-12` or `university`. `prior: true` marks a
concept taught before this course; it needs no placement or assessment. `grade` is -1 (PK) to 12, or
`"university"`.

## Method

1. Start from the intended performance at the end of the course, then list the concepts it needs.
2. For each concept, name its prerequisites and the task that will assess it.
3. Place concepts into units, prerequisites first.
4. For any concept above the unit's band, write a `bridge`: what the learner does at this age and what stays for later study. Without one, move the concept.
5. Run `python3 scripts/progression.py check graph.json`. Fix every error; decide on each unassessed warning.
6. Send program-level changes to faculty review (`bcit-education.cs-education-professor` or `bcit-education.bcit-education-professor`).

## Stopping conditions

- `check` exits 0 and every unassessed concept is either given a task or accepted by the reviewer as unassessed.
- The map needs an adopted-sequence or standards decision only a human can make: stop and hand it off.

## Output contract

JSON `{"ok", "errors", "warnings", "unassessed", "order", "note"}`. `order` is a valid prerequisite
order when the graph is acyclic, otherwise `null`.

## Failure states

- Exit 1: prerequisite cycle, unknown or duplicate concept, a concept sequenced before its prerequisite, a concept placed twice, a concept neither sequenced nor prior, or a band jump without a bridge.
- Exit 2 `invalid input`: unreadable JSON, missing `concepts` or `sequence`, a concept without an id, an unknown band, or a non-numeric grade.

## Adapters and missing capability

No external adapter. The script is the check. Without Python, list the concepts in prerequisite order
by hand and mark the map "unchecked".

## References

`references/sources.md` lists CSTA K-12 CS Standards (2026), CSTA's research page for the 2026
standards and CS2023, with version and rights for each. Live verification dates belong to the
standards registry in `edu-standards-alignment`.

## Evaluation cases

Fixtures in `company-fleets/fleets/bcit-education/fixtures/edu-learning-progression/`: a grades 9-12
progression that passes with one unassessed warning and one bridged university concept, and a
counterexample with a cycle, an unbridged university concept in grade 9 and an out-of-order concept.
Unit tests: `scripts/tests/test_progression.py`.
