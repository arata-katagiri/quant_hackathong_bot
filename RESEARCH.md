# Strategy research log

## October 1, 2026: five-minute baseline

Source: official Binance Vision monthly spot `5m` kline archives for `BTCUSDT` and `ETHUSDT`, June–August 2026. These are proxies for Roostoo's USD quotes, not exact execution data.

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

The original fast strategy traded too often and lost heavily after costs. Slower variants reduced turnover, but these three months alone do not establish a robust edge; none beat buy-and-hold over this period. We must test separate dates and rolling 14-day windows, then model the actual two-asset portfolio, Roostoo's fill behavior, pair precision, and the bot's risk limits before using live credentials.

Reproduce one run using the local five-minute archive:

```bash
PYTHONPATH=src python3 -m roostoo_bot.backtest \
  --csv data/market/BTCUSDT-5m-2026-06.zip data/market/BTCUSDT-5m-2026-07.zip data/market/BTCUSDT-5m-2026-08.zip \
  --output data/backtest_btc
```

The supplied ZIPs are research inputs and are intentionally excluded from Git.
