# Daily buyer-flow information screen — rejected

**No candidate is ready. Do not add this signal to trading.** Buying after a
day of net buyer-initiated trading did not predict profitable next-day returns
in this screen. January's small positive average did not persist in February
or March. This is a failed information screen, not a new portfolio strategy.

## Fixed question and timing

The [frozen plan](TRADE_FLOW_PLAN.md) asked whether the previous complete UTC
day's buyer-initiated quote volume exceeded seller-initiated quote volume.
At 00:05 UTC, use only the 288 five-minute bars ending at 00:00, excluding the
00:00–00:05 bar. Enter hypothetically at the 00:05 spot open and measure the
open 24 hours later. Entry and exit must both fall inside each report period.

The universe was BTC, ETH, XRP, BNB and SOL. All 20 December 2024–March 2025
spot archives were already local and were checked against published checksums.
December supplies warm-up. January–March prices had already been inspected in
earlier studies: this is known-data screening, NOT untouched validation. No
new download or April–June 2025 / April 2026 validation data was opened.

Executed trade imbalance is not order-book imbalance. The paper motivating
the question uses much broader international flows; our single-exchange sign
rule is not a replication. See the plan for primary sources and the exact
volume aggregation, assumed five-minute publication lag and rejection gates.

## Results: mean isolated 24-hour returns

Each observation pays a 0.1% fee per side and 0.05% base / 0.15% stress
slippage per side. These are isolated round-trip averages, not compounded
portfolio returns. Cash earns zero in this model. The basket control holds all
five coins equally over the SAME future interval with the SAME costs.

| Period | Selected observations | Opportunity dates | Before costs | Base costs | Stress costs |
| --- | ---: | ---: | ---: | ---: | ---: |
| January–March quarter | 147 | 66 | -0.81% | -1.11% | -1.31% |
| January | 59 | 26 | +0.56% | +0.26% | +0.06% |
| February | 33 | 17 | -1.03% | -1.33% | -1.53% |
| March | 48 | 21 | -2.39% | -2.68% | -2.87% |

Coverage was 100% overall and for every coin across 445 scheduled observations
(89 eligible entry dates times five coins). Selected counts: BTC 15, ETH 22,
XRP 25, BNB 54, SOL 31. Monthly selected counts sum to 140, not 147: seven
quarter observations cross a month boundary and are excluded from the
self-contained monthly reports. Reports overlap and are not independent trials.

| 14-day window | Selected observations | Opportunity dates | Mean stress return |
| --- | ---: | ---: | ---: |
| January 1–14 | 26 | 12 | -0.91% |
| January 15–28 | 30 | 12 | +0.67% |
| February 1–14 | 15 | 8 | -0.38% |
| February 15–28 | 17 | 8 | -2.54% |
| March 1–14 | 20 | 6 | -5.01% |
| March 15–28 | 24 | 12 | -1.08% |

Only one of six windows had a positive stress-cost average. Five had signals
on at least eight dates; these dates are opportunities, not executed fills or
verified qualifying trading days. Turnover and portfolio drawdown are not
defined by this isolated-observation study.

The selected observations underperformed the same-time basket by an average
0.160 percentage points under stress costs. Only 35.4% were profitable. The
worst isolated stress outcome was -19.82% of that position's capital; do not
label this a portfolio drawdown.

## Uncertainty and rejection

The predeclared 2,000-replicate circular seven-calendar-day block bootstrap
kept all coins together, included dates without signals and truncated samples
to 90 dates. All 2,000 replicates were valid. Approximate 95% intervals:

- Mean stress return: -2.634% to -0.203% per isolated observation.
- Mean basket advantage: -0.400 to +0.061 percentage points.

Coverage, sample-size and opportunity-frequency gates passed. Profitability /
relative advantage and monthly consistency failed. Do not flip the sign,
select favorable coins, change the horizon or promote January after seeing
these outcomes. Failure rejects this specified rule, not all trade-flow ideas.
It does not justify opening untouched validation or implementing a portfolio.

Limits include an assumed rather than first-seen-verified publication lag,
revisable archives, USD/USDT proxy prices, no order netting or cash/risk
simulation, a non-beta-matched control, only one quarter and repeated hypothesis
search. The confidence intervals do not correct the entire search for multiple
testing. Even a passing screen would not establish live profitability.

## Changes and verification

- `trade_flow.py`: strict schema, timestamp, volume, checksum and alignment
  checks; completed-day feature; future-return labels; costs/control; fixed gates.
- `test_trade_flow.py`: 13 new tests covering timestamp units, invalid volumes,
  weighted aggregation, look-ahead boundaries, future-price perturbation,
  missing coverage, costs and progression guards.
- All 153 tests passed with network connections blocked and zero connection
  attempts. A second offline run reproduced all 445 observation rows and the
  complete results byte-for-byte. A separate raw-column calculation confirmed
  the first BTC feature against the December 31 archive rows.

Existing engine, strategy and configuration files were unchanged in this
follow-up. No credentials were used for research, no orders placed, no EC2 or
.env changes made, and nothing committed, pushed or deployed. Short research
permission remains pending; it is not required for this long-only screen.

Seven earlier portfolio configurations and their 440 scenarios remain
unchanged. There are now two failed information screens (funding and trade
flow); neither is counted as an implemented strategy or more portfolio runs.

Saved summaries: `research/trade_flow_summary.json` and
`research/trade_flow_manifest.json`. Ignored local row-level output:
`data/trade_flow_screen/`. Reproduce using existing local data only:

```bash
cd /Users/umar/Documents/my_projects/quant_hackathong_bot
PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m roostoo_bot.trade_flow \
  --market data/vol_market --output data/trade_flow_reproduction
```

Use a fresh output directory. Keep `DRY_RUN=true` and
`LIVE_TRADING_ENABLED=false`; these commands do not change those settings.
