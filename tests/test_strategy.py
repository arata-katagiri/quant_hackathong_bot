from roostoo_bot.strategy import target_weight
import unittest


class StrategyTests(unittest.TestCase):
    def test_strategy_stays_in_cash_before_warmup(self) -> None:
        self.assertEqual(target_weight([100.0] * 20, 4, 10, 0.35), 0.0)

    def test_strategy_allocates_for_a_calm_uptrend(self) -> None:
        prices = [100 + i * 0.1 for i in range(80)]
        self.assertGreater(target_weight(prices, 12, 48, 0.35), 0)
        self.assertLessEqual(target_weight(prices, 12, 48, 0.35), 0.35)
