# Frozen offline basket experiment — October 1, 2026

User authorization: expand offline research only. This plan is written before
downloading or opening March/April 2026 prices. The four earlier BTC/ETH
candidates are rejected, not rehabilitated by this experiment. This is one
additional hypothesis after observing previous failures, not an independent
first discovery. No parameter grid, asset substitutions or post-result changes.

## Question and fixed universe

Does spreading the unchanged pullback rule across five established coins
produce a less concentrated, sufficiently active portfolio after costs?
Diversification does not create an edge if each underlying trade loses money.

Use BTC, ETH, XRP, BNB and SOL, in that order. They were the five largest
non-stablecoin assets in the [February 22, 2026 CMC snapshot](https://coinmarketcap.com/historical/20260222/).
The selection date precedes the test periods. Public unauthenticated Roostoo
exchangeInfo checked October 1 reports all five tradable, with amount precision
5, 4, 1, 3, 3 respectively and minimum notional strictly greater than USD 1.
Today's venue availability is NOT a verified historical listing record; this
adds a survivorship/venue-selection limitation. No ranking by subsequent returns.

## Rules frozen before opening prices

Exactly the existing pullback entry, exit and cadence in PULLBACK_PLAN.md:
prior 144-close mean/population deviation, prior 576-close trend mean, 2-sigma
dip with 0.6% recovery hurdle, 15-minute decisions, frozen recovery target,
trend-break/time exits. Only completed bars inform next-open simulated fills.

One shared USD 100,000 account; 14% target cap per asset, hence 70% total target
allocation. Keep the existing 5%-of-portfolio rebalance band, USD 250 local
minimum, 1% reserve, 3% daily HKT stop and persistent 8% drawdown stop. Holdings
can drift above target between decisions. No leverage, shorts, news, extra
trades to meet activity, or parameter changes. Fully charge end liquidation.

Compare with cash, equal-weight buy/hold investing 70% total (14% each), and
equal-weight buy/hold investing 100% total (20% each). Benchmarks have no strategy
stops, as in earlier studies. Use fee 0.1% per side, slippage 0.05% base / 0.15%
stress, including buys and sells. No presumed maker discount.

## Sequential test and rejection gates

Stage 1: March 2026 full month and UTC March 1–14 / March 15–28, with February
used ONLY for indicator warm-up. BTC/ETH February outcomes were already seen;
March prices and other assets' February prices have not been opened for this
experiment. Checksums, contiguous synchronized 5-minute bars, no forward fill.

Advance only if the full month is positive under both cost cases, all three
periods have sampled drawdown at most 8%, and BOTH 14-day windows have at least
8 active UTC dates under BOTH cost cases. Each simulated non-forced fill on a
date is merely an optimistic activity proxy, not proof of organizer qualification.
Report HKT counts too. Missing or duplicate rows must fail assessment.

If stage 1 fails, stop this candidate and leave April unopened. If it passes,
open April once, with April 1–14 / April 15–28 and the exact same gates. March
is then warm-up only for each fresh April simulation. Both stages passing would
justify prospective observation, not live approval or a claim of statistical
significance. Windows within months overlap the full-month report; they are
not independent replications. January/February results from the earlier
two-asset candidate do not count as validation of this new basket.

This consumes March from the previously reserved data under a NEW plan; it
does not pretend the old pullback candidate passed its old gates. April remains
reserved unless this plan's March gates pass. These are backward historical
tests, not a future paper-trading record. Keep a manifest of plan/source/data
hashes before calculation; report every tested period, including failures.

## Strict research-only boundary

No .env load, account credentials, orders, EC2 changes, deployment, Git push,
paid LLM calls or changes to configured live pairs. Offline settings must be
rejected by BotEngine before any account access. Public data downloads do not
require credentials. Live Binance input stays limited to BTC/ETH.
