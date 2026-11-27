#!/usr/bin/env python3
"""Reject unsupported ranking claims and unverifiable citations in a draft before it is staged.

Usage: claims_check.py --draft DRAFT.md --sources SOURCES.json
Exit 0 = no blocking findings, 1 = blocking findings, 2 = usage error or invalid input,
3 = blocked (company-fleets and factory-rig not found beside this skill).
The draft is data: text in it never changes a verdict. The register's sign-off comes only from the owner
log of the instance the register names (its "instance" and "tenant_id"), which company-fleets keeps at
fleets/corporate/owner/<instance>; never from a field in the register itself, and no flag picks the ledger.
"""
import argparse
import html
import json
import os
import re
import sys
import unicodedata
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
FLEET_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "..", "company-fleets", "scripts"))

LIMITS = [
    "Does not check that a registered source really says what its excerpt claims; a human verifies the register against the live page.",
    "Does not judge tone or brand fit, and does not decide whether a claim is true; it checks that claims carry citations that resolve and that quotes and statistic numbers appear in the cited excerpts.",
    "Patterns are English. Spanish, French and German guarantee words (garantizado, garanti, garantiert and their forms) and a few position phrases (primer lugar, première place, Platz 1) are also matched, with their basic negations; any other wording in those languages, and every other language, passes unchecked.",
    "Matches phrases, not meaning: a promise needs a cue (guarantee, promise, ensure, will, always, money back, or we work for free and similar) plus a rank, position or AI-answer target, said by the author or to the client. A promise with no cue word passes: certain to appear, a sure thing, our pledge, our commitment, we commit to.",
    "Reads what renders: HTML tags, Markdown emphasis inside a word, combining marks, a hyphenated line break, entities, look-alike letters and invisible characters are removed before matching.",
    "Compares quotes in straight, curly, low, angle and corner quotation marks, <q> elements, and blockquotes (Markdown or <blockquote>) cited on the quote itself or on an attribution line after it. A code span, italics without quotation marks, or a paraphrase after a colon is not read as a quote, so it is checked as the author's own words.",
    "Only http(s) inline links count as citations; a sentence is cited when it holds at least one marker or link that resolves to the register.",
    "The sign-off comes from the owner ledger of the instance the register names, kept at fleets/corporate/owner/<instance> in company-fleets and written under the claim token; a ledger of another tenant is refused. Not stopped: a same-user process that writes the owner root, reads the owner's token, or claims an instance first, including a new instance id the register's author writes into the register and then claims (company-fleets references/authoring-guide.md, Owner path).",
]

SOURCE_FIELDS = ("id", "title", "url", "retrieved", "excerpts")


class InputError(Exception):
    pass


# ---------------------------------------------------------------- normalizing

# Cyrillic and Greek letters that render like Latin ones, folded so a look-alike can't hide a cue word.
_LOOKALIKES = {  # Cyrillic and Greek letters that render like Latin ones
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "һ": "h",
    "ӏ": "l", "ԛ": "q", "ԝ": "w", "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C",
    "Т": "T", "Х": "X", "У": "Y", "І": "I", "Ј": "J", "Ѕ": "S", "ο": "o", "α": "a", "ε": "e", "ι": "i", "κ": "k", "ν": "v",
    "ρ": "p", "τ": "t", "υ": "u", "χ": "x", "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M",
    "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X"}
_CONFUSABLE = str.maketrans(_LOOKALIKES)
_QUOTES = str.maketrans({"“": '"', "”": '"', "„": '"', "‟": '"', "«": '"', "»": '"', "‘": "'", "’": "'", "‚": "'", "‹": "'", "›": "'",
                         "「": '"', "」": '"', "『": '"', "』": '"'})
_INVISIBLE_MARKS = {"͏"} | {chr(c) for c in range(0xFE00, 0xFE10)} | {"᠋", "᠌", "᠍"}


def clean_line(line):
    """What a reader sees: HTML entities decoded, NFKC (fullwidth, №, ligatures), format characters
    (zero-width, soft hyphen, bidi marks), combining marks and invisible joiners dropped, spaced-out letters
    rejoined, look-alike letters folded to Latin."""
    text = unicodedata.normalize("NFKC", html.unescape(line)).replace("\n", " ")
    text = "".join(c for c in text if unicodedata.category(c) not in ("Cf", "Mn", "Me") and c not in _INVISIBLE_MARKS)
    text = re.sub(r"\b(?:[^\W\d_] ){3,}[^\W\d_]\b", lambda m: m.group(0).replace(" ", ""), text)  # "G u a r a n t e e d"
    return text.translate(_CONFUSABLE)


