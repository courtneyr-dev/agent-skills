#!/usr/bin/env python3
"""Regression cases for link_claim_violations() in deepread_check.py.

The case that matters most is REGRESSION-1. A first implementation of this check
treated "contains no links" and "no outbound source links" as the same assertion,
so it failed a document that was telling the truth: no outbound *source* links,
but plenty of internal ones. A comment warning against that conflation did not
prevent it; this test did. Keep it.

Run: python3 test_link_claims.py
"""
import os
import sys

os.environ.setdefault("READWISE_TOKEN", "test-token-not-used")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deepread_check import (  # noqa: E402
    _host,
    _is_readwise_asset,
    _links_in,
    link_claim_violations,
)

SELF = "example.com"

INTERNAL_ONLY = """
<p>See <a href="/about">about</a> and <a href="https://example.com/archive">the archive</a>,
plus <a href="#footnote-1">a footnote</a> and <a href="mailto:x@example.com">mail</a>.</p>
"""

HAS_EXTERNAL = """
<p>Per <a href="https://www.mdpi.com/2075-4698/15/1/6">the survey</a> and
<a href="/about">our about page</a>.</p>
"""

READWISE_ONLY = """
<p>Figure: <a href="https://readwise-assets.s3.amazonaws.com/img/9.png">chart</a>
and <a href="https://readwise.io/read/01h">the reader copy</a>.</p>
"""

NO_LINKS = "<p>Plain prose with no anchors at all.</p>"

FAILURES = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    if not condition:
        FAILURES.append(f"{name}: {detail}")
    print(f"  [{status}] {name}" + (f" — {detail}" if not condition else ""))


def doc(notes, html, source_url=f"https://{SELF}/a"):
    return {"id": "x1", "notes": notes, "html_content": html, "source_url": source_url}


print("\n_host() — literal prefix, not lstrip charset")
check("strips a real www. prefix", _host("https://www.example.com/x") == "example.com",
      _host("https://www.example.com/x"))
# .lstrip("www.") would return "3.org" here — the bug this replaces.
check("leaves wordpress.org intact (lstrip would give 'ordpress.org')",
      _host("https://wordpress.org/plugins/") == "wordpress.org", repr(_host("https://wordpress.org/plugins/")))
check("strips www. from www.wordpress.org", _host("https://www.wordpress.org/") == "wordpress.org",
      repr(_host("https://www.wordpress.org/")))
check("leaves w3.org intact", _host("https://w3.org/TR/") == "w3.org",
      _host("https://w3.org/TR/"))
check("leaves ww2.example.com intact", _host("https://ww2.example.com/") == "ww2.example.com",
      _host("https://ww2.example.com/"))
check("handles a malformed url", _host("http://[bad") == "", repr(_host("http://[bad")))

print("\n_is_readwise_asset()")
check("s3 asset host", _is_readwise_asset("readwise-assets.s3.amazonaws.com"))
check("readwise.io", _is_readwise_asset("readwise.io"))
check("unrelated host is not an asset", not _is_readwise_asset("mdpi.com"))
check("unrelated amazonaws is not an asset", not _is_readwise_asset("foo.s3.amazonaws.com"))

print("\n_links_in() — classification")
every, external = _links_in(INTERNAL_ONLY, SELF)
check("counts navigable internal links", len(every) == 2, f"every={every}")
check("anchors and mailto are not navigation", all("mailto:" not in h and not h.startswith("#")
                                                   for h in every), f"every={every}")
check("no external in an internal-only doc", external == [], f"external={external}")

every, external = _links_in(HAS_EXTERNAL, SELF)
check("finds the external citation", len(external) == 1, f"external={external}")

every, external = _links_in(READWISE_ONLY, SELF)
check("readwise plumbing is not external", external == [], f"external={external}")
check("readwise links still count as links", len(every) == 2, f"every={every}")

print("\nTRUE POSITIVES — the claim is false, flag it")
v = link_claim_violations(doc("The article contains no links.", HAS_EXTERNAL))
check("'contains no links' vs a linked doc", len(v) == 1 and "contains no links" in v[0], v)

