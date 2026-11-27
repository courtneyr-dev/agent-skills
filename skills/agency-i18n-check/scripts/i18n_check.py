#!/usr/bin/env python3
"""Check gettext catalogs and page templates for i18n defects before release.

Structural checks only. Linguistic review stays a human step: the output always says so.
"""
import argparse
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple

# Plural counts from GlotPress locales/locales.php (translate.wordpress.org). See references/gettext-and-plurals.md.
PLURAL_COUNTS = {"ar": 6, "he": 2, "ru": 3, "pl": 3, "ja": 1, "zh_CN": 1, "es": 2, "fr": 2, "de": 2, "en": 2, "fa": 2, "ur": 2}
# Every GlotPress locale with text_direction 'rtl' (locales/locales.php, develop branch, retrieved 2026-11-25), by slug
# and, where it differs, ISO 639-1 code (snd is sd). A catalog whose translations are mostly right-to-left script also
# counts as right-to-left, whatever its name says. See references/rtl-layout.md.
RTL_LANGS = {"ar", "arq", "ary", "azb", "bcc", "bgn", "ckb", "dv", "fa", "ha", "haz", "he", "nqo", "ps", "sd", "skr", "snd", "ug", "ur", "yi"}

LIMITS = [
    "It does not judge meaning, tone, register or cultural fit; a human language reviewer does.",
    "It does not render the page, so visual overflow beyond declared max-length budgets needs a browser or human check.",
    "It only knows the plural counts in its table (ar, he, ru, pl, ja, zh_CN, es, fr, de, en, fa, ur); other languages get a non-blocking finding.",
    "CSS checks read declarations line by line after decoding CSS escapes, including four-value margin, padding, inset, scroll-margin, scroll-padding and border-width, border-style and border-color shorthand; rules built by preprocessors are not inspected, and border-radius corners and background-position keywords are not checked.",
    "Direction checks read dir on <html> and <body>, and CSS direction in every rule whose subject is html, body, :root or * (with any class, attribute or pseudo-class), inside @media, @supports and similar blocks too. dir=\"auto\", and a direction, margin, padding or inset value built with var(), are refused as unresolved. A dir=\"ltr\" on an inner element, such as an embedded code sample, is allowed.",
]
LINGUISTIC_REVIEW = {
    "status": "required",
    "owner": "human:language-reviewer",
    "note": "Structural checks only. A named human language reviewer must read every locale before release.",
}


class InputError(Exception):
    pass


@dataclass
class Entry:
    line: int
    ctxt: Optional[str] = None
    msgid: Optional[str] = None
    plural: Optional[str] = None
    msgstr: Optional[str] = None
    forms: Dict[int, str] = field(default_factory=dict)
    flags: set = field(default_factory=set)
    extracted: List[str] = field(default_factory=list)

    @property
    def key(self) -> Tuple[Optional[str], str]:
        return (self.ctxt, self.msgid)


# ---------- PO parser ----------

KEYWORD = re.compile(r'^(msgctxt|msgid_plural|msgid|msgstr)(?:\[(\d+)\])?\s*(".*")\s*$')
ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"'}


def _unquote(token: str, line: int) -> str:
    body = token[1:-1]
    if re.search(r'(?<!\\)(?:\\\\)*"', body):
        raise InputError("line %d: unescaped quote inside string" % line)
    out, i = [], 0
    while i < len(body):
        if body[i] == "\\":
            if i + 1 >= len(body) or body[i + 1] not in ESCAPES:
                raise InputError("line %d: unsupported escape sequence" % line)
            out.append(ESCAPES[body[i + 1]])
            i += 2
        else:
            out.append(body[i])
            i += 1
    return "".join(out)


