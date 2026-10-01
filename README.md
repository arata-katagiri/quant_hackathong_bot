# Roostoo Hackathon Bot — Baseline

An intentionally conservative, long-only trend-following bot for the Roostoo Quant Trading Hackathon. It is designed to be understandable, auditable, and safe to evolve—not to promise profitable trading.

**Research status (October 1):** The default 12/48 five-minute strategy performed poorly in a June–August 2026 historical test after estimated costs. Keep `DRY_RUN=true`; do not enable live trading with this configuration. See [RESEARCH.md](RESEARCH.md).

## Strategy

For each configured pair, the bot samples the Roostoo ticker every five minutes and builds a local price history. It holds cash until the fast moving average is above the slow moving average and volatility is below a safety threshold. It then targets a capped exposure per asset; otherwise it targets zero exposure. A rebalance band limits unnecessary trading.

The current baseline is deliberately **long-only**. It does not do market making, arbitrage, high-frequency trading, manual intervention, or force a trade when there is no strategy signal.

## Safety controls

- `DRY_RUN=true` by default: records intended orders but never sends them.
- Separate credentials through `.env`; the file is ignored by Git.
- Per-asset exposure cap, minimum order size, rebalance band.
- Daily-loss and peak-to-trough drawdown circuit breakers.
- Persistent state, JSONL decision logs, and detailed application logs.
- Deterministic HMAC-SHA256 signing for Roostoo signed endpoints.

## Local setup

```bash
cp .env.example .env
# The user-provided .env convention is already supported:
# ROOSTOO_API_KEY / ROOSTOO_API_SECRET for testing and
# ROOSTOO_COMPET_API_KEY / ROOSTOO_COMPET_API_SECRET for the live competition.
# Leave CREDENTIAL_SET=testing.
PYTHONPATH=src python3 -m roostoo_bot.main --once
PYTHONPATH=src python3 -m unittest discover -s tests
```

`--once` is the first test: it performs signed read calls, creates no orders while `DRY_RUN=true`, and writes `data/events.jsonl`.

Only after checking logs and testing, change `DRY_RUN=false` in the instance-local `.env`. Do not commit that file. Keep `CREDENTIAL_SET=testing` until the official Oct 4 start; then change it to `competition` on the instance only.

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
cp .env.example .env
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
PYTHONPATH=src python3 -m roostoo_bot.main --once
tail -n 5 data/events.jsonl
```

Do **not** change `CREDENTIAL_SET=competition` or `DRY_RUN=false` until the organizers open the live round on October 4 and this test has succeeded. `.env` is ignored by Git; never add it with `git add -f`.

## Repository hygiene for judging

- Never commit API keys, logs containing secrets, or `.env`.
- Commit each strategy change with a clear reason and timestamp.
- Keep a `CHANGELOG.md` of live changes and their expected effect.
- Before submission, document data sources, entry/exit rules, sizing, risk controls, exact run command, and limitations.

## Important limitations / next work

The initial historical test rejected the default strategy; see [RESEARCH.md](RESEARCH.md). Before any live orders, the bot also needs exchange-specific precision/minimum-order validation, a two-asset portfolio backtest, realistic execution checks, and a review of the required daily activity rule.

## Historical backtest

Download Binance Vision **five-minute spot klines** for the same asset, such as `BTCUSDT` or `ETHUSDT`. The simulator uses each candle's closing price to decide and the **next candle's open** to execute. It adds the 0.1% taker fee and a default 0.05% slippage allowance. Run each coin separately:

```bash
PYTHONPATH=src python3 -m roostoo_bot.backtest \
  --csv data/market/BTCUSDT-5m-2026-08.zip \
  --output data/backtest_btc
```

The command writes `summary.json` (return, buy-and-hold comparison, drawdown, Sharpe, Sortino, Calmar, trade count, and active trading days) and `equity_curve.csv`. It mirrors the live bot's five-minute sampling, warm-up, and rebalance rule. This is a **single-asset** simulator, so its results are not the combined BTC/ETH portfolio. Binance USDT candles are a proxy for Roostoo's USD quotes. A single historical month is not enough to prove a strategy works.

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
