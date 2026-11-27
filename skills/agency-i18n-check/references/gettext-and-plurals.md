# Gettext PO format and plural counts

Source: GNU gettext utilities manual, sections "PO Files" and "Translating plural forms"
Location: https://www.gnu.org/software/gettext/manual/html_node/PO-Files.html and https://www.gnu.org/software/gettext/manual/html_node/Translating-plural-forms.html
Version or retrieved date: page titles confirmed 2026-11-25; manual version and section text not re-fetched at authoring time
Rights: GNU Free Documentation License. Cited by title and URL, not copied.

Source: GlotPress, `locales/locales.php` (the locale definitions translate.wordpress.org uses)
Location: https://github.com/GlotPress/GlotPress/blob/develop/locales/locales.php
Version or retrieved date: `develop` branch, file retrieved 2026-11-25; the branch head was commit 8294329c48 (2026-11-23) when checked
Rights: GPL-2.0 (repository license reported by the GitHub API). Counts cited, file not copied.

## What the script takes from each source

| Script behavior | Source |
| --- | --- |
| Entry fields `msgctxt`, `msgid`, `msgid_plural`, `msgstr`, `msgstr[n]`, quoted continuation lines, escapes `\"` `\n` `\t` `\\` | PO Files section |
| Comments `#.` (extracted), `#:` (reference), `#,` (flags such as `fuzzy`) | PO Files section |
| Header entry (empty `msgid`) carrying `Language` and `Plural-Forms: nplurals=N` | PO Files and Translating plural forms sections |
| Plural entries need one `msgstr[n]` per form, N set by the header | Translating plural forms section |
| Entries match across POT and PO by the pair (`msgctxt`, `msgid`) | PO Files section |

The parser skips obsolete `#~` entries and accepts only the four escapes above plus `\r`. Octal and other C escapes raise a syntax error (exit 2).

## Plural counts the script knows

Read from the GlotPress file on 2026-11-25. A locale without a `nplurals` line there uses the class default of 2.

| Locale | nplurals | GlotPress value |
| --- | --- | --- |
| ar | 6 | set |
| he | 2 | default |
| ru | 3 | set |
| pl | 3 | set |
| ja | 1 | set |
| zh_CN | 1 | set |
| es | 2 | default |
| fr | 2 | set |
| de | 2 | default |
| en | 2 | default |
| fa | 2 | set |
| ur | 2 | default |

A regional code such as `es_ES` or `fr_FR` uses its base language's count. A base that is not in the table (`zh_TW`, `pt_BR`) is unknown, and the script reports a non-blocking `plural-forms-unknown-locale` finding. To add a language, read its block in the GlotPress file and extend `PLURAL_COUNTS` in `scripts/i18n_check.py`.

The GlotPress file changes as locales are added. Recheck the table against the file when a project ships a locale outside it.
