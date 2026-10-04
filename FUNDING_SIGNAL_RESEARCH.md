# Funding-rebound information screen — rejected

**No successful strategy found. Do not add this signal to trading.**
Negative perpetual-futures funding did not identify profitable eight-hour spot
rebounds in the specified screen. This tests a new information source, not
another moving-average setting. No new portfolio candidate was implemented.

## What was tested

The [frozen plan](FUNDING_SIGNAL_PLAN.md) specified one signal: the latest
previously published funding rate is negative. Observe it at 00:10, 08:10 or
16:10 UTC, allowing at least five minutes after the funding timestamp. Measure
the next eight-hour SPOT return. Never credit funding payments to spot holdings.
Do not trade futures, use leverage, or reverse the signal after seeing failure.

Downloaded and verified 20 official funding archives for BTC, ETH, XRP, BNB
and SOL, December 2024–March 2025: 363 records per coin. Combined them with
the existing verified spot archives. The full quarter had 1,345 scheduled asset
observations and 100% funding coverage for every coin. Negative funding occurred
in 426 observations over 85 UTC dates: BTC 35, ETH 46, XRP 105, BNB 104, SOL 136.

January–March spot outcomes had already been inspected in other research. This
is known-data screening, NOT untouched validation. No April–June 2025 or April
2026 data was downloaded or opened.

## Results: average isolated eight-hour returns

These percentages are averages of isolated hypothetical round trips, NOT
portfolio returns. Observations remain statistically correlated
across coins and time. Fees are 0.1% per side; slippage is 0.05% base / 0.15%
stress. Both sides are charged on each hypothetical observation.

| Period | Negative observations | Opportunity dates | Before costs | Base costs | Stress costs |
| --- | ---: | ---: | ---: | ---: | ---: |
| January–March quarter | 426 | 85 | -0.22% | -0.52% | -0.72% |
| January | 58 | 26 | +0.02% | -0.28% | -0.48% |
| February | 143 | 28 | -0.48% | -0.78% | -0.98% |
| March | 222 | 31 | -0.12% | -0.42% | -0.62% |

Month counts total 423, not 426: three selected quarter observations cross a
month boundary and are excluded from the corresponding self-contained month.
The quarter and its subperiods overlap; do not count them as independent trials.

All six 14-day windows had negative mean stress-cost outcomes. All six had
opportunities on at least eight dates (14, 10, 14, 14, 14, 14). These are signal
dates, not actual fills or confirmed qualifying trading days. Sufficient
activity alone does not make a useful strategy.

The negative-funding observations also underperformed the equal-weight basket
over the SAME eight-hour intervals by an average 0.072 percentage points under
stress costs. Only 34.7% of the stress-cost observations were profitable. The
worst isolated eight-hour stress outcome was -9.70% of that position's capital,
not a simulated portfolio drawdown.

## Uncertainty and verdict

The predeclared 2,000-replicate circular seven-date block bootstrap retained all
coins and intraday observations together and included zero-opportunity dates.
All 2,000 replicates were valid. Its approximate 95% intervals were:

- Mean stress-cost return: -0.924% to -0.491% per isolated observation.
- Mean basket-relative advantage: -0.151 to +0.002 percentage points.

The screen passed data coverage, sample-size and opportunity-frequency gates,
but failed profitability/relative-advantage and monthly-consistency gates.
There is no case to advance this specified rebound signal into a portfolio
implementation or open untouched validation for it. This does not prove all
funding information is useless, nor authorize selecting another threshold, time
horizon, coin subset or opposite trade from this failed screen.

Limitations: the publication lag is assumed, not reconstructed from historical
first-seen timestamps; archives can be revised; the simultaneous basket control
is not beta-matched; only one quarter is examined. Repeated hypothesis searches
and short time coverage limit statistical conclusions. There is no portfolio
cash/risk simulation here, no order netting, and no execution validation. The
seven earlier portfolio candidates remain rejected; their 440 scenario count
is unchanged. This adds one failed predictive-information screen, not a claimed
eighth executable strategy or 426 independent experiments.

## Code, verification and reproduction

- `funding_data.py`: public allowlisted archive downloader, published checksums,
  strict schema/unit/month/order validation and lagged, non-backfilling lookup.
- `funding_research.py`: isolated spot-return study, cost formula, same-time
  controls, date-block uncertainty, frozen gates and plan/source/input hashes.
- `test_funding_research.py`: 16 new offline tests. The total suite has 140
  passing tests with network connections blocked and zero connection attempts.
  Covers timestamp leakage, stale/changed intervals, checksums, bad inputs,
  future-price perturbation, costs, clustered sampling and progression gates.

No existing strategy code, engine or configuration was changed in this follow-up.
The research modules never load .env or import an account client. No private API
calls, orders, paid LLM use, EC2 changes, commits, push or deployment occurred.
Tracked summary/provenance:
`research/funding_summary.json`, `research/funding_manifest.json`. Ignored
local archives and row-level outputs: `data/funding_market/`, `data/funding_screen/`.

```bash
cd /Users/umar/Documents/my_projects/quant_hackathong_bot
PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m roostoo_bot.funding_research \
  --spot data/vol_market --funding data/funding_market \
  --output data/funding_screen_reproduction
```

The reproduction uses existing local data and makes no network calls. Use a new
output directory; reports are not overwritten. Keep normal trading disabled.