def parse_po(text: str) -> List[Entry]:
    """Return entries in file order, header included (msgid ''). Raises InputError('line N: ...')."""
    entries: List[Entry] = []
    cur: Optional[Entry] = None
    target = None  # (field name, form index) that continuation lines extend

    def finish():
        nonlocal cur, target
        if cur is not None and cur.msgid is not None:
            if cur.plural is None and cur.msgstr is None:
                raise InputError("line %d: entry has no msgstr" % cur.line)
            if cur.plural is not None and not cur.forms:
                raise InputError("line %d: msgid_plural entry has no msgstr[n]" % cur.line)
            if cur.plural is None and cur.forms:
                raise InputError("line %d: msgstr[n] without msgid_plural" % cur.line)
            if cur.plural is not None and cur.msgstr is not None:
                raise InputError("line %d: msgid_plural entry uses plain msgstr" % cur.line)
            entries.append(cur)
        cur, target = None, None

    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            finish()
            continue
        if line.startswith("#~"):
            continue
        if line.startswith("#"):
            if cur is not None and (cur.msgstr is not None or cur.forms):
                finish()
            cur = cur or Entry(line=n)
            if line.startswith("#."):
                cur.extracted.append(line[2:].strip())
            elif line.startswith("#,"):
                cur.flags.update(f.strip() for f in line[2:].split(",") if f.strip())
            continue
        if line.startswith('"'):
            if target is None or not re.match(r'^".*"$', line):
                raise InputError("line %d: string with no preceding keyword" % n)
            _extend(cur, target, _unquote(line, n))
            continue
        m = KEYWORD.match(line)
        if not m:
            raise InputError("line %d: unrecognized syntax: %s" % (n, line[:40]))
        kw, idx, token = m.group(1), m.group(2), m.group(3)
        value = _unquote(token, n)
        if kw in ("msgctxt", "msgid") and cur is not None and (cur.msgstr is not None or cur.forms):
            finish()
        cur = cur or Entry(line=n)
        if kw == "msgctxt":
            if cur.msgid is not None or cur.ctxt is not None:
                raise InputError("line %d: msgctxt out of order" % n)
            cur.ctxt, target = value, ("ctxt", None)
        elif kw == "msgid":
            if cur.msgid is not None:
                raise InputError("line %d: duplicate msgid in one entry" % n)
            cur.msgid, cur.line, target = value, n, ("msgid", None)
        elif kw == "msgid_plural":
            if cur.msgid is None or cur.plural is not None:
                raise InputError("line %d: msgid_plural out of order" % n)
            cur.plural, target = value, ("plural", None)
        else:
            if cur.msgid is None:
                raise InputError("line %d: msgstr before msgid" % n)
            if idx is None:
                cur.msgstr, target = value, ("msgstr", None)
            else:
                cur.forms[int(idx)], target = value, ("form", int(idx))
    finish()
    return entries


def _extend(entry: Entry, target, value: str) -> None:
    name, idx = target
    if name == "form":
        entry.forms[idx] += value
    else:
        setattr(entry, name, getattr(entry, name) + value)


def split_header(entries: List[Entry]) -> Tuple[Dict[str, str], Optional[int], List[Entry]]:
    for i, e in enumerate(entries):
        if e.ctxt is None and e.msgid == "":
            headers = {}
            for row in (e.msgstr or "").splitlines():
                k, sep, v = row.partition(":")
                if sep:
                    headers[k.strip()] = v.strip()
            return headers, e.line, entries[:i] + entries[i + 1:]
    return {}, None, entries


# ---------- pure rules ----------

PRINTF = re.compile(r"%%|%(?:(\d+)\$)?[-+ 0#']*(?:\d+|\*)?(?:\.\d+)?(?:hh|h|ll|l|L|q|j|z|t)?([sdiufFeEgGxXocpaA])")
NAMED = re.compile(r"\{[A-Za-z_]\w*\}")


def placeholders(s: str) -> List[str]:
    found = [(m.start(), m.group(0)) for m in PRINTF.finditer(s) if m.group(0) != "%%"]
    found += [(m.start(), m.group(0)) for m in NAMED.finditer(s)]
    return [tok for _, tok in sorted(found)]


def _printf(tokens):
    return [t for t in tokens if t.startswith("%")]


def finding(rule, blocking, line, excerpt, message, file=None):
    out = {"rule": rule, "blocking": blocking, "line": line, "excerpt": excerpt[:80], "message": message}
    if file is not None:
        out["file"] = file
    return out


