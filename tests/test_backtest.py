import csv
import tempfile
import unittest
from pathlib import Path

from roostoo_bot.backtest import Candle, load_candles, simulate_candles


class BacktestTests(unittest.TestCase):
    def test_five_minute_signal_fills_at_next_open(self) -> None:
        start = 1_785_542_400_000_000
        candles = [Candle(start + index * 300_000_000, 100 + index, 100 + index) for index in range(60)]
        result, curve = simulate_candles(candles, min_trade_usd=1, rebalance_band=0)
        self.assertEqual(curve[48], 50_000)
        self.assertLess(curve[49], 50_000)
        self.assertGreater(result.trades, 0)

    def test_five_minute_loader_rejects_gap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "klines.csv"
            start = 1_785_542_400_000_000
            with path.open("w", newline="") as stream:
                writer = csv.writer(stream)
                for index in range(51):
                    writer.writerow([start + index * 300_000_000 + (300_000_000 if index >= 25 else 0), 100, 101, 99, 100])
            with self.assertRaisesRegex(ValueError, "continuous"):
                load_candles([path])

    def test_charges_fee_for_an_entry_trade(self) -> None:
        start = 1_785_542_400_000_000
        candles = [Candle(start + index * 300_000_000, 100 + index * 0.1, 100 + index * 0.1) for index in range(80)]
        with_costs, _ = simulate_candles(candles, fast_window=4, slow_window=12, min_trade_usd=1, rebalance_band=0)
        without_costs, _ = simulate_candles(candles, fast_window=4, slow_window=12, min_trade_usd=1, rebalance_band=0, fee_rate=0, slippage_rate=0)
        self.assertGreater(with_costs.trades, 0)
        self.assertLess(with_costs.final_equity, without_costs.final_equity)
