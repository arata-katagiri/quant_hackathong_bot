# Frozen expanding-history forecast screen — October 2, 2026

This is one new, long-only offline information hypothesis. Prior failed rules
stay rejected; their gates and results are not revised. Several recent screens
reused January–March 2025. That narrow regime is not sufficient for selecting
another approach. This study instead evaluates three full earlier calendar
years, including all months, without choosing periods based on computed scores.

## Hypothesis and scope

A small regularized linear model may combine short-term reversal, longer trend,
volatility and trading-flow information better than independent sign rules.
It must forecast returns large enough to cover costs, not merely forecast the
direction correctly. [Bysik and Slepaczuk's cost-aware forecasting study](https://arxiv.org/abs/2606.00060)
motivates evaluating costs and sequential training, but uses different models
and data. Our six-feature ridge model is not a replication or validated by it.
No neural network, LLM, paid data or hyperparameter search is involved.

Use only the previously authorized BTC, ETH, XRP, BNB and SOL spot universe.
This fixed currently-supported universe has survivorship/selection bias when
applied before its December 2024 selection date. Do not claim a historical
investable universe or generalize to all coins. Do not swap assets after results.

## Data and point-in-time boundaries

Download official checksum-verified Binance five-minute monthly spot archives
from December 2020 through December 2024, 245 files. December 2020 is feature
warm-up; 2021 is initial training only. Evaluate January 2022–December 2024.
These are retrospective historical evaluations, not a prospective live record.
No January–March 2025 results enter fitting or selection in this study. The
reserved April–June 2025 and April 2026 periods stay unopened.

The [official archive format](https://github.com/binance/binance-public-data)
defines quote volume, taker-buy quote volume and timestamp units. Parse exact
schema, OHLC/volume validity, timestamp units, file-month membership and order.
Reject duplicates or malformed records. Record missing five-minute bars by day;
never forward-fill them. A feature needs 31 complete contiguous prior UTC days.
A day with zero quote volume is unavailable. Missing entry/exit prices make an
observation unscorable. Report these exclusions rather than silently dropping
them from the coverage denominator.

At 00:05 UTC each day, use data ending at 00:00 (five-minute assumed publication
lag). Features use only the previous 31 complete UTC days, not the current day's
00:00–00:05 bar. Entry is the actual 00:05 open, label exit the next day's 00:05
open. Last-day labels outside a report period are excluded. No terminal January
2025 archive is opened to label December 31, 2024.

## One fixed learner

Six features for each coin, computed from the completed daily closes/volumes:

1. One-day log return.
2. Seven-day log return.
3. Thirty-day log return.
4. Population standard deviation of the last 20 daily log returns.
5. Log of last day's quote volume / mean of the preceding 20 days' quote volumes.
6. Last day's `(2 * taker_buy_quote - total_quote) / total_quote`.

At 00:00 UTC on the first of each month, refit using all eligible observations
from January 2021 whose label exit is STRICTLY earlier than that fit time.
At least 1,500 training observations and 300 distinct entry dates are required;
otherwise no forecast that month. Save sample counts, maximum training exit,
feature means/scales, coefficients and intercept for every model.

Pool all five coins equally per observation, without asset identifiers. Standardize
features using training-only population means and standard deviations; a scale
below 1e-12 becomes one. Clip standardized features to [-5, 5] in both fitting
and prediction. Clip TRAINING gross-return labels to [-0.20, 0.20], never realized
evaluation returns. Fit an unpenalized intercept and ridge coefficients minimizing
`mean((y - intercept - z @ beta)^2) + 0.1 * sum(beta^2)`.
No model, feature, regularization, timing, horizon or threshold tuning.

Select an isolated long observation only when its predicted gross return exceeds
the exact break-even gross return for 0.1% fees and 0.15% adverse slippage on EACH
side: `(1.0015 * 1.001) / (0.9985 * 0.999) - 1`. Equality is not a signal.
No shorts or orders, and no quota-driven selections. This is an information
screen; fitting a regression is not approval to integrate it into the engine.

## Evaluation and controls

For every scheduled coin/day, save feature availability, labels, forecast,
selection, and base/stress isolated round-trip returns (same verified formula
as previous screens). Base slippage 0.05%, stress 0.15%; fees 0.1% per side.
Compare cash, the same-time equal five-coin basket, and forecast mean-squared
error against zero and the available training mean (unclipped training mean for
that control). Basket-relative results require all five labels on that date.

Report the full 2022–2024 span, each year, 36 months and 72 self-contained 14-day
windows (days 1–14 and 15–28). Counts are not independent experiments. Feature
coverage includes unscorable observations in the denominator. Opportunity dates
are not fills or confirmed qualifying trading days. Do not report portfolio
return, turnover or drawdown from this isolated-observation screen.

On the full span, use a 2,000-replicate circular seven-calendar-day block
bootstrap, seed 20261002, keeping coins together and including no-signal dates.
Report 95% intervals; these do not correct the whole project's repeated search.
All following gates are required before any new portfolio design:

1. Scorable forecast coverage >=95% overall and per coin, >=90% in each year.
2. At least 300 selections on >=150 dates, >=3 coins with >=50 selections each.
3. Mean stress return and same-time basket advantage positive, their bootstrap
   lower bounds positive, and >=95% of bootstrap replicates nonempty.
4. Positive stress mean in at least two of three years and 24 of 36 months.
5. At least 48 of 72 windows have opportunities on eight dates.
6. Forecast MSE beats the training-mean control in at least two of three years.

Failure rejects this exact learner for progression; no new threshold or feature
choice based on outcomes. A pass allows proposing a separately frozen portfolio
test and untouched validation, not opening them automatically or claiming success.
Live-input implementation, risk/cash/fill accounting and prospective observation
would still be required. No EC2, .env, private API, order, deployment or Git push.

## Verification requirements

Test label embargo and month boundaries, train-only normalization, future-data
perturbation, clipping, ridge/intercept algebra, cost threshold, missing-day
coverage, checksums/schema and complete-result gates. Save plan/input/source
fingerprints and reproduce predictions/results with network connections blocked.
