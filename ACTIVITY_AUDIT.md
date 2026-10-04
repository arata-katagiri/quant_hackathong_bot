# Activity versus profitability — existing-evidence audit

**No candidate is rescued, and no strategy is approved.** There is no evidence
here that long-only trading and the activity requirement are inherently
incompatible. Some tested strategies trade frequently but lose money; others
show occasional profits but insufficient or inconsistent activity. The task
remains finding an economic edge, not making artificial orders for a quota.

## Rule and measurement distinction

Rechecked the [organizer event page](https://luma.com/coghwiyt) on October 2:
the stated October 4–17 round requires eight active days and enough strategy
trades. A numeric daily count and governing timezone are still not specified.
These remain organizer questions, not parameters to invent in the simulator.

Portfolio tests count dates with actual simulated strategy/risk-exit fills,
excluding final forced liquidation. Information-only screens count entry
opportunity dates instead. An exit can occur on another day, so fewer than eight
ENTRY dates does not by itself prove fewer than eight TRADE dates. Conversely,
an entry-plus-exit calendar does not prove a funded, netted portfolio will
generate those fills or meet the organizer's definition.

The [audit plan](ACTIVITY_AUDIT_PLAN.md) was written before the new diagnostic.
No signal, price input, cost, progression gate or prior verdict was changed.

## Existing portfolio windows

Verified all 440 saved scenario rows and extracted the seven actual candidate
configurations, excluding controls. There are 96 unique candidate/cost/14-day
intervals. Duplicate aliases for identical September windows were collapsed,
with matching metrics required; no conflicting duplicate was found. These
periods are dependent and span different dates/universes, so they are not a
leaderboard of comparable independent trials.

Numbers below are counts of windows, NOT investment returns. “Base/stress”
uses each original study's costs unchanged; “active” means eight UTC fill dates.

| Candidate | Windows per cost | Profitable base/stress | Active base/stress | Both profitable and active, stress |
| --- | ---: | ---: | ---: | ---: |
| Baseline moving average | 10 | 1 / 0 | 9 / 8 | 0 |
| Buffered trend | 10 | 5 / 4 | 7 / 7 | 2 |
| Breakout | 10 | 2 / 2 | 0 / 0 | 0 |
| Two-asset pullback | 4 | 3 / 3 | 0 / 0 | 0 |
| Five-asset pullback | 2 | 0 / 0 | 0 / 0 | 0 |
| Volatility-scaled momentum | 6 | 0 / 0 | 6 / 6 | 0 |
| Daily relative strength | 6 | 2 / 2 | 4 / 4 | 1 |

The stress-cost jointly positive/active windows above also have sampled
drawdown <=8%; this does not repair their failed full-period/consistency gates.
In particular, volatility-scaled momentum naturally met the activity proxy in
all six windows and lost in all six. For this rule the main failure is economic,
not insufficient trading. Do not select buffered trend simply because it has
two jointly passing windows; its other results and failed gates remain binding.

Timezone can matter: buffered trend has seven qualifying-by-date-count windows
in UTC but five in HKT under either cost. Its base positive-and-active count is
three in UTC versus two in HKT. The five-asset pullback has zero active UTC
windows versus one HKT window, but loses in both. Full timezone details and
the original counts are saved in the diagnostic JSON.

## Information screens: entries are not all hypothetical events

Reconstructed the exact saved, self-contained 14-day selections and verified
that entry-date counts match every original report. Then counted the union of
entry and exit dates, without altering signals or outcomes.

| Screen | Windows | Eight UTC entry dates | Eight UTC entry-or-exit dates, unnetted |
| --- | ---: | ---: | ---: |
| Funding rebound | 6 | 6 | 6 |
| Daily buyer flow | 6 | 5 | 6 |
| Expanding-history forecast | 72 | 13 | 23 |

The last column is only an UNNETTED hypothetical event calendar. It omits
capital allocation, available cash, exchange minimums, risk stops, rejected
orders, partial fills and delayed executions. Consecutive isolated positions
in the same asset can create a sell and buy at the same instant; a sensible
portfolio may net those instead of generating meaningless activity. Actual
order behavior can also introduce other dates, so this is not a universal
upper bound. No offsetting orders should be manufactured to realize this count.

This correction does not change the fixed entry-opportunity gates or promote
a failed screen. It refines interpretation: those gates are research choices,
not exact measurements of the official requirement. Funding and buyer-flow
screens still failed profitability. Forecasting still fails coverage,
uncertainty, consistency and forecast-quality checks, independently of activity;
even its unnetted calendar has only 23 rather than the predeclared 48 windows.

## What this changes about the next decision

Do not loosen turnover bands or add tiny trades merely to obtain eight dates.
Do not infer from this audit that all long-only strategies are impossible.
Activity must be evaluated from a real portfolio's net decisions and fills,
alongside returns and risk, before any future candidate can be recommended.

A literature recheck did not establish a ready-made reversal rule for this
five-large-coin basket. In particular, [Ficura's primary study](https://wp.ffu.vse.cz/artkey/wps-202301-0003.php)
distinguishes weekly reversal in smaller/less-liquid coins from momentum in
larger/liquid coins. That is not evidence that all reversal ideas fail, but it
does not justify importing a small-coin weekly reversal result unchanged here.
No new reversal experiment was run in this audit.

Offline long/short research is a distinct proposed next direction, not an
inference from the failed returns or a guaranteed solution. Permission remains
pending; see SHORT_RESEARCH_PROPOSAL.md. It has not been simulated or implemented.
The pending choice does not automatically prohibit other authorized long-only
research, but no new long-only hypothesis is being selected by this diagnostic.

## Saved evidence and verification

- `activity_audit.py` reads existing reports only. No exchange, data download,
  .env loading, order submission or strategy integration.
- Five new tests cover later exit dates, timezone crossings, duplicate dates,
  interval boundaries, conflicting aliases and joint condition counts.
- All **175 tests pass** with network connections blocked and zero attempts.
  All 96 candidate/cost windows and 84 information calendars reproduce exactly.
- Results and provenance: `research/activity_audit_summary.json` and
  `research/activity_audit_manifest.json`. Original diagnostic runs remain in
  ignored `data/activity_audit/` and `data/activity_audit_verified/`.

No existing strategy/configuration, earlier research result, .env, EC2 or account
state changed. No orders, private API calls, new market archives, reserved
validation periods, paid LLM calls, commits, pushes or deployment were used.
Seven candidate configurations / 440 portfolio scenarios and three failed
information screens remain the research inventory; this audit adds none.

```bash
cd /Users/umar/Documents/my_projects/quant_hackathong_bot
PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m roostoo_bot.activity_audit \
  --output data/activity_audit_reproduction
```

Use a fresh output directory. Keep dry-run and the separate live-trading gate
unchanged. Ask the organizers for the numeric daily trade requirement and timezone.
