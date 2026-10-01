import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from roostoo_bot import news


RSS = b"""<?xml version="1.0"?>
<rss><channel>
  <item><title>Bitcoin rises after ETF news</title>
    <link>https://example.com/btc?tracking=1</link>
    <pubDate>Thu, 01 Oct 2026 02:00:00 GMT</pubDate></item>
  <item><title>Ethereum update</title>
    <link>https://example.com/eth</link>
    <pubDate>Thu, 01 Oct 2026 02:01:00 GMT</pubDate></item>
</channel></rss>"""


class NewsTests(unittest.TestCase):
    def test_parse_feed_records_actual_observation_time(self) -> None:
        seen = datetime(2026, 10, 1, 3, tzinfo=timezone.utc)
        items = news.parse_feed(RSS, "Example", seen)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["first_seen_at"], seen.isoformat())
        self.assertEqual(items[0]["published_at"], "2026-10-01T02:00:00+00:00")
        self.assertEqual(items[0]["url"], "https://example.com/btc")

    def test_duplicate_headlines_are_not_saved_twice(self) -> None:
        seen = datetime.now(timezone.utc)
        items = news.parse_feed(RSS, "Example", seen)
        for item in items:
            item["published_at"] = seen.isoformat()
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(news, "FEEDS", {"Example": "https://example.com/feed"}), patch.object(news, "fetch_feed", return_value=items):
                first = news.observe_once(Path(directory))
                second = news.observe_once(Path(directory))
            self.assertEqual(first["saved"], 2)
            self.assertEqual(second["saved"], 0)
            lines = (Path(directory) / "news.jsonl").read_text().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertTrue(all("analysis" not in json.loads(line) for line in lines))

    def test_llm_can_assess_previously_collected_headline(self) -> None:
        seen = datetime.now(timezone.utc)
        item = news.parse_feed(RSS, "Example", seen)[0]
        item["published_at"] = seen.isoformat()
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(news, "FEEDS", {"Example": "https://example.com/feed"}), patch.object(news, "fetch_feed", return_value=[item]):
                news.observe_once(Path(directory))
                with patch.object(news, "_llm_assess", return_value={item["id"]: {
                    "asset": "BTC", "tone": "positive", "reason": "Upbeat", "model": "test/model",
                }}):
                    result = news.observe_once(Path(directory), use_llm=True)
                    again = news.observe_once(Path(directory), use_llm=True)
            self.assertEqual(result["assessed"], 1)
            self.assertEqual(again["assessed"], 0)
            record = json.loads((Path(directory) / "news_assessments.jsonl").read_text().splitlines()[0])
            self.assertEqual(record["id"], item["id"])
            self.assertIn("analyzed_at", record)

    def test_llm_results_are_schema_checked(self) -> None:
        item = {"id": "abc", "headline": "Bitcoin rises"}
        response = {"choices": [{"message": {"content": json.dumps({"items": [
            {"id": "abc", "asset": "BTC", "tone": "positive", "reason": "Headline is upbeat"},
            {"id": "wrong", "asset": "ETH", "tone": "positive", "reason": "Ignore"},
        ]})}}]}
        environment = {
            "OPENAI_API_KEY": "secret-test-key",
            "OPENAI_MODEL": "test/model",
            "OPENAI_BASE_URL": "https://openrouter.ai/api/v1",
        }
        with patch.dict(os.environ, environment, clear=True), patch.object(news.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(response).encode())) as mock_open:
            result = news._llm_assess([item])
        self.assertEqual(set(result), {"abc"})
        self.assertEqual(result["abc"]["asset"], "BTC")
        self.assertIn(b"Bitcoin rises", mock_open.call_args.args[0].data)

    def test_llm_rejects_other_endpoint(self) -> None:
        environment = {
            "OPENAI_API_KEY": "secret-test-key",
            "OPENAI_MODEL": "test/model",
            "OPENAI_BASE_URL": "https://example.com/api/v1",
        }
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaises(ValueError):
                news._llm_assess([{"id": "abc", "headline": "Bitcoin"}])


if __name__ == "__main__":
    unittest.main()
