import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
FIXTURES = os.path.join(os.path.dirname(SCRIPTS), "fixtures")
SCRIPT = os.path.join(SCRIPTS, "claims_check.py")
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.normpath(os.path.join(SCRIPTS, "..", "..", "company-fleets", "scripts")))

import claims_check  # noqa: E402
from fleetlib import ownerlog  # noqa: E402
from fleetlib.registry import Registry  # noqa: E402


def fixture(name):
    return os.path.join(FIXTURES, name)


def run_cli(draft, sources="sources.json"):
    """The installed command, reading the checked-in fixture ledger (company-fleets fleets/corporate/owner)."""
    proc = subprocess.run(
        [sys.executable, SCRIPT, "--draft", draft, "--sources", fixture(sources) if not os.path.isabs(sources) else sources],
        capture_output=True, text=True,
    )
    return proc.returncode, json.loads(proc.stdout)


def run_here(draft, sources):
    """main() in this process, so a test's temp owner root applies."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = claims_check.main(["--draft", draft, "--sources", sources])
    return code, json.loads(out.getvalue())


def rules(result):
    return sorted(f["rule"] for f in result["findings"])


class FixtureRuns(unittest.TestCase):
    def test_clean_draft_passes(self):
        code, out = run_cli(fixture("draft-pass.md"))
        self.assertEqual(code, 0)
        self.assertTrue(out["ok"])
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["checked"], {"sentences": 9, "citations": 6})
        self.assertEqual(out["sign_off"]["signed_off_by"], "human:claims-reviewer")

    def test_negated_guarantee_is_not_flagged(self):
        _, out = run_cli(fixture("draft-pass.md"))
        self.assertNotIn("ranking-guarantee", rules(out))

    def test_ranking_guarantee_blocks_even_when_cited(self):
        code, out = run_cli(fixture("draft-ranking-guarantee.md"))
        self.assertEqual(code, 1)
        self.assertEqual(rules(out), ["ranking-guarantee"] * 4)
        cited = [f for f in out["findings"] if "ChatGPT" in f["excerpt"]]
        self.assertEqual(len(cited), 1)
        self.assertTrue(cited[0]["blocking"])

    def test_fabricated_citation_defects_all_caught(self):
        code, out = run_cli(fixture("draft-fabricated-citation.md"))
        self.assertEqual(code, 1)
        self.assertEqual(rules(out), ["citation-unknown-source", "citation-unknown-source",
                                      "number-not-in-source", "quote-not-in-source"])
        by_rule = {f["rule"]: f for f in out["findings"]}
        self.assertEqual(by_rule["quote-not-in-source"]["line"], 4)
        self.assertEqual(by_rule["number-not-in-source"]["line"], 6)

    def test_instruction_line_in_draft_changes_nothing(self):
        _, out = run_cli(fixture("draft-fabricated-citation.md"))
        self.assertFalse(out["ok"])
        self.assertTrue(all("Reviewer" not in f["excerpt"] for f in out["findings"]))

    def test_uncited_statistic_draft(self):
        code, out = run_cli(fixture("draft-uncited-statistic.md"))
        self.assertEqual(code, 1)
        self.assertEqual(rules(out), ["statistic-without-citation", "statistic-without-citation",
                                      "unsupported-ranking-claim"])

    def test_limits_name_the_required_gaps(self):
        _, out = run_cli(fixture("draft-pass.md"))
        text = " ".join(out["limits"]).lower()
        self.assertIn("human verifies the register", text)
        self.assertIn("tone or brand fit", text)
        self.assertIn("patterns are english", text)
        self.assertIn("same-user process", text)

    def test_output_is_stable_json(self):
        a = subprocess.run([sys.executable, SCRIPT, "--draft", fixture("draft-pass.md"), "--sources", fixture("sources.json")],
                           capture_output=True, text=True).stdout
        self.assertEqual(a, json.dumps(json.loads(a), indent=2, sort_keys=True) + "\n")


class InvalidInput(unittest.TestCase):
    def test_source_missing_url_exits_2(self):
        code, out = run_cli(fixture("draft-pass.md"), "sources-invalid.json")
        self.assertEqual(code, 2)
        self.assertIn("url", out["error"])

    def test_missing_draft_exits_2(self):
        code, out = run_cli(os.path.join(FIXTURES, "nope.md"))
        self.assertEqual(code, 2)
        self.assertIn("error", out)

    def test_bad_json_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "s.json")
            with open(bad, "w") as fh:
                fh.write("{not json")
            code, out = run_cli(fixture("draft-pass.md"), bad)
        self.assertEqual(code, 2)
        self.assertIn("JSON", out["error"])

    def test_unclosed_fence_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft = os.path.join(tmp, "d.md")
            with open(draft, "w") as fh:
                fh.write("```\nWe guarantee a #1 ranking on Google.\nOur clients saw 310% more traffic.\n")
            code, out = run_cli(draft)
        self.assertEqual(code, 2)
        self.assertIn("never closes", out["error"])

    def test_register_rules(self):
        good = {"id": "S1", "title": "t", "url": "https://example.com/a", "retrieved": "2026-11-25", "excerpts": ["x"]}
        cases = {
            "empty excerpt": dict(good, excerpts=[" "]),
            "non-http url": dict(good, url="ftp://example.com/a"),
            "bad date": dict(good, retrieved="25/11/2026"),
            "missing title": {k: v for k, v in good.items() if k != "title"},
        }
        for name, src in cases.items():
            with self.subTest(name):
                with self.assertRaises(claims_check.InputError):
                    claims_check.validate_register({"sources": [src]})
        with self.assertRaises(claims_check.InputError):
            claims_check.validate_register({"sources": [good, dict(good)]})
        self.assertEqual(claims_check.validate_register({"sources": [good]}), [good])

    def test_no_args_exits_2(self):
        proc = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("error", json.loads(proc.stdout))


SRC = [
    {"id": "S1", "title": "t1", "url": "https://example.com/one", "retrieved": "2026-11-25",
     "excerpts": ["No one can guarantee a #1 ranking on Google.", "Results vary by site.",
                  "If they guarantee you that their changes will give you first place in search results, find someone else."]},
    {"id": "S2", "title": "t2", "url": "https://example.com/two", "retrieved": "2026-11-25",
     "excerpts": ["Of 1,200 users, 42.5% renewed and renewals came 3 times faster."]},
]


def check(text):
    findings, checked = claims_check.check_draft(text, SRC)
    return sorted(f["rule"] for f in findings), checked


class RulesInDetail(unittest.TestCase):
    def test_guarantee_variants_are_flagged(self):
        for s in [
            "We guarantee rankings.",
            "Guaranteed rankings for every client.",
            "You will rank first for your keywords.",
            "Be #1 on Google by spring.",
            "We deliver the first page of Google.",
            "Land at the top of Google fast.",
            "We offer guaranteed visibility.",
            "Perplexity will cite your site every time.",
            "Copilot will recommend you.",
            "AI Overviews will feature your brand.",
            "We guarantee inclusion in AI Overviews.",
        ]:
            with self.subTest(s):
                self.assertIn("ranking-guarantee", check(s)[0])

    def test_negated_or_reported_guarantees_pass(self):
        for s in [
            "No one can guarantee a #1 ranking on Google.",
            "Nobody can guarantee top of Google placement.",
            "We can't guarantee rankings, and we won't pretend to.",
            "Beware of vendors that claim to guarantee rankings.",
            "ChatGPT will not recommend every site.",
            "Treat any scam that promises a #1 ranking on Google with suspicion.",
        ]:
            with self.subTest(s):
                self.assertNotIn("ranking-guarantee", check(s)[0])

    def test_cue_after_the_phrase_is_not_credited(self):
        # a limit, not a goal: the window reads only the clause before the match, so this errs toward blocking
        self.assertIn("ranking-guarantee", check("A guaranteed #1 on Google promise is a red flag.")[0])

    def test_negation_in_an_earlier_clause_does_not_excuse_a_promise(self):
        self.assertIn("ranking-guarantee", check("We never miss a deadline, and we guarantee rankings.")[0])
        self.assertIn("ranking-guarantee", check("Not only do we guarantee rankings, we report weekly.")[0])

    def test_unsupported_ranking_claim_needs_a_valid_citation(self):
        self.assertIn("unsupported-ranking-claim", check("Our service will boost your rankings.")[0])
        self.assertIn("unsupported-ranking-claim", check("Double your organic traffic.")[0])
        self.assertIn("unsupported-ranking-claim", check("Cut this and improve click-through rate.")[0])
        self.assertEqual(check("Our service can boost your rankings.[^S1]")[0], ["unsupported-ranking-claim"])
        self.assertEqual(check("Our service can boost your rankings.[^S9]")[0], ["citation-unknown-source", "unsupported-ranking-claim"])

    def test_neutral_ranking_talk_passes(self):
        self.assertEqual(check("Rankings change as search engines update.")[0], [])
        self.assertEqual(check("We track rankings weekly.")[0], [])

    def test_statistic_forms(self):
        for s in ["Sales rose 40%.", "Sales rose 12 percent.", "That is 3x better.", "Opens grew three times.",
                  "Twice as many people replied.", "It was 2.5-fold higher."]:
            with self.subTest(s):
                self.assertEqual(check(s)[0], ["statistic-without-citation"])

    def test_non_statistics_pass(self):
        for s in ["The grid is 3x3.", "We shipped in 2026.", "Version 3.5 is out.", "Call us at 555 0100."]:
            with self.subTest(s):
                self.assertEqual(check(s)[0], [])

    def test_number_must_appear_in_cited_excerpt(self):
        self.assertEqual(check("Renewals reached 42.5%.[^S2]")[0], [])
        self.assertEqual(check("Renewals reached 42%.[^S2]")[0], ["number-not-in-source"])
        self.assertEqual(check("Renewals came three times faster.[^S2]")[0], [])
        self.assertEqual(check("Renewals came 5 times faster.[^S2]")[0], ["number-not-in-source"])
        self.assertEqual(check("Of 1,200 users, 42.5% renewed.[^S2]")[0], [])

    def test_number_checks_only_cited_sources(self):
        self.assertEqual(check("Renewals reached 42.5%.[^S1]")[0], ["number-not-in-source"])

    def test_quote_matching_normalizes_curly_quotes_and_whitespace(self):
        self.assertEqual(check("Google says “No one can   guarantee a #1 ranking on Google.”[^S1]")[0], [])
        self.assertEqual(check('Google says "No one can guarantee a #1 ranking on Google".[^S1]')[0], [])
        self.assertEqual(check('Google says "Anyone can promise great results".[^S1]')[0], ["quote-not-in-source"])

    def test_uncited_quote_needs_a_citation_when_attributed(self):
        self.assertEqual(check('The report calls it "a fresh start".')[0], ["quote-without-citation"])
        self.assertEqual(check('The button reads "Give monthly" in every locale.')[0], [])

    def test_quote_can_hold_a_sentence_break(self):
        two = [{"id": "S4", "title": "t4", "url": "https://example.com/four", "retrieved": "2026-11-25",
                "excerpts": ["Results vary by site. Rankings move every week."]}]
        findings, checked = claims_check.check_draft('He said "Results vary by site. Rankings move every week."[^S4] Then he left.', two)
        self.assertEqual((findings, checked["sentences"]), ([], 2))

    def test_inline_link_citations(self):
        self.assertEqual(check("Renewals reached 42.5% ([data](https://example.com/two)).")[0], [])
        self.assertEqual(check("Renewals reached 42.5% ([data](https://example.com/two/)).")[0],
                         ["citation-unknown-source", "statistic-without-citation"])

    def test_marker_after_period_binds_to_its_sentence(self):
        rules_, checked = check("Renewals reached 42.5%.[^S2] Sales rose 40%.")
        self.assertEqual(rules_, ["statistic-without-citation"])
        self.assertEqual(checked, {"sentences": 2, "citations": 1})

    def test_findings_carry_line_numbers_across_wrapped_paragraphs(self):
        findings, _ = claims_check.check_draft("Intro line\nstill the intro.\n\nWe guarantee\nrankings now.\n", SRC)
        self.assertEqual([f["line"] for f in findings], [4])

    def test_footnote_definitions_and_code_fences_are_checked(self):
        findings, _ = claims_check.check_draft("[^S1]: We guarantee rankings (a definition line).\n\n```\nWe guarantee rankings\n```\n", SRC)
        self.assertEqual([(f["rule"], f["line"]) for f in findings], [("ranking-guarantee", 1), ("ranking-guarantee", 4)])


REVIEW_GUARANTEES = [  # the 25 phrasings from evidence/reviews/corporate-agency.md (probes g0-g24)
    "We guarantee a #1 ranking on Google.", "#1 ranking guaranteed.", "Your site gets a #1 ranking, guaranteed.",
    "First page in 30 days.", "You will be on the first page of Google in 30 days.", "You'll hit page one within 30 days.",
    "Your site will rank.", "Your pages will rank on Google within a month.", "We promise first-page results in 30 days.",
    "Inclusion in AI answers is guaranteed.", "AI answer inclusion guaranteed.", "ChatGPT will cite your brand.",
    "Get cited in ChatGPT and Perplexity answers, every time.", "Your brand will show up in AI Overviews.",
    "Our clients always land in the top three results.", "Top 3 placement assured.",
    "We get you ranked first, or your money back.", "Rank #1 or you don't pay.", "Guaranteed rankings.",
    "100% guaranteed top Google rankings.", "Number one on Google, certified.",
    "Your site will appear in Google's AI Overviews.", "Be the answer ChatGPT gives, guaranteed.",
    "Dominate page 1 of Google within 30 days.", "We will put you at the top of Google.",
]

# evidence/reviews/corporate-agency-rereview.md finding 10: cautionary and reporting sentences, plus verbatim S1 quotes
REREVIEW_BENIGN = [
    "Google guarantees nothing about rankings.", "Anyone who promises a #1 ranking is guessing.",
    "Agencies that promise top rankings should worry you.", "Our Google-certified team audits your site's visibility.",
    "We hit our deadline and listed your top 10 keywords.", "The report lists the pages that reach the top 3 results.",
    "Within 30 days we audit every page and show which pages sit in the top 10.", "The theme's warranty covers bugs, not rankings.",
    "We'll track where you rank each week.", "We will report on your rankings every month.", "We always measure traffic before and after a change.",
    'Google advises: "If they guarantee you that their changes will give you first place in search results, find someone else."[^S1]',
    'Google\'s guidance asks you to find "someone else"[^S1] if an SEO guarantees results.',
    'Google calls a ranking promise a reason to find "someone else"[^S1].',
]

# re-review findings 7 and minor 15: look-alike and invisible characters, and paraphrased promises
REREVIEW_DISGUISED = [
    "We guaran​teed a #1 ranking on Google.", "Guaran­teed #1 ranking on Google.", "Guaran&shy;teed #1 ranking on Google.",
    "Guаranteed #1 ranking on Google.", "Ｇｕａｒａｎｔｅｅｄ #1 ranking on Google.",
    "Guaranteed ＃1 on Google.", "Guaranteed №1 on Google.", "Guaran&#8203;teed #1 ranking on Google.",
    "You can count on a #1 ranking on Google.", "We make sure you rank #1 on Google.",
    "We ensure first-page rankings for every client.", "Your site ranks #1 on Google after our audit.",
]


# evidence/reviews/corporate-agency-rereview-2.md major 3: forms that passed in the second re-review
SECOND_REVIEW_GUARANTEES = [
    "A #1 ranking on Google is guaranteed by our team.", "Zero risk: you will outrank every competitor on Google.",
    "Fixture Co clients are always shown first in AI Overviews.", "Number one on Google, or we work for free.",
    "Guar**anteed** #1 ranking on Google.", "<b>Guar</b>anteed #1 ranking on Google.",
    "G\u0332u\u0332a\u0332r\u0332a\u0332n\u0332t\u0332e\u0332e\u0332d\u0332 #1 ranking on Google.", "We guaran-\nteed a #1 ranking on Google.",
    "Garantizamos el primer lugar en Google para su sitio.", "Nous garantissons la première place sur Google.",
    "Wir garantieren Platz 1 bei Google.", "Garantizado #1 en Google.",
]
SECOND_REVIEW_BENIGN = [
    "We can't promise a #1 ranking, and no honest agency can.", "No one can guarantee first-page placement on Google.",
    "Rankings depend on Google's algorithms, which we don't control.", "We track your position for 50 keywords and report changes monthly.",
    "Our warranty covers code defects for 90 days.", "Ask any vendor who guarantees rankings for their evidence.",
    "We promise a reply to every support ticket within one business day.", "Google ranked the page third last month; this month it ranks fifth.",
    "We guarantee our invoices are accurate to the cent.", "Number one priority: fix the broken checkout.",
    "Nous ne garantissons aucun classement sur Google.", "We ensure every page meets WCAG 2.2 AA before launch.",
    "No garantizamos el primer lugar en Google.", "Wir garantieren nicht Platz 1 bei Google.",
]
SECOND_REVIEW_QUOTES = [  # misquotes of S1, or attributed quotes with no citation
    "Google says \u2018great content wins in every search\u2019[^S1].", "Google says \u2039great content wins in every search\u203a[^S1].",
    "Google says \u300cgreat content wins in every search\u300d[^S1].", "Google says \u201agreat content wins in every search\u2018[^S1].",
    "Google says \u201dgreat content wins in every search\u201c[^S1].", "As Google puts it, \u2018links no longer matter for search\u2019.",
    "Google: \u00ablinks no longer matter for search\u00bb.", "> Write for search engines first, then people.[^S1]",
    "> Write for search engines first, then people.\n\nGoogle Search Central[^S1]", "> Write for search engines first, then people.\n\n\u2014 Google Search Central",
    "Google says <q>great content wins in every search</q>[^S1].", "<blockquote>Write for search engines first, then people.</blockquote>\n\n\u2014 Google[^S1]",
]


class ReviewProbes(unittest.TestCase):
    def test_second_review_guarantees_are_flagged(self):
        missed = [s for s in SECOND_REVIEW_GUARANTEES if "ranking-guarantee" not in check(s)[0]]
        self.assertEqual(missed, [])

    def test_second_review_benign_sentences_pass(self):
        blocked = {s: check(s)[0] for s in SECOND_REVIEW_BENIGN if check(s)[0]}
        self.assertEqual(blocked, {})

    def test_second_review_quote_forms_are_compared_with_the_source(self):
        missed = [s for s in SECOND_REVIEW_QUOTES if not {"quote-not-in-source", "quote-without-citation"} & set(check(s)[0])]
        self.assertEqual(missed, [])
        for s in ("> No one can guarantee a #1 ranking on Google.[^S1]", "Google says <q>No one can guarantee a #1 ranking on Google.</q>[^S1]",
                  "<blockquote>\nNo one can guarantee a #1 ranking on Google.\n</blockquote>\n\nGoogle Search Central[^S1]",
                  "Google says \u2018No one can guarantee a #1 ranking on Google.\u2019[^S1]"):
            with self.subTest(s):
                self.assertEqual(check(s)[0], [])

    def test_an_attribution_line_is_still_checked_as_the_authors_text(self):
        self.assertIn("ranking-guarantee", check("> No one can guarantee a #1 ranking on Google.\n\nGuaranteed #1 ranking[^S1]\n")[0])
        self.assertIn("ranking-guarantee", check("> No one can guarantee a #1 ranking on Google.\n\n\u2014 Guaranteed #1 on Google[^S1]\n")[0])

    def test_html_links_still_cite_and_lines_keep_their_numbers(self):
        self.assertEqual(check('Renewals reached 42.5% (<a href="https://example.com/two">data</a>).')[0], [])
        findings, _ = claims_check.check_draft("Intro.\n\n<blockquote>\nLinks no longer matter.\n</blockquote>\n\n<b>We</b> guarantee rankings.\n", SRC)
        self.assertEqual([(f["rule"], f["line"]) for f in findings], [("ranking-guarantee", 7)])

    def test_all_25_review_guarantee_phrasings_are_flagged(self):
        missed = [s for s in REVIEW_GUARANTEES if "ranking-guarantee" not in check(s)[0]]
        self.assertEqual(missed, [])

    def test_disguised_and_paraphrased_promises_are_flagged(self):
        missed = [s for s in REREVIEW_DISGUISED if "ranking-guarantee" not in check(s)[0]]
        self.assertEqual(missed, [])

    def test_cautionary_reporting_and_quoted_sentences_pass(self):
        blocked = {s: check(s)[0] for s in REREVIEW_BENIGN if check(s)[0]}
        self.assertEqual(blocked, {})

    def test_reporting_about_rankings_is_not_a_guarantee(self):
        for s in ["We will report on your rankings each month.", "Our team will review the AI Overviews you appear in.",
                  "We always explain how rankings work.", "Copilot can mention sites it finds useful."]:
            with self.subTest(s):
                self.assertNotIn("ranking-guarantee", check(s)[0])

    def test_short_or_partial_word_quotes_are_refused(self):
        self.assertEqual(check('Google says we are "ran"[^S1].')[0], ["quote-too-short"])
        self.assertEqual(check('Google says "guarantee"[^S1].')[0], ["quote-too-short"])
        self.assertEqual(check('Google says "one can guar" here[^S1].')[0], ["quote-not-in-source"])

    def test_text_a_reader_sees_is_checked(self):
        self.assertEqual(check("Our approach.\n\n```\nGuaranteed #1 ranking on Google.\n```\n")[0], ["ranking-guarantee"])
        self.assertEqual(check("Read the guidance[^S1].\n\n[^S1]: We guarantee first-page rankings in 30 days.\n")[0], ["ranking-guarantee"])
        self.assertEqual(check("Our approach.\n<!-- Guaranteed #1 ranking on Google. -->\n")[0], [])
        with self.assertRaises(claims_check.InputError):
            check("```\nWe guarantee a #1 ranking on Google.\nOur clients saw 310% more traffic.\n")

    def test_every_quote_form_is_compared_with_the_source(self):
        for s in ["Google says 'great content wins in every search'[^S1].", "Google says „expert writers beat everyone in search“[^S1].",
                  "Google says «expert writers beat everyone in search»[^S1].",
                  "> Write for search engines first, then people.\n\n— Google Search Central[^S1]\n"]:
            with self.subTest(s):
                self.assertIn("quote-not-in-source", check(s)[0])
        self.assertEqual(check('Google\'s guidance says "links no longer matter for search at all".')[0], ["quote-without-citation"])
        self.assertEqual(check("> No one can guarantee a #1 ranking on Google.\n\n— Google Search Central[^S1]\n")[0], [])
        self.assertEqual(check("> Links no longer matter.\n\n— Google\n")[0], ["quote-without-citation"])

    def test_number_from_a_different_fact_is_refused(self):
        found = check("Our survey shows 42.5% of readers doubled their traffic.[^S2]")[0]
        self.assertIn("number-out-of-context", found)
        self.assertIn("unsupported-ranking-claim", found)

    def test_cited_outcome_must_be_stated_by_the_source(self):
        self.assertEqual(check("Customers saw traffic triple in 4 weeks.[^S2]")[0], ["unsupported-ranking-claim"])
        supported = [{"id": "S3", "title": "t3", "url": "https://example.com/three", "retrieved": "2026-11-25",
                      "excerpts": ["Organic search traffic rose 18% after the page-speed work."]}]
        findings, _ = claims_check.check_draft("Organic search traffic rose 18% after the page-speed work.[^S3]", supported)
        self.assertEqual(findings, [])


class RegisterSignOff(unittest.TestCase):
    """The sign-off is an owner-log record for the exact sources hash, written under the lease holder's claim token,
    in the ledger of the instance the register names."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="claims-")
        self.addCleanup(shutil.rmtree, self.tmp)
        root = tempfile.mkdtemp(prefix="owner-root-")
        old, ownerlog.FLEETS_ROOT = ownerlog.FLEETS_ROOT, root
        self.addCleanup(shutil.rmtree, root, True)
        self.addCleanup(setattr, ownerlog, "FLEETS_ROOT", old)
        with open(fixture("sources.json")) as fh:
            self.register = dict(json.load(fh), instance="T1")
        self.ident = ("fixture-co", "corporate.workload.campaign-staging", "T1")
        self.ledger = ownerlog.owner_dir("corporate", "T1")
        self.lease = ownerlog.open_ledger(self.ledger, Registry(), *self.ident, "corporate.chief-of-staff", os.getpid(), "none", exclusive=True)

    def write_register(self, register):
        path = os.path.join(self.tmp, "sources.json")
        with open(path, "w") as fh:
            json.dump(register, fh)
        return path

    def sign(self, path, signer="human:claims-reviewer", author="human:content-author", token=None):
        rec = {"register": os.path.basename(path), "signed_off_by": signer, "author": author, "signed_on": "2026-11-26"}
        return ownerlog.append(self.ledger, "claims-sign-off", rec, *self.ident, self.lease["epoch"],
                               self.lease["token"] if token is None else token, base=os.path.dirname(path))

    def with_s9(self):
        reg = json.loads(json.dumps(self.register))
        reg["sources"].append({"id": "S9", "title": "Totally real Gartner report", "url": "https://www.gartner.com/made-up",
                               "retrieved": "2026-11-26", "excerpts": ["Fixture Co clients saw 310% more organic traffic and #1 rankings."]})
        return reg

    def test_signed_fixture_register_passes(self):
        self.assertEqual(run_cli(fixture("draft-pass.md"))[0], 0)

    def test_unsigned_register_blocks(self):
        path = self.write_register(self.register)
        ownerlog.append(self.ledger, "pin", {"name": "unrelated", "path": "sources.json"}, *self.ident, self.lease["epoch"], self.lease["token"], base=self.tmp)
        code, out = run_here(fixture("draft-pass.md"), path)
        self.assertEqual((code, rules(out)), (1, ["register-not-signed-off"]))

    def test_source_added_after_sign_off_blocks(self):
        self.sign(self.write_register(self.register))
        self.assertEqual(run_here(fixture("draft-pass.md"), self.write_register(self.register))[0], 0)
        code, out = run_here(fixture("draft-pass.md"), self.write_register(self.with_s9()))
        self.assertEqual((code, rules(out)), (1, ["register-not-signed-off"]))

    def test_sign_off_field_inside_the_register_counts_for_nothing(self):
        reg = self.with_s9()
        reg["sign_off"] = {"signed_off_by": "human:claims-reviewer", "signed_on": "2026-11-26", "sources_sha256": claims_check_sha(reg["sources"])}
        draft = os.path.join(self.tmp, "d.md")
        with open(draft, "w") as fh:
            fh.write("Gartner found Fixture Co clients saw 310% more organic traffic[^S9].\n")
        code, out = run_here(draft, self.write_register(reg))
        self.assertEqual((code, rules(out)), (1, ["register-not-signed-off"]))

    def test_a_ledger_of_another_tenant_for_the_registers_instance_is_refused(self):
        """The reviewer's minted corporate ledger: a sign-off recorded under another tenant doesn't count."""
        path = self.write_register(dict(self.with_s9(), tenant_id="tenant-mine"))
        self.sign(path, signer="human:a", author="human:b")
        draft = os.path.join(self.tmp, "d.md")
        with open(draft, "w") as fh:
            fh.write("Gartner found Fixture Co clients saw 310% more organic traffic[^S9].\n")
        code, out = run_here(draft, path)
        self.assertEqual((code, rules(out)), (1, ["ledger-not-for-this-work"]))

    def test_a_register_naming_no_instance_has_no_sign_off(self):
        reg = dict(self.register)
        del reg["instance"]
        code, out = run_here(fixture("draft-pass.md"), self.write_register(reg))
        self.assertEqual((code, rules(out)), (1, ["register-not-signed-off"]))

    def test_no_flag_picks_the_ledger(self):
        proc = subprocess.run([sys.executable, SCRIPT, "--draft", fixture("draft-pass.md"), "--sources", fixture("sources.json"),
                               "--owner-ledger", self.ledger], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)

    def test_author_cannot_sign_off_their_own_register(self):
        with self.assertRaises(ownerlog.OwnerLogError) as cm:
            self.sign(self.write_register(self.register), signer="human:content-author​")
        self.assertEqual(cm.exception.reason, "register-self-signed")

    def test_agent_role_cannot_sign_off(self):
        with self.assertRaises(ownerlog.OwnerLogError) as cm:
            self.sign(self.write_register(self.register), signer="corporate.lifecycle-marketer")
        self.assertEqual(cm.exception.reason, "record-invalid")

    def test_the_draft_author_cannot_record_a_sign_off_without_the_claim_token(self):
        with self.assertRaises(ownerlog.OwnerLogError) as cm:
            self.sign(self.write_register(self.with_s9()), token="")
        self.assertEqual(cm.exception.reason, "not-the-lease-holder")

    def test_missing_owner_log_blocks(self):
        code, out = run_here(fixture("draft-pass.md"), self.write_register(dict(self.register, instance="NOWHERE-1")))
        self.assertEqual((code, rules(out)), (1, ["owner-log-missing"]))


def claims_check_sha(sources):
    from factory_rig.canon import sha
    return sha(sources)


if __name__ == "__main__":
    unittest.main()