def check_placeholders(src: Entry, dst: Entry) -> List[dict]:
    ex = src.msgid
    if src.plural is None:
        if not dst.msgstr:
            return []
        want, got = placeholders(src.msgid), placeholders(dst.msgstr)
        if Counter(want) != Counter(got):
            lost = sorted((Counter(want) - Counter(got)).elements())
            extra = sorted((Counter(got) - Counter(want)).elements())
            return [finding("placeholder-mismatch", True, dst.line, ex,
                            "msgstr placeholders differ from msgid; missing %s, unexpected %s. Make the multiset match."
                            % (lost or "none", extra or "none"))]
        plain = [t for t in _printf(want) if "$" not in t]
        plain_got = [t for t in _printf(got) if "$" not in t]
        if len(plain) >= 2 and [t[-1] for t in plain] != [t[-1] for t in plain_got]:
            return [finding("placeholder-mismatch", True, dst.line, ex,
                            "unnumbered placeholders appear in a different type order; use %1$s style numbering to reorder.")]
        return []
    allowed = set(placeholders(src.msgid)) | set(placeholders(src.plural))
    count = next((t for t in _printf(placeholders(src.plural)) if t[-1] in "di"), None)
    required = allowed - {count}
    out = []
    for n, form in sorted(dst.forms.items()):
        if not form:
            continue
        got = set(placeholders(form))
        if got - allowed:
            out.append(finding("placeholder-mismatch", True, dst.line, ex,
                               "msgstr[%d] holds %s, which neither msgid nor msgid_plural has." % (n, sorted(got - allowed))))
        if required - got:
            out.append(finding("placeholder-mismatch", True, dst.line, ex,
                               "msgstr[%d] is missing %s." % (n, sorted(required - got))))
    return out


def locale_base(lang: str) -> str:
    return lang.replace("-", "_").split("_")[0].lower()


def expected_plurals(lang: str) -> Optional[int]:
    norm = lang.replace("-", "_")
    if norm in PLURAL_COUNTS:
        return PLURAL_COUNTS[norm]
    base = norm.split("_")[0]
    return PLURAL_COUNTS.get(base)


def check_plural_forms(headers: dict, header_line, po_entries: List[Entry], pot_entries: List[Entry]) -> List[dict]:
    out = []
    lang = headers.get("Language", "")
    pf = headers.get("Plural-Forms", "")
    m = re.search(r"nplurals\s*=\s*(\d+)", pf)
    declared = int(m.group(1)) if m else None
    if declared is None:
        out.append(finding("plural-forms", True, header_line, "Plural-Forms", "header has no Plural-Forms nplurals=N; add it."))
    if not lang:
        out.append(finding("plural-forms-unknown-locale", False, header_line, "Language", "header has no Language; plural count can't be checked."))
    else:
        want = expected_plurals(lang)
        if want is None:
            out.append(finding("plural-forms-unknown-locale", False, header_line, lang,
                               "Language %s is not in the plural table; check nplurals against GlotPress by hand." % lang))
        elif declared is not None and declared != want:
            out.append(finding("plural-forms", True, header_line, pf,
                               "header declares nplurals=%d but %s needs %d on translate.wordpress.org." % (declared, lang, want)))
    pot_plural = {e.key for e in pot_entries if e.plural is not None}
    for e in po_entries:
        if e.key in pot_plural and e.plural is None:
            out.append(finding("plural-forms", True, e.line, e.msgid, "POT entry is plural but this entry is singular."))
        need = expected_plurals(lang) if lang and expected_plurals(lang) else declared
        if e.plural is None or need is None:
            continue
        filled = [i for i, s in e.forms.items() if s]
        if sorted(e.forms) != list(range(need)) or len(filled) != need:
            out.append(finding("plural-forms", True, e.line, e.msgid,
                               "plural entry needs exactly %d non-empty msgstr[n]; found %d forms, %d non-empty." % (need, len(e.forms), len(filled))))
    return out


def _has_letters(s: str) -> bool:
    return any(c.isalpha() for c in NAMED.sub("", PRINTF.sub("", s)))


