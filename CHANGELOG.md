# Changelog

## 2026-10-04 — Python 3.9 HTTP-error compatibility hotfix

- A body-less mocked HTTP 403 caused `HTTPError.close()` to raise on EC2's
  Python 3.9, hiding the intended no-retry market-data error and failing tests.
- Close HTTP error streams only when one exists in both public candle and signed
  API clients; add a regression test for the signed client. No strategy,
  credentials, EC2 configuration, or order behavior changed.
- All 202 offline tests pass locally with network connections blocked; rerun
  the suite on EC2 before enabling any orders.

## 2026-10-04 — competition release preparation

- At the user's request after the October 4 start, selected the existing
  BTC/ETH buffered trend only as an experimental contest entry. It failed
  unseen profitability tests and is not guaranteed to meet activity rules.
- Added a guarded EC2 deployment runbook with exact parameters, read-only
  competition-account verification, two explicit order-enabling gates, and
  reconciliation/monitoring instructions. The default `.env.example` remains
  dry-run baseline to avoid silently enabling live orders on a fresh checkout.
- Verified 201 offline tests with network connections blocked and zero attempts.
  No EC2 configuration, credentials, account state, or orders changed here.

## 2026-10-02 — public-attention long/cash portfolio screen

- Froze a lagged Wikipedia-readership hypothesis before downloading eight public
  response files. All 2,254 observations pass schema/calendar checks; historical
  first-seen versions remain unverified and no live data integration was added.
- Ran 770 BTC/ETH scenarios across 77 usable fresh 14-day trials in known
  2022–2024 regimes. Mean return -0.94% base / -1.50% stress; rejected despite
  passing the activity proxy. No direction, lag or gate retuning after results.
- Added one research module and 12 tests; all 201 tests pass offline with zero
  network attempts. All 770 trade ledgers reconcile; all 770 summary rows and
  77 schedule files reproduce exactly. Existing trading/simulation
  code and previous study files are unchanged. Nine rejected configurations /
  1,980 portfolio scenarios; three prior failed information screens unchanged.
- No reserved validation, account access, orders, shorts, .env edits, EC2,
  paid LLM calls, commits, pushes or deployment.

## 2026-10-02 — monthly-horizon long/cash portfolio screen

- Froze a 30/90/365-day trend vote with covariance-aware daily risk sizing;
  evaluated the fixed five-asset universe in 78 scheduled 14-day trials.
  One trial was excluded for missing execution data, uniformly across paths.
- 770 portfolio runs completed on known 2022–2024 data. Mean candidate return
  +0.23% base / +0.15% stress, but uncertainty, consistency, activity and drawdown
  gates failed. No reserved validation opened or parameters revised.
- Added an offline-only scheduled-target interface to the shared simulator,
  preserving its normal path and risk priority; live engine/config unchanged.
- Added 14 tests; all 189 pass offline. All new summaries/schedules/verdicts
  reproduce exactly and 770 trade ledgers reconcile. Original 168 full scenario
  rows remain identical. Eight rejected configurations / 1,210 scenarios total.
- No new downloads, private APIs, credentials for research, orders, short
  simulations, .env edits, EC2 actions, paid LLM calls, commits, pushes or deployment.

## 2026-10-02 — activity/profitability measurement audit

- Reconciled 440 existing scenario rows into 96 unique candidate/cost/14-day
  intervals, removing identical aliases and rejecting contradictory duplicates.
- Distinguished simulated fill dates, entry-opportunity dates and unnetted
  hypothetical entry/exit calendars. Forecast count is 13/72 versus 23/72
  windows with eight dates, depending on proxy; neither verifies qualification.
- No gates relaxed or failed candidate rescued. Volatility momentum meets
  the date-count proxy in all six windows and loses in all six.
- Added five tests; all 175 pass with network blocked. All diagnostic results
  reproduce exactly. No existing strategy/configuration, prior result, account,
  EC2, .env, market-data download, reserved validation or deployment changes.

## 2026-10-02 — expanding-history forecast screen, no advancement

- Froze one six-feature ridge model, initial 2021 training and monthly refits
  for 2022–2024 evaluation. Downloaded 245 checksummed public spot archives.
- Before scores, audited 29 malformed close timestamps and recorded an explicit
  amendment: discard entire affected bars, preserve archives, never fill gaps.
  Original model, cost and progression gates were not altered.
- 451 selected observations averaged +0.33% base / +0.13% stress. Coverage,
  uncertainty, consistency, activity and forecast-error checks failed. No
  portfolio implementation or reserved validation opened.