def clean(text):
    return "\n".join(clean_line(line) for line in text.split("\n"))


def norm(text):
    return re.sub(r"\s+", " ", text.translate(_QUOTES)).strip()


_BLOCKQUOTE_HTML = re.compile(r"<blockquote\b[^>]*>(.*?)</blockquote\s*>", re.I | re.S)
_Q_HTML = re.compile(r"<q\b[^>]*>(.*?)</q\s*>", re.I | re.S)
_A_HTML = re.compile(r"<a\b[^>]*\bhref\s*=\s*[\"']?(https?://[^\"'\s>]+)[\"']?[^>]*>(.*?)</a\s*>", re.I | re.S)
_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9-]*(?:\s[^<>]*)?/?>")
_EMPHASIS = re.compile(r"\*{1,3}|~~|(?<![\w/])_{1,3}(?=\w)|(?<=\w)_{1,3}(?![\w/])")
_LINE_HYPHEN = re.compile(r"(?<=[^\W\d_])-[ \t]*\n\s*(?=[^\W\d_])")


def render_html(text):
    """HTML the draft carries, as a reader meets it: <blockquote> becomes a Markdown blockquote (same line count),
    <q> becomes quotation marks, <a href> becomes a Markdown link, and every other tag is dropped."""
    def bq(m):
        return "\n".join("> " + l.strip() for l in _TAG.sub("", m.group(1)).split("\n"))
    text = _BLOCKQUOTE_HTML.sub(bq, text)
    text = _Q_HTML.sub(lambda m: '"%s"' % m.group(1), text)
    text = _A_HTML.sub(lambda m: "[%s](%s)" % (m.group(2), m.group(1)), text)
    return _TAG.sub("", text)


# ---------------------------------------------------------------- register

def validate_register(data):
    """Return the source list or raise InputError."""
    if not isinstance(data, dict) or not isinstance(data.get("sources"), list) or not data["sources"]:
        raise InputError("sources file needs a non-empty 'sources' list")
    seen = set()
    for i, src in enumerate(data["sources"]):
        where = "source %d" % (i + 1)
        if not isinstance(src, dict):
            raise InputError("%s is not an object" % where)
        for field in SOURCE_FIELDS:
            if field not in src:
                raise InputError("%s is missing '%s'" % (where, field))
        for field in ("id", "title", "url", "retrieved"):
            if not isinstance(src[field], str) or not src[field].strip():
                raise InputError("%s has an empty '%s'" % (where, field))
        if not re.match(r"^https?://\S+$", src["url"]):
            raise InputError("%s url must start with http:// or https://" % where)
        try:
            datetime.strptime(src["retrieved"], "%Y-%m-%d")
        except ValueError:
            raise InputError("%s 'retrieved' must be YYYY-MM-DD" % where)
        ex = src["excerpts"]
        if not isinstance(ex, list) or not any(isinstance(e, str) and e.strip() for e in ex):
            raise InputError("%s needs at least one non-empty excerpt" % where)
        if src["id"] in seen:
            raise InputError("duplicate source id %s" % src["id"])
        seen.add(src["id"])
    return data["sources"]


def sign_off_findings(register, fr):
    """The owner log of the instance the register names must hold a sign-off for these exact sources by a named
    human other than the author. Any edit to the sources changes their hash, so it needs a new owner-recorded sign-off."""
    def f(rule, message):
        return {"rule": rule, "blocking": True, "line": None, "excerpt": "sources register", "message": message}
    ol, sources = fr["ownerlog"], register["sources"]
    if "instance" not in register:
        return [f("register-not-signed-off", "The register names no instance, so there is no owner ledger to hold its sign-off. Add the engagement's instance and tenant_id; the contract owner records the sign-off in that instance's ledger.")], None
    try:
        _, entries = ol.read_for("corporate", register["instance"], {"tenant": register.get("tenant_id")}, fr["registry"])
    except ol.OwnerLogError as exc:
        return [f(exc.reason, exc.detail)], None
    rec = ol.effective(entries, "claims-sign-off", fr["sha"](sources))
    if rec is None:
        return [f("register-not-signed-off", "The owner log has no sign-off for these exact sources. A reviewer other than the author checks each excerpt against the live page, and the contract owner records it with fleet owner-record --kind claims-sign-off.")], None
    body = rec["body"]
    if body["signed_off_by"] == body["author"]:
        return [f("register-self-signed", "The register's author signed it off; a different person must check the excerpts.")], None
    return [], {"signed_off_by": body["signed_off_by"], "author": body["author"], "owner_log_seq": rec["seq"]}


