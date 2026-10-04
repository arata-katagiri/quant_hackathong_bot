# Frozen daily relative-strength screen — October 2, 2026

This is the seventh fixed candidate configuration, not an approved strategy.
The six earlier configurations remain rejected. This plan is frozen before the
new candidate is run; parameters and gates will not be changed after results.

## Rationale and limits

Fičura (2023), [Impact of size and volume on cryptocurrency momentum and
reversal](https://wp.ffu.vse.cz/artkey/wps-202301-0003.php), reports different
return dynamics for large/liquid versus small/illiquid coins, including a
relationship between proximity to weekly highs and subsequent returns. That
motivates comparing coins with each other, instead of the earlier independent
time-series forecasts. It does not validate our five-coin, daily, long-only
adaptation. We will not import reversal results for small illiquid coins into
this large-coin basket.

[Han, Kang and Ryu](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4675565)
offer contrary evidence about cross-sectional momentum under realistic
assumptions. Literature is a reason to test, not an exemption from costs or a
guarantee. We do not claim to reproduce either paper.

## Fixed decision rule

- Same previously authorized BTC, ETH, XRP, BNB and SOL spot basket and saved
  exchange-rule snapshot. Historical availability on Roostoo is unverified.
- At 00:00 UTC daily, use exactly 2,017 previously closed five-minute prices
  per asset, sampled every 12 observations: 169 hourly-spaced closes covering
  seven days. No current candle or intrabar high enters the signal.
- A coin is eligible only if its latest close is strictly above its close seven
  days earlier. Rank eligible coins by latest close / maximum of those 169
  closes, highest first. Break exact ties alphabetically by pair, a deterministic
  convention rather than a tuned preference.
- Hold at most the top two, each targeted at 14% of current equity. Unused
  allocations remain cash: at most 28% total, no shorting or leverage. The 14%
  per-coin cap is retained from the prior basket study, not optimized here.
- Daily desired positions do not imply daily orders. Keep the existing 5%-of-
  equity rebalance band and USD 250 local minimum. Full exits bypass those local
  thresholds but must obey exchange precision and strict minimum notional.
  Do not force trades to meet activity requirements.
- Controls: (1) cash; (2) equal buy/hold at 28% gross; (3) equal buy/hold at 100%;
  (4) breadth control with the same eligible set, but no ranking. The breadth
  control spreads `0.14 * min(2, eligible_count)` equally over every eligible
  asset. Its TARGET gross exposure matches the candidate at each decision;
  realized exposure, risk halts and costs may differ.
- Shared cash/sell-before-buy sizing, 1% cash reserve, 3% HKT daily stop and
  persistent 8% drawdown stop. Risk checks every five minutes. Gaps and costs can
  overshoot these triggers; stops are not guaranteed loss bounds.
- Start with USD 100,000. Signals from prior closed data, fills at next five-
  minute open. Taker fees 0.1% per side plus 0.05% adverse slippage (base) or
  0.15% (stress). Charge final liquidation; exclude it from active-date counts.

## Evaluation and sealed validation

Screen January–March 2025, using December 2024 only for warm-up. These archives
and aggregate outcomes have ALREADY been inspected for the previous candidate.
This is a new frozen rule on known screening data, NOT a new out-of-sample test.
Run the full quarter, three fresh-start months, and six fresh-start 14-day windows
(days 1–14 and 15–28 of each month). Overlapping reports are not independent
observations. Five paths times ten periods times two costs = 100 scenarios.

Require every following gate under BOTH costs:

1. Full-quarter return positive and higher than breadth control.
2. At least two of three months profitable.
3. At least four of six 14-day windows profitable.
4. At least four of six windows with fills on eight or more UTC dates.
5. Every candidate report's maximum drawdown at most 8%.

The activity count is only a proxy. Organizer daily trade count/timezone remain
unresolved. These gates are conservative screening choices, not statistical
proof or official scoring rules.

Only a complete passing screen permits unchanged April–June 2025 validation
(March warm-up), with the same ten periods and gates. Otherwise do not download
or inspect that period for this candidate. April 2026 remains reserved. Even
both-stage success would still require further untouched/prospective checks,
realistic live-input implementation, execution validation and explicit human
approval before deployment. Repeated hypothesis searches create selection bias.

## Implementation boundary

Pure allocation function, shared offline simulator, exact plan hash, inputs and
source fingerprints, complete-result checks and no-overwrite report directories.
Both the candidate and its breadth control must require empty credentials,
dry-run and offline data; BotEngine refuses offline settings. No configured
trading pairs, .env, EC2, news/LLM calls, account reads or order submissions change.
