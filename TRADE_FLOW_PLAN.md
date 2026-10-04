# Frozen daily trade-flow information screen — October 2, 2026

This stays inside the authorized long-only, five-asset offline research scope.
Long/short permission remains pending and is not required for this test. No
existing failed strategy is retuned or promoted, and no live strategy is added.

## Hypothesis and source limitations

[Anastasopoulos et al., Order flow and cryptocurrency returns (2026)](https://doi.org/10.1016/j.finmar.2026.101047)
reports predictive evidence using international order flows and a broad coin
sample. Our Binance-USDT-only daily measure is an adaptation, not a reproduction
of that study or its nonlinear forecasting models. A relationship with a price
change during the SAME period is not a tradable forecast of the next period.

[Binance's public archive schema](https://github.com/binance/binance-public-data)
contains total quote volume and taker-buy quote volume. Subtracting taker-buy
volume from total volume gives seller-initiated quote volume. This measures
executed trade imbalance, not limit-order-book additions/cancellations.

The one hypothesis: positive buyer-initiated net trading over a completed day
predicts a positive NEXT-day spot return sufficient to pay transaction costs.
Do not choose a threshold, opposite sign, horizon or asset subset after results.

## Fixed data and timing

- BTC, ETH, XRP, BNB, SOL; existing checksum-verified December 2024–March 2025
  five-minute spot archives only. December is warm-up. January–March spot price
  outcomes have already been inspected, so this is known-data screening.
- At 00:05 UTC daily, use the 288 bars of the previous complete UTC day, ending
  at 00:00. The five-minute publication lag is assumed, not verified historical
  first-seen availability. Exclude the just-completed 00:00–00:05 bar.
- Compute `imbalance = (2 * sum(taker_buy_quote) - sum(total_quote)) /
  sum(total_quote)`. Select the observation only when imbalance is strictly
  positive. A balanced day is not a buy signal. Zero total volume is missing
  information, not a zero-valued signal.
- Enter at the 00:05 spot open and measure the open exactly 24 hours later.
  Entry and exit must lie strictly within the report period. Therefore the last
  calendar day of each self-contained period cannot supply a labeled observation.
  Do not open April data to complete its label.
- Validate checksums, OHLC, exact five-minute alignment, complete timestamps,
  finite/nonnegative base and quote volumes, and taker buys no larger than total.
  Up to 1e-8 units of independent CSV volume rounding is tolerated and clamped;
  larger inconsistencies fail. Require each feature to contain exactly 288
  contiguous bars. Missing data must not be forward-filled.

## Outcomes, controls and uncertainty

Measure an isolated long spot round trip, not a portfolio return. Reuse the
verified return formula from the funding screen: 0.1% fee per side plus adverse
slippage of 0.05% base / 0.15% stress. No funding payments, shorts or leverage.
Compare cash and the equal-weight five-asset basket over the SAME future day,
using the same costs. Report gross, base and stress mean/median return, win
fraction, worst isolated outcome and basket-relative advantage.

Report the quarter, three months and six 14-day windows (days 1–14 / 15–28).
Report available scheduled asset observations, feature coverage, selected counts,
distinct opportunity dates and per-coin counts. Dates are not executed fills or
verified qualifying days; subperiod reports overlap the quarter.

For the quarter use the same 2,000-replicate circular seven-calendar-day block
bootstrap, seed 20261002, on a 90-date grid. Keep all coins together within dates,
include zero-opportunity dates, and truncate sampled blocks to 90 dates. Require
at least 95% nonempty replicates. Report 2.5th/97.5th percentile intervals for
mean stress return and basket-relative advantage. The small time sample,
cross-coin dependence and repeated hypothesis search remain limitations.

## Fixed progression gates

All must pass before designing a portfolio implementation:

1. Quarter feature coverage at least 99% overall and for every coin.
2. At least 60 selected observations across at least 30 UTC dates; at least
   three coins with at least ten observations each.
3. Quarter mean stress return and same-time basket advantage positive, with
   both bootstrap lower bounds above zero and enough valid replicates.
4. At least two of three monthly mean stress returns positive.
5. At least four of six 14-day windows with opportunities on eight dates.

Failure rejects this specified signal for implementation; it does not disprove
all order-flow research. Do not flip its sign, select favorable coins, weaken
costs or relabel a profitable subset as success. No April–June 2025 or April 2026
validation is opened for a failure. A pass only justifies a new frozen portfolio
study, not a live recommendation or a successful-strategy claim.

## Boundaries and evidence

New strict volume loader and isolated offline analysis only. Existing engine,
configuration, trading pairs, .env, EC2 and account permissions remain unchanged.
No private API calls, new market downloads, paid LLM use, orders, commits or
pushes. Save the plan hash, source/input fingerprints, row-level observations
and complete results. Tests must cover lag boundaries, future-data perturbation,
volume integrity, costs, missing coverage and progression gates without network.
