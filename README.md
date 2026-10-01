# Roostoo Hackathon Bot — Baseline

An intentionally conservative, long-only trend-following bot for the Roostoo Quant Trading Hackathon. It is designed to be understandable, auditable, and safe to evolve—not to promise profitable trading.

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

## Repository hygiene for judging

- Never commit API keys, logs containing secrets, or `.env`.
- Commit each strategy change with a clear reason and timestamp.
- Keep a `CHANGELOG.md` of live changes and their expected effect.
- Before submission, document data sources, entry/exit rules, sizing, risk controls, exact run command, and limitations.

## Important limitations / next work

This baseline needs a separate historical-data backtest before it is used live. It also needs an event-specific review of exchange precision/minimum-order rules and an organizer-approved interpretation of the required daily activity rule. Those are the next engineering tasks, rather than switching on live orders.
