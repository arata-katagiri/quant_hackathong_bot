# Competition readiness — updated October 2, 2026

**Not ready for strategy deployment. No first-place claim is supported.**

| Requirement | Current evidence | Remaining gate |
| --- | --- | --- |
| Schedule and scoring | October 4 confirmed by user; event/FAQ reviewed in AUDIT.md | Updated first-trade deadline; official ratio conventions |
| Activity compliance | Portfolio fill dates distinguished from entry-only information proxies; ACTIVITY_AUDIT.md | Organizer's qualifying trade count/timezone and executable portfolio evidence |
| Credible strategy | Nine fixed candidate configurations, 1,980 portfolio scenarios, plus three information screens | All nine candidates and all three screens failed progression; no candidate approved |
| Honest portfolio simulation | Shared cash/risk/sizing, prior closed signals, next-open fills, fees, checksummed data, look-ahead and engine-parity tests | Latency, partial fills and intrabar risks remain approximations |
| Basic order execution | One explicitly approved BTC round trip filled and reconciled; fees and flat ending wallet recorded | Broader execution cases require new, separately scoped approval |
| Duplicate-order safety | Durable intents; unknown submissions block; fill-progress persistence and partial-fill/cancellation restart fixtures | Actual accepted-but-lost response and delayed wallet visibility remain untested |
| Operational reliability | Point-in-time testing preflight and offline suite pass | Extended host observation and disk/service supervision |
| Deployment | Local code and docs only; no push or EC2 changes | Reviewed strategy, rule clarifications, user-approved release/deployment |
| Repository submission | Event page says repository link due before October 14; open-source code and traceable commits required | Current work remains uncommitted and unpublished; publishing needs approval and a reviewed release |
| Competition result | Competition has not started | Real ranking and judging; no guarantee of profit or first place |

Keep `DRY_RUN=true` and `LIVE_TRADING_ENABLED=false`. The completed test trade
authorization is not permission to run a strategy, repeat the probe or deploy.
News remains observational and is not a trading input.

## Safe next steps

1. Ask organizers: "Under the October 4 schedule, what is the first-trade
   deadline, how many executed strategy trades qualify a day, which timezone is
   used, and how are the final risk ratios sampled and annualized?"
2. Review ATTENTION_RESEARCH.md, LONG_TREND_RESEARCH.md, ACTIVITY_AUDIT.md, FORECAST_RESEARCH.md, TRADE_FLOW_RESEARCH.md, FUNDING_SIGNAL_RESEARCH.md, RELATIVE_STRENGTH_RESEARCH.md, VOL_MOMENTUM_RESEARCH.md, BASKET_RESEARCH.md, COST_ATTRIBUTION.md, RESEARCH_V2.md,
   PULLBACK_RESEARCH.md, EXECUTION_VALIDATION.md and EXECUTION_FAULTS.md. Do not
   tune rejected rules to their now-seen evaluation periods or force activity.
3. Verify this local copy without orders:

```bash
cd /Users/umar/Documents/my_projects/quant_hackathong_bot
PYTHONPATH=src python3 -m unittest discover -s tests -q
SSL_CERT_FILE=/etc/ssl/cert.pem PYTHONPATH=src python3 -m roostoo_bot.preflight
```

The user authorized a strictly offline expansion to five assets. That frozen
March study also failed; April remains reserved and unopened. No more tests of
this candidate are warranted by its gates. Further strategy research needs a
genuinely different rationale and a new predeclared evaluation, not retuning to
these now-seen data. Shorting, paid LLM calls, new account order tests and any
deployment still need separately scoped decisions. No code changes or commands
on EC2 are needed for reviewing these results.

## Public-rule recheck and completion audit — October 2

