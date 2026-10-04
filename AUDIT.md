# October 1 audit

## Verified rules and unresolved details

The [official event page](https://luma.com/coghwiyt) states October 4–17, $100,000
initial capital, and at least eight active strategy-trading days. The user also
confirmed a newer October 4 announcement. Its screening order is compliance,
top-20 regional portfolio return, then 0.4 Sortino + 0.3 Sharpe + 0.3 Calmar, then
code review. Advertised taker/maker fees are 0.1%/0.05%; a marketable limit order
can be a taker, as the later testing round trip demonstrated. Automated execution and traceable
commits are required; HFT, market making, arbitrage and leverage are prohibited.

The [official FAQ](https://roostoo.notion.site/Roostoo-Quant-Trading-Hackathon-Official-FAQ-313ba22fed798042bab7c93c609d004e)
was read in the browser on October 1. It confirms 30 API calls/minute including
queries, Binance-sourced quotes, ticker-only market data, automatic end liquidation,
and no manual trading. Its September 30/October 1 dates conflict with the event
page and the user's newer announcement; use October 4 as the working date.

Still not specified: how many strategy trades make a day qualify; which timezone
defines such a day; exact first-trade deadline under the updated schedule; official
return sampling, risk-free rate and ratio annualization. Ask organizers to clarify
these. One fill per calendar day in research is only an activity proxy.

October 2 public recheck: the schedule conflict and missing activity/metric
details remain. The event also requires the repository link before October 14.
FAQ Q28's ban on manual stops needs clarification alongside its permission for
code updates and redeployment. See READINESS.md for the completion audit; no
new account calls or orders were used for this rules review.

[Official API documentation](https://github.com/roostoo/Roostoo-API-Documents)
defines quantity precision and a strict `price * quantity > MiniOrder` test.
Unauthenticated `/v3/exchangeInfo` on October 1 returned BTC precision 5, ETH 4,
minimum $1 each, both tradable. Public `InitialWallet` is $50,000 and describes
the general test setup, not the event's announced capital. Authenticated read-only
testing confirmed SpotWallet parsing, $50,000 equity and zero pending orders.
No competition key was used. The initial audit was read-only; a subsequent
explicitly approved test-order attempt is documented in
[EXECUTION_VALIDATION.md](EXECUTION_VALIDATION.md). The docs' legacy fee examples
are not used as event fee estimates.

## Findings and implemented responses

| Severity | Original issue | Local change |
| --- | --- | --- |
| Critical | Buy size could exceed free cash or reuse locked cash | Shared portfolio sizing reserves fees, adverse price allowance and 1% cash; refreshes actual wallet after each confirmed fill |
| Critical | Lost submit response/restart could create another order | Intent fsynced before submission; no submit retries; unknown outcome blocks further orders pending review |
| Critical | HMAC signed encoded pair values, contrary to official demo | Sign sorted decoded values separately from form-encoded transport; real pair-history read now succeeds; preflight exercises this path |
| High | Partial/pending orders treated as complete | Query known order ID; require recognized terminal status and matching identity/quantity; block new orders while pending |
| High | Later inconsistent reports could erase partial-fill progress | October 2: require explicit filled quantity, persist cumulative high-water mark before logging, reject regressions across restart |
| High | Failure flag could override conflicting order acceptance evidence | October 2: failure responses containing order details remain unknown; keep durable intent and block automatic resubmission |
| High | Fixed six decimals violated current pair rules | Fetch exchange rules hourly; Decimal floor rounding; validate tradability and exchange minimum |
| High | Loss circuit breaker blocked the sale needed to reduce risk | Risk guards target zero exposure; exits bypass strategy rebalance band; daily and drawdown stops latch |
| High | Two bot processes or repeated --once could duplicate decisions | Nonblocking file lock and persisted processed bucket |
| High | Untimestamped samples compressed outages into normal history | Five-minute boundary scheduling, late-sample rejection, gap reset, separate v2 state |
| High | Live ticker snapshots did not match historical candle signals | Default public Binance closed-candle input with immediate historical warm-up, continuity checks and no silent fallback; Roostoo quotes still govern sizing |
| High | Misspelled DRY_RUN silently enabled orders | Strict boolean parsing; additional default-off live gate; client itself blocks orders by default |
| High | Single-asset results did not model shared cash or risk limits | New synchronized portfolio simulator reuses strategy, sizing, precision and risk functions |
| Medium | API calls had no pacing/recovery policy | 2.5-second request spacing; bounded retries/backoff for reads; fresh timestamps per attempt |
| Medium | Wallet arithmetic ignored locked holdings/unpriced assets | Include locked spot balances in equity; reject unknown nonzero holdings and nonfinite data |
| Medium | Old backtest accepted NaN/invalid OHLC | Validate price bounds, timestamps, gaps, duplicates, complete candles and asset alignment; verify archive checksums |
| Medium | Failure exit code always zero; API error text could echo values | Nonzero one-shot failure code; API errors log status/type rather than raw response bodies |
| Low | CoinDesk failure had no HTTP status | RSS failure now includes numeric HTTP status; other sources continue |

## Evidence

Offline tests cover shared cash, locked assets, decimal floor/minimum checks, small
exits, daily stop reset and persistent drawdown stop, corrupt/unknown inputs,
duplicate buckets, stale quotes, missed samples, process lock, submit timeout after
restart, partial fills, pending orders, API read retry pacing, default client
submission block, and future-price perturbation. A deterministic fixture also
compares the simulator's order sequence with the execution engine using a fake
exchange when next-open equals the prior close. This proves that fixture, not all
real exchange behavior.

The Roostoo-only read-only preflight succeeded with testing credentials. The later
combined check failed twice at the public candle feed with `URLError`, while a
separate public-data check retrieved and validated 577 candles for each asset.
After adding one bounded retry for public transport failures, the final combined
preflight passed: testing equity $50,000, no pending orders, and 49 valid closed
candles for each pair. This point-in-time pass does not establish feed reliability;
repeated observation on the deployment host is still required. Latched risk exits
skip candle requests entirely. The follow-up suite has 65 passing offline tests,
including fresh-start engine/simulator parity and pullback state transitions.
The later execution/signing suite expands this to 76 offline tests; these use
fake clients and dummy keys and do not change `.env` or contact Roostoo. Separately,
the explicitly approved BTC test round trip filled and reconciled both legs,
ending with $49,999.98 cash, no BTC and no pending orders. See the execution report
for the exact scope and the initially failed signing attempt.

October 2 follow-up: [EXECUTION_FAULTS.md](EXECUTION_FAULTS.md) documents ten new
offline fault-injection tests, bringing the suite to 98. The fake exchange now
changes cash, locks and holdings during partial-fill lifecycle tests. These
fixtures do not establish real backend partial-fill/cancellation behavior.

## Remaining risks / deployment gate

* No candidate has passed unseen-period profitability and activity checks.
  The separately frozen pullback and authorized five-asset basket both failed.
  March was consumed under the new BASKET_PLAN.md; April remains unopened.
  Historical warm-up no longer invents pre-start active signals.
* A BTC filled buy/sell and USD fee denomination are now verified on testing.
  ETH orders, actual partial fills/cancellations, maker fees and accepted-but-lost
  submit responses remain unverified. One success does not establish reliability.
* Unknown submission without an ID cannot be safely matched automatically: the
  API documents no client-order idempotency key. The engine conservatively blocks.
* The guard samples every five minutes; price gaps, unavailable markets and wide
  spreads can delay liquidation and exceed loss thresholds. Cash sizing uses a
  price allowance, not a guaranteed market-order execution bound.
* Only configured spot holdings are valued; this version does not manage short
  positions or margin wallets. Use a clean spot account if ever approved.
* Simulation fills are immediate and complete at next-open plus estimated costs.
  Binance USDT candles proxy Roostoo USD quotes; no historical order book or queue
  model is available. End liquidation costs are estimated conservatively.
* The default signal feed now imports validated closed Binance candles, matching
  the research source. Publication delays, data outages and HTTP latency can
  still cause skipped decisions; simulation does not model these. Legacy Roostoo
  snapshot mode is explicitly a different signal input.
* Limits/locks apply to this process/data directory, not unrelated programs or
  other directories using the same account. JSONL decision logs still require
  disk monitoring; application logs rotate.

Do not deploy or enable orders based on passing unit tests alone. Any later live
change requires a reviewed strategy, organizer clarifications, separately approved
testing of execution, and a committed version. EC2, `.env`, and GitHub were not
modified by the local audit.