def check_catalog(pot_entries: List[Entry], po_entries: List[Entry]) -> List[dict]:
    """untranslated, placeholder-mismatch and length-budget, keyed by (msgctxt, msgid)."""
    out = []
    by_key = {e.key: e for e in po_entries}
    for src in pot_entries:
        dst = by_key.get(src.key)
        if dst is None:
            out.append(finding("untranslated", True, None, src.msgid, "entry is missing from this catalog; add and translate it."))
            continue
        texts = [dst.msgstr] if src.plural is None else [dst.forms[i] for i in sorted(dst.forms)]
        if "fuzzy" in dst.flags:
            out.append(finding("untranslated", True, dst.line, src.msgid, "entry is flagged fuzzy; a human must resolve it."))
        if not any(t for t in texts if t):
            out.append(finding("untranslated", True, dst.line, src.msgid, "msgstr is empty."))
        allow = any(re.match(r"i18n-allow-identical:\s*\S", c) for c in src.extracted)
        same = [t for t in texts if t and t in (src.msgid, src.plural) and _has_letters(t)]
        if same and not allow:
            out.append(finding("untranslated", True, dst.line, src.msgid,
                               "msgstr matches the source text; translate it or add '#. i18n-allow-identical: <reason>' in the POT."))
        for c in src.extracted:
            m = re.match(r"max-length:\s*(\d+)\s*$", c)
            if m:
                over = [t for t in texts if len(t) > int(m.group(1))]
                if over:
                    out.append(finding("length-budget", True, dst.line, src.msgid,
                                       "translation is %d characters; the budget is %s. Shorten it." % (len(over[0]), m.group(1))))
        out += check_placeholders(src, dst)
    return out


class _Page(HTMLParser):
    """Start tags (name, attributes, line, source text) and <style> contents as a browser parses them: comments are
    skipped, unquoted and oddly spaced attributes are read, names are lowercased."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags, self.styles, self._style = [], [], False

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, {k.lower(): (v or "") for k, v in attrs}, self.getpos()[0], self.get_starttag_text() or ""))
        self._style = tag == "style"

    def handle_endtag(self, tag):
        if tag == "style":
            self._style = False

    def handle_data(self, data):
        if self._style:
            self.styles.append((self.getpos()[0], data))


DIRECTION_LTR = re.compile(r"(?<![\w-])direction\s*:\s*ltr\b")
DIRECTION_VAR = re.compile(r"(?<![\w-])direction\s*:[^;}]*\bvar\(")
SHORTHAND_VAR = re.compile(r"(?<![\w-])(?:margin|padding|inset)\s*:[^;}]*\bvar\(")
ROOT_TYPES = ("", "*", "html", "body")
CSS_ESCAPE = re.compile(r"\\([0-9a-f]{1,6})[ \t]?|\\([^\n0-9a-f])", re.I)


def css_plain(css: str) -> str:
    """Comments blanked (newlines kept), CSS escapes decoded (margin-\\6c eft is margin-left), lowercased."""
    text = COMMENT.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), css)
    def decode(m):
        ch = chr(int(m.group(1), 16)) if m.group(1) and 0 < int(m.group(1), 16) < 0x110000 else (m.group(2) or " ")
        return " " if ch in "\r\n" else ch  # keep the line count, so findings keep their line numbers
    return CSS_ESCAPE.sub(decode, text).lower()


def css_rules(text: str) -> List[Tuple[str, str, int]]:
    """(selector, declarations, offset of the declarations) for every style rule, at any depth inside @media,
    @supports, @layer, @container and other block at-rules. Expects css_plain text."""
    out, start, i, n = [], 0, 0, len(text)
    while i < n:
        c = text[i]
        if c == "{":
            prelude = text[start:i].strip()
            if prelude.startswith("@"):
                start = i + 1
            else:
                depth, j = 1, i + 1
                while j < n and depth:
                    depth += {"{": 1, "}": -1}.get(text[j], 0)
                    j += 1
                out.append((prelude, text[i + 1:j - 1], i + 1))
                start = i = j
                continue
        elif c in "};":
            start = i + 1
        i += 1
    return out


def _top_level_split(selector: str) -> List[str]:
    parts, depth, cur = [], 0, ""
    for ch in selector:
        depth += {"(": 1, ")": -1}.get(ch, 0)
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    return parts + [cur]


def targets_root(selector: str) -> bool:
    """True when a selector's subject (its last compound) is html, body, :root or every element, whatever class,
    id, attribute or pseudo-class qualifies it: html[lang], body > *, :root:not(.x), html.rtl."""
    for sel in _top_level_split(selector):
        compound = re.split(r"[\s>+~]+", re.sub(r"\([^()]*\)", "()", sel.strip()))[-1]
        if compound.startswith(":root"):
            return True
        kind = re.sub(r"\[[^\]]*\]|::?[\w-]+(?:\(\))?|[.#][\w-]+", "", compound)
        if kind in ROOT_TYPES and sel.strip():
            return True
    return False


def root_direction(css: str, file: str, first_line: int = 1) -> List[dict]:
    """A CSS rule whose subject is html, body, :root or * and that sets direction: ltr overrides dir on a
    right-to-left page; one that sets direction with var() can't be resolved here, so it is refused too."""
    text = css_plain(css)
    out = []
    for selector, decls, at in css_rules(text):
        if not targets_root(selector):
            continue
        line = first_line + text.count("\n", 0, at)
        excerpt = (" ".join(selector.split()) + " {" + " ".join(decls.split()) + "}")[:120]
        if DIRECTION_LTR.search(decls):
            out.append(finding("rtl-direction", True, line, excerpt,
                               "a rule on %s sets direction: ltr on a page serving a right-to-left locale; remove it so dir decides." % " ".join(selector.split()), file))
        elif DIRECTION_VAR.search(decls):
            out.append(finding("rtl-direction-unresolved", True, line, excerpt,
                               "a rule on %s sets direction from var(); the check can't resolve custom properties, so it can't confirm the page stays right-to-left. Set direction from dir instead." % " ".join(selector.split()), file))
    return out


