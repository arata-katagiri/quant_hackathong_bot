# October 4 competition deployment — experimental entry

This is an operational runbook, **not a claim of a profitable or qualified
strategy**. The user confirmed the October 4 start and asked for a deployment
choice. Use the existing long-only BTC/ETH `buffered_trend` implementation. It
is less frenetic than the rejected 12/48 baseline and already shares code with
the portfolio backtest. Do not add news, shorts, or the offline five-asset
research paths to the live engine during this release.

The rule checks fully closed Binance BTC/ETH five-minute candles. Once per hour,
it may target 35% of equity in each coin when its 12-hour average exceeds its
48-hour average by 0.5%; an active position exits when the short average is no
longer above the long average. It keeps at least a 1% cash reserve, avoids small
rebalances, and has 3% daily HKT and persistent 8% peak-to-trough stop logic.
Those stops submit market exits when possible; **they do not cap actual loss**
during gaps, exchange errors, outages, or if minimum-order rules prevent exit.

Why only an experimental choice: the May unseen test returned -2.49%, the
September 1–14 unseen test returned -4.08% (-4.55% with higher slippage), and
only 5/10 descriptive fortnight windows were profitable or had at least eight
HKT fill dates. Eleven fill dates in one unseen window are a proxy, not proof
that the organizer counts the required number of trades. Full evidence is in
[RESEARCH_V2.md](RESEARCH_V2.md). Cash avoids strategy losses but cannot satisfy
an active-trading requirement; the high-turnover baseline lost more. Do not
manufacture trades just to meet a date count.

## On EC2: inspect, update, and observe before enabling orders

Run these in the EC2 shell you already use. Do not paste keys or `.env` contents
into a chat, terminal transcript, or Git. Make sure this is the **competition**
account, not the testing account. No step here changes the EC2 instance until
you run it yourself.

```bash
cd ~/quant_hackathong_bot
git status --short
pgrep -af '[r]oostoo_bot.main' || true
git pull --ff-only origin main
PYTHONPATH=src python3 -m unittest discover -s tests -q
```

Stop at a dirty checkout, failed pull/test, or unexpected bot process. If the
old dry-run loop is still running, identify its exact PID from `pgrep` and stop
that process before starting a replacement. Never run two bot loops against the
same account; local locking is not a substitute for verifying which processes
are running. Do not delete or overwrite `data/` or any state file. If a
competition **live** state file or prior live order exists, reconcile it before
starting a new loop.

Edit the existing ignored `.env` on EC2 with `nano .env`; preserve the already
installed keys and set these non-secret lines exactly. `CREDENTIAL_SET` selects
`ROOSTOO_COMPET_API_KEY` and `ROOSTOO_COMPET_API_SECRET`; do not rename the
secrets or commit this file.

```ini
CREDENTIAL_SET=competition
DRY_RUN=true
LIVE_TRADING_ENABLED=false
PAIRS=BTC/USD,ETH/USD
POLL_SECONDS=300
DATA_DIR=data
STRATEGY=buffered_trend
SIGNAL_SOURCE=binance
FAST_WINDOW=144
SLOW_WINDOW=576
DECISION_EVERY_BARS=12
SIGNAL_BUFFER=0.005
MAX_ASSET_WEIGHT=0.35
REBALANCE_BAND=0.05
MIN_TRADE_USD=250
MAX_DAILY_LOSS=0.03
MAX_DRAWDOWN=0.08
FEE_RATE=0.001
SLIPPAGE_RATE=0.0005
CASH_RESERVE=0.01
MAX_SPREAD=0.005
MAX_QUOTE_AGE_SECONDS=30
MAX_SAMPLE_LAG_SECONDS=30
```

Then run a read-only competition-account cycle and inspect **non-secret** logs:

```bash
chmod 600 .env
PYTHONPATH=src python3 -c 'from roostoo_bot.config import Settings, load_dotenv; load_dotenv(); s = Settings.from_env(); print("effective:", s.credential_set, s.strategy, s.dry_run, s.live_trading_enabled, s.pairs)'
PYTHONPATH=src python3 -m roostoo_bot.main --once --dry-run
tail -n 20 data/events.jsonl
tail -n 20 data/bot.log
```

The `--dry-run` flag forces order submission off even if `.env` was accidentally
enabled. The first command prints no key material; verify its effective
configuration is `competition buffered_trend True False` for BTC/ETH. Shell
environment variables override `.env`, so resolve any mismatch before
continuing. Check that `cycle_started` says `strategy=buffered_trend` and
`dry_run=true`, that a fresh `cycle` has sensible BTC/ETH prices and account
equity, and that there is no `api_failure`, `unexpected_failure`,
`signal_data_unavailable`, `execution_blocked`, stale quote, or pending order.
Some hours legitimately show `targets=null` because decisions are hourly; a
dry-run order may also legitimately be absent. **Do not infer that a successful
read-only cycle guarantees an order will fill.** If the account equity differs
from the expected competition balance or there are existing positions/orders,
pause and inspect rather than resetting state.

Only after these checks, if you accept the documented loss/qualification risk,
edit the same `.env` to:

```ini
DRY_RUN=false
LIVE_TRADING_ENABLED=true
```

That is the point at which normal strategy orders become possible. Start one
loop, without `--dry-run`, and monitor it:

```bash
nohup env PYTHONPATH=src python3 -m roostoo_bot.main > data/console.log 2>&1 &
pgrep -af '[r]oostoo_bot.main'
tail -n 30 data/events.jsonl
tail -n 30 data/console.log
```

`nohup` does not restart after an EC2 reboot. Arrange an approved single-process
supervisor if needed, and inspect logs and exchange account state regularly.
Treat any unknown submit outcome, pending/partial order, stale data, missing
candles, or repeated API failure as a **manual reconciliation issue**; do not
repeatedly run `--once` or delete state to “unstick” it. Ask the organizer how
emergency stops and operational restarts are treated under its no-manual-trading
rule. The official daily qualifying trade threshold and timezone remain unclear.

Keep the `.env` and `data/` out of Git. The code release does not deploy or
trade by itself. Record the exact release commit and any later parameter change
before submitting the open-source repository link to the organizer.
