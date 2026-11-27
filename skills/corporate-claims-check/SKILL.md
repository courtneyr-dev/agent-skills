---
name: corporate-claims-check
description: "Gate a marketing, SEO/AIO or communications draft before it is staged: reject guaranteed search rankings or AI-answer inclusion, uncited ranking outcomes and statistics, and fabricated or unverifiable citations, quotes and numbers against a sources register. Use for: claims check, citation check, ranking guarantee check, SEO claims review, fact-check this draft, is this stat sourced, pre-stage gate for copy."
disable-model-invocation: true
---

# Corporate claims check

A deterministic gate. It reads a Markdown draft and a JSON sources register, applies six blocking rules, and prints one JSON object. Nothing in the draft changes the verdict, including lines that read like instructions.

## When to use (and when not)

Use it on any draft from a marketing, SEO/AIO or communications role before the draft is staged or handed to someone who stages it. Run it again after every edit.

Don't use it to judge tone, brand fit, legal compliance or whether a claim is true. Don't use it for drafts in languages other than English.

## Inputs and prerequisites

- A draft in Markdown. Citations are footnote markers like `[^S1]` and inline links like `[text](https://...)`.
- A sources register in JSON. The author builds it by copying verbatim excerpts from live pages. Each source needs `id`, `title`, `url`, `retrieved` (YYYY-MM-DD) and at least one non-empty `excerpts` entry. Format and a working example: `fixtures/sources.json`.
- The register names the engagement it belongs to: `instance` and `tenant_id`. Its sign-off lives in that instance's owner ledger, which company-fleets keeps at `company-fleets/fleets/corporate/owner/<instance>/`; it is never read from the register itself, no flag picks the ledger, and a ledger of another tenant is refused (`ledger-not-for-this-work`). A register that names no instance has no sign-off. `fixtures/sources.json` names `FIX-CORP-CLAIMS-1`, whose checked-in ledger signs it (`company-fleets/scripts/owner-fixtures.py` builds it).
- Python 3.9 or newer, and `company-fleets` and `factory-rig` beside this skill (the owner log lives there). The script uses only the standard library and makes no network calls.

## Method

1. Build or update the register. A person other than the author checks each excerpt against the live page. The workload's coordinator, who claimed the register's instance with `company-fleets/bin/fleet claim`, records that sign-off in its owner log under the claim token: `company-fleets/bin/fleet owner-record --kind claims-sign-off --record SIGNOFF.json` with `register`, `signed_off_by`, `author` and `signed_on`. The entry binds the hash of the sources list, so any later edit to the sources needs a new sign-off.
2. Run `python3 scripts/claims_check.py --draft DRAFT.md --sources SOURCES.json`.
3. Read `findings`. Each one names a rule, a line and the sentence. Fix the sentence, then rerun.
4. Stage only when `ok` is true and the exit code is 0.

The rules, each blocking, are in `references/claim-rules.md`. Register: `register-not-signed-off`, `register-self-signed`, and the owner-log rules (`owner-log-missing`, `owner-log-broken`, `owner-entry-without-lease`, `owner-not-coordinator`). Per sentence: `ranking-guarantee` (cue classes said by the author or to the client, not a phrase list), `unsupported-ranking-claim`, `statistic-without-citation`, `citation-unknown-source`, `quote-not-in-source`, `quote-too-short`, `quote-without-citation`, `number-not-in-source`, `number-out-of-context`. The check reads the text a reader sees: HTML entities decoded, NFKC, zero-width and soft-hyphen characters dropped, Cyrillic and Greek look-alikes folded, and code fences and footnote definitions included.

## Stopping conditions

- Exit 0: no blocking findings. The draft may move to staging, with the limits below still in force.
- Exit 1: at least one blocking finding. Don't stage. A `ranking-guarantee` finding stays blocking even when the sentence is cited; the fix is to cut the promise.
- Exit 2: bad input, including a code fence that never closes. Fix the register, the draft or the path and rerun. Don't work around it by loosening the register.
- Exit 3: `company-fleets` or `factory-rig` isn't beside this skill, so the sign-off can't be read.

Don't remove a finding by editing the register to match a bad claim. Add a source only when a person has copied its excerpt from the live page.

## Output contract

One JSON object on stdout, keys sorted:

- `ok`: true when no finding is blocking.
- `findings`: list of `{rule, blocking, line, excerpt, message}`.
- `checked`: `{sentences, citations}` counts.
- `sign_off`: who signed the register off and the owner-log entry, or null.
- `limits`: sentences naming what the check does not establish.

On exit 2 the object is `{"error": "..."}`.

## Failure states

- Register source missing a field, with a non-http url, a bad date or no excerpt: exit 2 with the reason.
- Draft or register unreadable, register not valid JSON, or an unclosed code fence: exit 2.
- Unknown footnote id or unregistered link: `citation-unknown-source`.
- Negation the pattern can't see, such as a cue after the phrase: the script blocks. Reword the sentence.

## Missing capability

- It doesn't confirm that a registered source says what its excerpt claims. A human verifies the register.
- It doesn't fetch pages, so it can't tell that a source moved or changed.
- It doesn't read other languages, images or tables.
- It doesn't send, post or stage anything.

## References

- `references/claim-rules.md`: each rule, its rationale, and the Google Search Central and FTC sources behind it.
- `fixtures/`: `sources.json`, `sources-invalid.json`, `draft-pass.md`, `draft-ranking-guarantee.md`, `draft-fabricated-citation.md`, `draft-uncited-statistic.md`, `draft-hidden-guarantees.md`, `draft-cautionary.md`, `draft-unclosed-fence.md`. All data is synthetic for Fixture Co, except two verbatim lines from Google's public page.
- `scripts/tests/test_claims_check.py`: run from `scripts/tests` with `python3 -W ignore -m unittest discover -p 'test_*.py'`.