def check_template(text: str, file: str) -> List[dict]:
    page = _Page()
    page.feed(text)
    page.close()
    out = []
    html_tag = next((t for t in page.tags if t[0] == "html"), None)
    if html_tag is None:
        out.append(finding("rtl-direction", False, None, "", "no <html> element found; check dir and lang in the full layout.", file))
    else:
        out += [finding("rtl-direction", True, html_tag[2], html_tag[3], "<html> lacks %s; set it from the page locale (a literal or a template expression)." % a, file)
                for a in ("dir", "lang") if a not in html_tag[1]]
    for name, attrs, line, src in page.tags:
        if name in ("html", "body"):
            direction = attrs.get("dir", "").strip().lower()
            if direction == "ltr":
                out.append(finding("rtl-direction", True, line, src, "<%s> sets dir=\"ltr\" on a page serving a right-to-left locale; set dir from the locale (rtl here)." % name, file))
            elif direction == "auto":
                out.append(finding("rtl-direction-unresolved", True, line, src, "<%s> sets dir=\"auto\", which lets the browser guess from the first strong character; set dir from the locale (rtl here)." % name, file))
            style = css_plain(attrs.get("style", ""))
            if DIRECTION_LTR.search(style):
                out.append(finding("rtl-direction", True, line, src, "<%s> style sets direction: ltr on a page serving a right-to-left locale; remove it so dir decides." % name, file))
            elif DIRECTION_VAR.search(style):
                out.append(finding("rtl-direction-unresolved", True, line, src, "<%s> style sets direction from var(), which the check can't resolve; set direction from dir." % name, file))
        if attrs.get("style"):
            out += check_css(attrs["style"], file, line)
    for line, css in page.styles:
        out += check_css(css, file, line) + root_direction(css, file, line)
    return out


