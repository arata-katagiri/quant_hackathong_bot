# Slower volatility-scaled momentum — screening failed

The resumed search produced another clear rejection, not a successful strategy.
This candidate adjusts long-only positions using one-, three- and seven-day
trends and reduces allocation when volatility rises. It decides every six
hours; risk checks still run every five minutes. No settings were selected by
trying alternative values on the evaluation period.

The [frozen plan](VOL_MOMENTUM_PLAN.md) preceded downloading 20 public Binance
archives. December 2024 warmed indicators; January–March 2025 was the screen.
April–June 2025 validation and the reserved April 2026 period were NOT opened.

## Portfolio results

Returns include 0.1% fees and 0.05% adverse slippage per side, plus end liquidation.
Stress uses 0.15% slippage. Every simulation begins with USD 100,000 in cash.

| Candidate period | Base return | Stress return | Base max drawdown | Base turnover | Active UTC dates |
| --- | ---: | ---: | ---: | ---: | ---: |
| Full January–March quarter | -5.12% | -6.15% | 7.29% | 14.08x | 74 |
| January | -1.02% | -1.69% | 3.30% | 6.86x | 29 |
| February | -1.85% | -2.16% | 2.17% | 3.06x | 20 |
| March | -2.35% | -2.79% | 2.51% | 4.47x | 25 |

Turnover = total traded notional / starting capital. The quarter and fresh-start
months are different simulations; their returns need not compound to the same
number because position starts and persistent risk halts differ.

| Full-quarter comparison | Base return | Base max drawdown | Base turnover |
| --- | ---: | ---: | ---: |
| Candidate | -5.12% | 7.29% | 14.08x |
| Volatility-only control | -3.10% | 8.21% | 3.23x |
| Cash | 0.00% | 0.00% | 0.00x |
| Buy/hold, 70% total invested | -14.86% | 30.96% | 1.25x |
| Buy/hold, 100% total invested | -21.23% | 41.68% | 1.79x |

The volatility-only control uses the same sizing/cadence/stops but no timing
forecast. Buy/hold has no strategy stops. The candidate lost less than unguarded
buy/hold, but lost MORE than the volatility-only control and cash. That is not
evidence of a useful timing edge. Stress-case drawdown reached 8.03%; a sampled
8% stop cannot guarantee an 8% final maximum after gaps and execution costs.

## Competition-length windows and cause of failure

| UTC 14-day window | Base return | Stress return | Active UTC dates, base/stress |
| --- | ---: | ---: | ---: |
| January 1–14 | -0.19% | -0.49% | 13 / 13 |
| January 15–28 | -0.67% | -0.99% | 13 / 13 |
| February 1–14 | -0.77% | -0.95% | 10 / 10 |
| February 15–28 | -1.15% | -1.32% | 10 / 10 |
| March 1–14 | -1.59% | -1.70% | 11 / 11 |
| March 15–28 | -0.81% | -1.17% | 14 / 14 |

All six windows met the eight-date screening proxy naturally through changing
forecast/risk allocations. All six lost money. More activity did not solve the
economic problem. These are executed-fill dates, NOT confirmed qualifying days;
the organizer's exact daily trade threshold/timezone remains unresolved.

Quarter base fixed-trade attribution: -USD 3,012.57 price P&L before costs,
-USD 1,407.89 fees and -USD 703.95 slippage = -USD 5,124.41 net. Fees hurt,
but the actual price decisions also lost before costs. This is reconciliation
of identical fills, not a hypothetical cost-free strategy rerun. All 100 new
detailed reports reconcile to final equity.

## Decision and boundaries

Rejected: quarter profitability/control comparison, monthly profitability and
14-day profitability gates all failed. The activity proxy passed; drawdown
passed base but failed stress. The always-long volatility control is an ablation,
not a replacement winner. No thresholds, gates or asset lists were changed.

The study adds 100 scenarios (10 periods x 5 candidate/control/benchmark paths
x 2 cost assumptions), bringing the stored total to 340. They are not independent
samples; the month/window reports overlap the quarter. Six candidate
configurations have now been rejected across studies. Repeated hypothesis
testing creates selection bias, so a later positive result must still survive
untouched validation and prospective observation.

Research remains offline: the new strategy is only valid with empty credentials
and SIGNAL_SOURCE=offline, which BotEngine refuses. Default strategy, configured
pairs, .env and EC2 remain unchanged. No new orders or account queries were made.
Before any future deployment, a selected candidate would need an approved live
data adapter: this seven-day history does not fit the current BTC/ETH-only
999-sample live-input limit. Do not change that limit as a deployment shortcut.

## Reproduction and files

`vol_momentum.py` implements the pure forecast; `vol_research.py` enforces the
fixed periods, controls, costs and screening gates. `test_vol_momentum.py`
covers the formula, volatility floor, scale invariance, timing, safety,
look-ahead protection and sealed-stage guard. The offline suite has 110 tests.

Saved tracked results: `research/vol_manifest.json`, `vol_summary.json`,
`vol_verdict.json`, `vol_cost_attribution.json`. Ignored local archives/traces:
`data/vol_market/` and `data/vol_screen/`.

```bash
cd /Users/umar/Documents/my_projects/quant_hackathong_bot
PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m roostoo_bot.vol_research \
  --market data/vol_market --output data/vol_screen_reproduction --stage screen
```

Use a new output directory. Do not run the validation stage for this failed
candidate. Continued research needs a distinct rationale and another predeclared
test, not a renamed version of this failure or retuning to September.