# ---------------------------------------------------------------- draft structure

_FOOTNOTE_DEF = re.compile(r"^\[\^([^\]\s]+)\]:\s*")
_COMMENT = re.compile(r"^<!--.*-->$")
_HEADING = re.compile(r"^#{1,6}\s")
_LIST = re.compile(r"^(?:[-*+]|\d+[.)])\s+")
_FENCE = re.compile(r"^(```|~~~)")
_ATTRIBUTION = re.compile(r"^(?:—|–|--|―)\s*\S")


def attribution(line):
    """A line after a blockquote that names who said it: a dash line, or a short cited name with no sentence in it."""
    if _ATTRIBUTION.match(line):
        return True
    words = re.sub(r"\[\^[^\]\s]+\]", "", line).strip()
    return bool(re.search(r"\[\^[^\]\s]+\]", line)) and not re.search(r"[.!?]", words) and len(words.split()) <= 8
_MARKERS_TAIL = re.compile(r"(?:\[\^[^\]\s]+\])+")
_MARKERS_ANY = re.compile(r"\[\^[^\]\s]+\]")


def split_blocks(text):
    """Return [(first_line_number, text, kind, cite_ids)]. kind: para, quote or footnote. Fenced code counts as
    text a reader sees; a footnote definition is text cited by its own id; a blockquote is a quotation when it is
    cited on itself (> words[^S1]) or by the attribution line after it (— Source[^S1], or a short cited name).
    An unclosed fence is invalid input."""
    blocks, cur, start, fence = [], [], None, None

    def flush(kind="para", cite=()):
        nonlocal cur, start
        if cur:
            blocks.append([start, "\n".join(cur), kind, list(cite)])
        cur, start = [], None

    quote = []
    for no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if fence:
            if line.startswith(fence[0]):
                flush()
                fence = None
            else:
                start = start or no
                cur.append(line)
            continue
        m = _FENCE.match(line)
        if m:
            flush()
            fence = (m.group(1), no)
            continue
        if line.startswith(">"):
            quote.append((no, line.lstrip("> ").strip()))
            continue
        if quote and line:
            body = " ".join(t for _, t in quote if t)
            if attribution(line):  # the attribution line is still read below as the author's own text
                blocks.append([quote[0][0], body, "quote", re.findall(r"\[\^([^\]\s]+)\]", line)])
            else:
                blocks.append([quote[0][0], body, "quote" if _MARKERS_ANY.search(body) else "para", []])
            quote = []
        if not line or _COMMENT.match(line):
            flush()
            continue
        fn = _FOOTNOTE_DEF.match(line)
        if fn:
            flush()
            blocks.append([no, line[fn.end():], "footnote", [fn.group(1)]])
            continue
        if _HEADING.match(line):
            flush()
            blocks.append([no, line, "para", []])
            continue
        if _LIST.match(line):
            flush()
            line = _LIST.sub("", line, count=1)
        if not cur:
            start = no
        cur.append(line)
    if fence:
        raise InputError("the draft opens a %s fence at line %d and never closes it, so every later line would be hidden from the check; close it" % fence)
    if quote:
        body = " ".join(t for _, t in quote if t)
        blocks.append([quote[0][0], body, "quote" if _MARKERS_ANY.search(body) else "para", []])
    flush()
    return sorted(blocks, key=lambda b: b[0])


def split_sentences(text):
    """Return [(offset, sentence)]. Never splits inside double quotes."""
    out, n, i, start, inq = [], len(text), 0, 0, False
    while i < n:
        c = text[i]
        boundary_from = None
        if c == '"':
            inq = not inq
            if not inq and i > 0 and text[i - 1] in ".!?":
                boundary_from = i + 1
        elif c in "„«" or (c == "“" and not inq):
            inq = True
        elif c in "”»“":
            inq = False
            if i > 0 and text[i - 1] in ".!?":
                boundary_from = i + 1
        elif c in ".!?" and not inq:
            j = i + 1
            while j < n and text[j] in "”')":
                j += 1
            boundary_from = j
        if boundary_from is not None:
            j = boundary_from
            m = _MARKERS_TAIL.match(text, j)
            if m:
                j = m.end()
            if j >= n or text[j].isspace():
                piece = text[start:j]
                if piece.strip():
                    out.append((start + len(piece) - len(piece.lstrip()), piece.strip()))
                start = j
                i = j
                continue
        i += 1
    tail = text[start:]
    if tail.strip():
        out.append((start + len(tail) - len(tail.lstrip()), tail.strip()))
    return out


