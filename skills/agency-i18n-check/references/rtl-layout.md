# Right-to-left layout and the human review step

Source: W3C Internationalization, "Structural markup and right-to-left text in HTML"
Location: https://www.w3.org/International/questions/qa-html-dir
Version or retrieved date: page title confirmed 2026-11-25; guidance text not re-fetched at authoring time
Rights: W3C copyright and document license terms; check the page footer (not re-fetched at authoring time). Cited by title and URL, not copied.

Source: MDN Web Docs, "CSS logical properties and values"
Location: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_logical_properties_and_values
Version or retrieved date: page title confirmed 2026-11-25; page text not re-fetched at authoring time
Rights: MDN content is licensed CC-BY-SA 2.5 or later. Cited by title and URL, not copied.

Source: GlotPress, `locales/locales.php` (the locale definitions translate.wordpress.org uses)
Location: https://github.com/GlotPress/GlotPress/blob/develop/locales/locales.php
Version or retrieved date: `develop` branch, file retrieved 2026-11-25 (the same retrieval `gettext-and-plurals.md` cites); the right-to-left list below was read from that copy on 2026-11-26, not re-fetched
Rights: GPL-2.0. Locale codes cited, file not copied.

## Which locales are right-to-left

Every GlotPress locale whose `text_direction` is `rtl`: ar, arq, ary, azb, bcc, bgn, ckb, dv, fa (and fa_AF), ha, haz, he, nqo, ps, skr, snd (ISO 639-1 sd), ug, ur, yi. GlotPress marks Hausa (ha) right-to-left for its Ajami script. The script also treats a catalog as right-to-left when most letters in its translations have the Unicode bidirectional class R or AL, so a locale missing from this list, or a file named for another locale, still gets the RTL rules.

## Why the script checks these things

- The `dir` attribute on `<html>` sets the base text direction, and `lang` names the language. The `rtl-direction` rule requires both. A template expression such as `dir="{{dir}}"` counts, because the template engine fills it per locale.
- Physical properties (`margin-left`, `float: left`, `left: 0`) stay on the same screen side when the page flips. Logical equivalents (`margin-inline-start`, `float: inline-start`, `inset-inline-start`) follow the writing direction. The `rtl-physical-css` rule flags the physical forms and suggests the logical one.
- The exemption comment `/* i18n-allow-physical: <reason> */` covers cases where the layout must not flip, such as a mirrored sprite. It needs a reason, and it turns one finding on its line into a non-blocking `rtl-physical-exempted` finding that names the reason, so the language reviewer sees every exemption.
- `dir` and CSS `direction` are read on `<html>` and `<body>`, from the parsed page, so a comment can't stand in for the real element and `dir=" LTR"` counts as `ltr`.

## Why linguistic review is a human step

The script compares structure: placeholders, plural counts, empty or copied strings, declared length budgets, direction markup. It cannot read Arabic, Hebrew or Spanish. Meaning, tone, register, terminology and cultural fit need a person who reads the language. Every result therefore carries `linguistic_review.status: "required"` with owner `human:language-reviewer`, and no field says a catalog is approved, correct or reviewed. Fixture catalogs are synthetic text that no language reviewer has read.
