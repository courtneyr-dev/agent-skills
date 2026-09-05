#!/usr/bin/env python3
"""Tests for the pure parts of gather.py: note splice, rendering, backoff, parsers."""
import datetime as dt
import json
import pathlib
import sys
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gather  # noqa: E402

SECTION = "## Gathered\n<!-- gathered:start -->\n_summary_\n\n- [a](u)\n<!-- gathered:end -->\n"
NOW = dt.datetime(2026, 9, 4, 17, 0)


def empty(**overrides):
    base = {s: {"items": [], "error": None} for s in ("github", "trac", "things")}
    base.update(overrides)
    return base


class SpliceTests(unittest.TestCase):
    def test_inserts_before_daily_inboxes_when_missing(self):
        note = "# Day\n\n## A\n\ntext\n\n## 📥 Daily Inboxes\n\n- [ ] x\n"
        out = gather.splice_section(note, SECTION)
        self.assertLess(out.index("## Gathered"), out.index("## 📥 Daily Inboxes"))
        self.assertTrue(out.startswith("# Day\n\n## A\n\ntext\n\n"))
        self.assertTrue(out.endswith("## 📥 Daily Inboxes\n\n- [ ] x\n"))

    def test_replaces_existing_section_bounded_by_end_marker(self):
        old = "## Gathered\n<!-- gathered:start -->\n_old_\n- [old](u)\n<!-- gathered:end -->\n"
        note = "# Day\n\n" + old + "\nfooter line\n"
        out = gather.splice_section(note, SECTION)
        self.assertNotIn("[old]", out)
        self.assertIn("[a](u)", out)
        self.assertTrue(out.startswith("# Day\n\n"))
        self.assertTrue(out.endswith("\nfooter line\n"))
        self.assertEqual(out.count("## Gathered"), 1)

    def test_replaces_hand_edited_section_up_to_next_h2(self):
        note = "# Day\n\n## Gathered\n\n- hand\n\n## Next\n\nkeep\n"
        out = gather.splice_section(note, SECTION)
        self.assertNotIn("- hand", out)
        self.assertTrue(out.endswith("## Next\n\nkeep\n"))
        self.assertEqual(out.count("## Gathered"), 1)

    def test_appends_when_no_anchor(self):
        note = "# Day\n\n## Only\n\ntext\n"
        out = gather.splice_section(note, SECTION)
        self.assertTrue(out.startswith(note))
        self.assertTrue(out.endswith("<!-- gathered:end -->\n"))

    def test_rerun_is_idempotent(self):
        note = "# Day\n\n## 📥 Daily Inboxes\n\n- [ ] x\n"
        once = gather.splice_section(note, SECTION)
        twice = gather.splice_section(once, SECTION)
        self.assertEqual(once, twice)