# ---------------------------------------------------------------- the guarantee rule

# A guarantee is an un-negated promise cue plus a target the cue can promise, said by the author or to the client.
# Cue classes: (pattern, targets it pairs with). PROMISE verbs said by a third party ("Google guarantees nothing",
# "Agencies that promise top rankings") are reported speech; a prediction (WILL, ALWAYS) about a search or AI engine
# ("ChatGPT will cite your brand") is still the author's promise to the client.
PROMISE = re.compile(r"\b(?:guarantee[ds]?|guaranteeing|assured?|assures|promise[ds]?|promising|risk[- ]free)\b"
                     r"|\bmoney[- ]back\b|\bor you don'?t pay\b|\bor it'?s free\b|\bor (?:we|you)\b[^.;]{0,24}\bfree\b"
                     r"|\bgaranti\w*|\bgarantiz\w*|\bgarantier\w*")  # es, fr, de: garantizado, garanti(e), garantiert
QUALIFIER = re.compile(r"\b(?:certified|warrant(?:s|ed|y|ies)?)\b")  # "Number one on Google, certified": the position comes first
COMMIT = re.compile(r"\b(?:ensures?|ensuring|make sure|makes sure|count on|rest assured)\b")  # "We ensure first-page rankings"
WILL_CUE = re.compile(r"\bwill\b|'ll\b|\bshall\b|\b(?:is|are) going to\b")
ALWAYS_CUE = re.compile(r"\balways\b|\bevery time\b|\bnever fails?\b")
ACHIEVE_CUE = re.compile(r"\b(?:dominate|hit|land|reach|deliver|get you|put you|take you|secure|win)\b")
TIME_CUE = re.compile(r"\b(?:in|within)\s+(?:\d+|a|one|two|three|four|six|thirty|ninety)\s+(?:days?|weeks?|months?)\b"
                      r"|\bby (?:next )?(?:week|month|quarter|spring|summer|fall|autumn|winter|year)\b|\bovernight\b")
POSITION = re.compile(r"#\s?1\b|\bno\.?\s?1\b|\bnumber (?:one|1)\b|\btop\s+(?:\d+|one|two|three|five|ten)\b"
                      r"|\bprimer lugar\b|\bprimera (?:posici[oó]n|p[aá]gina)\b|\bpremi[eè]re (?:place|position|page)\b"
                      r"|\berste[nr]? (?:platz|seite|position)\b|\bplatz (?:1|eins)\b"
                      r"|\btop (?:spot|position|result|results|ranking|rankings|placement)\b|\b(?:first|1st)[- ](?:page|place|position|result)s?\b"
                      r"|\bpage (?:one|1)\b|\btop of (?:google|bing|yahoo|search|the (?:search )?results)\b|\bposition (?:one|1)\b"
                      r"|\branked (?:first|#\s?1|number one|top)\b")
RANK_TARGET = re.compile(r"\brank(?:s|ed|ing|ings)?\b|\bvisibility\b|\btraffic\b|\binclusion\b")
AI_TARGET = re.compile(r"\b(?:ai (?:answers?|overviews?|mode|search|results)|chatgpt|perplexity|gemini|copilot|claude)\b")
AI_VERB = re.compile(r"\b(?:cite[sd]?|citing|recommend(?:s|ed)?|feature[sd]?|mention(?:s|ed)?|include[sd]?|inclusion|appear|show up|shown|listed|surface|be the answer)\b")
RANK_VERB_AFTER = re.compile(r"^\s+(?:\w+ly\s+|soon\s+|also\s+)?(?:rank|be ranked|outrank)\b")
NOT_AFTER = re.compile(r"^\s+(?:not|never|nothing|no)\b")
CLAIM_RESULT = re.compile(r"\b(?:you|your (?:site|pages?|brand|business|store|website|content))\s+(?:\w+\s+)?(?:ranks?|is ranked|are ranked|sits?|appears?)\b")

# Who says it: the nearest speaker word before the cue, in the cue's own clause. A third-party subject makes a
# promise verb reported speech ("Agencies that promise top rankings", "Google guarantees nothing"); a search or AI
# engine counts as that subject only for promise verbs, because "ChatGPT will cite your brand" is the author's prediction.
FIRST = {"we", "our", "us", "i", "my", "me", "we'll", "we're", "we've", "ours"}
SECOND = {"you", "your", "you'll", "you're", "you've", "yours"}
ENGINES = {"google", "google's", "bing", "yahoo", "chatgpt", "perplexity", "gemini", "copilot", "claude"}
THIRD = {"who", "that", "which", "whom", "he", "she", "they", "anyone", "anybody", "someone", "somebody", "nobody",
         "everyone", "everybody", "others", "agency", "agencies", "vendor", "vendors", "consultant", "consultants", "seo", "seos",
         "company", "companies", "firm", "firms", "provider", "providers", "competitor", "competitors", "scam", "scams"}
