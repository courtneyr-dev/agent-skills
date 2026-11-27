---
name: edu-standards-alignment
description: "Checks education standards alignments and professional-source references against a live-verified registry, so a draft never claims a match it cannot support. Use whenever a lesson, unit, course, program map, teacher-education module or syllabus cites NBEA, NOCTI, ISTE, CSTA (student or teacher), CS2023, Pennsylvania certification or staffing rules, state or district curriculum, or a professional organization such as CSTA, ACM SIGCSE, SIGCITE, NBEA CBTR, ACTE or PBEA; when someone asks to 'map this to standards', 'crosswalk', 'check alignment', 'does this cover the NBEA areas', or 'is this the right edition'. Returns honest gaps for missing, protected or unverified sources, catches student/teacher standard mix-ups, wrong editions and ignored district adoptions, and rejects membership or credential claims. Not for writing the lesson itself (bcit-learning-package, cs-classroom-instruction)."
license: MIT
disable-model-invocation: true
---

# Standards alignment and professional sources

A mapping is only as strong as the source behind it. This skill keeps one registry of standards, qualification and policy sources (`references/standards-registry.json`, 23 records) and one of professional organizations (`references/organizations.json`, 12 records), each checked against its live page on 2026-11-25: 19 standards records and 10 organizations verified, NBEA, NBEA CBTR and PBEA unreachable, and the rest recorded as gaps or unverified. It checks every alignment against them.

## When to use and when not to

Use it for any objective-to-standard mapping, edition question, NBEA content-area or ISTE educator-role coverage check, and any document that names an educator organization.

Don't use it to decide what a standard means for a lesson: a teacher of record reads the standard on the source site and records the review. The checker confirms structure (source, edition, audience, identifier scheme, review), not that the objective fits the standard's text.

## Inputs and prerequisites

- An alignment file: `{"context": {"learner_audience": "students|teachers|university", "district_adoptions": [record ids]}, "alignments": [{"objective_id", "criterion_id", "record_id", "standard_id"?, "edition"?, "audience"?, "reviewer"?, "evidence"?, "progression_bridge"?, "status": "verified|partial|unverified|gap|not-applicable"}]}`.
- A coverage file: `{"courses": [{"id", "<field>": [labels]}]}`.
- An organization-reference file: `{"references": [{"name", "relation"}]}`.
- The two registries. Python 3.9+.

## Method

1. Run `scripts/standards_check.py registry` and `orgs`. Stop if either fails: a stale or malformed registry can't vouch for anything.
2. Run `align FILE`. Per row it computes the highest status the evidence supports:
   - Source not registered, unreachable, or a gap (district curriculum, local policy) → gap.
   - NOCTI: no credential is selected and blueprint content is restricted, so any competency id or item is an error and the row is a gap.
   - Identifier outside the record's published scheme (for example a CSTA 2017 id under the 2026 record) → error.
   - Identifier that fits the format but isn't in the record's stored list of published ids (`ids`: 289 CSTA 2026, 120 CSTA 2017, 126 ISTE, 17 CS2023 codes, identifiers only) → `id-not-published` error. A record with a format but no stored list caps the row at unverified (`id-list-not-stored`).
   - Teacher or educator standard cited for a student objective, a student standard for a teacher-practice objective, or CS2023 in a school unit without a `progression_bridge` → error.
   - Superseded edition with no recorded district adoption, or a newer edition when the district adopted an older one → error. An adopted older edition is kept.
   - Accessibility, design, interoperability or course-review references (WCAG, UDL, CASE, QTI, Quality Matters) are not learning standards → error.
   - Standard text in the row when the license forbids bundling → error.
   - `verified` and `partial` need a `human:` reviewer and an evidence file that exists next to the alignment file or under company-fleets; otherwise the row drops to unverified (`no-human-review`, `review-evidence-missing`).
   A claimed status above the supported one is an `overclaimed` error.
3. Run `coverage FILE --record nbea-2023 --field nbea_areas` for the ten NBEA areas (a computing-only program fails) or `--record iste-educators --field iste_educator_labels` for the seven ISTE educator roles.
4. Run `org-refs FILE` on any syllabus, persona or report that names organizations.
5. Label the draft with the coverage the checker reports (`verified`, `partial` or `gap`).

## Stopping conditions

- Every row has a supported status, and every error is either fixed or kept as a recorded gap.
- A source you need is unreachable: record it, keep the row a gap, and name the human step that resolves it.

## Output contract

JSON on stdout. `align` returns `ok`, `errors` (count), `coverage`, `supported_counts`, per-objective best status and per-row `claimed`, `supported` and `findings` (each with `severity`, `code`, `message`). Exit 0 when nothing blocks the claims, 1 for findings or invalid input, 2 for usage.

## Failure states

- `status: invalid` for a malformed file; `invalid-registry` when a registry fails its own check.
- Network-dependent facts are never fetched at check time; a stale registry is a human resume step, not a silent pass.

## Adapters and missing capability

No adapter is required. The Learning Commons Knowledge Graph is not connected; even if it were, connector availability is not NBEA, NOCTI or ISTE coverage. Without a verified source, the output is a gap with the source and limitation named.

## References

`references/sources.md` lists each source with edition, license and permitted use. The registries hold metadata, short public labels and published identifiers only, never standard or assessment text. Identifiers are cited under each source's terms: CSTA CC BY-NC-SA with attribution, ISTE noncommercial educational use with attribution. The id lists were extracted on 2026-11-26; `evidence/sources/standard-ids.txt` records the commands and counts. To refresh after a new edition, rerun that extraction and replace the record's `ids`. Evidence for each live check is in `company-fleets/fleets/bcit-education/evidence/sources/`.

## Evaluation cases

In `company-fleets/fleets/bcit-education/evals.json`: `standards-honest-gaps-pass`, `nbea-ten-areas-covered`, `source-registries-valid`, `org-sources-cited-correctly` (positive); `standards-overclaim-rejected`, `missing-standard-is-a-gap`, `standards-mixup-and-edition-caught`, `computing-only-not-bcit`, `org-credential-claims-rejected`, `invented-wellformed-ids-rejected` (negative); `district-adoption-preserved` (boundary). Unit tests: `scripts/tests/test_standards_check.py`.