COMMENT = re.compile(r"/\*.*?\*/", re.S)
ALLOW = re.compile(r"/\*\s*i18n-allow-physical:\s*(\S.*?)\s*\*/", re.I)
PHYSICAL = [
    (re.compile(r"(?<![\w.#-])((?:scroll-)?(?:margin|padding)-(?:left|right))\s*:"), lambda m: m.group(1).replace("left", "inline-start").replace("right", "inline-end")),
    (re.compile(r"(?<![\w.#-])(border-(?:left|right)(?:-[a-z]+)?)\s*:"), lambda m: m.group(1).replace("left", "inline-start").replace("right", "inline-end")),
    (re.compile(r"(?<![\w.#-])(left|right)\s*:(?!:)"), lambda m: "inset-inline-" + ("start" if m.group(1) == "left" else "end")),
    (re.compile(r"(?<![\w.#-])(float\s*:\s*(?:left|right))\b"), lambda m: "float: inline-start or inline-end"),
    (re.compile(r"(?<![\w.#-])(text-align\s*:\s*(?:left|right))\b"), lambda m: "text-align: start or end"),
    (re.compile(r"(?<![\w.#-])(clear\s*:\s*(?:left|right))\b"), lambda m: "clear: inline-start or inline-end"),
    # four-value shorthand whose right and left differ (margin: 0 0 0 10px) is physical; equal sides are symmetric
    (re.compile(r"(?<![\w.#-])((margin|padding|inset|scroll-margin|scroll-padding|border-width|border-style|border-color)\s*:\s*[^\s;!}]+\s+([^\s;!}]+)\s+[^\s;!}]+\s+(?!\3(?:[\s;!}]|$))[^\s;!}]+)"),
     lambda m: "%s-block plus %s-inline-start and %s-inline-end" % (m.group(2), m.group(2), m.group(2))),
]


def check_css(text: str, file: str, first_line: int = 1) -> List[dict]:
    """Property names are case-insensitive, so the match runs on lowercased text. An author exemption silences the
    first physical property on its line but stays in the output, non-blocking, for the language reviewer to confirm."""
    blanked = css_plain(text)
    out = []
    for n, (raw, clean) in enumerate(zip(text.splitlines(), blanked.splitlines()), first_line):
        hits = []
        for rx, suggest in PHYSICAL:
            hits += [(m.start(), m.group(0).strip(), suggest(m)) for m in rx.finditer(clean)]
        for m in SHORTHAND_VAR.finditer(clean):
            out.append(finding("rtl-css-unresolved", True, n, m.group(0).strip(),
                               "a margin, padding or inset shorthand built with var() may set different left and right sides, which the check can't resolve; use the -block and -inline-start/-end properties.", file))
        hits.sort()
        allow = ALLOW.search(raw)
        if hits and allow:
            out.append(finding("rtl-physical-exempted", False, n, hits[0][1],
                               "the page author exempted this physical property (%s); the language reviewer confirms the layout must not flip." % allow.group(1), file))
            hits = hits[1:]
        for _, excerpt, logical in hits:
            out.append(finding("rtl-physical-css", True, n, excerpt,
                               "physical direction breaks right-to-left layout; use %s." % logical, file))
    return out


# ---------- shell ----------

def read_text(path: str) -> str:
    if not os.path.isfile(path):
        raise InputError("file not found: %s" % path)
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (UnicodeDecodeError, OSError) as exc:
        raise InputError("cannot read %s: %s" % (path, exc))


def load_po(path: str) -> List[Entry]:
    try:
        return parse_po(read_text(path))
    except InputError as exc:
        if str(exc).startswith(("file not found", "cannot read")):
            raise
        raise InputError("%s: %s" % (path, exc))


LOCALE_SHAPE = re.compile(r"^[a-z]{2,3}(?:_[A-Z]{2})?$")


def known_locale(tok: str) -> bool:
    return expected_plurals(tok) is not None or locale_base(tok) in RTL_LANGS


