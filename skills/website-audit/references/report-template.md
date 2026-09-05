# Report template

Load at Phase 8, after scoring and deduplication.
_Synced from the master playbook. Edit the playbook, not this file._

## Report structure

Front-load the decision. The reader who stops after the first page should still know what to do.
Depth sits behind that, grouped by mechanism, never repeated (Standing Rule 8).

```
# <Site> — audit title
<date> · <complexity> · read-only

## The decision this feeds
## What was wrong with the going-in theory      ← if a hypothesis was killed, lead with it
## What to do first                              ← top 5–7, table only, no prose between rows
## Findings                                      ← grouped by mechanism
## What is working                               ← required, not optional
## <The decision question>                       ← e.g. the platform/rebuild split
## Measurement appendix                          ← numbers on record, out of the findings' way
## Limitations
## What would upgrade this audit
## Adjacent work not performed
## Self-review + definition of done, line by line
```

### Finding format

Mechanism first, then proof (Standing Rule 7). Five things, in this order:

1. **What is happening** — the mechanism, in plain words.
2. **How it was tested** — instrument, viewport, sample, date. Enough to re-run.
3. **Evidence** — the label, the specific observation, and the coverage. Name what was *not*
   observed.
4. **Who it affects** — which people, and how many if that is known. If it is not known, say so
   rather than implying scale.
5. **Correction** — the smallest change that resolves the mechanism (Standing Rule 14), and whether
   it is executable within the stated constraints.

Then the five-axis table.

### Rules for the write-up

- Group by mechanism. Fifteen instances is one finding with an instance list.
- No preamble, no restating the assignment.
- Every criticism carries a user consequence.
- Hedge honestly: without user evidence, *may cause* / *creates a risk* / *requires validation* —
  never *users are confused*.
- **"What is working" is mandatory.** Opening a list of problems without it is unfair and costs the
  report its credibility with the people who built the thing.
- **A withdrawn finding stays visible.** If the audit disproved its own claim, say so in the report
  rather than quietly deleting it. The correction is often the most valuable thing in the document.
- If the methodology was partial, say so in the header and in Limitations.
