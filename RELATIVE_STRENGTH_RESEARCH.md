# Daily relative strength — screen failed

**No strategy is ready.** The seventh fixed candidate ranks BTC, ETH, XRP, BNB
and SOL against each other, buys at most the two eligible coins closest to their
seven-day highs, and otherwise keeps cash. It lost after costs and failed its
predeclared profitability and drawdown gates. Do not deploy it or substitute the
breadth control as a newly selected winner.

The [plan](RELATIVE_STRENGTH_PLAN.md) was frozen before this rule was tested.
January–March 2025 data had already been examined for the previous study, so
these results are a SCREEN on known data, not an independent out-of-sample test.
April–June 2025 validation and the reserved April 2026 period remain unopened.

## Candidate results

All runs start with USD 100,000 and charge 0.1% fees each side, adverse slippage
of 0.05% base / 0.15% stress, and end liquidation. At most 28% of equity is
targeted for investment (14% in each of two coins). Turnover is total traded
notional divided by starting capital, including final liquidation.

| Period | Base return | Stress return | Base max drawdown | Base turnover | Active UTC dates |
| --- | ---: | ---: | ---: | ---: | ---: |
| January–March quarter | -0.83% | -1.35% | 8.05% | 9.17x | 34 |
| January | +2.02% | +1.48% | 5.92% | 5.45x | 20 |
| February | -1.83% | -2.13% | 4.12% | 3.10x | 12 |
| March | -7.82% | -8.11% | 7.99% | 5.79x | 19 |

Quarter and month results do not compound: each month starts afresh in cash,
whereas the quarter preserves its previous equity peak and risk halts. The
quarter stopped trading under its risk controls for 8,335 base-case bars. Its
small final loss is not evidence that every part of the quarter was safe.

| UTC 14-day window | Base return | Stress return | Active UTC dates, base/stress |
| --- | ---: | ---: | ---: |
| January 1–14 | -0.32% | -0.54% | 8 / 8 |
| January 15–28 | +2.92% | +2.63% | 10 / 10 |
| February 1–14 | +1.84% | +1.76% | 3 / 3 |
| February 15–28 | -3.64% | -3.89% | 9 / 9 |
| March 1–14 | -5.56% | -5.74% | 6 / 6 |
| March 15–28 | -1.54% | -1.93% | 11 / 11 |

Only two of six windows were profitable under either cost assumption. Four of
six met the eight-date screening proxy; this passed only the activity gate, not
the full screen. These are dates with simulated executed fills, NOT verified
qualifying trading days. No extra trades were manufactured to meet activity.

## Controls and loss attribution

| Quarter path | Base return | Stress return | Base drawdown | Base turnover |
| --- | ---: | ---: | ---: | ---: |
| Relative-strength candidate | -0.83% | -1.35% | 8.05% | 9.17x |
| Breadth control, without ranking | -3.99% | -4.26% | 8.05% | 6.26x |
| Cash | 0.00% | 0.00% | 0.00% | 0.00x |
| Buy/hold, 28% invested | -5.94% | -5.99% | 13.55% | 0.50x |
| Buy/hold, 100% invested | -21.23% | -21.39% | 41.68% | 1.79x |

The breadth control has the same eligibility gate and target gross exposure,
but spreads that target across every eligible asset instead of selecting two.
Its realized exposure/risk halts can differ; buy/hold does not use strategy stops.
Outperforming losing controls is not the same as profitability or reliable edge.

Fixed-trade quarter attribution: +USD 547.30 price P&L, -USD 916.66 fees and
-USD 458.33 modeled slippage = -USD 827.70 net. All 100 detailed reports
reconcile. This decomposition preserves the actual fills; it is NOT a claim
that a cheaper-order strategy would produce the same trades or profits. Limit
orders are not automatically maker fills. Four negative competition-length
windows and drawdown overshoot remain concerns independent of this attribution.

The base/stress quarter drawdowns were 8.05% / 8.25%. Five-minute sampling,
price movement and execution costs can overshoot the 8% trigger. The screen
correctly rejected this; the threshold was not relaxed after the result.

## Verification, files and boundaries

Fourteen new offline tests bring the suite to 124, all passing with socket
connections blocked (zero attempts). They check ranking, ties, eligibility,
matched target exposure, scale invariance, cadence, credential/engine guards,
future-price perturbation, cash safety, frozen plan/gates and sealed validation.
The new 28%-invested buy/hold benchmark includes rounding and both-side costs.
The original 168 scenario summaries reproduce exactly after these additions.

`src/roostoo_bot/relative_strength.py` is the pure rule; `relative_research.py`
is its fixed runner. The shared strategy dispatcher and offline-only config
guard were extended; the normal live input and configured pairs were not.
Tracked records: `research/relative_manifest.json`, `relative_summary.json`,
`relative_verdict.json`, `relative_cost_attribution.json`. Local detailed
traces: `data/relative_screen/`; existing archives: `data/vol_market/`.

There are now seven rejected fixed candidate configurations and 440 saved
scenarios INCLUDING controls, cost variants and overlapping periods. That is
not 440 independent experiments. Repeated searching creates selection bias;
we retain every rejection and cannot promise that continued search will find a
profitable strategy. Untouched and prospective evidence would still be needed.

No account calls, orders, paid LLM use, .env changes, commits, push, deployment or
EC2 changes occurred. The offline settings have empty credentials, and BotEngine
refuses them. Existing live historical-input limits are not bypassed.

```bash
cd /Users/umar/Documents/my_projects/quant_hackathong_bot
PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m roostoo_bot.relative_research \
  --market data/vol_market --output data/relative_screen_reproduction --stage screen
```

Use a new output directory. Do not open the validation stage for this failed
candidate, retune its rules on now-seen results, or promote a losing control.