_CLAUSE_BREAK = re.compile(r"[,;:]|\b(?:but|however|yet|and|or|while|whereas)\b")


def _clause_before(low, pos):
    return _CLAUSE_BREAK.split(low[:pos])[-1]


PREPOSITIONS = {"on", "in", "at", "for", "from", "of", "to", "with", "by", "across", "inside", "within", "into", "onto", "over"}


def speaker(low, pos, engines_speak):
    """first, second, third or none (an imperative or a headline fragment) for the cue at pos. A search or AI engine
    after a preposition ("a #1 ranking on Google is guaranteed") is where the result shows, not who speaks."""
    words = re.findall(r"[a-z][a-z'#]*", _clause_before(low, pos))
    for i in range(len(words) - 1, -1, -1):
        word = words[i]
        if word in FIRST:
            return "first"
        if word in SECOND:
            return "second"
        if word in THIRD or (engines_speak and word in ENGINES and not (i and words[i - 1] in PREPOSITIONS)):
            return "third"
    return "none"


_NEG = re.compile(
    r"\b(?:no one|nobody|cannot|can't|can not|won't|will not|don't|do not|doesn't|does not|didn't"
    r"|never|isn't|is not|aren't|not|no|beware|be wary|myth|red flag|scam"
    r"|ne|n'|nicht|kein(?:e|en|er|em)?|jamais|aucune?|nunca|jam[aá]s|ning[uú]n[oa]?"
    r"|claims? to|claiming to|too good to be true)\b"
)
_NEG_EXEMPT = re.compile(r"\b(?:not only|no doubt|no wonder|no other|no matter)\b")


def negated(sentence, pos):
    """True when the clause before pos negates the match."""
    return bool(_NEG.search(_NEG_EXEMPT.sub("", _clause_before(sentence, pos))))


def _words_between(low, a, b):
    return len(re.findall(r"[\w#']+", low[min(a, b):max(a, b)]))


def _same_clause(low, a, b):
    return not _CLAUSE_BREAK.search(low[min(a, b):max(a, b)])


def guarantee_hit(low):
    """Return the cue and target that make a lowercased sentence a ranking or AI-answer guarantee, or None."""
    def live(rx, engines_speak=False):
        return [m for m in rx.finditer(low) if not negated(low, m.start()) and not NOT_AFTER.match(low[m.end():])
                and speaker(low, m.start(), engines_speak) != "third"]
    pos = [m for m in POSITION.finditer(low) if not negated(low, m.start())]
    targets = pos + list(RANK_TARGET.finditer(low)) + list(AI_TARGET.finditer(low))
    for cue in live(PROMISE, True):
        if targets:
            return "%s ... %s" % (cue.group(0), targets[0].group(0))
    for cue in live(QUALIFIER, True):
        near = [m for m in pos if m.end() <= cue.start() and _words_between(low, m.end(), cue.start()) <= 4]
        if near:
            return "%s ... %s" % (near[-1].group(0), cue.group(0))
    for cue in live(COMMIT, True):
        near = [m for m in pos if m.start() > cue.start() and _words_between(low, cue.end(), m.start()) <= 5 and _same_clause(low, cue.end(), m.start())]
        if near:
            return "%s ... %s" % (cue.group(0), near[0].group(0))
    for cue in live(WILL_CUE):
        if RANK_VERB_AFTER.match(low[cue.end():]):
            return cue.group(0) + RANK_VERB_AFTER.match(low[cue.end():]).group(0)
        near = [m for m in pos if m.start() > cue.start() and _words_between(low, cue.end(), m.start()) <= 6]
        verb = next((v for v in AI_VERB.finditer(low[cue.end():]) if _words_between(low[cue.end():], 0, v.start()) <= 2), None)
        if near:
            return "%s ... %s" % (cue.group(0), near[0].group(0))
        if verb and AI_TARGET.search(low):
            return "%s %s ... %s" % (cue.group(0), verb.group(0), AI_TARGET.search(low).group(0))
    for cue in live(ALWAYS_CUE):
        if pos or (AI_TARGET.search(low) and AI_VERB.search(low)):
            return "%s ... %s" % (cue.group(0), (pos[0] if pos else AI_TARGET.search(low)).group(0))
    for cue in live(ACHIEVE_CUE):
        near = [m for m in pos if m.start() > cue.start() and _words_between(low, cue.end(), m.start()) <= 5 and _same_clause(low, cue.end(), m.start())]
        if near:
            return "%s ... %s" % (cue.group(0), near[0].group(0))
    for cue in live(TIME_CUE):
        near = [m for m in pos if _same_clause(low, cue.start(), m.start())]
        if near:
            return "%s ... %s" % (cue.group(0), near[0].group(0))
    for m in CLAIM_RESULT.finditer(low):
        near = [p for p in pos if p.start() >= m.end() - 1 and _words_between(low, m.end(), p.start()) <= 3]
        if near and not negated(low, m.start()):
            return "%s ... %s" % (m.group(0), near[0].group(0))
    return None


