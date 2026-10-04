# Roostoo Hackathon Bot — Research and Execution

A long-only spot research bot for the Roostoo Quant Trading Hackathon, with a shared BTC/ETH portfolio simulator and guarded execution engine.

**October 4 release choice:** no strategy has demonstrated a reliable edge. For a contest entry, the existing BTC/ETH `buffered_trend` is selected as an **experimental** live configuration, not validated as profitable or guaranteed to qualify. Follow the guarded [competition deployment runbook](COMPETITION_DEPLOYMENT.md) before enabling orders. Its unseen September fortnight lost 4.08% after estimated costs. The suite has 201 passing offline tests. See [RESEARCH_V2.md](RESEARCH_V2.md) for results and [AUDIT.md](AUDIT.md) for verified rules and limitations. The older single-asset study is retained in [RESEARCH.md](RESEARCH.md).

Latest: a [public-attention long/cash test](ATTENTION_RESEARCH.md), using delayed
Wikipedia readership rather than price-only signals, lost an average 0.94% base /
1.50% stress per two-week trial. Activity passed but profitability did not.
Nine rejected configurations / 1,980 portfolio scenarios now; historical counts
do not prove point-in-time availability. No live integration or deployment.

A separately frozen [pullback follow-up](PULLBACK_RESEARCH.md) also failed: it lost money in February and traded on only 3–4 UTC dates per 14-day window. Passing offline tests is not evidence of profitable trading. The separately approved [execution check](EXECUTION_VALIDATION.md) exposed and fixed a request-signing bug; consult that report for actual backend validation status.

The approved testing-account round trip subsequently completed, leaving no BTC or pending orders. This does not validate a strategy. See [READINESS.md](READINESS.md) for the remaining gates. The October 4 release procedure is documented separately; a Git push does not deploy to EC2.

The subsequently authorized [five-asset offline study](BASKET_RESEARCH.md) also
failed: March return -1.77% base / -2.84% higher slippage, with too few active
dates in both 14-day windows. April remains unopened. Configured trading pairs
are unchanged. [Cost attribution](COST_ATTRIBUTION.md) separates price losses
from fees/slippage without pretending costs can simply be removed.

An October 2 [execution fault-injection follow-up](EXECUTION_FAULTS.md) adds
restart tests with real changes to simulated cash/holdings, rejects missing or
regressing fill reports, and preserves ambiguous order outcomes. The suite now
has 98 passing offline tests. This is not additional real order validation.

The resumed search tested [slower volatility-scaled momentum](VOL_MOMENTUM_RESEARCH.md)
on previously uninspected January–March 2025 data. It also failed: -5.12% base /
-6.15% higher-slippage quarter return, with all six 14-day windows negative.
Its activity proxy passed, but its forecasts did not add value over the
volatility-only control. There are now 110 passing offline tests. This new
candidate is research-only and cannot run in BotEngine; no deployment is approved.

The next fixed [daily relative-strength screen](RELATIVE_STRENGTH_RESEARCH.md)
also failed: -0.83% base / -1.35% stress for January–March 2025, only two of six
14-day windows profitable, and drawdown above its limit. This used already-seen
screening data; untouched validation remains sealed. Seven candidates have now
been rejected. There are 124 passing offline tests, and no strategy is approved.

A separate [funding-rebound information screen](FUNDING_SIGNAL_RESEARCH.md)
also failed. Across 426 negative-funding observations, the average eight-hour
spot return was -0.22% before costs / -0.52% base / -0.72% stress. These are
isolated observation means, not portfolio returns. This signal was not added
to the trading engine. The suite now has 140 passing offline tests.

The subsequent [daily buyer-flow screen](TRADE_FLOW_RESEARCH.md) also failed:
147 selected observations averaged -0.81% gross / -1.11% base / -1.31% stress
over the following 24 hours. January's positive average did not persist in
February or March. These are isolated returns, not a portfolio backtest.
All 153 tests pass offline; results reproduce exactly. No live code or
configuration changed, and reserved validation periods remain unopened.

The [expanding-history forecast screen](FORECAST_RESEARCH.md) trained monthly
from past data and evaluated 2022–2024. Its selected isolated returns averaged
+0.33% base / +0.13% stress, but uncertainty includes losses, scorable coverage
was only 83.38%, and consistency/activity/forecast-quality gates failed. A
positive average is not a validated strategy. The report discloses archive faults
and a pre-result data-handling amendment. All 170 tests pass; no live integration.

An [activity-measurement audit](ACTIVITY_AUDIT.md) distinguishes portfolio fill
dates from information-screen entry dates and unnetted entry/exit calendars.
No candidate is rescued. The forecast's unnetted calendar reaches eight dates
in 23/72 windows versus 13/72 entry-only; neither proves qualification. Existing
gates and results remain unchanged. All 175 tests pass offline.

