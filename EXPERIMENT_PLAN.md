# Frozen experiment plan — October 1, 2026

Defined before fetching unseen archives or running the new portfolio simulator.
No parameter search or selection using September results is authorized by this plan.

Three hypotheses: (1) original 12/48 five-minute baseline, every bar; (2) buffered
trend, 144/576 samples (12h/48h), 0.5% entry buffer, exit at fast <= slow, hourly
decisions, fixed 35% cap each; (3) 48-hour closing-price breakout, 12-hour exit
channel, 0.5% breakout buffer, hourly decisions, fixed 35% cap each. The latter two
aim to reduce turnover; their activity can be insufficient. No forced trades.

Use identical shared cash, 3% daily loss and 8% drawdown liquidation guards, 1%
cash reserve, 5% rebalance band for increases/partial trims, and exits exempt from
that band. BTC/ETH caps are 35% each. Round quantities down to public exchange
precision. Market cost assumption: 0.1% fee plus 0.05% adverse slippage per side.
Stress at 0.15% slippage per side. Simulate next-open fills after a closed-candle
signal; include final liquidation costs separately and in headline return.

Initial portfolio: $100,000. Benchmarks: cash, fully invested 50/50 buy-and-hold,
and exposure-matched 35/35 buy-and-hold plus 30% cash (purchase once, no rebalancing).
Report drawdown, gross traded notional / initial equity (one-way turnover), fees,
executions by HKT and UTC day, and research ratios from HKT daily returns. The
organizer's sampling and exact definition of enough daily trades are unknown;
one fill on a day is only an activity proxy, never a claim of qualification.

June–August and September 15–28 were already inspected, so are NOT fresh holdouts.
Fetch untouched May and September 1–14 archives, freeze configurations above, then
evaluate them once. May is a previously unseen backward holdout; September 1–14
is an unseen later-date holdout relative to June–August. Report each separately.
Also use non-overlapping 14-day windows across June–August and each untouched
period. Start each window in cash with up to 576 prior candles for warm-up when
available; explicitly label windows that have to warm up from cash. Boundaries
are UTC for reproducibility; count filled trading dates in HKT and UTC.

No deployment recommendation unless returns survive costs and stress in both
untouched periods, drawdown remains acceptable, results are not dominated by one
window, and at least eight genuinely active days are plausible. Any additional
hypothesis after seeing results needs a new holdout. A negative conclusion is a
valid outcome. Cash benchmarks do not satisfy the competition activity rule.