# ---------------------------------------------------------------- outcomes, statistics, citations, quotes

_OUTCOME_VERB = r"(?:boost|improv|increas|grow|grew|lift|rais|rose|rise|jump|soar|skyrocket|doubl|tripl|multipl|driv|gain|climb|win|earn|secur)\w*"
_OUTCOME_NOUN = (
    r"(?:rankings?|serp|search visibility|ai visibility|visibility|click[- ]through(?: rates?)?|ctr"
    r"|(?:(?:organic|search|web(?:site)?|site) )?traffic|organic (?:visits|clicks|search))"
)
OUTCOME_PATTERNS = [
    re.compile(r"\b" + _OUTCOME_VERB + r"\b[^.]{0,40}?\b" + _OUTCOME_NOUN + r"\b"),
    re.compile(r"\b" + _OUTCOME_NOUN + r"\b[^.]{0,30}?\b" + _OUTCOME_VERB + r"\b"),
    re.compile(r"\brank(?:s|ed|ing)?\s+(?:higher|better)\b"),
    re.compile(r"\bhigher\s+(?:search\s+)?rank"),
]

_NUM = r"\d[\d,]*(?:\.\d+)?"
_WORD_NUMS = {"two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7",
              "eight": "8", "nine": "9", "ten": "10", "twelve": "12", "twenty": "20",
              "twice": "2", "thrice": "3"}
STAT_NUMERIC = [
    re.compile(r"(?<![\w.])(" + _NUM + r")\s?(?:%|percent\b|per cent\b)"),
    re.compile(r"(?<![\w.])(" + _NUM + r")\s?[x×](?!\w)"),
    re.compile(r"(?<![\w.])(" + _NUM + r")(?:\s+times\b|-fold\b)"),
]
_WORD_STAT = re.compile(r"\b(?:(?:two|three|four|five|six|seven|eight|nine|ten|twelve|twenty)(?:\s+times\b|-?fold\b)|twice\b|thrice\b)")

MARKER = re.compile(r"\[\^([^\]\s]+)\]")
LINK = re.compile(r"(?<!!)\[([^\]]*)\]\((https?://[^)\s]+)\)")
BARE_URL = re.compile(r"https?://\S+")
QUOTE = re.compile(r'"([^"]+)"|(?<![\w\'])\'(.+?)\'(?![\w\'])')
ATTRIBUTED = re.compile(r"\b(?:says?|said|states?|stated|writes?|wrote|according to|calls?|called|advises?|advised|recommends?|recommended"
                        r"|warns?|warned|notes?|noted|claims?|claimed|told|tells|explains?|explained|puts it|in (?:its|their|his|her) words|guidance)\b|:\s*$")


def quotes_in(plain):
    return [(m.start(), m.end(), (m.group(1) or m.group(2) or "").strip()) for m in QUOTE.finditer(plain)]


def stat_numbers(sentence):
    """Return [(shown, [candidates])] for each percentage or multiplier in a lowercased sentence."""
    found = []
    for pat in STAT_NUMERIC:
        for m in pat.finditer(sentence):
            found.append((m.group(0).strip(), [m.group(1)]))
    for m in _WORD_STAT.finditer(sentence):
        word = re.match(r"[a-z]+", m.group(0)).group(0)
        found.append((m.group(0), [word, _WORD_NUMS[word]]))
    return found


STOP = set("that this with from they their there have been were what when where which while about after before into over than then them these those your yours ours shows show said says also only just very more most some such each every other".split())


def stems(text):
    return {w[:5] for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in STOP}