v = link_claim_violations(doc("There are no outbound source links.", HAS_EXTERNAL))
check("'no outbound source links' vs external", len(v) == 1 and "outbound" in v[0], v)

v = link_claim_violations(doc("The piece contains no links.", INTERNAL_ONLY))
check("'contains no links' vs internal-only", len(v) == 1, v)

v = link_claim_violations(doc("No external links appear anywhere.", HAS_EXTERNAL))
check("'no external links' vs external", len(v) == 1, v)

print("\nREGRESSION-1 — the case the first implementation got wrong")
v = link_claim_violations(doc(
    "The author cites nothing: there are no outbound source links, though the post "
    "does link around its own site.", INTERNAL_ONLY))
check("truthful 'no outbound links' + internal links is NOT flagged", v == [],
      f"false positive: {v}")

print("\nREGRESSION-1b — the measured false positive: 9 links, 0 external")
NINE_INTERNAL = "<p>" + "".join(f'<a href="https://example.com/p{i}">p{i}</a> ' for i in range(9)) + "</p>"
v = link_claim_violations(doc("The capture has no outbound links to sources.", NINE_INTERNAL))
check("9 internal links + 'no outbound links' is NOT flagged", v == [], f"false positive: {v}")
v = link_claim_violations(doc("The capture contains no links.", NINE_INTERNAL))
check("9 internal links + 'contains no links' IS flagged", len(v) == 1, f"missed: {v}")

print("\nREGRESSION-2 — Readwise-hosted assets are not outbound citations")
v = link_claim_violations(doc("There are no outbound source links.", READWISE_ONLY))
check("readwise assets do not disprove an outbound claim", v == [], f"false positive: {v}")

print("\nTRUE NEGATIVES — no claim, or claim is true")
check("no claim at all", link_claim_violations(doc("A normal analysis.", HAS_EXTERNAL)) == [])
check("true 'contains no links'", link_claim_violations(doc("It contains no links.", NO_LINKS)) == [])
check("true 'no outbound links'", link_claim_violations(
    doc("There are no outbound links.", NO_LINKS)) == [])

print("\nUNCHECKED IS NOT A FINDING")
d = {"id": "x", "notes": "The article contains no links.", "source_url": "https://example.com/a"}
check("no markup available -> no violation", link_claim_violations(d) == [])
check("fetcher raising -> no violation", link_claim_violations(
    d, fetch_html=lambda _: (_ for _ in ()).throw(RuntimeError("429"))) == [])
check("fetcher supplies markup -> violation found", len(link_claim_violations(
    d, fetch_html=lambda _: HAS_EXTERNAL)) == 1)

print("\nSUBDOMAIN HANDLING")
v = link_claim_violations({
    "id": "x", "notes": "There are no outbound source links.",
    "source_url": "https://example.com/a",
    "html_content": '<p><a href="https://blog.example.com/p">our blog</a></p>'})
check("a subdomain of the source is internal", v == [], f"false positive: {v}")

print("\nQUOTED MENTION IS NOT AN ASSERTION")
# REGRESSION-2: a note that corrects an earlier mistake quotes the phrase it is
# disowning. Matching that quote failed a document that had already fixed itself.
v = link_claim_violations({
    "id": "x",
    "notes": ('An earlier processing pass on this document recorded "no outbound links". '
              'That was wrong -- the capture carries a direct link to the primary reporting.'),
    "source_url": "https://example.com/a",
    "html_content": '<p><a href="https://techcrunch.com/x">the reporting</a></p>'})
check("quoted mention of the phrase is not a claim", v == [], f"false positive: {v}")

# ...but an unquoted assertion in the same document must still fail.
v = link_claim_violations({
    "id": "x",
    "notes": ('An earlier pass recorded "no outbound links". '
              'This capture has no outbound source links.'),
    "source_url": "https://example.com/a",
    "html_content": '<p><a href="https://techcrunch.com/x">the reporting</a></p>'})
check("unquoted assertion still caught alongside a quote", v != [], "missed a real false claim")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED:")
    for f in FAILURES:
        print("  -", f)
    sys.exit(1)
print("all link-claim regression cases pass")