Reopened the [event page](https://luma.com/coghwiyt) and read the
[official FAQ](https://roostoo.notion.site/Roostoo-Quant-Trading-Hackathon-Official-FAQ-313ba22fed798042bab7c93c609d004e)
through the browser. The event still gives October 4–17 and eight active dates,
without a numeric daily trade threshold. FAQ Q25/Q26 still give September 30
and October 1 at 8pm. Do not infer a replacement deadline from those old dates.
The user-confirmed October 4 announcement remains our working schedule.

FAQ Q22/Q23 still specify 30 requests per minute including reads. Q28 allows
recorded code changes but prohibits discretionary intervention, including manual
stops; ask how emergency stops and deployment restarts should be handled. This
does not override the user's control over their computer or authorize us to
change the running instance. Q29 describes automatic end liquidation. Q31
permits long/short trading, but that is not approval to expand our implementation.

The event describes several award categories and a judged final presentation,
not a single backtest statistic that proves first place. The objective cannot
be considered achieved by passing unit tests or choosing the best losing
candidate. No new research period, account call or order was used in this review.

| Original requirement | Current evidence | Honest status |
| --- | --- | --- |
| 1. Audit correctness and operations | AUDIT.md; EXECUTION_VALIDATION.md; EXECUTION_FAULTS.md; 189 offline tests | Local audit/fixes delivered; broader backend and EC2 behavior remain unverified |
| 2. Realistic combined portfolio test | Shared cash, sizing/risk/strategy functions; closed-bar next-open simulation; costs, synchronized checked inputs, parity and future-perturbation tests | Implemented, with documented fill/latency/intrabar approximations |
| 3. Strategy studies and benchmarks | 1,210 saved scenarios, fixed plans, separated periods, cash/buy-hold/volatility/breadth controls, costs/drawdown/turnover/date counts | Delivered; activity counts are proxies, not confirmed qualifying days |
| 4. Evidence-based recommendation | Eight candidate configurations failed their validation gates | No candidate recommended; April 2026 remains unopened |
| 5. Tested, documented improvements and credential hygiene | Local release fingerprints, offline tests and scoped secret checks | Delivered locally; no release commit, push or deployment authorized |
| Win first place | No validated candidate, approved competition deployment or actual competition result | Not achieved; cannot be guaranteed |

The user resumed the search. The next completed study remained spot-only and
is documented in VOL_MOMENTUM_RESEARCH.md; it failed and did not advance to
April–June 2025 validation. Repeating failed experiments or opening the reserved
April 2026 period without a new justified plan is not the next step. Continued
offline research does not authorize orders, shorting in the running bot or deployment.

The following daily relative-strength screen also failed, on explicitly
already-inspected January–March 2025 data. See RELATIVE_STRENGTH_RESEARCH.md.
No April–June 2025 validation inputs were opened. The original 168 scenario
summaries still reproduce exactly, and 124 tests pass with network sockets
blocked. Keep both trading gates disabled; a profitable January alone is not
evidence of readiness.

The next follow-up tested public derivatives funding as information for spot,
without implementing futures or any new trading strategy. It failed before and
after costs; see FUNDING_SIGNAL_RESEARCH.md. This adds one information screen,
not more portfolio scenario runs. The current suite has 140 passing offline
tests. All trading boundaries and unopened validation periods remain intact.

The following rules/API feasibility review is recorded in
SHORT_RESEARCH_PROPOSAL.md. It identifies why short-position accounting cannot
reuse the spot ledger unchanged. Offline long/short research permission has been
requested but not received; no short simulation, private request or engine change
was made. The current spot preflight is not a complete account-equity check for
an account with short positions.

While that optional permission remains pending, a further authorized long-only
screen tested completed-day buyer-flow imbalance. It failed: mean next-day
return -0.81% gross / -1.11% base / -1.31% stress; only one of three months and
one of six 14-day windows had positive stress averages. See
TRADE_FLOW_RESEARCH.md. All 445 observation rows and results reproduce exactly;
153 tests pass with network connections blocked and zero attempts. This adds
the second failed information screen, not more portfolio scenarios. Existing
engine/configuration and reserved validation periods remain unchanged. Optional
short permission is not a blocker to otherwise authorized long-only research.

A broader 2022–2024 expanding-history forecast screen subsequently failed
progression despite positive selected-observation averages. See
FORECAST_RESEARCH.md for incomplete coverage, wide uncertainty, failed activity
and forecast-quality checks, and the pre-result archive-quality amendment.
This is the third information screen, not a portfolio simulation. All 170 tests
pass offline and all 5,475 observations, 36 monthly model records and results
reproduce exactly. No reserved validation, engine or deployment changes.

ACTIVITY_AUDIT.md now separates actual simulated fill dates from entry-only
and unnetted event proxies. Some candidates trade frequently and still lose;
there is no proof that long-only trading and activity are inherently incompatible.
All prior gates and verdicts stand. The offline suite has 175 passing tests;
this is an audit of existing evidence, not new strategy scenarios or approval.

The subsequent monthly-horizon long/cash portfolio test adds 770 scenarios on
77 usable fresh 14-day trials in 2022–2024. Mean stress return +0.15%, but
uncertainty, profitable-window count, activity and 8% drawdown checks failed;
see LONG_TREND_RESEARCH.md. It is the eighth rejected configuration, not a
deployment recommendation. All 189 tests pass; original 168 rows and all new
summaries reproduce, and all new cash/P&L ledgers reconcile. No reserved
validation, live engine/configuration, shorting or deployment changes.

Credential check on this local checkout: none of the current nonempty key/secret
values in .env appeared in 39 locally reachable Git blobs or 183 local data
log/JSON report/journal files. .env is not tracked. No values were printed or
sent externally. This is a scoped check, not proof that unknown old credentials,
unreachable objects, other machines, or external copies are clean. The reachable
Git history checked was based on HEAD
`217d5e1e6778a1ea200367830cdb7c9abc9de3b8`; no remote fetch was needed or made.
