# Frozen spot-only volatility/momentum study — October 2, 2026

The user resumed the goal: continue until a successful strategy is found. All
five earlier configurations remain rejected. This is a new offline hypothesis,
not permission for orders, shorting implementation, deployment or .env changes.
The plan is frozen before opening the 2025 evaluation archives. No grid search,
asset substitutions or changes after observing this study's returns.

## Rationale and controls

Test a slower, continuous momentum allocation with volatility-based sizing,
rather than a binary intraday signal. Liu and Tsyvinski's
[Risks and Returns of Cryptocurrency](https://www.nber.org/papers/w24877)
motivates investigating historical crypto momentum; it does not validate our
horizons or today's profitability. Kim, Tse and Wald's
[Time series momentum and volatility scaling](https://www.sciencedirect.com/science/article/pii/S1386418116301379)
warns that scaling can explain apparent timing benefits. Therefore an always-long
volatility-sizing control is mandatory. Our precise parameters are design choices,
not claimed to have been established by either paper.

Use BTC/ETH/XRP/BNB/SOL, the five largest non-stablecoins in the
[December 29, 2024 snapshot](https://coinmarketcap.com/historical/20241229/).
They also match the already authorized, currently Roostoo-supported basket.
Historical Roostoo availability is unverified: venue-survivorship limitations
remain. Use the saved October 1 quantity precision/minimum assumptions, not
unknown historical exchange rules.

## Exact candidate

Every six hours (UTC 00:00/06:00/12:00/18:00), use only prior completed five-minute
closes. Obtain 169 hourly-spaced closes from the last 2017 five-minute closes.
Compute 168 hourly log returns and daily volatility
`v = max(0.005, population_std(hourly_log_returns) * sqrt(24))`.

For horizons h = 1, 3, 7 days, compute
`z_h = log(latest_close / close_h_days_ago) / (v * sqrt(h))`.
Set `forecast = clip(mean(z_1, z_3, z_7), 0, 1)`.
Set `risk_weight = 0.14 * min(1, 0.02 / v)` and
`target_weight = risk_weight * forecast` independently for each asset.

The 0.5% daily-volatility floor prevents division by zero/unstable sizing. The
2% reference volatility reduces holdings in turbulent markets; it is not a
guaranteed portfolio volatility target. Five correlated coins are not five
independent bets. Portfolio target investment never exceeds 70%; no leverage.

Use shared cash USD 100,000; existing exchange flooring, free-cash safeguards,
1% reserve, USD 250 minimum, 3% HKT daily stop and persistent 8% drawdown stop.
Change the rebalance band for this candidate only to 0.5% of equity, so genuine
changes in continuous risk forecasts can alter holdings. This is not an activity
quota. Exit signals still bypass the local band/minimum. Risk is checked every
five minutes; orders fill at next open plus costs, final liquidation included.

Fee: 0.1% per side. Slippage: 0.05% base and 0.15% stress per side. Compare with
cash, equal buy/hold 70%, equal buy/hold 100%, and a volatility-only control using
the same risk_weight, cadence, band and risk stops but forecast=1. The control
is an ablation, not a second candidate to select if the candidate fails.

## Sequential data protocol

Stage 1: January–March 2025 full quarter, each of its three months separately,
and six fresh-start 14-day windows: days 1–14 and 15–28 of each month. December
2024 is indicator warm-up only. These prices have not been inspected in this
project, but are retrospective historical data, not a future record.

Screening gates, all required under both cost cases:

1. Full quarter return > 0 and above the volatility-only control.
2. At least two of three individual months return > 0.
3. At least four of six 14-day windows return > 0.
4. At least four of six windows have >= 8 active UTC dates.
5. Sampled maximum drawdown <= 8% in every candidate report.

Passing only allows Stage 2, April–June 2025, with identical settings, monthly
windows and gates. March 2025 becomes warm-up only for each fresh simulation.
Never fit or change parameters between stages. Stop the candidate when a stage
fails. All evaluated rows, including controls and failures, must be saved.

If both stages pass, propose an unchanged final test on the still-unopened
April 2026 period, with its own published protocol BEFORE opening that data.
This plan does not automatically consume April 2026. A promising retrospective
candidate still needs prospective observation and user-approved operational
validation; simulated profitability is not guaranteed live success.

These are screening rules for this new mechanism, not relaxed claims that old
candidates passed their old gates. Monthly/fortnight windows overlap full-quarter
reports and are not independent replications. More research increases selection
bias; do not assign a significance level from these few screens. Activity is
only an optimistic executed-fill-date proxy while organizer details are unknown.

## Reproducibility and safety

Use public checksum-verified Binance spot archives, aligned continuous five-minute
timestamps, no forward filling. Preserve original studies. Record plan/source/
input hashes before computation. Require a full passing prior-stage report before
loading Stage 2. Offline settings must have no keys and be rejected by BotEngine.
Live configuration, default strategy and configured pairs remain unchanged.