- Added 17 tests; all 170 pass with network blocked and zero attempts. All
  5,475 observations, 36 model records and complete results reproduce exactly.
- Seven candidates / 440 portfolio scenarios unchanged; three information
  screens now failed progression. No existing engine/configuration changes,
  .env edits, account calls, orders, EC2 actions, paid LLM calls, commits or pushes.

## 2026-10-02 — daily trade-flow information screen

- Froze one completed-day buyer-imbalance / next-day spot hypothesis, using
  existing five-asset archives only. Strict volume/schema/checksum checks and
  lagged boundaries; no new downloads or account calls.
- Selected 147 of 445 observations across 66 UTC dates. Mean return -0.81%
  gross / -1.11% base / -1.31% stress. Profitability and monthly consistency
  failed; no portfolio implementation or untouched validation opened.
- Added 13 tests, bringing the suite to 153. All pass with network blocked and
  zero connection attempts. All observation rows and results reproduce exactly.
- Seven portfolio candidates / 440 scenarios unchanged; two failed information
  screens now recorded. No existing engine/configuration changes, credentials
  used for research, orders, .env changes, EC2 actions, commits or pushes.

## 2026-10-02 — long/short feasibility review, permission pending

- Rechecked official event rules and short endpoint documentation. Recorded
  collateral/fee distinctions and unanswered account-equity/holding-cost rules
  in SHORT_RESEARCH_PROPOSAL.md. Existing spot preflight does not verify shorts.
- Requested permission for offline long/short research only. No simulation,
  strategy, engine or account changes; no short orders or reserved data opened.
  No performance claim or additional research scenario count.

## 2026-10-02 — funding-information feasibility screen

- Froze a single negative-funding / eight-hour spot-rebound hypothesis. Added
  public, checksum-verified archive handling and lagged non-backfilling lookup.
  Downloaded 20 December 2024–March 2025 funding archives; no private APIs.
- The screen had complete coverage and 426 selected observations. Mean spot
  return -0.22% gross / -0.52% base / -0.72% stress. Profitability and monthly
  consistency failed. No portfolio candidate implemented; validation stays shut.
- Added an isolated return/cost/control analysis, date-block bootstrap and
  16 tests. All 140 tests pass offline with zero network connection attempts.
  Seven prior portfolio candidates / 440 scenarios remain unchanged; this is
  one additional predictive-information screen, not a successful strategy.
- Existing strategy/engine/config code, .env, EC2 and deployment are untouched.
  No account calls, orders, paid LLM calls, commits or pushes.

## 2026-10-02 — fixed relative-strength follow-up, still offline

- Froze one daily cross-sectional ranking rule and matched-gross breadth control;
  evaluated 100 scenarios on explicitly already-seen January–March 2025 data.
  Quarter return -0.83% base / -1.35% stress; only two of six 14-day windows
  profitable. Profitability and drawdown gates failed; validation stays sealed.
- Added pure allocation, offline-only guards, a costed 28%-invested buy/hold
  benchmark, complete-result checks and 14 tests. All 124 offline tests pass
  with network sockets blocked and zero connection attempts.
- All 100 new detailed reports reconcile to final equity. Original 168 full
  scenario rows reproduce exactly. Seven candidates / 440 scenarios including
  controls and overlapping periods; none approved. No parameter search.
- No new downloads, account calls, .env edits, orders, EC2 changes, commits,
  pushes or deployment. Source/results/docs updated only in local copies.

## 2026-10-02 — resumed spot-only search, volatility/momentum screen

- Predeclared one new slower continuous-forecast/volatility-sizing candidate,
  with an always-long volatility control and cash/buy-hold benchmarks.
- Verified the fixed five-asset universe against a pre-2025 ranking; downloaded
  checksum-verified December 2024–March 2025 public archives after freezing rules.
- Completed 100 new scenarios. The quarter lost 5.12% base / 6.15% stress; all
  six 14-day windows lost despite satisfying the activity-date proxy. Rejected
  the candidate without opening its April–June 2025 validation or April 2026.
- Added offline-only forecast/config guards and 12 tests; 110 tests pass.
  All 100 detailed reports reconcile through fixed-trade cost attribution.
  No account credentials, .env changes, orders, EC2 changes, commits or pushes.

## 2026-10-02 — readiness and public-rule recheck

