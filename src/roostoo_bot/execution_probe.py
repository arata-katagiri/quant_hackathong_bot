"""One explicitly approved TEST-account round trip; never a strategy runner.

The normal bot and .env remain in dry-run. This separate tool can submit orders
ONLY with an explicit CLI confirmation and a testing-key configuration. A durable
journal prevents re-submitting a leg, including when its outcome is unknown.
"""
from __future__ import annotations
import argparse
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
import os
from pathlib import Path
import time

from .client import OrderRejected, RoostooAPIError, RoostooClient
from .config import Settings, load_dotenv
from .engine import TERMINAL
from .portfolio import PairRules, Quote, balances, number
from .state import StateStore

PAIR = "BTC/USD"


class ExecutionProbe:
    def __init__(self, client, settings: Settings, *, approved: bool, clock=time.time):
        if not approved or settings.credential_set != "testing" or not settings.dry_run:
            raise ValueError("requires explicit testing-only approval; normal dry-run must remain enabled")
        if getattr(client, "api_key", settings.api_key) != settings.api_key:
            raise ValueError("client does not match approved testing key")
        self.client, self.settings, self.clock = client, settings, clock
        self.store = StateStore(settings.data_dir, "approved-test-roundtrip")

    def wallet(self):
        return balances(self.client.balance()["Wallet"], ("BTC/USD","ETH/USD"))

    def quote(self):
        payload = self.client.ticker(PAIR)
        if abs(self.clock()-number(payload["ServerTime"])/1000) > 30:
            raise ValueError("stale test quote")
        row = payload["Data"][PAIR]
        quote = Quote(number(row["MaxBid"]),number(row["MinAsk"]))
        if quote.spread > .005:
            raise ValueError("test spread exceeds safety bound")
        return quote

    def no_pending(self):
        count = self.client.pending_count()["TotalPending"]
        if type(count) is not int or count != 0:
            raise ValueError("account has pending orders; test blocked")

    def record(self, state, name, detail):
        leg = state[name]
        if str(detail.get("OrderID")) != leg["order_id"] or detail.get("Pair") != PAIR or detail.get("Side") != name.upper():
            raise ValueError("test order identity mismatch")
        quantity, filled = number(detail["Quantity"]), number(detail["FilledQuantity"])
        previous_filled = number(leg.get("detail", {}).get("filled_quantity", 0))
        if filled + 1e-10 < previous_filled:
            raise ValueError("test cumulative filled quantity decreased; review required")
        if abs(quantity-float(leg["quantity"])) > 1e-10 or filled > quantity+1e-10:
            raise ValueError("test order quantity mismatch")
        status = detail.get("Status")
        if status not in TERMINAL | {"PENDING","PARTIAL","PARTIALLY_FILLED"}:
            raise ValueError("unknown test order status")
        average = number(detail.get("FilledAverPrice",0))
        if filled and average <= 0 or status == "FILLED" and abs(filled-quantity) > 1e-10:
            raise ValueError("inconsistent test fill report")
        if name == "buy" and filled and average > float(leg["price"])+1e-8:
            raise ValueError("buy execution exceeds limit price")
        coin = detail.get("CommissionCoin")
        if coin not in {None,"USD","BTC"}:
            raise ValueError("unexpected fee denomination")
        safe = {"status":status,"filled_quantity":filled,"average_price":average,"commission_coin":coin,
                "commission":number(detail["CommissionChargeValue"]) if "CommissionChargeValue" in detail else None,
                "commission_rate":number(detail["CommissionPercent"]) if "CommissionPercent" in detail else None}
        leg["detail"] = safe
        self.store.save(state)
        return safe

    def submit(self, state, name):
        leg = state[name]
        if leg.get("submit_started"):
            if not leg.get("order_id"):
                raise ValueError("previous test submit has no resolved ID; never resubmit")
            return
        leg["submit_started"] = True
        leg["submitted_at"] = self.clock()
        self.store.save(state)
        try:
            if name == "buy":
                payload = self.client.place_limit_order(PAIR,"BUY",leg["quantity"],leg["price"])
            else:
                payload = self.client.place_market_order(PAIR,"SELL",leg["quantity"])
        except OrderRejected:
            leg["explicitly_rejected"] = True
            self.store.save(state)
            raise
        except RoostooAPIError as exc:
            leg["submit_error"] = str(exc)  # client messages omit raw response bodies
            self.store.save(state)
            raise
        detail = payload.get("OrderDetail",{})
        if detail.get("OrderID") is None:
            raise ValueError("test submit missing ID; never resubmit")
        leg["order_id"] = str(detail["OrderID"])
        self.store.save(state)
        self.record(state,name,detail)

    def settle(self, state, name):
        leg = state[name]
        for attempt in range(6):
            payload = self.client.query_order(leg["order_id"])
            rows = [r for r in payload.get("OrderMatched",[]) if str(r.get("OrderID")) == leg["order_id"]]
            if len(rows) != 1:
                raise ValueError("test order cannot be reconciled")
            detail = self.record(state,name,rows[0])
            if detail["status"] in TERMINAL:
                return detail
            if attempt == 2 and not leg.get("cancel_started"):
                leg["cancel_started"] = True
                self.store.save(state)
                try:
                    self.client.cancel_order(leg["order_id"])
                except RoostooAPIError:
                    pass  # only subsequent exact-ID queries can confirm terminal state
        raise ValueError("test order still unresolved; do not submit another")

    def run(self):
        with self.store.lock():
            state = self.store.load()
            identity = hashlib.sha256(self.settings.api_key.encode()).hexdigest()[:16]
            if state.get("account",identity) != identity:
                raise ValueError("testing account differs from journal")
            if state.get("finished"):
                return state["report"]
            if "buy" not in state:
                self.no_pending()
                exchange = self.client.exchange_info()
                if exchange.get("IsRunning") is not True:
                    raise ValueError("exchange not running")
                raw = exchange["TradePairs"][PAIR]
                rule = PairRules.from_api(raw)
                precision = raw["PricePrecision"]
                if type(precision) is not int or not 0 <= precision <= 12 or not rule.can_trade:
                    raise ValueError("invalid or disabled BTC market")
                initial = self.wallet()
                if initial["BTC"]["Free"] or initial["BTC"]["Lock"] or initial["USD"]["Free"] < 10:
                    raise ValueError("requires no initial BTC and at least $10 free testing cash")
                quote = self.quote()
                # Limit price caps principal; $9 leaves over $1 below the human
                # $10 authorization for fees. No additional buy is permitted.
                price = (Decimal(str(quote.ask))*Decimal("1.001")).quantize(Decimal(1).scaleb(-precision),rounding=ROUND_CEILING)
                quantity = rule.floor(float(Decimal("9")/price))
                if quantity <= 0 or quantity*price <= Decimal(str(rule.min_notional)) or quantity*price > 9:
                    raise ValueError("approved size cannot meet exchange rules")
                state.update(account=identity,initial_wallet=initial,amount_precision=rule.amount_precision,min_notional=rule.min_notional,
                             buy={"quantity":format(quantity,"f"),"price":format(price,"f")},started_at=self.clock())
                self.store.save(state)
            self.submit(state,"buy")
            buy = self.settle(state,"buy")
            self.no_pending()
            after_buy = self.wallet()
            state["after_buy"] = after_buy
            self.store.save(state)
            if "sell" not in state and buy["filled_quantity"] > 0:
                acquired = after_buy["BTC"]["Free"]-state["initial_wallet"]["BTC"]["Free"]
                rule = PairRules(state["amount_precision"],state["min_notional"])
                quantity = rule.floor(min(number(acquired),buy["filled_quantity"]))
                if quantity <= 0 or float(quantity)*self.quote().bid <= rule.min_notional:
                    raise ValueError("acquired quantity cannot be sold within exchange minimum; review needed")
                state["sell"] = {"quantity":format(quantity,"f")}
                self.store.save(state)
            sell = None
            if "sell" in state:
                self.submit(state,"sell")
                sell = self.settle(state,"sell")
            self.no_pending()
            final = self.wallet()
            report = {"credential_set":"testing","buy":buy,"sell":sell,
                      "bought_btc":buy["filled_quantity"],"sold_btc":sell["filled_quantity"] if sell else 0,
                      "buy_notional":buy["filled_quantity"]*buy["average_price"],
                      "remaining_btc":final["BTC"]["Free"]+final["BTC"]["Lock"],
                      "cash_change":final["USD"]["Free"]-state["initial_wallet"]["USD"]["Free"],
                      "pending_orders":0,"strategy_approved_for_live":False,"normal_bot_dry_run":True}
            state.update(finished=True,report=report,final_wallet=final,finished_at=self.clock())
            self.store.save(state)
            return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-testing-roundtrip",action="store_true")
    args = parser.parse_args()
    if not args.confirm_testing_roundtrip:
        parser.error("fresh human approval is required before passing --confirm-testing-roundtrip")
    load_dotenv()
    os.environ.update(CREDENTIAL_SET="testing",DRY_RUN="true",LIVE_TRADING_ENABLED="false")
    settings = Settings.from_env()
    if settings.api_key == os.getenv("ROOSTOO_COMPET_API_KEY"):
        raise ValueError("testing and competition key aliases must be distinct")
    client = RoostooClient(settings.api_key,settings.secret_key,allow_orders=True,request_interval=4)
    try:
        result = ExecutionProbe(client,settings,approved=True).run()
        print(json.dumps(result,indent=2,allow_nan=False))
        return 0 if result["sell"] and result["remaining_btc"] < 1e-12 else 1
    except Exception as exc:
        print(f"testing probe stopped ({type(exc).__name__}); inspect its durable journal before any further orders")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
