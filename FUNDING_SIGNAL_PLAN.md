# Frozen funding-signal feasibility screen — October 2, 2026

Question: does a previously published negative perpetual-futures funding rate
identify an eight-hour SPOT rebound large enough to cover costs? This is a
predictive-information screen, not a portfolio backtest or a deployment plan.
The seven failed portfolio candidates and their gates remain unchanged.

## Rationale and limits

[Binance's funding explanation](https://www.binance.com/en-NZ/support/faq/detail/360033525031)
describes payments between perpetual-futures holders. Negative funding means
short holders pay long holders. Spot holdings receive NO funding payments.
The [BIS crypto-carry paper](https://www.bis.org/publications/working-paper-1087-crypto-carry)
links elevated futures carry with crash risk; that is not evidence that negative
perpetual funding predicts a profitable short-horizon rebound. Our rebound
hypothesis is an inference to test, not a conclusion from the paper. Funding
and dated-futures basis are not interchangeable measures.

We will use derivatives data only as public information. No futures, shorts,
leverage, funding collection or cash-and-carry/arbitrage trades are proposed.

## Data and timestamp rules

- Same five-asset basket: BTC, ETH, XRP, BNB and SOL. Current Roostoo support and
  historical spot data are already recorded; historical Roostoo listing history
  remains unverified.
- Official Binance USD-M monthly funding archives for December 2024 through
  March 2025, verified against published SHA-256 files. Schema verified using
  December BTC only before freezing this plan: `calc_time` in milliseconds,
  `funding_interval_hours`, `last_funding_rate`.
- Existing verified five-minute SPOT archives for the same months. Price
  outcomes for January–March have already been inspected in earlier research.
  This is known-data screening, not fresh out-of-sample evidence.
- Evaluate at 00:10, 08:10 and 16:10 UTC. At each time, select the latest
  realized funding record with `calc_time <= entry_time - 5 minutes`. Do not
  backfill from a later record. Require its age to be no greater than its own
  declared funding interval. Missing/stale signals are missing, not zero.
- The five-minute publication lag is an explicit conservative assumption,
  not proof of historical feed availability. It needs prospective verification
  before any implementation. Interval changes are read from each record.
- Entry is the spot open at the evaluation time. Exit is the spot open exactly
  eight hours later. All outcomes must lie strictly inside the evaluated period;
  no April spot or funding data is opened. Check aligned continuous candles,
  duplicate/invalid funding records, exact timestamps and input checksums.

## Single fixed signal, costs and controls

The one signal is `last_funding_rate < 0`. Zero is NOT negative. No sweep over
thresholds, horizons, coins, timing delays or cost assumptions. No price trend
filter will be selected after observing outcomes.

For each negative-funding observation, compute forward gross spot return and
net per-dollar return:

`exit_open * (1-slip) * (1-fee) / (entry_open * (1+slip) * (1+fee)) - 1`.

Fee = 0.001 each side; slippage = 0.0005 base or 0.0015 stress. The comparison
is cash (zero) and the equal-weight five-asset spot return over the SAME eight
hours, with the SAME cost assumption. This simultaneous basket control helps
separate asset selection from a market-wide bounce, but is not beta-matched.
No funding credit, annualized trading score or portfolio return is calculated.
Each observation represents an isolated round trip; adjacent signals have not
been netted into a continuous holding or modeled as executable portfolio orders.

## Reports and progression gates

Report quarter, individual months and six non-overlapping 14-day windows
(days 1–14 and 15–28). Report coverage, negative-signal observations, distinct
opportunity dates, per-coin counts, average/median return, basket-relative
advantage, win fraction and worst isolated outcome. Overlapping quarter/month/
window reports are not independent replication. Opportunity dates are not fills
or confirmed qualifying trading days.

For the full quarter, use a fixed-seed (20261002), 2,000-replicate circular
seven-calendar-day block bootstrap. Sample entire date blocks, preserving all
coins and intraday observations together; truncate each resample to the original
90 dates. Compute the conditional mean net return and simultaneous-basket
advantage on selected observations. Use the 2.5th/97.5th percentiles. Include
zero-opportunity dates in the sampling grid. Empty-event replicates are invalid;
require at least 95% valid replicates. This is only an approximate uncertainty
check on a short, selected research sample, not corrected proof after all prior
hypothesis searches.

Proceed to designing a frozen portfolio candidate ONLY if ALL these gates pass:

1. At least 99% funding coverage on the quarter's scheduled asset observations,
   and at least 99% separately for each coin.
2. At least 60 negative-signal observations across at least 30 UTC dates, and
   at least three coins with at least ten observations each.
3. Stress-cost mean net return and basket-relative advantage both positive,
   with their bootstrap lower bounds above zero.
4. At least two of three months have positive stress-cost conditional means.
5. At least four of six 14-day windows have opportunities on eight UTC dates.

These are feasibility requirements, not official competition rules. If a gate
fails, reject this specified signal for implementation; do not flip its sign,
relax costs, select an attractive subset, or claim all derivatives information
is useless. Do not open April–June 2025 or reserved April 2026 for this failure.
Even a pass would need a separately frozen cash/position/risk simulation and
untouched validation before any live recommendation.

## Implementation boundary

New public-data loader/downloader and isolated offline analysis only. No normal
strategy dispatcher, live configuration or engine changes. Empty-account public
requests only; no .env reading, competition keys, paid LLM calls, EC2 changes,
orders, commits, push or deployment. Preserve plan/source/data fingerprints,
row-level outputs and failures. Tests must use fake archives and no network.
