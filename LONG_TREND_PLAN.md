# Frozen monthly-horizon long/cash portfolio screen — October 2, 2026

One new candidate, not a retuning or promotion of the seven failed candidates.
Earlier trend rules used hours or a few days. [Moskowitz, Ooi and Pedersen](https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum)
study substantially longer time-series trends across futures/forwards.
[AQR's description of its historical trend study](https://www.aqr.com/-/media/AQR/Documents/Insights/White-Papers/Trend-Following-and-Rising-Rates2023.pdf)
uses 1-, 3- and 12-month horizons. These are reasons to investigate a different
time scale, NOT evidence validating this crypto adaptation or its parameters.
No borrowed performance claim, leverage, short positions or affiliation.

## One exact allocation rule

Use the fixed authorized BTC/ETH/XRP/BNB/SOL basket. At 00:05 UTC daily, use
366 actual prior UTC daily closing prices per coin, ending at 00:00. The daily
close is the close of its 23:55 five-minute candle, with valid closing timestamp.
Require every daily closing point in that 366-day calendar; never fill missing
daily closes. This price-only rule does not need intraday volume observations.
Do not import the forecast model's stricter full-day-volume requirement.

For each h in (30, 90, 365) calendar days, compute the sign of
`latest_close / close_h_days_earlier - 1`; exact zero contributes zero.
Set the coin's preliminary weight to `0.14 * max(0, mean(signs))`.
These day counts approximate the cited monthly horizons; they are not optimized.

Compute 20 daily log-return vectors from the most recent 21 prior closes.
For each vector calculate its return under the preliminary weights. Let sigma
be the population standard deviation of these 20 portfolio-return observations.
Multiply all preliminary weights by `min(1, 0.0075 / sigma)`; if sigma is zero,
use one. This is a covariance-aware estimated daily volatility budget of 0.75%,
not a guaranteed realized risk bound. No upward leverage; each asset <=14%,
total <=70%. Correlated coins are not independent bets.

Use a 0.25%-of-equity rebalance band and USD250 minimum, representing a fixed
minimum meaningful allocation adjustment, not an activity quota. Full exits
still bypass local thresholds but obey exchange precision/minimum notional.
Daily signals do not force daily trades; net holdings are resized, not closed
and reopened to manufacture activity.

Retain shared USD100,000 cash, sell-before-buy sizing, 1% cash reserve,
0.1% fees each side, 0.05% base / 0.15% stress slippage each side,
3% HKT daily stop and persistent 8% drawdown stop. Risk checks remain every
five minutes. A fresh 14-day trial starts flat with fresh risk state; there is
no reset or restart within a trial. Charge final liquidation and exclude that
forced final liquidation from activity counts. Triggers can be overshot.

## Controls, timing and implementation

Controls: cash; equal buy/hold at 70% and 100% gross; and a covariance-budget
control with preliminary weights always 14% per coin, using exactly the same
daily volatility budget, cadence, band and risk stops. That control is an
ablation, not a fallback candidate to select after failure.

The candidate/control decide at 00:05 using data cut off at 00:00, an assumed
five-minute publication lag. Fixed buy/hold benchmarks enter at the first
00:00 open as in earlier studies; they require no signal publication. Record
this five-minute entry difference. Execution is immediate at the scheduled
five-minute open plus costs, so venue latency, partial fills, bid/ask basis and
intrabar risk remain approximations. Risk, cash and sizing use shared functions.

Add an explicit offline target schedule to the portfolio simulator, guarded by
empty credentials, dry-run, disabled live trading, complete weights, caps and
source cutoff at least one bar earlier than execution. No live engine/config
integration. No schedule changes the ordinary simulator path when omitted.
Test no-schedule parity and future-price/feature perturbations before research.

## Frozen evaluation calendar and missing data

Use existing, already-inspected December2020–December2024 archives only. Verify
all checksums. Warm-up is 2021 and needed earlier observations. No downloads or
January2025 prices are needed. Universe-survivorship bias before its December2024
selection date remains; this is known-data screening, not untouched validation.

Starting January1, 2022, advance exactly 14 days through December31, 2024;
include only complete intervals ending by January1, 2025. There are 78
non-overlapping, fresh-start 14-day trials; the last four days are an unused
remainder, not a selected evaluation window. Assign a trial's year by its start.
Do not cherry-pick profitable years or restart at an adverse intermediate date.

Reject malformed/duplicate/out-of-month input. Reuse the disclosed forecast
archive rule for 29 invalid close-time records: discard the whole bar; do not
repair it. A missing intraday bar anywhere inside a trial makes that entire
trial unavailable for ALL candidate/control/cost paths. Missing required daily
close history at any scheduled decision likewise makes a trial unavailable.
Keep excluded windows and reasons in coverage counts; no forward-filled risk
marks or assumed executions. Require >=95% of the 78 scheduled trials usable.

Run all five paths under both costs in each usable trial. Save full cash/equity
and trade traces, return, drawdown, turnover, fees and UTC/HKT fill-date counts.
Do not call the aggregate of fresh-start trials a continuously traded portfolio.
Report mean/median trial return and per-year means; published ratios remain
per-trial approximations, not the organizer's verified scoring convention.

## Progression gates, fixed before calculation

Under BOTH cost assumptions require:

1. At least 75/78 trials usable (>=95%). Exclusions cannot make frequency gates
   easier: their denominators remain all 78 scheduled trials.
2. Mean trial return positive and above the covariance-only control. Require
   positive lower 95% bootstrap bounds for mean return and paired advantage.
3. At least two of three start-year mean returns positive.
4. At least 52/78 trials profitable and 52/78 with >=8 actual simulated UTC
   fill dates, without counting final forced liquidation.
5. Every candidate trial's sampled drawdown <=8%.

Use 2,000 circular two-trial-block bootstrap replicates, seed20261002, over
the full 78-slot calendar. Sample candidate and control together; preserve
unavailable slots and omit them only from within-replicate means. Truncate to
78 slots; require >=95% nonempty replicates. These intervals are descriptive
and do not correct the full project's multiple testing or remove serial risk.

Failure rejects this exact candidate without changing its horizon, sizing,
band or gates. A pass would only justify a separately frozen untouched
validation proposal; April–June2025 and April2026 stay unopened in this run.
No guarantee of profit, qualification or winning is implied by any backtest.

## Safety and evidence

Plan, source, exchange assumptions, schedule and archive fingerprints; complete
exclusion inventory; offline tests; deterministic rerun of summaries and cash/P&L
reconciliation. Original 168-scenario output must still reproduce after the
shared simulator extension. No private API/credentials, .env, news/paid LLM,
short simulations, orders, EC2, commits, pushes or deployment.
