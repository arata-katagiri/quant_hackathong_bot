# Five-asset offline result: rejected

**No candidate is ready. Keep the bot in dry-run.** Adding XRP, BNB and SOL to
BTC/ETH did not rescue the fixed pullback rule. March lost money after costs,
and neither 14-day window reached eight active UTC dates. April was not
downloaded or opened; the frozen stopping rule was honored.

## Results

The candidate uses 14% target allocation per coin, maximum 70% total target
exposure, with existing shared cash, sizing and risk rules. Every row starts
fresh with USD 100,000. Return includes fees, slippage and end liquidation.

| Portfolio / period | Base return | Higher-slippage return | Base max drawdown | Base turnover | Active UTC dates / HKT dates |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pullback basket, March | -1.77% | -2.84% | 2.16% | 10.82x | 12 / 16 |
| Pullback basket, March 1–14 | -1.04% | -1.73% | 1.80% | 6.94x | 7 / 9 |
| Pullback basket, March 15–28 | -0.05% | -0.28% | 0.64% | 2.25x | 4 / 5 |
| Cash, March | 0.00% | 0.00% | 0.00% | 0.00x | 0 / 0 |
| Equal buy/hold, 70% invested, March | +0.53% | +0.39% | 11.64% | 1.41x | 1 / 1 |
| Equal buy/hold, 100% invested, March | +0.75% | +0.55% | 16.00% | 2.01x | 1 / 1 |

Turnover is total bought-plus-sold notional divided by starting capital, not
the number of round trips. Active dates count non-forced simulated fills; they
are **not verified qualifying days**. UTC windows cross HKT date boundaries,
so their HKT counts can differ. Buy/hold benchmarks do not have strategy risk
stops and do not meet the activity proxy; their positive return is not a
deployment recommendation. Month and within-month windows overlap, so these
are not independent samples.

The candidate generated 78 March fills and paid USD 1,081.96 in modeled fees.
Fixed-trade attribution shows -USD 150.71 from price movement before costs,
minus USD 1,081.96 fees and USD 540.98 modeled slippage, yielding -USD 1,773.65.
In plain English: it did not earn enough from price changes to pay for trading.
See COST_ATTRIBUTION.md for why this is not a zero-cost strategy rerun.

## Predeclared decision

- Positive March under both cost scenarios: **failed**.
- All periods' sampled drawdown at most 8%: passed (not a guaranteed loss cap).
- Both 14-day windows at least eight active UTC dates under both costs: **failed**.
- Advance to April: **no**. Live approval: **no**.

The earlier four BTC/ETH candidates remain rejected. This is a fifth candidate
configuration, not a broad parameter search. There are now 240 saved scenario
results across all studies, including benchmarks and stress cases—not 240
independent validation samples. Do not keep changing settings until one of
these already-seen periods produces a green number.

## Protocol and limitations

[BASKET_PLAN.md](BASKET_PLAN.md) was frozen before retrieving March data. The
universe was the five largest non-stablecoin assets in the
[February 22 CMC snapshot](https://coinmarketcap.com/historical/20260222/),
intersected with current public Roostoo availability. That current-availability
check is not a historical listing record. The new experiment explicitly
consumed March from the old reserved periods; it does not claim the old
two-asset pullback passed its gate.

Ten official Binance February/March spot archives were checksum-verified.
February supplies indicator history only. Synchronized five-minute candles
have no gaps, duplicates or forward fills. Binance USDT prices proxy Roostoo
USD prices; live spread, latency, partial fills, gaps within candles and future
availability remain limitations. Fee 0.1% each side; base/slippage-stress
0.05%/0.15% each side. News is not used.

The simulator shares decision, sizing and risk functions with the bot, but
offline five-asset settings cannot run through BotEngine. Live configured
pairs, .env, DRY_RUN, EC2, competition credentials and GitHub were unchanged.
No additional account reads, order tests or paid LLM calls were performed for
this experiment; the only Roostoo call was public exchangeInfo.

## Files and safe reproduction

- `research/basket_manifest.json`: pre-computation plan, source and data hashes.
- `research/basket_summary.json`: all 24 basket/benchmark/cost/period results.
- `research/basket_verdict.json`: machine-readable failed gates.
- `research/cost_attribution.json`: reconciliation of 120 detailed reports.
- `data/basket_march/`: ignored local equity/fill traces and originals.
- `data/basket_market/`: ignored, checksum-verified public archives.

Only if you want to reproduce the already completed offline result, use a NEW
output directory. No API keys are required; this does not run the trading bot:

```bash
cd /Users/umar/Documents/my_projects/quant_hackathong_bot
PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m roostoo_bot.basket_research \
  --market data/basket_market --output data/basket_march_reproduction --stage march
```

The April command rejects a failing March report before loading April inputs.
No action is needed on EC2. The useful user follow-up is organizer clarification
of the October 4 first-trade deadline, daily qualifying trade count/timezone,
and official metric conventions, as detailed in READINESS.md.
