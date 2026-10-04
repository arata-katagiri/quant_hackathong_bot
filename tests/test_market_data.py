import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError
from roostoo_bot.market_data import MarketDataError, closed_prices, _public_payload


def rows():
    # Three fully closed five-minute candles immediately before 15 minutes epoch.
    return [[i * 300000, "100", "102", "99", "101", "10", (i + 1) * 300000 - 1] for i in range(3)]


class MarketDataTests(unittest.TestCase):
    def test_only_contiguous_closed_candles_are_accepted(self):
        self.assertEqual(closed_prices(rows(), 3, 900), [101, 101, 101])

    def test_forming_candle_is_rejected(self):
        values = rows()
        values[-1][6] = 900000
        with self.assertRaises(MarketDataError):
            closed_prices(values, 3, 900)

    def test_stale_or_duplicate_candles_are_rejected(self):
        with self.assertRaises(MarketDataError):
            closed_prices(rows(), 3, 1200)
        values = rows()
        values[-1] = values[-2]
        with self.assertRaises(MarketDataError):
            closed_prices(values, 3, 900)

    def test_transient_public_read_retries_once(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b"[]"
        with patch("roostoo_bot.market_data.urlopen", side_effect=[URLError(TimeoutError()), response]) as opened, patch("roostoo_bot.market_data.time.sleep") as sleep:
            self.assertEqual(_public_payload("https://example.invalid/klines"), b"[]")
        self.assertEqual(opened.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_public_access_denied_is_not_retried(self):
        error = HTTPError("https://example.invalid", 403, "forbidden", {}, None)
        with patch("roostoo_bot.market_data.urlopen", side_effect=error) as opened:
            with self.assertRaisesRegex(MarketDataError, "HTTP 403"):
                _public_payload("https://example.invalid/klines")
        self.assertEqual(opened.call_count, 1)