class RenderTests(unittest.TestCase):
    def test_orders_newest_first_within_source(self):
        g = empty(github={"items": [
            {"ref": "o/r#1", "title": "older", "url": "u1", "updated": "2026-01-01T00:00:00Z", "kind": "issue"},
            {"ref": "o/r#2", "title": "newer", "url": "u2", "updated": "2026-02-01T00:00:00Z", "kind": "issue"},
        ], "error": None})
        out = gather.render_section(g, NOW)
        self.assertLess(out.index("newer"), out.index("older"))

    def test_summary_line_counts_and_failures(self):
        g = empty(
            github={"items": [
                {"ref": "o/r#1", "title": "t", "url": "u", "updated": "", "kind": "issue"},
                {"ref": "o/r#2", "title": "t", "url": "u", "updated": "", "kind": "pr", "role": "authored"},
            ], "error": None},
            trac={"items": [], "error": "HTTP 503"},
            things={"items": [{"title": "t", "url": "things:///show?id=X", "updated": "", "list": "today",
                               "project": "", "due": ""}], "error": None},
        )
        out = gather.render_section(g, NOW)
        lines = out.splitlines()
        self.assertEqual(lines[0], "## Gathered")
        self.assertEqual(lines[1], "<!-- gathered:start -->")
        summary = lines[2]
        self.assertIn("2026-09-04 17:00", summary)
        self.assertIn("GitHub 2", summary)
        self.assertIn("Things 1", summary)
        self.assertIn("Trac", summary)
        self.assertIn("HTTP 503", summary)
        self.assertEqual(lines[-1], "<!-- gathered:end -->")

    def test_every_item_line_is_a_deep_link(self):
        g = empty(
            github={"items": [{"ref": "o/r#1", "title": "Bad [title] here", "url": "https://x/1",
                               "updated": "", "kind": "issue"}], "error": None},
            trac={"items": [{"ref": "#1", "title": "s", "url": "https://core.trac.wordpress.org/ticket/1",
                             "updated": "", "status": "new", "milestone": "", "relation": "following"}],
                  "error": None},
            things={"items": [{"title": "t", "url": "things:///show?id=X", "updated": "", "list": "inbox",
                               "project": "P", "due": "2026-09-05"}], "error": None},
        )
        out = gather.render_section(g, NOW)
        item_lines = [l for l in out.splitlines() if l.startswith("- ")]
        self.assertEqual(len(item_lines), 3)
        for line in item_lines:
            self.assertRegex(line, r"^- \[[^\]]+\]\(\S+\)")

    def test_trac_with_empty_watchlist_says_so(self):
        g = empty(trac={"items": [], "error": None, "meta": {"watched": 0}})
        out = gather.render_section(g, NOW)
        self.assertIn("0 watched", out.splitlines()[2])
        self.assertIn("watchlist", out)

    def test_stale_source_is_marked(self):
        g = empty(github={"items": [{"ref": "o/r#1", "title": "t", "url": "u", "updated": "", "kind": "issue"}],
                          "error": "HTTP 503", "stale_from": "2026-09-04T09:00"})
        out = gather.render_section(g, NOW)
        self.assertIn("stale", out)
        self.assertIn("09:00", out)


class BackoffTests(unittest.TestCase):
    def test_429_honors_retry_after(self):
        self.assertEqual(gather.backoff_seconds(429, {"retry-after": "7"}, 0), 7.0)

    def test_429_without_header_is_exponential(self):
        self.assertEqual(gather.backoff_seconds(429, {}, 2), 4.0)

    def test_403_rate_limited_waits_for_reset(self):
        reset = int(time.time()) + 30
        s = gather.backoff_seconds(403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": str(reset)}, 0)
        self.assertTrue(25 <= s <= 31, s)

    def test_503_is_retried(self):
        self.assertEqual(gather.backoff_seconds(503, {}, 1), 2.0)

    def test_404_is_not_retried(self):
        self.assertIsNone(gather.backoff_seconds(404, {}, 0))

    def test_gives_up_after_max_attempts(self):
        self.assertIsNone(gather.backoff_seconds(429, {}, gather.MAX_ATTEMPTS - 1))


class ParserTests(unittest.TestCase):
    def test_parse_gh_response_splits_status_headers_body(self):
        raw = ("HTTP/2.0 404 Not Found\r\nContent-Type: application/json\r\n"
               "X-Ratelimit-Remaining: 4991\r\n\r\n{\"message\":\"Not Found\"}")
        status, headers, body = gather.parse_gh_response(raw)
        self.assertEqual(status, 404)
        self.assertEqual(headers["x-ratelimit-remaining"], "4991")
        self.assertEqual(json.loads(body)["message"], "Not Found")

    def test_parse_gh_response_empty_output(self):
        self.assertEqual(gather.parse_gh_response(""), (0, {}, ""))

    def test_parse_things_output(self):
        us, rs = "\x1f", "\x1e"
        raw = rs.join([
            us.join(["ID1", "Task one", "2026-09-01T10:00:00", "2026-09-05", "Proj", "Area"]),
            us.join(["ID2", "Task two", "2026-09-02T10:00:00", "", "", ""]),
        ]) + rs
        items = gather.parse_things_output(raw, "today")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["url"], "things:///show?id=ID1")
        self.assertEqual(items[0]["due"], "2026-09-05")
        self.assertEqual(items[0]["updated"], "2026-09-01T10:00:00")
        self.assertEqual(items[1]["project"], "")
        self.assertEqual(items[1]["list"], "today")

    def test_parse_trac_ticket_marks_ownership(self):
        payload = {"metadata": {"ticket": {"id": 63290, "summary": "Cover block", "status": "reopened",
                                            "owner": "you", "milestone": "7.1"}}}
        item = gather.parse_trac_ticket(63290, payload, "you")
        self.assertEqual(item["relation"], "owned")
        self.assertEqual(item["url"], "https://core.trac.wordpress.org/ticket/63290")
        self.assertEqual(item["status"], "reopened")


