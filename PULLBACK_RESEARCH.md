# Pullback follow-up — rejected, October 1, 2026

**No deployment recommendation.** This hypothesis buys an unusually large dip
only while the longer trend is rising, then exits on recovery, trend failure or
expiry. It is different from buying momentum or a breakout. Rules were fixed in
[PULLBACK_PLAN.md](PULLBACK_PLAN.md) before opening this dataset, not tuned after
seeing its results. Historical reversal research motivates the idea but does not
validate our implementation or establish a current profitable edge.

## New evidence

Six official, checksum-verified BTC/ETH archives cover December 2025–February
2026. December provides warm-up only. January and February had not previously
been inspected in this project; these are backward historical evaluations, not
prospective live tests. Forty-eight runs combine six periods, four portfolios
and two cost assumptions. All begin with $100,000 and no positions or active
signals; both assets share cash. Base costs are 0.1% fee + 0.05% slippage per side,
stress is 0.1% fee + 0.15% slippage per side. Returns include final liquidation.

| Period | Base return | Stress return | Base drawdown | Turnover | Active UTC / HKT dates |
| --- | ---: | ---: | ---: | ---: | ---: |
| January, full month | +1.65% | +0.87% | 0.59% | 7.79× | 8 / 10 |
| February, full month | −1.01% | −1.77% | 2.35% | 7.73× | 7 / 8 |
| Jan 1–14 | +0.62% | +0.26% | 0.42% | 3.51× | 4 / 5 |
| Jan 15–28 | +1.45% | +1.10% | 0.47% | 3.54× | 3 / 4 |
| Feb 1–14 | +0.82% | +0.40% | 1.71% | 4.22× | 4 / 4 |
| Feb 15–28 | −1.82% | −2.16% | 2.35% | 3.48× | 3 / 4 |

Turnover is gross bought plus sold notional divided by starting capital. Active
dates exclude forced liquidation and are only a proxy for the unknown organizer
definition. Each month has 22 strategy fills; estimated base fees are $778.71 and
$773.16 respectively. The full-month and reset 14-day results are separate runs,
so they should not be added together.

| Base-cost comparison | January return / drawdown | February return / drawdown |
| --- | ---: | ---: |
| Pullback | +1.65% / 0.59% | −1.01% / 2.35% |
| Cash | 0% / 0% | 0% / 0% |
| Buy/hold 35% BTC + 35% ETH | −9.86% / 18.57% | −12.36% / 18.75% |
| Buy/hold 50% BTC + 50% ETH | −14.08% / 25.64% | −17.66% / 26.73% |

Lower loss than buy-and-hold during a falling market does not prove a reliable
profit-making edge. This low-exposure strategy remains negative in February.

## Predeclared decision

- Both full months positive after stress costs: **FAIL**.
- All four windows stay below 8% sampled drawdown: **PASS**.
- At least three windows have eight active UTC dates: **FAIL, zero of four**.

Therefore **reject**. March–April has not been downloaded or opened for this
hypothesis. Do not lower the entry threshold or force trades to satisfy activity.
Keep the unused periods separate from any future design until its rules are fixed.
Research code is retained for reproducibility; the default strategy and real
environment were not changed. This research submitted no orders. A subsequent,
separately approved test-account round trip is documented in
[EXECUTION_VALIDATION.md](EXECUTION_VALIDATION.md); no EC2 changes, push or deployment occurred.

## Simulator correction and validation

During this work, warm-up was corrected to populate price indicators only, not
carry hypothetical active strategy state into a fresh cash portfolio. Risk
evaluation now occurs at execution boundaries, like the engine, without an
extra pre-boundary account sample. All 168 earlier result rows were reproduced
exactly after this correction; their published financial conclusions did not
change. New differential tests compare actual fake-client engine orders against
simulated orders across fresh starts, multiple strategies and risk stops. These
fixtures do not prove untested backend fill behavior or latency assumptions.

The research stage passed 65 offline tests; the later signing/execution suite
expands the passing total to 76. `research/pullback_manifest.json` records the frozen
plan, input checksums and source hashes; `research/pullback_summary.json` contains
all 48 summary rows; `research/pullback_verdict.json` records the rejected gates.
Detailed traces are in ignored `data/pullback_research/`.

Reproduce locally without credentials:

```bash
PYTHONPATH=src python3 -m roostoo_bot.pullback_research \
  --market data/pullback_market --output data/pullback_research_recheck
```

This uses the supplied archive copies. The downloader can retrieve them again:

```bash
SSL_CERT_FILE=/etc/ssl/cert.pem PYTHONPATH=src python3 -m roostoo_bot.download_data \
  --output data/pullback_market --months 2025-12 2026-01 2026-02
```