def in_context(sentence, excerpt):
    """At least half of the sentence's content words also appear in the excerpt that holds its number."""
    want = stems(sentence)
    return not want or len(want & stems(excerpt)) * 2 >= len(want)


def _strip_commas(text):
    return re.sub(r"(?<=\d),(?=\d)", "", text)


def number_in(candidates, excerpts_lower):
    for cand in candidates:
        c = _strip_commas(cand)
        pat = re.compile(r"(?<![\d.])" + re.escape(c) + r"(?![\d]|\.\d)") if c[0].isdigit() \
            else re.compile(r"\b" + re.escape(c) + r"\b")
        if any(pat.search(_strip_commas(e)) for e in excerpts_lower):
            return True
    return False


def _finding(rule, line, sentence, message):
    return {"rule": rule, "blocking": True, "line": line,
            "excerpt": norm(sentence)[:120], "message": message}


def quote_findings(quotes, excerpts, line, raw, cited):
    """Each quote must be two or more whole words found verbatim in a cited excerpt; an attributed quote needs a citation.
    Returns (findings, spans of verified quotes, which are the source's words and skip the guarantee rule)."""
    out, verified = [], []
    for a, b, q in quotes:
        needle = norm(q).rstrip(".,;:!?…").strip()
        if not needle:
            continue
        if not cited:
            continue
        if len(re.findall(r"\w+", needle)) < 2:
            out.append(_finding("quote-too-short", line, raw,
                                'Quoted text "%s" is one word, too short to tie to a source. Quote two or more words of the excerpt or drop the quote marks.' % needle[:60]))
        elif not any(re.search(r"(?<!\w)" + re.escape(needle) + r"(?!\w)", e) for e in excerpts):
            out.append(_finding("quote-not-in-source", line, raw,
                                'Quoted text "%s" does not appear, as whole words, in any excerpt of the cited sources. Quote the excerpt exactly or drop the quote marks.' % needle[:60]))
        else:
            verified.append((a, b))
    return out, verified


def check_sentence(raw, line, by_id, by_url, extra_ids=(), kind="para"):
    """Return (findings, citation_count) for one sentence. extra_ids cite it from outside (a footnote's own id,
    a blockquote's attribution line). kind 'quote' means the whole sentence is quoted from the cited source."""
    findings = []
    ids = MARKER.findall(raw) + list(extra_ids)
    urls = [m.group(2) for m in LINK.finditer(raw)]
    cited = []
    for sid in dict.fromkeys(ids):
        if sid in by_id:
            cited.append(by_id[sid])
        else:
            findings.append(_finding("citation-unknown-source", line, raw,
                "Footnote [^%s] is not in the sources register. Register the source with a verbatim excerpt or remove the claim." % sid))
    for url in dict.fromkeys(urls):
        if url in by_url:
            cited.append(by_url[url])
        else:
            findings.append(_finding("citation-unknown-source", line, raw,
                "Link %s is not a registered source url. Register it with a verbatim excerpt or remove the claim." % url))

    plain = norm(_EMPHASIS.sub("", BARE_URL.sub("", MARKER.sub("", LINK.sub(r"\1", _LINE_HYPHEN.sub("", raw))))))
    excerpts = [norm(clean(e)) for s in cited for e in s["excerpts"]]
    excerpts_lower = [e.lower() for e in excerpts]
    quotes = [(0, len(plain), plain)] if kind == "quote" else quotes_in(plain)
    qf, verified = quote_findings(quotes, excerpts, line, raw, cited)
    findings += qf
    if not cited and quotes and (kind == "quote" or ATTRIBUTED.search(plain[:quotes[0][0]])):
        findings.append(_finding("quote-without-citation", line, raw,
            'Quotes "%s" from someone with no registered citation. Cite the source whose excerpt holds these exact words, or paraphrase without quote marks.' % norm(quotes[0][2])[:60]))

    spoken = plain
    for a, b in reversed(verified):
        spoken = spoken[:a] + " " + spoken[b:]
    low = spoken.lower()
    hit = guarantee_hit(low)
    if hit:
        findings.append(_finding("ranking-guarantee", line, raw,
            "Promises a search rank, position or AI-answer inclusion (matched '%s'). No one controls a search engine's ranking, so a citation does not fix this. Rewrite as what the work does, with no promised result." % hit))

    stats = stat_numbers(low)
    if not cited:
        for pat in OUTCOME_PATTERNS:
            hit = next((m for m in pat.finditer(low) if not negated(low, m.start())), None)
            if hit:
                findings.append(_finding("unsupported-ranking-claim", line, raw,
                    "Outcome claim about rankings, traffic, visibility or click-through (matched '%s') with no registered citation. Cite a registered source or cut the claim." % hit.group(0)))
                break
        if stats:
            findings.append(_finding("statistic-without-citation", line, raw,
                "Statistic '%s' has no registered citation. Cite a registered source that holds the number or cut it." % stats[0][0]))
    else:
        for shown, cands in stats:
            holders = [e for e in excerpts_lower if number_in(cands, [e])]
            if not holders:
                findings.append(_finding("number-not-in-source", line, raw,
                    "Statistic '%s' does not appear in any excerpt of the cited sources. Fix the number or cite a source that holds it." % shown))
            elif not any(in_context(norm(BARE_URL.sub("", MARKER.sub("", LINK.sub("", raw)))), e) for e in holders):
                findings.append(_finding("number-out-of-context", line, raw,
                    "Statistic '%s' appears in the cited source, but for a different fact: the excerpt holding it shares under half of this sentence's content words. Cite the excerpt that states this fact." % shown))
        for pat in OUTCOME_PATTERNS:
            claim = next((m for m in pat.finditer(low) if not negated(low, m.start())), None)
            if claim:
                verb = re.search(_OUTCOME_VERB, claim.group(0))
                noun = re.search(_OUTCOME_NOUN, claim.group(0))
                vs = verb.group(0)[:4] if verb else ""
                ns = noun.group(0).split()[-1][:5] if noun else ""
                if not any(vs in e and ns in e for e in excerpts_lower):
                    findings.append(_finding("unsupported-ranking-claim", line, raw,
                        "Outcome claim '%s' is cited, but no cited excerpt states that outcome. Cite the excerpt that does or cut the claim." % claim.group(0)))
                break
    return findings, len(ids) + len(urls)