The new [monthly-horizon long/cash portfolio](LONG_TREND_RESEARCH.md) also failed.
Across 77 usable fresh 14-day trials in 2022–2024, it averaged +0.23% base /
+0.15% stress, but uncertainty, profitability frequency, activity and drawdown
gates failed. This is a real shared-cash simulation, not isolated trade averages.
All 770 new runs reconcile; original 168 rows remain identical. Eight rejected
configurations / 1,210 portfolio scenarios; 189 passing tests. No live integration.

## Strategy

Every five minutes, the bot requests fully closed BTC/ETH candles from Binance's public, credential-free data API. This matches the historical signal input and supplies the required history immediately; no multi-day collection wait is needed. Roostoo's current bid/ask and account balances determine order size. The baseline holds cash until the fast moving average is above the slow moving average and volatility is below a safety threshold, then targets capped exposure. A rebalance band limits unnecessary trading.

`SIGNAL_SOURCE=binance` is the default. Missing, stale, incomplete or malformed candles block strategy orders; there is no silent source substitution. Risk exits can still proceed with valid Roostoo quotes. The explicit legacy option `SIGNAL_SOURCE=roostoo` collects ticker samples locally and is not exactly the same input as the backtest.

The default remains the rejected `baseline` for transparent comparison in observation mode. The October 4 runbook selects `buffered_trend` explicitly in EC2 `.env` as an experimental contest entry, with `FAST_WINDOW=144`, `SLOW_WINDOW=576`, and `DECISION_EVERY_BARS=12`. `cash` generates zero exposure targets. No strategy forces a trade to meet an activity quota. Shorting is outside this implementation.

The rejected `pullback` research candidate uses the same 144/576 windows, 15-minute decisions (`DECISION_EVERY_BARS=3`), and the exact rules in [PULLBACK_PLAN.md](PULLBACK_PLAN.md). It is not enabled by default.

## Safety controls

- `DRY_RUN=true` by default: records intended orders but never sends them.
- Separate credentials through `.env`; the file is ignored by Git.
- Shared cash budget, fee/slippage allowance, cash reserve, and dynamic exchange quantity precision/minimum notional.
- Daily-loss and peak-to-trough drawdown guards request liquidation; exits bypass the rebalance band. The drawdown halt persists; the daily halt resets at HKT midnight. They cannot guarantee a maximum loss during gaps or outages.
- Durable order intent before submission; ambiguous outcomes block further orders. Identified pending/partial orders are queried until terminal. Order submissions are never automatically retried.
- Per-directory engine lock; at most one processed five-minute bucket; closed-candle validation (or gap-reset warm-up in legacy ticker mode).
- Persistent state, JSONL decision logs, and detailed application logs.
- Deterministic HMAC-SHA256 signing for Roostoo signed endpoints.

## Local setup

```bash
# New installations only: do not overwrite an existing .env.
test -e .env || cp .env.example .env
# The user-provided .env convention is already supported:
# ROOSTOO_API_KEY / ROOSTOO_API_SECRET for testing and
# ROOSTOO_COMPET_API_KEY / ROOSTOO_COMPET_API_SECRET for the live competition.
# Leave CREDENTIAL_SET=testing.
PYTHONPATH=src python3 -m roostoo_bot.main --once --dry-run
PYTHONPATH=src python3 -m unittest discover -s tests
```

`--once --dry-run` performs signed read calls, forces observation without orders, and writes `data/events.jsonl`. Keep `CREDENTIAL_SET=testing`; use the preflight below for a command that enforces the testing credential set as well.

Passing tests or reaching October 4 does not approve a strategy. Changing `DRY_RUN` alone cannot enable normal bot orders: a separate `LIVE_TRADING_ENABLED` gate defaults to false. The later isolated test-account probe received specific human approval; that permission does not authorize running a strategy or deploying anything.

## EC2 deployment

1. Move this repository to the EC2 instance through a method permitted by the event guide (for example, a private Git repository or a Session Manager transfer workflow).
2. No package installation is required; it uses only the Python standard library.
3. Create `.env` there with the **appropriate** credential set. Start with `DRY_RUN=true`.
4. Run one cycle, inspect `data/events.jsonl` and `data/bot.log`, then leave it running only after tests succeed.
5. Use a service manager or supervised terminal session; record every configuration/code change in Git.

### Exact credential setup on EC2

Do this only inside the EC2 instance, never in GitHub and never in a chat window:

```bash
cd ~/quant_hackathong_bot
test -e .env || cp .env.example .env
nano .env
chmod 600 .env
```

Put the credentials already issued by Roostoo into the matching values in `.env`; retain these settings while testing:

```ini
CREDENTIAL_SET=testing
DRY_RUN=true
```

The bot recognizes these supplied names directly:

```ini
ROOSTOO_API_KEY=...                 # testing key
ROOSTOO_API_SECRET=...              # testing secret
ROOSTOO_COMPET_API_KEY=...          # competition key
ROOSTOO_COMPET_API_SECRET=...       # competition secret
```

