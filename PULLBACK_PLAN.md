# Frozen follow-up hypothesis — October 1, 2026

Written before fetching or inspecting December 2025–April 2026 archives. The
previous three candidates failed; all May–September periods are now seen data.
No parameter sweep or adjustment after viewing this experiment is permitted.

## Hypothesis, not an established edge

Temporary selling pressure may reverse during an otherwise rising market.
De Nicola's [On the Intraday Behavior of Bitcoin](https://ledgerjournal.org/ojs/ledger/article/view/213)
reports historical intraday reversal patterns. It motivates testing a different
mechanism; it does NOT validate these rules, ETH, current market conditions or
profitability after our fees. The trend filter and thresholds below are our own
unvalidated design choices, not parameters claimed to come from that paper.

## One fixed candidate: pullback

Use completed five-minute BTC/ETH candles. Decide every 15 minutes. Before the
latest close, calculate the mean and population standard deviation of the prior
144 closes (12 hours) and the mean of the prior 576 closes (48 hours).

When inactive, enter only when all are true:

1. The 12-hour mean exceeds the 48-hour mean, and latest close exceeds the 48-hour
   mean (uptrend filter; this can skip most opportunities).
2. Latest close is at least two short-window standard deviations below the
   12-hour mean; standard deviation must be positive.
3. A return to that mean would gain at least 0.6% before costs: twice the baseline
   round-trip fee/slippage estimate. This is a hurdle, not an expected return.

Freeze that mean as the signal's recovery target. Exit on the first decision at
or above that target, at or below the current 48-hour mean, or 144 bars after the
entry signal (12 hours). Do not re-enter on the same decision that exits. Time is
measured from signal activation, not an assumed exchange fill. Persistent signal
state is shared by simulation and the engine; do not invent pre-start positions
while warming indicators. A new simulation starts cash and neutral signals.

Use unchanged 35% per-asset caps, shared $100,000, 1% cash reserve, 5% rebalance
band, $250 local minimum, exchange precision/minimums, 3% daily HKT stop and 8%
persistent drawdown stop. Risk exits override the strategy. No forced activity.
Base fee/slippage: 0.1%/0.05% each side; stress slippage 0.15%, fee unchanged.
Benchmark cash and buy/hold 35/35 and 50/50; include final liquidation costs.

## Data and sequential stopping rule

First evaluate January and February 2026 separately, plus four UTC 14-day windows:
Jan 1–14, Jan 15–28, Feb 1–14 and Feb 15–28. December 2025 is warm-up only.
Download official checksum-verified files to a separate directory. These are
previously unseen BACKWARD historical tests, not a genuinely future live test.

Reject without opening March–April if either full month is non-positive after
stress costs, any window breaches 8% sampled drawdown, or fewer than three of the
four windows show eight active UTC dates. A fill on a date is only an activity
proxy, not confirmed qualification. Report base/stress returns, drawdown,
turnover, fees, fills, and both HKT/UTC date counts. Do not loosen gates to pass.

Only if all preliminary gates pass, open March–April once with identical rules,
require positive stressed return in each month and at least three of four
14-day windows showing eight active UTC dates; then still require prospective
observation and separately authorized execution validation before deployment.

No orders, deployment, competition credentials, .env edits or paid LLM calls are
part of this experiment. Baseline configuration and DRY_RUN remain unchanged.
