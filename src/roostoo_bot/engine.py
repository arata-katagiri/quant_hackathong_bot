from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import time

from .client import OrderRejected, RoostooAPIError, RoostooClient
from .config import Settings
from .logging_utils import event
from .market_data import MarketDataError, fetch_closed_history
from .portfolio import PairRules, Quote, balances, equity, next_order, number, strategy_targets, update_risk
from .state import StateStore

TERMINAL = {"FILLED", "CANCELED", "CANCELLED", "REJECTED", "EXPIRED"}


class BotEngine:
    def __init__(self, client: RoostooClient, settings: Settings, *, clock=time.time, market_data=fetch_closed_history) -> None:
        if settings.signal_source == "offline":
            raise ValueError("offline research settings cannot run in BotEngine")
        self.client, self.settings, self.clock = client, settings, clock
        self.market_data = market_data
        namespace = f"{settings.credential_set}.{'dry' if settings.dry_run else 'live'}"
        self.store = StateStore(settings.data_dir, namespace)
        self.rules: dict[str, PairRules] = {}
        self.rules_at = 0.0

    def _quotes(self) -> dict[str, Quote]:
        payload = self.client.ticker()
        timestamp = number(payload["ServerTime"]) / 1000
        if abs(self.clock() - timestamp) > self.settings.max_quote_age_seconds:
            raise ValueError("ticker timestamp is stale or server clock differs")
        return {pair: Quote(float(payload["Data"][pair]["MaxBid"]), float(payload["Data"][pair]["MinAsk"])) for pair in self.settings.pairs}

    def _rules(self) -> None:
        if not self.rules or self.clock() - self.rules_at >= 3600:
            payload = self.client.exchange_info()
            if payload.get("IsRunning") is not True:
                raise ValueError("exchange is not running")
            self.rules = {pair: PairRules.from_api(payload["TradePairs"][pair]) for pair in self.settings.pairs}
            self.rules_at = self.clock()

    def _detail(self, state: dict, detail: dict) -> bool:
        inflight = state["inflight"]
        if str(detail.get("OrderID")) != str(inflight.get("order_id")):
            raise ValueError("order ID mismatch")
        if detail.get("Pair") != inflight["pair"] or detail.get("Side") != inflight["side"]:
            raise ValueError("order identity mismatch")
        if "FilledQuantity" not in detail:
            raise ValueError("order report missing FilledQuantity")
        filled = number(detail["FilledQuantity"])
        previous_filled = number(inflight.get("filled_quantity_seen", 0))
        if filled + 1e-10 < previous_filled:
            raise ValueError("cumulative filled quantity decreased; order remains unresolved")
        requested = number(inflight["quantity"])
        reported = number(detail["Quantity"])
        if abs(reported - requested) > 1e-10 or filled > requested + 1e-10:
            raise ValueError("order quantity mismatch")
        status = detail.get("Status")
        if status not in TERMINAL | {"PENDING", "PARTIALLY_FILLED", "PARTIAL"}:
            raise ValueError("unknown order status")
        if status == "FILLED" and abs(filled - requested) > 1e-10:
            raise ValueError("FILLED response has incomplete quantity")
        average_price = number(detail.get("FilledAverPrice", 0))
        if filled > 0 and average_price <= 0:
            raise ValueError("executed order has no valid fill price")
        commission = number(detail["CommissionChargeValue"]) if "CommissionChargeValue" in detail else None
        # Persist the highest validated cumulative fill across restarts. A stale
        # terminal response must not erase evidence of an actual partial fill.
        inflight["filled_quantity_seen"] = max(previous_filled, filled)
        self.store.save(state)  # preserve progress even if the event log fails
        event(self.settings.data_dir, "order_status", order_id=inflight["order_id"], pair=inflight["pair"], side=inflight["side"], status=status, filled_quantity=filled,
              average_price=average_price, commission=commission)
        if status in TERMINAL:
            state.pop("inflight")
            self.store.save(state)
        return status in TERMINAL

    def _reconcile(self, state: dict) -> bool:
        inflight = state.get("inflight")
        if not inflight:
            return True
        if not inflight.get("order_id"):
            event(self.settings.data_dir, "execution_blocked", reason="unknown_submit_outcome_requires_review")
            return False
        payload = self.client.query_order(str(inflight["order_id"]))
        matches = [row for row in payload.get("OrderMatched", []) if str(row.get("OrderID")) == str(inflight["order_id"])]
        if len(matches) != 1:
            event(self.settings.data_dir, "execution_blocked", reason="order_not_reconciled")
            return False
        return self._detail(state, matches[0])

    def run_once(self) -> str:
        with self.store.lock():
            return self._run_locked()

    def _run_locked(self) -> str:
        state = self.store.load()
        identity = hashlib.sha256(self.settings.api_key.encode()).hexdigest()[:16]
        if state.get("account", identity) != identity:
            raise ValueError("account changed; use a separate DATA_DIR")
        state["account"] = identity
        config = {key: value for key, value in asdict(self.settings).items() if key not in {"api_key", "secret_key", "data_dir"}}
        signature = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        if state.get("config", signature) != signature:
            state.update(prices={}, signals={})
            state.pop("history_bar", None)
            state.pop("pullback_entries", None)
        state["config"] = signature
        now = self.clock()
        bar = int(now // self.settings.poll_seconds)
        event(self.settings.data_dir, "cycle_started", dry_run=self.settings.dry_run, strategy=self.settings.strategy, bar=bar)
        if state.get("last_bar", -1) >= bar:
            event(self.settings.data_dir, "cycle_skipped", reason="bar_already_processed")
            return "held"
        self._rules()
        quotes = self._quotes()
        wallet = balances(self.client.balance()["Wallet"], self.settings.pairs)
        value = equity(wallet, quotes)
        reason = update_risk(state.setdefault("risk", {}), value, now, self.settings)
        history = state.setdefault("prices", {})
        targets = None
        signal_unavailable = False
        if reason != "ok":
            targets = dict.fromkeys(self.settings.pairs, 0.0)
        elif now % self.settings.poll_seconds <= self.settings.max_sample_lag_seconds:
            if self.settings.signal_source == "binance":
                try:
                    history = self.market_data(self.settings.pairs, self.settings.slow_window + 1, bar * 300)
                    state["prices"], state["history_bar"] = history, bar
                    targets = strategy_targets(history, state, self.settings, bar)
                except MarketDataError as exc:
                    signal_unavailable = True
                    event(self.settings.data_dir, "signal_data_unavailable", reason=str(exc))
            else:
                if state.get("history_bar", bar - 1) != bar - 1:
                    history = state["prices"] = {}
                    state["signals"] = {}
                    event(self.settings.data_dir, "history_reset", reason="missing_sample")
                for pair, quote in quotes.items():
                    samples = history.setdefault(pair, [])
                    samples.append(quote.mid)
                    del samples[:max(0, len(samples) - self.settings.slow_window - 1)]
                state["history_bar"] = bar
                targets = strategy_targets(history, state, self.settings, bar)
        else:
            event(self.settings.data_dir, "sample_skipped", reason="late_in_five_minute_bucket")
        state["last_bar"] = bar
        self.store.save(state)
        event(self.settings.data_dir, "cycle", equity=value, prices={p:q.mid for p,q in quotes.items()}, reason=reason, targets=targets)
        if not self._reconcile(state):
            return "blocked"
        if targets is None:
            return "blocked" if signal_unavailable else "held"
        pending = self.client.pending_count()
        count = pending.get("TotalPending")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError("invalid pending order count")
        if count:
            event(self.settings.data_dir, "execution_blocked", reason="pending_orders", count=count)
            return "blocked"
        traded: set[str] = set()
        for _ in self.settings.pairs:
            wallet = balances(self.client.balance()["Wallet"], self.settings.pairs)
            quotes = self._quotes()
            reason = update_risk(state["risk"], equity(wallet, quotes), self.clock(), self.settings)
            if reason != "ok":
                targets = dict.fromkeys(self.settings.pairs, 0.0)
            self.store.save(state)
            intent = next_order(wallet, quotes, self.rules, targets, self.settings, excluded=traded, risk_reason=reason)
            if intent is None:
                break
            traded.add(intent.pair)
            if self.settings.dry_run:
                event(self.settings.data_dir, "dry_run_order", **asdict(intent))
                break  # no invented fills or cash in observation logs
            if not self.settings.live_trading_enabled:
                raise ValueError("live trading is not enabled")
            state["inflight"] = {**asdict(intent), "submitted_at": self.clock()}
            self.store.save(state)  # durable BEFORE the only non-idempotent call
            try:
                payload = self.client.place_market_order(intent.pair, intent.side, intent.quantity)
            except OrderRejected:
                state.pop("inflight")
                self.store.save(state)
                event(self.settings.data_dir, "order_rejected", pair=intent.pair)
                return "blocked"
            except RoostooAPIError:
                event(self.settings.data_dir, "execution_blocked", reason="submit_outcome_unknown")
                raise
            detail = payload.get("OrderDetail", {})
            if detail.get("OrderID") is None:
                raise ValueError("submit response missing OrderID; review required")
            state["inflight"]["order_id"] = str(detail["OrderID"])
            self.store.save(state)
            if not self._detail(state, detail):
                return "blocked"
        return "ok"
