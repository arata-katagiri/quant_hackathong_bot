# Combined BTC/ETH portfolio study — October 1, 2026

**Verdict: no candidate is ready.** The slow trend's attractive June–August result
does not survive the untouched periods, and breakout trades too rarely. This study
improves measurement and execution safeguards; it does not establish a profitable
competition strategy.

## Protocol and provenance

[EXPERIMENT_PLAN.md](EXPERIMENT_PLAN.md) fixed three hypotheses before the new
archives were downloaded or results inspected. All 64 BTC/ETH archives passed the
[official Binance](https://github.com/binance/binance-public-data) SHA-256 checks.
They span May 1–September 28, 2026, continuously at five-minute intervals. Post-2025
spot timestamps are microseconds. Inputs, settings and the plan hash are in
`data/research_v2/manifest.json`; all 168 runs are in `results.json` with detailed
full-period equity/fill traces in subdirectories.

The reviewable `research/summary.json` snapshot contains all 168 summary rows;
`research/manifest.json` records archive checksums, frozen settings, the plan hash,
and source-file hashes. A final rerun reproduced every result exactly. These are
local files, not a pushed or deployed release.

Follow-up correction: historical warm-up now initializes indicators without
hypothetical active signals, and risk observations occur at engine execution
boundaries. All 168 result rows remained identical after rerunning. Corrected
traces are in `data/research_v2_corrected`; the original manifest is retained as
`research/original_v2_manifest.json`. A distinct fourth hypothesis is documented
in [PULLBACK_RESEARCH.md](PULLBACK_RESEARCH.md), not mixed into this original study.

May and September 1–14 were unseen before this study. May is a backward holdout;
September 1–14 is later than the June–August development period. June–August and
September 15–28 had already influenced prior research and are NOT clean holdouts.
The small number of untouched regimes limits the strength of any conclusion.

Both assets share $100,000, 35% asset caps, a 1% cash reserve, a 5% rebalance band,
a 3% daily HKT stop, and an 8% persistent drawdown stop. Exits bypass the local
minimum/band but obey exchange minimums. Decisions use only observed closes;
fills occur at the following open. Base costs are 0.1% fee plus 0.05% adverse
slippage per side. Stress triples slippage to 0.15%. Headline returns include
estimated final liquidation costs. Prices are Binance USDT proxies.

The baseline decides every five minutes with its original 12/48 rule. Buffered
trend uses 12h/48h averages, a 0.5% entry buffer, exit at fast <= slow, and hourly
decisions. Breakout buys above the prior 48h closing high plus 0.5%, exits below
the prior 12h closing low, and decides hourly. Both new candidates use fixed 35%
active weights. Parameters were not retuned after seeing results.

## Full-period results after base costs

Each cell is **return / maximum sampled drawdown**, in percent.

| Portfolio | May, unseen | Jun–Aug, seen | Sep 1–14, unseen | Sep 15–28, seen |
| --- | ---: | ---: | ---: | ---: |
| Baseline | −7.80 / 8.07 | −8.27 / 8.32 | −7.11 / 7.24 | −5.65 / 5.70 |
| Buffered trend | −2.49 / 5.18 | +12.83 / 7.05 | −4.08 / 5.72 | +1.18 / 3.59 |
| Breakout | +0.44 / 0.99 | +6.80 / 3.47 | −2.20 / 2.28 | 0.00 / 0.00 |
| Cash | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Buy/hold 35% BTC + 35% ETH | −5.30 / 10.85 | +10.12 / 15.87 | +0.30 / 3.87 | +4.56 / 4.07 |
| Buy/hold 50% BTC + 50% ETH | −7.58 / 15.17 | +14.46 / 22.66 | +0.42 / 5.47 | +6.51 / 5.64 |

Benchmarks purchase once and do not rebalance or use the strategy risk guards.
Cash and buy/hold are comparisons, not activity-compliant entries. The baseline's
three-month result stops after its drawdown guard trips; it is not a full-period
active strategy. Its changed result versus the old report reflects shared capital,
functional risk exits and persistent stopping, not a recovered trading edge.

## Unseen September 1–14: turnover and activity

| Portfolio | Base return | Stress return | One-way turnover / capital | Strategy fills | Active HKT dates |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline | −7.11% | −8.13% | 47.02× | 337 | 15 |
| Buffered trend | −4.08% | −4.55% | 4.81× | 12 | 11 |
| Breakout | −2.20% | −2.27% | 0.68× | 2 | 2 |
| Cash | 0% | 0% | 0× | 0 | 0 |
| Buy/hold 35/35 | +0.30% | +0.16% | 1.40× | 2 | 1 |
| Buy/hold 50/50 | +0.42% | +0.22% | 2.00× | 2 | 1 |

Turnover is gross purchased + sold notional divided by initial capital, including
end liquidation. Activity excludes forced end liquidation. UTC-bounded 14-day
windows touch 15 HKT dates; the report includes both UTC and HKT counts. A date
with one fill is only a proxy; the organizer's "enough trades" condition is unknown.

## Ten non-overlapping 14-day windows

Two May windows, six June–August windows and two September windows. These aggregate
seen and unseen periods, so this table is descriptive rather than pure out-of-sample
evidence. All start in cash and use available earlier history for warm-up.

| Portfolio | Positive windows / 10 | Median return | Windows with ≥8 active HKT dates / 10 |
| --- | ---: | ---: | ---: |
| Baseline | 1 | −7.46% | 9 |
| Buffered trend | 5 | +0.15% | 5 |
| Breakout | 2 | 0.00% | 0 |
| Cash | 0 | 0.00% | 0 |
| Buy/hold 35/35 | 6 | +1.33% | 0 |
| Buy/hold 50/50 | 6 | +1.89% | 0 |

Buffered trend's +15.82% August 10–23 window dominates its apparent success;
it traded on only four HKT dates in that window. Its May return falls to −3.38%
under stress costs. This is insufficient for a live recommendation.

Ratios use complete HKT daily returns, zero assumed risk-free rate and 365-day
annualization; incomplete first/last days are excluded from Sharpe/Sortino.
Calmar uses annualized total return divided by sampled maximum drawdown. Short
sample annualization is unstable, and official sampling conventions are unknown;
we do not claim these are official scores. Drawdown is sampled at five-minute
closes and can miss intrabar extremes.

## Next research decision

Reject the fast baseline; do not tune the two slow candidates to these holdouts.
Further research should introduce a distinct, economically motivated hypothesis
and reserve additional unseen data before evaluation. Execution integration can
be tested separately only with explicit authorization for actual test orders.
News stays observational; no timestamp-correct predictive evaluation exists yet.