Run a single safe test cycle, then inspect its non-secret logs:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m roostoo_bot.main --once --dry-run
tail -n 5 data/events.jsonl
```

Do **not** enable orders from these older testing instructions. Use the current [competition deployment runbook](COMPETITION_DEPLOYMENT.md) for the experimental October 4 release. `.env` is ignored by Git; never add it with `git add -f`. A Git push alone never changes the existing EC2 process.

## Repository hygiene for judging

- Never commit API keys, logs containing secrets, or `.env`.
- Commit each strategy change with a clear reason and timestamp.
- Keep a `CHANGELOG.md` of live changes and their expected effect.
- Before submission, document data sources, entry/exit rules, sizing, risk controls, exact run command, and limitations.

## Important limitations / next work

The portfolio study rejects every candidate. See [execution validation](EXECUTION_VALIDATION.md) for what has and has not been checked against actual backend orders. The exact qualifying daily trade count and official metric sampling remain unspecified. Do not interpret the simulator's activity count as qualification.

## Local verification and portfolio study

All offline tests use fake exchange clients; they do not load `.env` or place orders:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The read-only preflight **forces the testing credential set and disables orders**, regardless of environment defaults. It checks clock, rules, ticker, balances, pending orders, pair-specific authenticated order history, and closed-candle availability, and saves `data/preflight.json`:

```bash
PYTHONPATH=src python3 -m roostoo_bot.preflight
```

On this Mac's Python installation, TLS checks require the existing system CA bundle: prefix the command with `SSL_CERT_FILE=/etc/ssl/cert.pem`. Do not disable certificate verification. This workaround is not normally needed on EC2.

Reproduce the frozen experiments from public, checksum-verified archives (no credentials required):

```bash
PYTHONPATH=src python3 -m roostoo_bot.download_data \
  --output data/market --months 2026-05 2026-06 2026-07 2026-08 \
  --start-date 2026-09-01 --end-date 2026-09-28
PYTHONPATH=src python3 -m roostoo_bot.research \
  --market data/market --output data/research_v2_corrected
```

The study writes per-period cash/equity and fill traces, `results.json`, and a SHA-256 input/configuration manifest. Full protocol: [EXPERIMENT_PLAN.md](EXPERIMENT_PLAN.md). `portfolio_backtest` also supports custom `--btc` and `--eth` archive lists and `--strategy`.

V2 state lives in `data/state.v2.<credential_set>.<dry|live>.json`. Old untimestamped `state.json` is preserved but not reused, isolating test/dry/live risk baselines. The default public candle source obtains 49 closed candles for baseline or 577 for the slow candidates. Only legacy ticker mode needs to collect those observations over time. Do not copy dry-run account/risk state into a live account. Run one bot process per account and data directory; the request limiter is local to the process.

## Historical backtest

Download Binance Vision **five-minute spot klines** for the same asset, such as `BTCUSDT` or `ETHUSDT`. The simulator uses each candle's closing price to decide and the **next candle's open** to execute. It adds the 0.1% taker fee and a default 0.05% slippage allowance. Run each coin separately:

```bash
PYTHONPATH=src python3 -m roostoo_bot.backtest \
  --csv data/market/BTCUSDT-5m-2026-08.zip \
  --output data/backtest_btc
```

The command writes `summary.json` and `equity_curve.csv`. This retained **legacy single-asset** simulator does not include the new shared portfolio and risk controls; use `research` or `portfolio_backtest` for current evidence. Binance USDT candles are a proxy for Roostoo's USD quotes. A single historical month is not enough to prove a strategy works.

## Optional news research (separate from trading)

The news observer fetches headlines from the public CoinDesk, Decrypt, and Cointelegraph RSS feeds. It stores each headline's **first-seen time** in `data/news.jsonl`, independently of the publisher's publication time. It neither reads Roostoo credentials nor imports the order client, and its output does **not** change the bot's trading decisions.

Run one read-only collection cycle:

```bash
PYTHONPATH=src python3 -m roostoo_bot.news --once
tail -n 5 data/news.jsonl
```

To add optional headline labels, set `OPENAI_BASE_URL=https://openrouter.ai/api/v1`, `OPENAI_API_KEY`, and `OPENAI_MODEL` in the instance-local `.env`, then run:

```bash
PYTHONPATH=src python3 -m roostoo_bot.news --once --llm
tail -n 5 data/news_assessments.jsonl
```

Only public headlines are sent to OpenRouter. The observer caps classification at three relevant headlines per cycle; `--llm` may incur API charges. If a feed or model is unavailable, headlines already fetched remain saved and unclassified headlines can be retried later. The analysis labels the **tone of the headline**, not the likely price movement. No news label should affect orders without a timestamp-correct backtest and a separate decision to change the strategy.

For ongoing collection, run `PYTHONPATH=src python3 -m roostoo_bot.news` as a **separate** process (default interval: one hour). Add `--llm` only if you want ongoing model usage. These commands require no Roostoo API keys. Keep `.env`, `data/news.jsonl`, and `data/news_assessments.jsonl` out of Git.
