import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from update_scholar_citations import (
    article_ids, parse_citation_count, read_cache, scholar_user_id, update_counts, write_cache,
)


class ScholarCitationTests(unittest.TestCase):
    def test_meta_citation_count(self):
        self.assertEqual(parse_citation_count('<meta name="description" content="Paper. Cited by 1,234. More info">'), 1234)
        self.assertEqual(parse_citation_count('<meta property="og:description" content="Cited by 7">'), 7)

    def test_no_citation_is_not_zero(self):
        self.assertIsNone(parse_citation_count('<html><title>CAPTCHA</title></html>'))
        self.assertIsNone(parse_citation_count('<meta name="description" content="Some paper">'))

    def test_only_valid_results_update(self):
        cache = {"first": 8, "second": 4, "third": 0}
        with patch("update_scholar_citations.time.sleep", return_value=None):
            result = update_counts(cache, lambda user, paper: {"first": None, "second": 5, "third": 0}[paper],
                                   ["first", "second", "third"], "abc")
        self.assertEqual(result, {"first": 8, "second": 5, "third": 0})

    def test_rejected_lower_counts(self):
        with patch("update_scholar_citations.time.sleep", return_value=None):
            result = update_counts({"first": 10}, lambda _user, _paper: 3, ["first"], "abc")
        self.assertEqual(result["first"], 10)

    def test_cache_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "counts.yml"
            write_cache(path, {"xyz": 0, "abc": 11})
            self.assertEqual(read_cache(path), {"abc": 11, "xyz": 0})

    def test_bib_and_profile(self):
        self.assertEqual(article_ids('google_scholar_id={id1}\ngoogle_scholar_id={id2}\ngoogle_scholar_id={id1}'), ["id1", "id2"])
        self.assertEqual(scholar_user_id("scholar_userid: abc123 # ID\n"), "abc123")


if __name__ == "__main__":
    unittest.main()
