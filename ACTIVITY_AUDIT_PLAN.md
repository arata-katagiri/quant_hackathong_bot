# Activity measurement audit — October 2, 2026

This audit diagnoses existing records. It is NOT a new strategy test, parameter
search or relaxation of an earlier progression gate. No new prices or reserved
validation data will be opened. All existing failed verdicts remain intact.

The public event page requires eight active days with enough strategy trades,
but does not specify a numeric daily threshold or timezone. Existing portfolio
reports count actual simulated non-final-liquidation fills. Information screens
instead count selected entry dates. Those are different quantities. A strategy
exit on a later date can create activity, while simultaneous exits/reentries
could net out. Neither signal count is proof of qualifying fills.

## Fixed diagnostic

1. Verify fingerprints of the existing 440 portfolio scenario rows. Select
   only the seven named candidate configurations, not controls. Identify exact
   14-day intervals from timestamps, not names. Collapse duplicate aliases of
   the SAME configuration/cost/start/end; reject contradictory duplicates.
2. Separately by candidate and cost, count windows with positive net return,
   at least eight simulated fill dates (UTC and HKT), both conditions, and both
   plus sampled drawdown <=8%. Retain all unique-window details. Do not pool
   these dependent, differently dated windows as independent statistical trials.
3. For each existing funding, flow and forecast information screen, reconstruct
   the saved self-contained 14-day selections without changing any signal.
   Report entry dates and the union of hypothetical entry/exit dates, in UTC
   and HKT. Use the saved labels' timestamps, not guessed holding periods.
4. Explicitly label the latter as an UNNETTED, unfunded, no-risk-overlay event
   calendar. It is not an executable portfolio, guaranteed activity upper bound,
   official qualification or permission to submit offsetting orders. Real
   sizing, netting, risk stops and order outcomes can change dates and counts.
5. Check that reconstructed entry counts equal the original reports. Save
   source hashes, all diagnostic rows and aggregated counts. Add tests for
   cross-midnight exits, timezone boundaries, duplicate dates, excluded end
   labels, conflicting aliases and joint profitability/activity counts.

The audit may refine explanatory wording, but cannot rescue a failed candidate.
In particular, fewer than eight entry dates alone does not prove fewer than
eight executed-trade dates. Conversely, an unnetted calendar above eight does
not prove that a sensible portfolio can qualify. No strategy/order/configuration
code, credentials, .env, EC2, account API calls, commits or deployment change.
