# Where the simulated losses came from

This reconciles the exact saved trades, separating price movement from fees
and assumed execution slippage. All amounts below are percentages of initial
portfolio capital. Costs subtract from the first column to produce net return.

| Candidate / period | Price P&L before costs | Fees | Modeled slippage | Net return |
| --- | ---: | ---: | ---: | ---: |
| Baseline, September 1–14 | -0.06% | 4.70% | 2.35% | -7.11% |
| Buffered trend, September 1–14 | -3.36% | 0.48% | 0.24% | -4.08% |
| Breakout, September 1–14 | -2.10% | 0.07% | 0.03% | -2.20% |
| Two-asset pullback, January | +2.82% | 0.78% | 0.39% | +1.65% |
| Two-asset pullback, February | +0.15% | 0.77% | 0.39% | -1.01% |

Plainly: the baseline paid a lot to trade repeatedly without a positive gross
result. The slow trend and breakout also made losing price decisions in that
September period. February pullback's small gross gain could not cover costs.
Reducing fees is not enough to establish a reliable winning strategy.

## What this calculation does—and does not—mean

For each BUY, reference notional = simulated fill notional / (1 + slippage).
For each SELL, divide by (1 - slippage). Signed reference cash flows give the
price P&L. The difference from actual simulated cash flows is slippage plus
recorded fees. Holdings must end flat; all cash flows and reported fees must
reconcile to final equity or the calculation fails.

Quantities, trade times, risk halts and strategy decisions remain FIXED. This is
not a new zero-cost strategy backtest: removing costs would change portfolio
equity, sizing and potentially risk decisions. It is not evidence that a
different fee arrangement would produce the quoted gross result. Slippage is
an assumption, not a historical Roostoo fill measurement.

The initial run reconciled 96 detailed reports (48 original full-period reports
and 48 pullback reports); the original 14-day-only summary rows have no saved
trade traces and are deliberately excluded. An additional basket study can be
included explicitly. File hashes accompany every calculation.

```bash
PYTHONPATH=src python3 -m roostoo_bot.attribution \
  --reports data/research_v2_corrected data/pullback_research \
  --output data/cost_attribution.json
```

No credentials, network requests or orders are involved.
