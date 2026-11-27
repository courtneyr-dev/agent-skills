---
name: consult-i18n-check
description: Check a translated string catalog against its source for placeholder, plural-category, RTL and bidi, length, hardcoded-format, glossary and untranslated-string defects with a deterministic script. Use for localization QA on i18n-catalog.v1 files before handoff or release. Not for judging translation accuracy; that goes to human:locale-reviewer.
disable-model-invocation: true
---

# Consult i18n check

`scripts/i18n_check.py` compares one target catalog to its source catalog and reports mechanical defects: placeholders, CLDR plural categories, bidi controls, RTL placeholder isolation, length limits, hardcoded dates and currency, glossary terms, untranslated strings and stale revisions. It never judges whether a translation is correct. That review stays with `human:locale-reviewer`, and the output says so on every run.

## When to use

- A target-locale catalog is ready for QA or release and you need a repeatable pass/fail.
- You changed source strings and need to find stale or broken targets.
- You add a locale and need to confirm its plural forms match CLDR.

## Not for

- Translation accuracy, tone, register or cultural fit. Route to `human:locale-reviewer`. Never write a native-language review yourself.
- Docs localization strategy. Use the installed skill `docs-localization-strategy` (samber/developer-relations-skills).
- Gettext POT/PO catalogs, page templates and CSS: use the agency fleet's `agency-i18n-check`. This skill takes JSON catalogs (`i18n-catalog.v1`); convert other formats first.

## Inputs

- Source and target catalog: `schema` `i18n-catalog.v1`, `label`, `locale`, `direction` (`ltr` or `rtl`), `source_revision`, optional `same_as_source_ok` (keys), `messages`. Each message is `{"text": "...", "max_length": 20}` (`max_length` optional, set on the source) or `{"plural": {"one": "...", "other": "..."}}`.
- Optional glossary: `schema` `i18n-glossary.v1`, `terms` of `{source, locale, target}`.
- Worked example: `fixtures/source-en.json`, `fixtures/target-fr.json`, `fixtures/glossary.json`.

## Method

1. Run `python3 scripts/i18n_check.py --source S --target T [--glossary G]`.
2. Fix each `error` defect. Read each `warning` and decide.
3. For `blocked`, add the locale to `references/cldr-plural-categories.json` from CLDR (regeneration command is in that file), then rerun. Never guess categories.
4. Send the passing catalog to `human:locale-reviewer`.

Defect codes: `missing-translation`, `untranslated`, `placeholder-mismatch`, `plural-categories`, `plural-placeholder`, `bidi-unbalanced`, `rtl-placeholder-unisolated` (warning), `direction-mismatch`, `length-exceeds-max`, `hardcoded-format` (warning), `terminology-mismatch`, `stale-source-revision`, `plural-rules-unknown`.

Rules worth knowing:

- Placeholders: `{name}`, `{0}`, `{{var}}`, `%s`, `%d`, `%1$s`, `%(name)s`, compared as multisets.
- Count placeholder: `{count}`, `{n}`, `{num}`, `{number}`, `{total}` (also `{{...}}` and `%(...)s` forms), `{0}`, `%d`, `%1$d`. Plural forms `zero`, `one` and `two` may omit it.
- A target counts as RTL for the isolation warning when its locale base language is RTL or its `direction` is `rtl`.
- The language match uses the base subtag, so `fr-CA` uses `fr`.

## Stopping conditions

- Both catalogs load and every check ran: report the result.
- Unknown plural locale: stop at `blocked` for plural keys; other checks already ran.
- Invalid input: stop at exit 2.

## Output contract

One JSON object: `source_locale`, `target_locale`, `cldr_version`, `status` (`pass`, `defects`, `blocked`), `defects` (each `code`, `severity`, `key`, `message`), `counts` by code, `linguistic_review`, `not_checked`. Exit 0 when no error-severity defect (warnings alone exit 0), 1 when any error, 2 for invalid input or usage. Catalog-level defects use the key `(catalog)`.

## Failure states

- Bad JSON, wrong `schema`, missing `messages`, or an unreadable file: `{"error": "..."}`, exit 2.
- Locale missing from the plural table: `plural-rules-unknown`, status `blocked`, exit 1.
- Target `source_revision` differs from the source: `stale-source-revision`, exit 1.

## Adapters and missing capability

Needs only `python3` 3.9+. No network. If no `human:locale-reviewer` exists for the locale, report the review as outstanding; do not substitute a model review.

## References and rights

| Source | Version | Rights |
|---|---|---|
| Unicode CLDR plural rules (`references/cldr-plural-categories.json`) | CLDR 48.0, Unicode 17.0, ICU 78.3 | Unicode License v3 |
| UAX #9, Unicode Bidirectional Algorithm | Unicode 17.0 | Unicode terms of use |
| W3C Internationalization, "Inline markup and bidirectional text in HTML" | current | W3C document license, cite only |

## Tests

```bash
cd scripts/tests && python3 -m unittest -v
```
