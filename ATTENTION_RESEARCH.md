# Public-attention portfolio result — October 2, 2026

**Rejected. No strategy is ready for deployment.** Buying BTC/ETH after their
Wikipedia readership cooled did not produce a dependable advantage. Frequent
trading did not make it profitable. Do not reverse the signal, select only its
profitable year, or promote a comparison portfolio based on this result.

## What was tested

One frozen long/cash adaptation of an external-information hypothesis, not
another fit of a price indicator. The original study and timing limitations are
linked in [ATTENTION_PLAN.md](ATTENTION_PLAN.md), frozen before download with
SHA256 `83ddeef2333e6e04e8107fda7b42891e3187ebbd162073ced7cb3cb4148ea1ec`.
Its historical findings do not validate this adaptation.

At 00:05 UTC, compare each article's counts from two and three calendar days
ago. Falling/equal positive counts target 35% in that coin; rising counts
target cash. Both assets share one USD100,000 wallet. The latest count has a
24-hour-five-minute assumed publication delay. Consecutive unchanged targets
are netted, not closed and reopened. The strategy cannot short or use leverage.

The public snapshot has 2,254 observations in eight files, December 2021 through
December 2024, with no absent or zero-count days. Article, project, agent,
access, date, ordering and count checks passed. Original responses, download
URLs, retrieval timestamps and hashes are preserved in `data/attention_source`.
Historic first-seen versions remain unverified; today's snapshot is not proof
that the same counts were available on every historical decision date.

Existing price archives cover known 2022–2024 market regimes, not fresh holdout
data. Of 78 scheduled nonoverlapping fresh-cash 14-day trials, 77 were usable.
March 11–24, 2023 was excluded for a missing execution bar for every path/cost.
The last four calendar days are the protocol's unused remainder. BTC/ETH alone
determine this trial coverage; unused assets do not exclude trials.

Each usable trial ran five paths at two cost levels: **770 scenarios, not 770
independent hypotheses**. Costs include 0.1% fee each side and 0.05% base or
0.15% stress slippage each side. Candidate and daily controls share sizing,
cash limits, a 0.25% rebalance band, USD250 minimum, a 3% HKT daily loss stop
and persistent 8% drawdown halt. Final liquidation costs count; its forced
fill date does not. Risk is sampled every five minutes and can overshoot.

## Compact results

Returns below are averages of 77 separate two-week trials, not compounded
three-year returns. Activity fractions keep all 78 scheduled trials in their
denominator. Turnover is traded notional divided by starting equity.

| Path | Mean return, base | Mean return, stress | Worst drawdown, stress | Mean turnover, stress | Windows with >=8 UTC fill dates, stress |
| --- | ---: | ---: | ---: | ---: | ---: |
| Attention candidate | -0.94% | -1.50% | 8.79% | 4.93x | 67/78 |
| Price-contrarian control | -1.03% | -1.55% | 11.00% | 5.46x | 61/78 |
| Constant 35%/35% daily control | +0.44% | +0.12% | 11.10% | 2.41x | 43/78 |
| Cash | 0.00% | 0.00% | 0.00% | 0.00x | 0/78 |
| 70% equal buy-and-hold | +0.40% | +0.25% | 29.60% | 1.40x | 0/78 |

Buy-and-hold enters at the first 00:00 open without strategy risk stops; the
three daily paths first act at 00:05. Price-contrarian uses the same delayed
dates as attention. Comparisons are diagnostics, not substitute recommendations.
Cash avoids trading losses in this model but fails the activity proxy; it is
not a proposed qualifying competition strategy.

Candidate mean trial returns by start year:

| Start year | Base | Stress |
| --- | ---: | ---: |
| 2022 | -2.00% | -2.59% |
| 2023 | -0.99% | -1.51% |
| 2024 | +0.25% | -0.31% |

The candidate was profitable in only 28/78 scheduled trials at base costs and
26/78 under stress; the frozen requirement was 52/78. Median return was -0.94%
base / -1.66% stress. Its 95% block-bootstrap mean-return interval was
[-1.93%, +0.02%] base and [-2.45%, -0.51%] stress. Paired advantage over the
price control was uncertain: [-0.91, +1.04] and [-0.97, +0.97] percentage
points, respectively. These descriptive intervals do not correct the project's
multiple-testing history.

Coverage and the eight-fill-date proxy passed. Profitability, advantage,
year consistency, profitable-window frequency and drawdown gates failed.
HKT activity was 70/78 base and 69/78 stress; UTC activity was 68/78 and 67/78.
Neither timezone count proves the organizer's still-unspecified definition of
a qualifying trading day.

## It was not just fees

Holding the simulated trades fixed, the average base-cost USD100,000 trial
earned **-$190.93 from price changes**, then paid $499.89 fees and $249.94
modeled slippage: net **-$940.76**. Under stress: -$267.90 price P&L, $493.40
fees, $740.11 slippage, net **-$1,501.41**. This reconciles recorded fills;
it is not a rerun claiming what a zero-cost strategy would have done. Higher
costs can also change risk-stop timing and subsequent trades.

## Verification and files

- Added `src/roostoo_bot/attention.py` and 12 tests. The full 201-test suite
  passes with sockets blocked and zero network attempts.
- All 770 detailed trade ledgers reconcile to fees and final cash/equity.
- An independent rerun reproduced all 770 summary rows, 77 daily schedule
  files, exclusions and verdict exactly. Summaries-only mode omits duplicate
  trace writes, not calculations or controls. Source/input/settings fingerprints
  also match; only retrieval-independent run metadata differ.
- `research/attention_{manifest,summary,verdict,excluded,attribution}.json`
  preserves compact machine-readable evidence; ignored `data/attention_screen`
  retains every schedule, equity trace and fill ledger.
- No existing engine, configuration, strategy, simulator, earlier experiment
  or earlier result file was changed. Live integration was not added.

Public data download (only for a fresh local reproduction directory):

```bash
SSL_CERT_FILE=/etc/ssl/cert.pem PYTHONPATH=src python3 -m roostoo_bot.attention download \
  --output data/attention_source_reproduction
```

Offline reproduction using the preserved snapshot and archives:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m roostoo_bot.attention research \
  --market data/forecast_market --attention data/attention_source \
  --output data/attention_reproduction
```

Use a new output directory; the runner refuses to overwrite research records.
These commands do not load `.env`, access a trading account or place orders.

## Decision and remaining risks

Keep `DRY_RUN=true` and `LIVE_TRADING_ENABLED=false`. No reserved validation
was opened; April–June 2025 and April 2026 remain untouched. No new orders,
short simulations, paid model calls, EC2 changes, commits, pushes or deployment.
News remains observational. The local repository remains uncommitted.

Even a better historical result would still face snapshot revisions, missing
historical publication times, article/traffic definitions, USD/USDT price basis,
immediate-fill assumptions, intrabar moves, outages and selection bias from
repeated research. This result supplies no basis to expose the competition
account. Profit and competition qualification are not guaranteed.