class RetryTests(unittest.TestCase):
    class _Proc:
        def __init__(self, stdout, stderr="", returncode=0):
            self.stdout, self.stderr, self.returncode = stdout, stderr, returncode

    def test_gh_api_retries_on_429_then_succeeds(self):
        replies = [self._Proc("HTTP/2.0 429 Too Many Requests\nRetry-After: 3\n\n{}", "gh: rate limited", 1),
                   self._Proc("HTTP/2.0 200 OK\nX-Ratelimit-Remaining: 9\n\n[{\"number\": 1}]")]
        sleeps = []
        real_run, real_sleep = gather.subprocess.run, gather.time.sleep
        gather.subprocess.run = lambda *a, **k: replies.pop(0)
        gather.time.sleep = sleeps.append
        try:
            data = gather.gh_api("/issues", {"page": 1})
        finally:
            gather.subprocess.run, gather.time.sleep = real_run, real_sleep
        self.assertEqual(data, [{"number": 1}])
        self.assertEqual(sleeps, [3.0])

    def test_gh_api_does_not_retry_when_gh_itself_fails(self):
        replies = [self._Proc("", "gh: To get started with GitHub CLI, please run: gh auth login", 4)]
        sleeps = []
        real_run, real_sleep = gather.subprocess.run, gather.time.sleep
        gather.subprocess.run = lambda *a, **k: replies.pop(0)
        gather.time.sleep = sleeps.append
        try:
            with self.assertRaises(gather.SourceError) as ctx:
                gather.gh_api("/issues")
        finally:
            gather.subprocess.run, gather.time.sleep = real_run, real_sleep
        self.assertIn("gh auth login", str(ctx.exception))
        self.assertEqual(sleeps, [])


class StateTests(unittest.TestCase):
    def test_failed_source_falls_back_to_previous_items(self):
        fresh = empty(github={"items": [], "error": "HTTP 503"})
        state = {"last_run": "2026-09-04T09:00", "sources": {"github": {"items": [
            {"ref": "o/r#1", "title": "t", "url": "u", "updated": "", "kind": "issue"}]}}}
        merged = gather.merge_with_state(fresh, state)
        self.assertEqual(len(merged["github"]["items"]), 1)
        self.assertEqual(merged["github"]["stale_from"], "2026-09-04T09:00")
        self.assertEqual(merged["github"]["error"], "HTTP 503")

    def test_healthy_source_ignores_state(self):
        fresh = empty(github={"items": [{"ref": "o/r#2", "title": "t", "url": "u", "updated": "", "kind": "issue"}],
                              "error": None})
        state = {"last_run": "2026-09-04T09:00", "sources": {"github": {"items": [
            {"ref": "o/r#1", "title": "t", "url": "u", "updated": "", "kind": "issue"}]}}}
        merged = gather.merge_with_state(fresh, state)
        self.assertEqual([i["ref"] for i in merged["github"]["items"]], ["o/r#2"])
        self.assertNotIn("stale_from", merged["github"])

    def test_watchlist_parses_ids_and_skips_comments(self):
        text = "# comment\n63290  Cover block overlays\n\n  12345\nnot-a-ticket\n"
        self.assertEqual(gather.parse_watchlist(text), [63290, 12345])


if __name__ == "__main__":
    unittest.main()
