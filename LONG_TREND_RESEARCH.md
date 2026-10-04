# Monthly-horizon long/cash portfolio — rejected

**Positive average, insufficient evidence. No strategy is ready for deployment.**
The fixed longer-horizon rule had a small positive average over fresh 14-day
portfolios, but failed uncertainty, consistency, activity and drawdown gates.
It is the eighth rejected portfolio configuration, not a successful strategy.

## Why this was a different test

The [frozen plan](LONG_TREND_PLAN.md) drew its longer time scale from primary
time-series-momentum research, not from adjusting a previously failed horizon
to September. The exact rule combined 30-, 90- and 365-day trend signs, retained
only positive combined exposure, and reduced all weights when their estimated
joint volatility exceeded a 0.75% daily budget. Maximum target investment was
70%, at most 14% per coin. Those choices were frozen before this run.

The five-asset universe and price data were already inspected; this is known-data
screening, not new out-of-sample validation. Retrospective universe selection
and Binance-USDT versus Roostoo-USD differences remain. No new data was downloaded.

Unlike the prior isolated-return screens, these are shared-cash portfolio tests:
USD100,000 per trial, actual net position adjustments, exchange rounding and
minimums, fees, slippage, final liquidation, and shared daily/drawdown risk guards.
No daily sell/rebuy sequence was imposed just to generate trading dates.

## Coverage and results

Scheduled 78 consecutive non-overlapping 14-day trials beginning January1,
2022. One trial, March11–24, 2023, was excluded for missing execution bars;
all candidate/control/cost paths were excluded together. No filling of missing
prices or assumed executions. Coverage: 77/78, or 98.72%. The final four days
of 2024 are the deterministic unused remainder.

Five paths times two cost cases times 77 usable trials produced **770 scenarios**.
Each trial starts flat and resets risk only at its beginning. These results
must NOT be compounded or presented as a continuously traded three-year account.

| Portfolio | Mean 14-day return, base | Mean 14-day return, stress | Worst stress drawdown | Mean stress turnover | Stress trials with eight UTC fill dates |
| --- | ---: | ---: | ---: | ---: | ---: |
| Monthly-horizon candidate | +0.23% | +0.15% | 8.22% | 0.74x | 41 |
| Covariance-only control | +0.19% | +0.10% | 11.60% | 0.80x | 52 |
| Cash | 0.00% | 0.00% | 0.00% | 0.00x | 0 |
| Equal buy/hold, 70% | +0.84% | +0.70% | 26.98% | 1.41x | 0 |
| Equal buy/hold, 100% | +1.21% | +1.00% | 38.54% | 2.01x | 0 |

Fees are 0.1% each side; slippage is 0.05% base / 0.15% stress each side.
Turnover is total bought/sold notional divided by starting equity. Buy/hold
does not use strategy risk stops and enters at 00:00, five minutes before the
signal-dependent candidate/control. These controls are not fallback candidates.

| Trial start year | Usable trials | Mean candidate return, base | Mean candidate return, stress |
| --- | ---: | ---: | ---: |
| 2022 | 27 | -0.19% | -0.22% |
| 2023 | 25 | +0.32% | +0.24% |
| 2024 | 25 | +0.58% | +0.47% |

These are mean trial returns grouped by START year, not annual account returns;
some trials cross a year boundary. The candidate's median return was zero under
both costs, including six completely flat trials. It was profitable in 34
trials at base costs and 33 under stress, below the predeclared 52/78 requirement.
Only 41 trials met the eight-fill-date proxy under either cost or timezone,
also below 52. Final forced liquidation does not count as activity.

The worst candidate trial, July27–August9, 2024, lost 7.18% under stress and
reached 8.22% peak-to-trough drawdown. The risk trigger is not a guaranteed loss
bound: sampled moves and liquidation costs can overshoot it. Do not reduce the
stop afterward to make this particular test pass.

## Uncertainty, costs and decision

The predeclared paired circular two-trial-block bootstrap used all 78 calendar
slots, including the unavailable slot, 2,000 replicates and seed20261002.
All replicates were nonempty. Approximate 95% intervals under stress:

- Mean 14-day candidate return: -0.393% to +0.790%.
- Mean advantage over the covariance control: -0.587 to +0.719 percentage points.

Neither lower bound is positive. The mean stress advantage of 0.056 percentage
points is too uncertain to establish an improvement. These intervals are
descriptive, not a correction for the project's repeated hypothesis search.

All 770 detailed trade ledgers reconcile to final equity. For the candidate,
mean base P&L per USD100,000 trial decomposes into USD338.55 from price moves,
minus USD74.45 fees and USD37.23 modeled slippage, leaving USD226.87.
Under stress, mean net P&L is USD152.63. Attribution keeps the actual fills fixed;
it is not a rerun without costs or an argument to waive costs.

Coverage and the two-positive-start-years gate passed. Profit/uncertainty,
profitable-trial count, activity and maximum drawdown failed. No parameter,
band, horizon or gate has been revised based on these outcomes. The candidate
does not advance to untouched validation. Neither control is promoted.

## Engineering and verification

- `long_trend.py`: pure allocation, past-only daily schedules, input integrity,
  common exclusions, fixed trial calendar, bootstrap, gates and full provenance.
- `portfolio_backtest.py`: optional scheduled targets, accepted only with empty
  credentials, offline settings and trading disabled; validates timing and
  complete bounded weights. Risk checks take priority. The live engine and
  configuration are unchanged and cannot execute this research schedule.
- `test_long_trend.py`: 14 new tests. All **189 tests pass** with network
  connections blocked and zero attempts.
- All 770 full summary rows, 77 candidate/control schedules, exclusions and
  verdict reproduce exactly. The verification run omits duplicate detailed
  trace writes; the original full traces are preserved.
- The original 168 complete scenario rows reproduce exactly after extending
  the shared simulator. All 770 new cost attributions reconcile to cash.

Known limits: assumed five-minute data publication lag; immediate next-boundary
fills; unverified venue latency, partial fills and historical listing/rule
availability; intrabar drawdown can exceed sampled drawdown; estimated
volatility is not a realized-risk guarantee. Official daily trade counts and
metric conventions remain unresolved.

Saved evidence: `research/long_trend_summary.json`, `long_trend_manifest.json`,
`long_trend_verdict.json`, `long_trend_excluded.json`, and
`long_trend_attribution.json` in the same research directory. Ignored full
traces: `data/long_trend_screen/`; summary/schedule reproduction:
`data/long_trend_verify/`.

The project now has eight rejected portfolio configurations and 1,210 saved
portfolio scenarios, plus three information screens that failed progression.
These are not 1,210 independent strategies or validation samples.

No account credentials, private requests, orders, paid LLM calls, .env edits,
EC2 actions, commits, pushes or deployment. No short simulations. Reserved
April–June2025 and April2026 validation stays unopened. Keep `DRY_RUN=true`
and `LIVE_TRADING_ENABLED=false`.

```bash
cd /Users/umar/Documents/my_projects/quant_hackathong_bot
PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m roostoo_bot.long_trend \
  --market data/forecast_market --output data/long_trend_reproduction
```

Use a new output directory. Reproduction uses saved public data only.
