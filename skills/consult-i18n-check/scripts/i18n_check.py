#!/usr/bin/env python3
"""Deterministic i18n catalog check. Standard library only, Python 3.9+."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from typing import Any, Dict, List, Optional

CATALOG_SCHEMA = "i18n-catalog.v1"
GLOSSARY_SCHEMA = "i18n-glossary.v1"
RTL_LANGS = {"ar", "he", "fa", "ur", "yi", "ps", "sd", "ug", "dv"}
COUNT_NAMES = {"count", "n", "num", "number", "total"}
COUNT_TOKENS = {"{0}", "%d", "%1$d"}
OPTIONAL_COUNT_FORMS = {"zero", "one", "two"}
CATALOG_KEY = "(catalog)"
PLACEHOLDER_RE = re.compile(
    r"\{\{[^{}]+\}\}|\{[A-Za-z0-9_.]+\}|%\([A-Za-z0-9_]+\)s|%\d+\$[sd]|%[sd]"
)
DATE_RE = re.compile(r"\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b")
CURRENCY_RE = re.compile(r"[$€£¥]\s?\d|\d\s?[$€£¥]")
FSI, PDI = "⁨", "⁩"
EMBED_OPEN = {"‪", "‫", "‭", "‮"}
EMBED_CLOSE = "‬"
ISOLATE_OPEN = {"⁦", "⁧", "⁨"}
ISOLATE_CLOSE = "⁩"

NOT_CHECKED = [
    "translation accuracy, tone, register and cultural fit",
    "grammar and agreement inside plural forms",
    "ICU MessageFormat select, gender and nested syntax",
    "locale number and date formatting beyond literal date and currency patterns",
    "rendered layout, fonts and visual truncation",
    "keys present only in the target catalog",
    "glossary inflection and compound forms",
]
LINGUISTIC_REVIEW = {
    "status": "required",
    "by": "human:locale-reviewer",
    "note": "This check does not judge translation accuracy, tone, register or cultural fit",
}


class InputError(Exception):
    pass


def load_json(path: str) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError as exc:
        raise InputError("cannot read %s: %s" % (path, exc.strerror))
    except ValueError as exc:
        raise InputError("invalid JSON in %s: %s" % (path, exc))


def validate_catalog(data: Any, path: str) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise InputError("%s: top level must be an object" % path)
    if data.get("schema") != CATALOG_SCHEMA:
        raise InputError("%s: schema must be %r" % (path, CATALOG_SCHEMA))
    for field in ("locale", "source_revision"):
        if not isinstance(data.get(field), str) or not data[field]:
            raise InputError("%s: missing or invalid %r" % (path, field))
    if data.get("direction") not in ("ltr", "rtl"):
        raise InputError("%s: direction must be 'ltr' or 'rtl'" % path)
    ok = data.get("same_as_source_ok", [])
    if not isinstance(ok, list) or not all(isinstance(k, str) for k in ok):
        raise InputError("%s: same_as_source_ok must be a list of keys" % path)
    messages = data.get("messages")
    if not isinstance(messages, dict):
        raise InputError("%s: missing 'messages' object" % path)
    for key, msg in messages.items():
        if not isinstance(msg, dict):
            raise InputError("%s: message %r must be an object" % (path, key))
        if "plural" in msg:
            forms = msg["plural"]
            if not isinstance(forms, dict) or not forms or not all(
                isinstance(v, str) for v in forms.values()
            ):
                raise InputError("%s: message %r has an invalid 'plural'" % (path, key))
        elif isinstance(msg.get("text"), str):
            ml = msg.get("max_length")
            if ml is not None and (isinstance(ml, bool) or not isinstance(ml, int)):
                raise InputError("%s: message %r max_length must be an integer" % (path, key))
        else:
            raise InputError("%s: message %r needs 'text' or 'plural'" % (path, key))
    return data


def validate_glossary(data: Any, path: str) -> List[Dict[str, str]]:
    if not isinstance(data, dict) or data.get("schema") != GLOSSARY_SCHEMA:
        raise InputError("%s: schema must be %r" % (path, GLOSSARY_SCHEMA))
    terms = data.get("terms")
    if not isinstance(terms, list):
        raise InputError("%s: missing 'terms' list" % path)
    for term in terms:
        if not isinstance(term, dict) or not all(
            isinstance(term.get(f), str) and term[f] for f in ("source", "locale", "target")
        ):
            raise InputError("%s: each term needs source, locale and target strings" % path)
    return terms


def load_plural_table() -> Dict[str, Any]:
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "references", "cldr-plural-categories.json"
    )
    return load_json(path)


def base_lang(locale: str) -> str:
    return re.split(r"[-_]", locale.strip().lower())[0]


def forms_of(msg: Dict[str, Any]) -> Dict[str, str]:
    if "plural" in msg:
        return dict(msg["plural"])
    return {"": msg["text"]}


def placeholders(text: str) -> Counter:
    return Counter(PLACEHOLDER_RE.findall(text))


def is_count_placeholder(token: str) -> bool:
    if token in COUNT_TOKENS:
        return True
    match = re.match(r"\{\{\s*(\w+)\s*\}\}|\{(\w+)\}|%\((\w+)\)[sd]", token)
    if not match:
        return False
    name = next(g for g in match.groups() if g)
    return name.lower() in COUNT_NAMES


def defect(code: str, severity: str, key: str, message: str) -> Dict[str, str]:
    return {"code": code, "severity": severity, "key": key, "message": message}


def depth_unbalanced(text: str, opens: set, close: str) -> bool:
    depth = 0
    for ch in text:
        if ch in opens:
            depth += 1
        elif ch == close:
            depth -= 1
            if depth < 0:
                return True
    return depth != 0


def check_bidi(key: str, text: str) -> List[Dict[str, str]]:
    out = []
    if depth_unbalanced(text, EMBED_OPEN, EMBED_CLOSE):
        out.append(defect("bidi-unbalanced", "error", key,
                          "embedding or override (U+202A-U+202E) is not closed by U+202C PDF"))
    if depth_unbalanced(text, ISOLATE_OPEN, ISOLATE_CLOSE):
        out.append(defect("bidi-unbalanced", "error", key,
                          "isolate (U+2066-U+2068) is not closed by U+2069 PDI"))
    return out


def unisolated(text: str) -> List[str]:
    bad = []
    for m in PLACEHOLDER_RE.finditer(text):
        before = text[m.start() - 1] if m.start() > 0 else ""
        after = text[m.end()] if m.end() < len(text) else ""
        if before != FSI or after != PDI:
            bad.append(m.group(0))
    return bad


def check_form_text(key: str, text: str, rtl_target: bool) -> List[Dict[str, str]]:
    out = check_bidi(key, text)
    if rtl_target:
        bad = unisolated(text)
        if bad:
            out.append(defect("rtl-placeholder-unisolated", "warning", key,
                              "placeholder not wrapped in U+2068 ... U+2069: " + ", ".join(bad)))
    scan = PLACEHOLDER_RE.sub(" ", text)
    if DATE_RE.search(scan):
        out.append(defect("hardcoded-format", "warning", key,
                          "literal date %r; use a locale date formatter" % DATE_RE.search(scan).group(0)))
    if CURRENCY_RE.search(scan):
        out.append(defect("hardcoded-format", "warning", key,
                          "literal currency amount %r; use a locale currency formatter" % CURRENCY_RE.search(scan).group(0)))
    return out


def check_plurals(key: str, src: Dict[str, Any], tgt: Dict[str, Any],
                  src_cats: Optional[List[str]], tgt_cats: Optional[List[str]],
                  src_locale: str, tgt_locale: str) -> List[Dict[str, str]]:
    if src_cats is None or tgt_cats is None:
        unknown = [loc for loc, cats in ((src_locale, src_cats), (tgt_locale, tgt_cats)) if cats is None]
        return [defect("plural-rules-unknown", "error", key,
                       "no CLDR plural table entry for %s; categories not guessed" % ", ".join(unknown))]
    out = []
    sp, tp = src["plural"], tgt["plural"]
    if set(sp) != set(src_cats):
        out.append(defect("plural-categories", "error", key,
                          "source forms %s differ from CLDR %s for %s" % (sorted(sp), sorted(src_cats), src_locale)))
    if set(tp) != set(tgt_cats):
        out.append(defect("plural-categories", "error", key,
                          "target forms %s differ from CLDR %s for %s" % (sorted(tp), sorted(tgt_cats), tgt_locale)))
    if "other" in sp:
        need = placeholders(sp["other"])
        for form, text in sorted(tp.items()):
            have = placeholders(text)
            required = Counter({t: n for t, n in need.items()
                                if not (form in OPTIONAL_COUNT_FORMS and is_count_placeholder(t))})
            missing = required - have
            extra = have - need
            if missing or extra:
                parts = []
                if missing:
                    parts.append("missing " + ", ".join(sorted(missing.elements())))
                if extra:
                    parts.append("unexpected " + ", ".join(sorted(extra.elements())))
                out.append(defect("plural-placeholder", "error", key,
                                  "form %r: %s (source other has %s)" % (form, "; ".join(parts), ", ".join(sorted(need.elements())) or "none")))
    return out


def check_catalogs(source: Dict[str, Any], target: Dict[str, Any],
                   glossary: List[Dict[str, str]], table: Dict[str, List[str]]) -> Dict[str, Any]:
    defects: List[Dict[str, str]] = []
    s_loc, t_loc = source["locale"], target["locale"]
    s_lang, t_lang = base_lang(s_loc), base_lang(t_loc)
    s_cats, t_cats = table.get(s_lang), table.get(t_lang)
    ok_same = set(source.get("same_as_source_ok", [])) | set(target.get("same_as_source_ok", []))

    if target["source_revision"] != source["source_revision"]:
        defects.append(defect("stale-source-revision", "error", CATALOG_KEY,
                              "target source_revision %r differs from source %r" % (target["source_revision"], source["source_revision"])))
    for label, cat in (("source", source), ("target", target)):
        in_rtl_set = base_lang(cat["locale"]) in RTL_LANGS
        if in_rtl_set != (cat["direction"] == "rtl"):
            defects.append(defect("direction-mismatch", "error", CATALOG_KEY,
                                  "%s locale %s is %s but direction is %s" % (
                                      label, cat["locale"], "rtl" if in_rtl_set else "ltr", cat["direction"])))
    rtl_target = t_lang in RTL_LANGS or target["direction"] == "rtl"
    terms = [t for t in glossary if base_lang(t["locale"]) == t_lang]

    for key, smsg in source["messages"].items():
        tmsg = target["messages"].get(key)
        if tmsg is None:
            defects.append(defect("missing-translation", "error", key, "key absent from target"))
            continue
        s_plural, t_plural = "plural" in smsg, "plural" in tmsg
        if s_plural != t_plural:
            defects.append(defect("plural-categories", "error", key,
                                  "source is %s but target is %s" % ("plural" if s_plural else "plain text", "plural" if t_plural else "plain text")))
            continue
        sf, tf = forms_of(smsg), forms_of(tmsg)
        for form, text in sorted(tf.items()):
            if not text.strip():
                defects.append(defect("missing-translation", "error", key, "empty target text" + (" for form %r" % form if form else "")))
        shared = [f for f in sf if f in tf and tf[f].strip()]
        if key not in ok_same and shared and all(tf[f] == sf[f] for f in shared):
            defects.append(defect("untranslated", "error", key, "target text is identical to source"))
        if s_plural:
            defects.extend(check_plurals(key, smsg, tmsg, s_cats, t_cats, s_loc, t_loc))
        else:
            if placeholders(sf[""]) != placeholders(tf[""]) and tf[""].strip():
                defects.append(defect("placeholder-mismatch", "error", key,
                                      "source has %s, target has %s" % (sorted(placeholders(sf[""]).elements()), sorted(placeholders(tf[""]).elements()))))
            max_len = smsg.get("max_length")
            if max_len is not None and len(tf[""]) > max_len:
                defects.append(defect("length-exceeds-max", "error", key,
                                      "target is %d characters, max_length is %d" % (len(tf[""]), max_len)))
        for form, text in sorted(tf.items()):
            defects.extend(check_form_text(key, text, rtl_target))
            if form in sf:
                for term in terms:
                    if re.search(r"\b%s\b" % re.escape(term["source"]), sf[form], re.IGNORECASE) \
                            and term["target"].lower() not in text.lower():
                        defects.append(defect("terminology-mismatch", "error", key,
                                              "source term %r requires target term %r" % (term["source"], term["target"])))

    defects.sort(key=lambda d: (d["key"], d["code"], d["message"]))
    counts = dict(Counter(d["code"] for d in defects))
    if any(d["code"] == "plural-rules-unknown" for d in defects):
        status = "blocked"
    elif defects:
        status = "defects"
    else:
        status = "pass"
    return {
        "source_locale": s_loc,
        "target_locale": t_loc,
        "status": status,
        "defects": defects,
        "counts": counts,
        "linguistic_review": dict(LINGUISTIC_REVIEW),
        "not_checked": list(NOT_CHECKED),
    }


class QuietParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        print(json.dumps({"error": "usage: " + message}, indent=2, sort_keys=True))
        sys.exit(2)


def main(argv: Optional[List[str]] = None) -> int:
    parser = QuietParser(description="Check a target string catalog against its source.")
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--glossary")
    args = parser.parse_args(argv)
    try:
        source = validate_catalog(load_json(args.source), args.source)
        target = validate_catalog(load_json(args.target), args.target)
        glossary = validate_glossary(load_json(args.glossary), args.glossary) if args.glossary else []
        plural_ref = load_plural_table()
    except InputError as exc:
        print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True))
        return 2
    result = check_catalogs(source, target, glossary, plural_ref["categories"])
    result["cldr_version"] = plural_ref["cldr_version"]
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 1 if any(d["severity"] == "error" for d in result["defects"]) else 0


if __name__ == "__main__":
    sys.exit(main())
