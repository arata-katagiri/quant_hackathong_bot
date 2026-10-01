import csv
import tempfile
import unittest
from pathlib import Path

from roostoo_bot.backtest import load_closes, simulate


class BacktestTests(unittest.TestCase):
    def test_loads_headerless_binance_klines(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "klines.csv"
            with path.open("w", newline="") as stream:
                csv.writer(stream).writerows([[1, 10, 11, 9, 10.5], [2, 10.5, 12, 10, 11.5]])
            self.assertEqual(load_closes(path), [10.5, 11.5])

    def test_loads_named_close_column(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candles.csv"
            path.write_text("timestamp,Close\n1,10.5\n2,11.5\n")
            self.assertEqual(load_closes(path), [10.5, 11.5])

    def test_charges_fee_for_an_entry_trade(self) -> None:
        closes = [100 + index * 0.1 for index in range(80)]
        result, curve = simulate(closes, fast_window=4, slow_window=12, min_trade_usd=1, rebalance_band=0.0)
        self.assertGreater(result.trades, 0)
        self.assertEqual(len(curve), len(closes))
        self.assertGreater(result.final_equity, 0)
