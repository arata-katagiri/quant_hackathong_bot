# Frozen public-attention long/cash screen — October 2, 2026

One new external-information hypothesis. No short simulation or live integration.
The [2019 Wikipedia study, section 4.4](https://www.frontiersin.org/journals/blockchain/articles/10.3389/fbloc.2019.00012/full)
uses falling/equal daily views for its long leg and rising views for its short
leg. Its historical performance varied by coin and period. We test only the
long/cash adaptation, not a replication or a borrowed profitability claim.

## Data and fixed rule

Use BTC/USD and ETH/USD only, already within the authorized universe. Map to
English Wikipedia's exact `Bitcoin` and `Ethereum` titles, with `all-access`
and `user` traffic. These clear article mappings avoid adding ambiguous exchange
or protocol pages for the other three assets. No article search by performance,
redirect aggregation, alternate languages, news, model training or paid LLM.

Download daily public counts December 2021–December 2024 in eight annual/partial
annual requests, sequentially, with an identifying User-Agent and verified TLS.
Record raw bytes, SHA256, URL and actual retrieval time. Validate metadata,
UTC-midnight timestamps, strict ordering, integer nonnegative counts and bounds.
Duplicate or malformed rows abort. Missing rows or explicit zero counts make
the affected required signal unavailable, not zero attention. Do not fill them.
Hashes establish this snapshot's integrity, not historic publication time.

At 00:05 UTC on execution date D, compare counts for D-2 and D-3. If both are
positive and views(D-2) <= views(D-3), target 35% of equity in that asset;
otherwise target zero. The newer input day closed at D-1 00:00, giving a
24-hour-five-minute publication lag. Never use D-1 or D counts in that decision.
This matches the original study's next-day-closing-price timing approximately,
with a five-minute execution delay; daily counts are NOT known at their day's
start. Future observations must not change earlier signals.

A [2022 Wikimedia staff explanation](https://lists.wikimedia.org/hyperkitty/list/analytics@lists.wikimedia.org/thread/3VHDVLXIGIOYHOVAKPMOYKKWUMINSAUI/)
described overnight processing and possible cache delay. It is not a current
service guarantee. Historical first-seen versions, revisions, outages and bot
classification changes are unverified. Even a statistical pass cannot certify
point-in-time availability or justify deployment without prospective evidence.
See [API concepts](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/concepts/page-views.html)
and [access policy](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/documentation/access-policy.html).

Net existing holdings daily; do not close/rebuy an unchanged position. Fixed
0.25%-of-equity rebalance band and USD250 minimum; no activity-driven trades.
Keep USD100,000 shared starting cash, caps 35% each/70% total, 1% cash reserve,
0.1% taker fees each side, 0.05% base/0.15% stress slippage each side, five-minute
risk checks, 3% HKT daily stop and persistent 8% drawdown halt. Final liquidation
is charged but does not count as a qualifying fill date. Stops can overshoot.

## Calendar and comparisons

Reuse already-inspected 2022–2024 spot archives and December 2021 warm-up;
the existing strict loader may validate the full stored 245-archive collection,
but only BTC/ETH are traded and determine execution coverage. Preserve the
documented invalid-close-bar exclusion rule; no repair or forward filling.
Use the existing 78 nonoverlapping 14-day fresh-cash trials starting January 1,
2022; the final four days are unused. This is screening on known market regimes,
not untouched validation. New attention values do not make known prices unseen.

Exclude an entire trial for all paths/costs if any BTC/ETH execution bar or
required attention/price-control observation is missing. Keep the full 78-slot
calendar and reasoned exclusions. Report coverage before economics.

Five paths under both costs: attention candidate; price-contrarian control
(35% if close(D-2) <= close(D-3), else zero); daily constant-35%-each control;
cash; equal buy/hold 70%. Controls use identical risk, costs and rebalance bands.
The two daily controls execute at 00:05; the price control uses the same old
dates and cutoff as attention. Buy/hold enters at the first 00:00 open, as in
earlier research, and has no strategy risk stops. Disclose these differences.
No control can be promoted after candidate failure. No random-seed strategy search.

## Pre-result progression gates

Require BOTH cost settings to pass all of:

1. At least 75/78 trials usable.
2. Positive mean candidate return and positive lower 95% bootstrap bound.
3. Mean candidate return above price-contrarian control, with positive lower
   95% bound for paired advantage. Daily constant control is diagnostic only.
4. Positive mean returns in at least two of three start-year groups.
5. At least 52/78 profitable trials and 52/78 with >=8 actual UTC fill dates.
6. Every candidate trial's sampled drawdown <=8%.

Use 2,000 circular two-trial-block bootstrap replicates, seed20261002, preserving
paired missing slots over all 78 trials; require >=95% nonempty replicates.
Intervals are descriptive, not adjusted for the project's multiple experiments.
Report return, drawdown, turnover, actual UTC/HKT activity, fees and cash/P&L
reconciliation. Means of fresh-start trial returns are NOT compounded returns.

Freeze/hash this plan before fetching attention or calculating outcomes. A fail
rejects this exact candidate without reversing its direction or tuning lag,
allocation, band, dates or gates. A pass only warrants a new untouched-validation
and prospective-data protocol; April–June 2025 and April 2026 stay unopened.
Offline tests, exact rerun and ledger reconciliation precede handoff. Keep
DRY_RUN true; no .env, private APIs, shorts, orders, EC2, commits, pushes or deploys.
