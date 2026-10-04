# Expanding-history forecast screen — does not advance

**A positive sample average is not a successful strategy. No trading approval.**
The new learner produced a small positive average after estimated costs, but
uncertainty includes losses, coverage is inadequate, and consistency, activity
and forecast-quality gates fail. Do not deploy it or retune it to these results.

## What changed in the research approach

Recent information screens reused one already-inspected quarter. This study
instead used 2021 for initial training and evaluated all of 2022–2024. A small
ridge regression combined six price/volatility/volume/flow features. It refitted
monthly using only completed labels strictly before that month's start. Data
from the evaluated month's future could not enter its model or normalization.

The [original frozen plan](FORECAST_PLAN.md) fixed the six features, regularization,
training requirement, return horizon, cost-based selection threshold, periods
and gates before downloads and scores. This is a retrospective expanding-history
evaluation, not a prospective record. Later monthly models legitimately learn
from earlier completed evaluation months. There was no hyperparameter search.
The existing five-coin universe carries survivorship/selection bias before its
December 2024 selection date. Old studies and their failed gates are unchanged.

## Data fault and disclosed pre-result handling

Downloaded 245 public monthly spot archives, approximately 96 MiB, with published
checksums. The first run stopped in December 2020 warm-up before any model fit
or score: a bar's close timestamp preceded its open timestamp. A schema-only
audit found 29 invalid closing timestamps in 2,147,125 records across 29 files.

Before calculating any performance, a [data-handling amendment](FORECAST_DATA_AMENDMENT.md)
specified discarding those entire bars, never repairing their prices/timestamps
or filling the gaps. Original archives remain unchanged. The original plan
also remains unchanged; both fingerprints are required by the runner. Other
malformed fields, ordering violations and duplicates remain fatal errors.

Each coin also has 271 genuinely absent five-minute bars. Missing plus rejected
bars affect ten UTC days per coin, except XRP with nine. A feature requires 31
complete prior days; the resulting exclusions are deliberately not hidden.
There were only 911 eligible training observations at January 2022, below the
fixed 1,500 minimum. No model was available January–May 2022; June had 1,566.
This and subsequent feature gaps make overall scorable coverage only 83.38%.
The coverage gate is NOT relaxed after discovering the issue.

## Results: averages of selected isolated 24-hour observations

Entry/exit are actual 00:05 UTC five-minute opens on consecutive days. All
features end at the preceding midnight, allowing an assumed five-minute
publication lag. Fees are 0.1% each side; slippage is 0.05% base or 0.15% stress
each side. Select only when the forecast exceeds the exact stress-cost
break-even gross return. All reported realized returns are unclipped.

| Period | Scorable coverage | Selected observations | Before costs | Base costs | Stress costs |
| --- | ---: | ---: | ---: | ---: | ---: |
| Full 2022–2024 span | 83.38% | 451 | +0.63% | +0.33% | +0.13% |
| 2022 | 58.52% | 121 | -0.11% | -0.41% | -0.61% |
| 2023 | 91.48% | 168 | +0.89% | +0.59% | +0.39% |
| 2024 | 100.00% | 162 | +0.90% | +0.60% | +0.40% |

These are NOT portfolio or annual returns and cannot be compounded as if all
positions shared one dollar. The 2022 row does not represent full-year coverage.
Portfolio drawdown and turnover are undefined here; shared cash, allocation,
order netting and risk exits have not been simulated for this learner.

There are 5,475 scheduled observations, 4,565 scorable forecasts and 451
selections across 292 UTC dates. Selected counts: BTC 37, ETH 71, XRP 124,
BNB 57, SOL 162. Full-span versus subperiod denominators differ because labels
crossing each subperiod's end are excluded. The 112 reports overlap; they are
not independent trials. Opportunity dates are not fills or verified qualifying
trading days. Saved reports include all 36 months and 72 fourteen-day windows.

Only 16 of 36 months had a positive stress average, against the required 24.
Only 13 of 72 fourteen-day windows had signals on eight dates, against the
required 48. Stress win rate was 45.7%. The worst isolated stress result was
-42.18% of that position's capital, not a simulated portfolio drawdown. A risk
overlay cannot be assumed to remove that loss without testing its full effects.

The selected observations beat the same-time, same-cost equal five-coin basket
by 0.141 percentage points on average under stress. However, the fixed
2,000-replicate seven-date block bootstrap gave approximate 95% intervals:

- Mean stress return: -0.543% to +0.782% per isolated observation.
- Mean basket advantage: -0.150 to +0.466 percentage points.

All replicates were valid. Neither lower bound is positive. These intervals
also do not correct for all hypotheses already examined in this project.
The learner's mean-squared forecast error beat the available training-mean
control in only 2024, not the required two of three years. Overall MSE was
0.00154158 versus 0.00153862 for that simple control. Positive selected returns
alone do not establish superior forecasting or a dependable edge.

## Verdict and verification

Sample-size gate passed. Coverage, profitability/uncertainty, yearly/monthly
consistency, activity and forecast-quality gates failed. This exact learner
does not advance to portfolio implementation or reserved validation. Inadequate
coverage limits what can be concluded; this is not proof that all forecasting
models fail. Do not silently lengthen training, loosen coverage, change features
or lower costs to turn this particular screen into a pass.

- Added `forecast_research.py` and 17 offline tests. The suite now has **170
  passing tests**, with network connections blocked and zero attempts.
- Tests cover the regression/intercept equations, training-only scaling and
  clipping, monthly refit embargo, future-data perturbation, cost threshold,
  missing/rejected bars, archive boundaries and complete progression gates.
- A second run reproduced all 5,475 observation rows, all 36 monthly model
  records (31 fitted, five unavailable), and complete results byte-for-byte.
  Current-code provenance is in `data/forecast_screen_verified/`; the initial
  completed run is preserved separately in `data/forecast_screen/`.
- A validation-order hardening ensured other malformed fields cannot hide
  behind a rejected close timestamp. It did not change any result; both runs
  reconcile exactly. No model settings or gates changed after scores.

Tracked evidence: `research/forecast_summary.json`, `research/forecast_models.json`,
`research/forecast_manifest.json`, `research/forecast_archive_audit.json`.
All seven earlier portfolio candidates / 440 portfolio scenarios are unchanged.
There are now three information screens that failed progression, not three
new implemented strategies.

No existing engine/configuration files, trading pairs, .env or EC2 were changed.
No account credentials were used for research, no orders placed, and nothing
committed, pushed or deployed. No paid LLM was called. April–June 2025 and April
2026 remain unopened. Keep `DRY_RUN=true` and `LIVE_TRADING_ENABLED=false`.

To reproduce from the saved public archives without any network request:

```bash
cd /Users/umar/Documents/my_projects/quant_hackathong_bot
PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m roostoo_bot.forecast_research \
  --market data/forecast_market --output data/forecast_reproduction
```

Use a new output directory. No deployment or account preflight is needed to
review these offline results.
