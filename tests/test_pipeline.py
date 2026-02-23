import unittest

from hf_daily_papers_newsfeed.pipeline import (
    extract_daily_papers_records,
    extract_paper_ids,
    find_latest_date_from_homepage,
    score_topics,
    summarize,
)


class TestPipeline(unittest.TestCase):
    def test_find_latest_date(self):
        html = '<a href="/papers/date/2026-02-20">latest</a>'
        self.assertEqual(find_latest_date_from_homepage(html), "2026-02-20")

    def test_extract_paper_ids(self):
        html = 'x /papers/2602.12345 y /papers/2602.12345#community z /papers/2602.54321"'
        self.assertEqual(extract_paper_ids(html), ["2602.12345", "2602.54321"])

    def test_extract_daily_papers_records(self):
        html = '&quot;dailyPapers&quot;:[{&quot;paper&quot;:{&quot;id&quot;:&quot;2602.12345&quot;},&quot;title&quot;:&quot;T&quot;}]'
        recs = extract_daily_papers_records(html)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["paper"]["id"], "2602.12345")

    def test_score_topics(self):
        topics = {
            "llm": ["language model", "token"],
            "multimodal": ["image", "video"],
        }
        matched, score = score_topics("A language model for image tokens", "", topics)
        self.assertIn("llm", matched)
        self.assertIn("multimodal", matched)
        self.assertGreater(score, 0)

    def test_summarize(self):
        s, why = summarize("t", "a" * 500, ["llm"])
        self.assertTrue(len(s) <= 240)
        self.assertIn("llm", why)


if __name__ == "__main__":
    unittest.main()
