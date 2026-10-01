# Strategy research log

## October 1, 2026: five-minute baseline

Source: official Binance Vision monthly spot `5m` kline archives for `BTCUSDT` and `ETHUSDT`, June–August 2026. These are proxies for Roostoo's USD quotes, not exact execution data.

The organizer's [Data Sources Pack](https://roostoo.notion.site/Data-Sources-Pack-318ba22fed7980118a69c7a614995930) also lists CryptoDataDownload and CoinAPI. Binance Vision is the closest free historical source for the bot's five-minute price rule. Other data sources should be added only when a specific strategy needs their extra fields.

Method: for each asset separately, calculate the strategy signal after a candle closes and execute at the following candle's open. Start with $50,000 cash, charge 0.10% taker fee and 0.05% slippage on each fill, and use the live bot's 5% rebalance band and 35% maximum asset weight. The continuous June–August test has 26,496 five-minute candles per asset. Buy-and-hold includes its initial purchase costs. Results are single-asset simulations, not a combined BTC/ETH portfolio.

| Asset | Fast / slow samples | Approximate windows | Strategy return | Buy-and-hold | Trades | Days with trades |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| BTC | 12 / 48 | 1h / 4h | −21.23% | +6.50% | 1,129 | 92 |
| ETH | 12 / 48 | 1h / 4h | −20.21% | +22.77% | 1,286 | 92 |
| BTC | 48 / 192 | 4h / 16h | −4.23% | +6.50% | 413 | 88 |
| ETH | 48 / 192 | 4h / 16h | −3.99% | +22.77% | 465 | 90 |
| BTC | 144 / 576 | 12h / 48h | +2.64% | +6.50% | 165 | 57 |
| ETH | 144 / 576 | 12h / 48h | +6.23% | +22.77% | 183 | 60 |
| BTC | 288 / 864 | 24h / 72h | +3.51% | +6.50% | 108 | 51 |
| ETH | 288 / 864 | 24h / 72h | +4.20% | +22.77% | 114 | 53 |

The original fast strategy traded too often and lost heavily after costs. Slower variants reduced turnover, but these three months alone do not establish a robust edge; none beat buy-and-hold over this period. We next tested separate 14-day windows and still need to model the actual two-asset portfolio, Roostoo's fill behavior, pair precision, and the bot's risk limits before using live credentials.

## Competition-length checks

Six non-overlapping 14-day windows were cut from the continuous June–August archives. Each window starts with cash and warms up its own signal history. The table reports how many windows had positive returns and how many had trades on at least eight days. The active-day count is a proxy; the organizers must decide whether it meets their definition of sufficient strategy trades.

| Asset | Fast / slow samples | Profitable windows / 6 | Median 14-day return | Worst 14-day return | Windows with ≥8 trading days / 6 |
| --- | ---: | ---: | ---: | ---: | ---: |
| BTC | 12 / 48 | 1 | −4.30% | −5.32% | 6 |
| ETH | 12 / 48 | 1 | −3.67% | −5.53% | 6 |
| BTC | 48 / 192 | 2 | −1.15% | −3.35% | 6 |
| ETH | 48 / 192 | 2 | −1.36% | −4.32% | 6 |
| BTC | 144 / 576 | 2 | −0.17% | −1.03% | 3 |
| ETH | 144 / 576 | 3 | +0.82% | −1.52% | 4 |
| BTC | 288 / 864 | 3 | +0.24% | −1.06% | 1 |
| ETH | 288 / 864 | 2 | −0.47% | −1.41% | 2 |

As a separate, more recent check, official Binance Vision daily archives for September 15–28 were combined into another 14-day window:

| Asset | Fast / slow samples | Strategy return | Buy-and-hold | Trades | Days with trades |
| --- | ---: | ---: | ---: | ---: | ---: |
| BTC | 12 / 48 | −2.63% | +6.63% | 150 | 14 |
| ETH | 12 / 48 | −3.05% | +6.72% | 174 | 14 |
| BTC | 48 / 192 | +1.69% | +6.63% | 46 | 13 |
| ETH | 48 / 192 | +1.38% | +6.72% | 57 | 13 |
| BTC | 144 / 576 | +1.71% | +6.63% | 21 | 8 |
| ETH | 144 / 576 | +1.91% | +6.72% | 23 | 7 |
| BTC | 288 / 864 | +1.85% | +6.63% | 13 | 7 |
| ETH | 288 / 864 | +2.06% | +6.72% | 10 | 6 |

The slower variants improved in September, but the earlier 14-day windows remain weak. None of these tests models the combined two-asset portfolio or reproduces Roostoo fills precisely. **No variant is approved for live trading yet.**

Reproduce one run using the local five-minute archive:

```bash
PYTHONPATH=src python3 -m roostoo_bot.backtest \
  --csv data/market/BTCUSDT-5m-2026-06.zip data/market/BTCUSDT-5m-2026-07.zip data/market/BTCUSDT-5m-2026-08.zip \
  --output data/backtest_btc
```

Add `--fast-window 48 --slow-window 192` (or another tested pair) to reproduce a slower variant.

The supplied ZIPs are research inputs and are intentionally excluded from Git.