def locale_from_path(path: str) -> str:
    """The locale a file name states (ar.po, donate-es.po, pl_PL.po). The catalog's own header never decides."""
    stem = os.path.basename(path)
    stem = stem[:-3] if stem.endswith(".po") else stem
    toks = [x for x in re.split(r"[-.]", stem) if LOCALE_SHAPE.match(x)]
    known = [x for x in toks if known_locale(x)]
    if len(known) > 1:
        raise InputError("%s: the file name names more than one locale (%s); pass --po LOCALE=PATH" % (path, ", ".join(known)))
    if known:
        return known[0]
    if len(toks) == 1:
        return toks[0]
    raise InputError("%s: can't tell the locale from the file name; name it <locale>.po or pass --po LOCALE=PATH" % path)


def split_locale_arg(arg: str) -> Tuple[Optional[str], str]:
    left, sep, right = arg.partition("=")
    if sep and LOCALE_SHAPE.match(left) and right:
        return left, right
    return None, arg


def rtl_script(entries: List[Entry]) -> bool:
    """True when most letters in the translations are right-to-left script (bidi class R or AL), whatever the locale is called."""
    kinds = Counter(unicodedata.bidirectional(c) for e in entries for t in [e.msgstr or ""] + list(e.forms.values()) for c in t if c.isalpha())
    return kinds["R"] + kinds["AL"] > kinds["L"]


def run(pot_path, po_paths, template=None, css_paths=()):
    _, _, pot_entries = split_header(load_po(pot_path))
    locales, any_rtl = [], False
    for arg in po_paths:
        explicit, path = split_locale_arg(arg)
        headers, header_line, entries = split_header(load_po(path))
        if not headers.get("Language"):
            raise InputError("%s: the header has no Language; add it so it can be checked against the file's locale" % path)
        try:
            named = locale_from_path(path)
        except InputError:
            named = None
        if explicit and named and locale_base(named) != locale_base(explicit):
            raise InputError("%s: the file name says %s but --po names %s; rename the file or pass the locale it holds" % (path, named, explicit))
        lang = explicit or named or locale_from_path(path)
        rtl = locale_base(lang) in RTL_LANGS or rtl_script(entries)
        any_rtl = any_rtl or rtl
        mismatch = []
        if locale_base(headers["Language"]) != locale_base(lang):
            mismatch = [finding("locale-mismatch", True, header_line, "Language: " + headers["Language"],
                                "the header says %s but this file is the %s catalog; rules follow %s. Fix the header." % (headers["Language"], lang, lang))]
        findings = mismatch + check_plural_forms(dict(headers, Language=lang), header_line, entries, pot_entries) + check_catalog(pot_entries, entries)
        for f in findings:
            f["file"] = path
        locales.append({"locale": lang, "direction": "rtl" if rtl else "ltr", "file": path, "findings": findings})
    template_findings, limits = [], list(LIMITS)
    rtl_inputs = ([template] if template else []) + list(css_paths)
    if any_rtl:
        if template:
            template_findings += check_template(read_text(template), template)
        for css in css_paths:
            text = read_text(css)
            template_findings += check_css(text, css) + root_direction(text, css)
        if not rtl_inputs:
            limits.append("A right-to-left locale was checked but no --template or --css was given, so the RTL layout rules did not run.")
    elif rtl_inputs:
        limits.append("No checked locale is right-to-left, so the template and CSS rules did not run.")
    blocking = any(f["blocking"] for loc in locales for f in loc["findings"]) or any(f["blocking"] for f in template_findings)
    return {"ok": not blocking, "locales": locales, "template_findings": template_findings,
            "linguistic_review": dict(LINGUISTIC_REVIEW), "limits": limits}


class JsonParser(argparse.ArgumentParser):
    def error(self, message):
        emit({"error": message})
        sys.exit(2)


def emit(obj):
    print(json.dumps(obj, indent=2, sort_keys=True))


def main(argv=None):
    p = JsonParser(description="Check gettext catalogs and page templates for i18n defects.")
    p.add_argument("--pot", required=True)
    p.add_argument("--po", action="append", required=True)
    p.add_argument("--template")
    p.add_argument("--css", action="append", default=[])
    args = p.parse_args(argv)
    try:
        result = run(args.pot, args.po, args.template, args.css)
    except InputError as exc:
        emit({"error": str(exc)})
        return 2
    emit(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