- Re-read the public event page and FAQ. The old FAQ start/first-trade dates
  still conflict with the October 4 schedule; daily qualification details remain
  unresolved. Added the before-October-14 repository-link deadline and the need
  to clarify permitted operational restarts/emergency stops.
- Mapped the original requirements to current evidence in READINESS.md, keeping
  a local completed audit distinct from a validated strategy or competition win.
- Current credential values were absent from 39 locally reachable Git blobs
  and 183 local data log/JSON report/journal files. .env remains untracked.
  No secrets printed, account calls, new experiments, orders or deployment.

## 2026-10-02 — offline execution fault injection

- Added a fake order lifecycle with partial fills, locked cash, cancellation,
  completion, explicit rejection and accepted-but-lost responses across restart.
- Reproduced and fixed missing/regressing filled-quantity handling. Persist the
  highest validated fill before logging, including when logging fails.
- Conflicting failure/order-detail submit responses now remain unknown instead
  of being treated as safely rejected. No automatic retries or ID guessing.
- Added corresponding probe record validation; did not rerun the real probe.
- 98 offline tests pass. No strategy/backtest changes, new research periods,
  account queries, orders, .env edits, EC2 actions, commits or pushes.
  See EXECUTION_FAULTS.md for exact synthetic evidence and remaining limits.

## 2026-10-01 — authorized offline basket expansion

- Froze a five-asset pullback plan before opening March. Added BTC/ETH/XRP/BNB/SOL
  research only; original configured trading pairs remain unchanged.
- Added equal-weight shared-cash benchmarks, validated optional public archive
  symbols, and credential-free offline settings that BotEngine refuses to run.
- All 24 new scenario runs completed. March candidate lost 1.77% base / 2.84%
  under higher slippage; neither 14-day window met the activity proxy. Rejected
  it and did not open April. Five configurations / 240 total scenario runs now.
- Added fixed-trade cost attribution; 120 detailed reports reconcile to equity.
  Expanded the offline suite to 88 tests. Reproduced all 168 earlier portfolio
  result rows exactly; the April rejection guard also has an offline test.
  No new orders, environment changes,
  EC2 actions, competition credentials, paid LLM calls, commits or pushes.

## 2026-10-01 — explicitly approved testing-account execution check

- Fixed HMAC canonicalization: sign decoded parameter values, independently of
  form encoding. The bug was exposed by the first failed test attempt and an
  HTTP 401 on pair-specific history, then verified with successful read-only
  history after the fix. Added that read path to normal preflight.
- Preserved the failed attempt's journal; obtained fresh approval before another
  attempt. The approved second attempt bought and sold 0.00010 BTC ($8.43 buy),
  finished with no BTC/pending orders and $49,999.98 testing cash. Both fees were
  0.1% in USD. No additional test trades are authorized.
- Added a durable one-round-trip probe and regression tests; 76 offline tests
  pass. EC2, competition credentials, real .env, GitHub and the normal dry-run
  configuration are unchanged. No strategy is approved for deployment.

## 2026-10-01 — follow-up, still local and not deployed

- Corrected indicator warm-up to begin with neutral strategy state and aligned
  risk sampling with engine decision boundaries. Re-ran all 168 earlier results;
  every summary row remained identical.
- Added one predeclared pullback hypothesis, 48 separate public-data experiments,
  explicit rejection gates and provenance. It failed profitability/activity
  gates; the reserved March–April holdout remains unopened.
- Expanded to 65 offline tests, including fake-engine/simulator parity across
  strategies, risk stops, pullback entry/exit/expiry and future-data perturbation.
- No environment changes, orders, competition keys, EC2 changes or deployment.

## 2026-10-01 — local audit and research, not deployed

- Added shared BTC/ETH cash, sizing, precision, strategy and risk logic, reused by
  an execution engine and a next-open portfolio simulator.
- Added durable order intents, reconciliation blocking, per-directory locking,
  safe configuration gates, API pacing and bounded read retries.
- Added a public closed-candle signal feed with historical warm-up and validation.
  Early transport checks failed; a final combined read-only preflight passed after
  adding bounded retry. This is not a claim of deployment readiness.
- Added three predeclared strategy hypotheses, cash/buy-and-hold comparisons,
  checksum-verified data acquisition and 168 reproducible experiment results.
- Rejected all candidates for deployment. Added 55-test offline verification,
  a testing-only read preflight, an audit and a research report.
- Preserved user credentials, existing EC2 behavior and observational-only news.
  No orders, push, deployment or real environment changes were performed.