def check_draft(text, sources):
    """Pure core: draft text and a validated source list in, (findings, checked) out. Raises InputError on an unclosed fence."""
    by_id = {s["id"]: s for s in sources}
    by_url = {s["url"]: s for s in sources}
    findings, n_sent, n_cite = [], 0, 0
    for first_line, block, kind, cite in split_blocks(clean(render_html(text))):
        pieces = [(0, block)] if kind == "quote" else split_sentences(block)
        for offset, sentence in pieces:
            n_sent += 1
            line = first_line + block[:offset].count("\n")
            f, c = check_sentence(sentence, line, by_id, by_url, cite, kind)
            findings.extend(f)
            n_cite += c
    findings.sort(key=lambda f: (f["line"], f["rule"]))
    return findings, {"sentences": n_sent, "citations": n_cite}


# ---------------------------------------------------------------- CLI

def _read(path, what):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise InputError("cannot read %s %s: %s" % (what, path, exc))


def fleet_tools():
    """company-fleets' owner log and factory-rig's hash, or None when they are not beside this skill."""
    if not os.path.isdir(os.path.join(FLEET_SCRIPTS, "fleetlib")):
        return None
    sys.path.insert(0, FLEET_SCRIPTS)
    try:
        from fleetlib import ownerlog
        from fleetlib.registry import Registry
        from factory_rig.canon import sha
    except ImportError:
        return None
    return {"ownerlog": ownerlog, "registry": Registry(), "sha": sha}


def run(draft_path, sources_path, fr):
    text = _read(draft_path, "draft")
    try:
        data = json.loads(_read(sources_path, "sources"))
    except json.JSONDecodeError as exc:
        raise InputError("sources file is not valid JSON: %s" % exc)
    sources = validate_register(data)
    findings, checked = check_draft(text, sources)
    sign, signed = sign_off_findings(data, fr)
    findings = sign + findings
    ok = not any(f["blocking"] for f in findings)
    return {"ok": ok, "findings": findings, "checked": checked, "sign_off": signed, "limits": LIMITS}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check a draft for unsupported claims and bad citations.")
    parser.add_argument("--draft", required=True)
    parser.add_argument("--sources", required=True, help="the source register; its instance and tenant_id name the owner ledger that holds its sign-off")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code not in (0, None):
            print(json.dumps({"error": "usage: --draft DRAFT.md --sources SOURCES.json"}, indent=2, sort_keys=True))
            return 2
        raise
    fr = fleet_tools()
    if fr is None:
        print(json.dumps({"ok": False, "status": "blocked", "reason": "company-fleets and factory-rig must sit beside this skill (looked in %s)" % FLEET_SCRIPTS}, indent=2, sort_keys=True))
        return 3
    try:
        result = run(args.draft, args.sources, fr)
    except InputError as exc:
        print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
