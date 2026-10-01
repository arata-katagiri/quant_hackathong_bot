from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any

from .client import RoostooClient
from .config import Settings
from .logging_utils import event
from .state import StateStore
from .strategy import target_weight


class BotEngine:
    def __init__(self, client: RoostooClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings
        self.store = StateStore(settings.data_dir)

    def _mid_prices(self) -> dict[str, float]:
        result: dict[str, float] = {}
        for pair in self.settings.pairs:
            data = self.client.ticker(pair)["Data"][pair]
            bid, ask = float(data["MaxBid"]), float(data["MinAsk"])
            result[pair] = (bid + ask) / 2
        return result

    @staticmethod
    def _equity(wallet: dict[str, Any], prices: dict[str, float]) -> float:
        total = float(wallet.get("USD", {}).get("Free", 0)) + float(wallet.get("USD", {}).get("Lock", 0))
        for pair, price in prices.items():
            coin = pair.split("/")[0]
            balance = wallet.get(coin, {})
            total += price * (float(balance.get("Free", 0)) + float(balance.get("Lock", 0)))
        return total

    def _safe_to_trade(self, state: dict[str, Any], equity: float) -> tuple[bool, str]:
        today = datetime.now(timezone.utc).date().isoformat()
        if state.get("day") != today:
            state["day"] = today
            state["day_start_equity"] = equity
        state["peak_equity"] = max(float(state.get("peak_equity", 0)), equity)
        daily_start = float(state["day_start_equity"])
        peak = float(state["peak_equity"])
        if daily_start > 0 and (equity / daily_start - 1) <= -self.settings.max_daily_loss:
            return False, "daily_loss_limit"
        if peak > 0 and (equity / peak - 1) <= -self.settings.max_drawdown:
            return False, "drawdown_limit"
        return True, "ok"

    def run_once(self) -> None:
        state = self.store.load()
        prices = self._mid_prices()
        history = state.setdefault("prices", {})
        for pair, price in prices.items():
            samples = history.setdefault(pair, [])
            samples.append(price)
            del samples[: max(0, len(samples) - self.settings.slow_window - 1)]

        wallet = self.client.balance()["Wallet"]
        equity = self._equity(wallet, prices)
        allowed, reason = self._safe_to_trade(state, equity)
        event(self.settings.data_dir, "cycle", equity=equity, prices=prices, trading_allowed=allowed, reason=reason)
        if not allowed:
            self.store.save(state)
            return

        for pair, price in prices.items():
            coin = pair.split("/")[0]
            desired_weight = target_weight(history[pair], self.settings.fast_window, self.settings.slow_window, self.settings.max_asset_weight)
            current_quantity = float(wallet.get(coin, {}).get("Free", 0))
            current_value = current_quantity * price
            target_value = equity * desired_weight
            delta_value = target_value - current_value
            if abs(delta_value) < max(self.settings.min_trade_usd, equity * self.settings.rebalance_band):
                event(self.settings.data_dir, "hold", pair=pair, current_value=current_value, target_value=target_value)
                continue

            side = "BUY" if delta_value > 0 else "SELL"
            raw_quantity = abs(delta_value) / price
            quantity = math.floor(raw_quantity * 1_000_000) / 1_000_000
            if side == "SELL":
                quantity = min(quantity, current_quantity)
            if quantity <= 0:
                continue
            order = {"pair": pair, "side": side, "quantity": quantity, "estimated_value": quantity * price}
            if self.settings.dry_run:
                event(self.settings.data_dir, "dry_run_order", **order)
            else:
                response = self.client.place_market_order(pair, side, quantity)
                event(self.settings.data_dir, "order_submitted", **order, response=response)
        self.store.save(state)

