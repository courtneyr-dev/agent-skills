"""Fetch logs under fleets/*/evidence/sources keep identifiers, headings and short phrases from third-party
pages. A sentence-length excerpt (12 words or more) has to be the log writer's own paraphrase or a citation,
labeled `L<n> (paraphrase):` or `L<n> (citation):`, so no page's paragraph is republished here."""
import glob
import os
import re
import unittest

from support import SKILL

EXCERPT = re.compile(r"^L\S+?(?: \((paraphrase|citation)\))?:\s?(.*)$")


class SourceLogs(unittest.TestCase):
    def test_no_unlabeled_sentence_length_excerpts(self):
        logs = glob.glob(os.path.join(SKILL, "fleets", "*", "evidence", "sources", "*.txt"))
        self.assertTrue(logs)
        found = []
        for path in logs:
            with open(path, encoding="utf-8") as fh:
                for n, line in enumerate(fh, 1):
                    m = EXCERPT.match(line.rstrip("\n"))
                    if m and not m.group(1) and len(m.group(2).split()) >= 12:
                        found.append("%s:%d" % (os.path.relpath(path, SKILL), n))
        self.assertEqual(found, [], "quote these as a paraphrase or a citation, not verbatim")


if __name__ == "__main__":
    unittest.main()
