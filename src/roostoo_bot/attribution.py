"""Reconcile fixed historical fills into price P&L, fees and modeled slippage.

This is NOT a zero-cost strategy rerun: the quantities, timing and risk decisions
stay exactly as executed in the original simulation. No credentials are loaded.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from .portfolio import number


def attribute(summary: dict, trades: list[dict], slippage_rate: float) -> dict:
    initial = number(summary["initial_equity"])
    final = number(summary["final_equity"])
    if initial <= 0 or not math.isfinite(slippage_rate) or not 0 <= slippage_rate < 1:
        raise ValueError("invalid capital or slippage assumption")
    flows, reference_flows, costs, fees, positions = [], [], [], [], {}
    for row in trades:
        side = row["side"]
        if side not in {"BUY","SELL"}:
            raise ValueError("unknown fill side")
        quantity, price = number(row["quantity"]), number(row["price"])
        notional, fee = number(row["notional"]), number(row["fee"])
        if quantity <= 0 or price <= 0 or not math.isclose(notional,quantity*price,rel_tol=1e-10,abs_tol=1e-7):
            raise ValueError("fill notional does not reconcile")
        direction = 1 if side == "BUY" else -1
        reference = notional / (1 + direction * slippage_rate)
        reference_flows.append(-direction * reference)
        flows.append(-direction * notional - fee)
        costs.append(direction * (notional-reference))
        fees.append(fee)
        positions.setdefault(row["pair"],[]).append(direction * quantity)
    if any(abs(math.fsum(values)) > 1e-10 for values in positions.values()):
        raise ValueError("attribution requires a liquidated portfolio, not unmarked open positions")
    price_pnl, fee_total, slippage = math.fsum(reference_flows), math.fsum(fees), math.fsum(costs)
    net = math.fsum(flows)
    if not math.isclose(net,final-initial,rel_tol=1e-9,abs_tol=1e-6):
        raise ValueError("fills do not reconcile to final equity")
    if not math.isclose(fee_total,number(summary["fees"]),rel_tol=1e-9,abs_tol=1e-6):
        raise ValueError("fills do not reconcile to reported fees")
    if not math.isclose(price_pnl-fee_total-slippage,net,rel_tol=1e-9,abs_tol=1e-6):
        raise ValueError("cost decomposition does not reconcile")
    return {"same_trades_price_pnl":price_pnl,"fees":fee_total,"modeled_slippage":slippage,"net_pnl":net,
            "same_trades_before_costs_return":price_pnl/initial,"fee_drag":fee_total/initial,
            "slippage_drag":slippage/initial,"net_return":net/initial,
            "fill_count_including_liquidation":len(trades),"liquidated":True,
            "interpretation":"fixed trade schedule, not a cost-free strategy backtest"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports",nargs="+",type=Path,required=True)
    parser.add_argument("--output",type=Path,default=Path("data/cost_attribution.json"))
    args = parser.parse_args()
    rows = []
    for root in args.reports:
        for path in sorted(root.glob("*/*/*/summary.json")):
            summary = json.loads(path.read_text())
            cost = summary["cost"]
            if cost not in {"base","stress"}:
                raise ValueError("unknown cost scenario; cannot infer slippage")
            trades_path = path.with_name("trades.csv")
            with trades_path.open(newline="") as stream:
                trades = list(csv.DictReader(stream))
            rows.append({"study":root.name,"period":summary["period"],"strategy":summary["strategy"],"cost":cost,
                         "active_days_utc":summary["active_days_utc"],"active_days_hkt":summary["active_days_hkt"],
                         "summary_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                         "trades_sha256":hashlib.sha256(trades_path.read_bytes()).hexdigest(),
                         **attribute(summary,trades,.0005 if cost=="base" else .0015)})
    if not rows:
        raise ValueError("no detailed reports found")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(rows,indent=2,allow_nan=False)+"\n")
    print(f"Reconciled {len(rows)} detailed reports to their final equities; output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
