#!/usr/bin/env python3
"""Render template.html into donate.<locale>.html for en (source strings) and every locales/<locale>.po.

SYNTHETIC FIXTURE (Fixture Co). Standard library only. Fails (exit 1) on any template key missing from a
catalog, so a page can never ship with an untranslated or unknown string.
"""
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RTL = {"ar", "he", "fa", "ur"}
PLURAL = {  # CLDR cardinal rules for the locales this page ships, as gettext form indexes
    "en": lambda n: 0 if n == 1 else 1,
    "es": lambda n: 0 if n == 1 else 1,
    "ar": lambda n: 0 if n == 0 else 1 if n == 1 else 2 if n == 2 else 3 if 3 <= n % 100 <= 10 else 4 if 11 <= n % 100 <= 99 else 5,
}
KEY = re.compile(r"\{\{(.+?)\}\}")


def unquote(s):
    return re.sub(r'\\(.)', lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), s[1:-1])


def read_po(path):
    """{msgid: msgstr or [forms]} for single-line entries, as build.py's own catalogs are written."""
    out, cur = {}, {}
    for line in open(path, encoding="utf-8").read().splitlines() + [""]:
        m = re.match(r'^(msgid|msgid_plural|msgstr)(?:\[(\d+)\])?\s+(".*")$', line)
        if m:
            kw, idx, val = m.group(1), m.group(2), unquote(m.group(3))
            if kw == "msgstr" and idx is not None:
                cur.setdefault("forms", []).append(val)
            else:
                cur[kw] = val
        elif not line.strip() and cur:
            if cur.get("msgid"):
                out[cur["msgid"]] = cur.get("forms") or cur.get("msgstr")
            cur = {}
    return out


def render(template, lang, catalog):
    missing = []

    def sub(m):
        key = m.group(1)
        if key == "lang":
            return lang
        if key == "dir":
            return "rtl" if lang in RTL else "ltr"
        if key.startswith("n:"):
            msgid, n = key[2:].rsplit("|", 1)
            forms = catalog.get(msgid)
            if not forms:
                missing.append(msgid)
                return ""
            return html.escape(forms[PLURAL[lang](int(n))].replace("%d", n))
        if not catalog.get(key):
            missing.append(key)
            return ""
        return html.escape(catalog[key])
    page = KEY.sub(sub, template)
    return page, missing


def main():
    template = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    pot = read_po(os.path.join(HERE, "locales", "donate.pot"))
    source = {k: k for k in pot}
    pot_text = open(os.path.join(HERE, "locales", "donate.pot"), encoding="utf-8").read()
    for m in re.finditer(r'msgid ("(?:[^"\\]|\\.)*")\nmsgid_plural ("(?:[^"\\]|\\.)*")', pot_text):
        source[unquote(m.group(1))] = [unquote(m.group(1)), unquote(m.group(2))]
    catalogs = {"en": source}
    for name in sorted(os.listdir(os.path.join(HERE, "locales"))):
        if name.endswith(".po"):
            catalogs[name[:-3]] = read_po(os.path.join(HERE, "locales", name))
    failed = False
    for lang, catalog in catalogs.items():
        page, missing = render(template, lang, catalog)
        if missing:
            print("donate.%s.html: missing %s" % (lang, ", ".join(missing)))
            failed = True
            continue
        with open(os.path.join(HERE, "donate.%s.html" % lang), "w", encoding="utf-8") as fh:
            fh.write(page)
        print("wrote donate.%s.html" % lang)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
