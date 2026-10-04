# Execution fault-injection follow-up — October 2, 2026

**Engineering improvement only. No strategy is approved, and no new real orders
or account queries were made.** EC2, .env and the completed test journals are
unchanged. These tests use in-memory exchange responses and temporary state
directories, not testing-account or competition credentials.

## Findings reproduced before fixes

| Simulated failure | Previous behavior | Updated behavior |
| --- | --- | --- |
| Partial fill followed after restart by a cancellation reporting fewer filled units | Earlier fill progress was not saved; the terminal report could clear the order | Save the highest validated filled quantity; a decrease blocks reconciliation |
| Cancellation report omits FilledQuantity | Missing data was silently treated as zero | Require an explicit filled quantity; preserve unresolved order |
| Submit says Success=false but includes order details | Classified as a definite rejection, allowing engine to forget the intent | Classify as an unknown outcome; retain intent and never automatically resubmit |
| Event log fails after a valid fill report | Newly observed fill progress was not yet durable | Save progress before logging; failure leaves the order for reconciliation |

The first targeted run reproduced the first three gaps (two failed assertions
and one wrong exception type). A separate logging test failed for both partial
and complete fill reports before its persistence fix. All now pass.

This does NOT establish that Roostoo has produced these faults. They are
adversarial, synthetic responses used to check safe behavior. Its
[official order/query examples](https://github.com/roostoo/Roostoo-API-Documents#query-order)
include explicit FilledQuantity fields. Some old examples have inconsistent
quantity/average-price combinations; we do not weaken validation to accept
contradictory evidence. A downward correction requires review, not a new order.

## Additional lifecycle evidence

The new fake exchange actually adjusts available cash, locked cash and asset
holdings. It covers:

- Partial BUY, process restart, blocked second order, then cancellation and a
  changed signal: sell only the position actually acquired, not requested size.
- Partial BUY followed by completion after restart: use refreshed holdings and
  cash, without another BTC buy; other asset sizing uses remaining cash.
- An order genuinely accepted by the fake exchange but its response lost:
  block after restart even though the balance changed; do not infer an ID.
- Definite rejection: no invented holdings and no retry in the same bucket.
- Regressing or missing fill reports after restart: retain unresolved intent.
- Log failure: persist observed fill progress and retain the order.

The isolated, already-used execution probe also rejects decreasing fill
reports. Only its offline record-validation method was tested; its real CLI
was NOT run again. Previous approval remains consumed.

## Verification and limits

98 offline tests pass, including ten new tests in this follow-up. Existing
engine/simulator parity tests still pass. Strategy rules, market data,
portfolio-backtest implementation and the 240 stored research results were
not changed. No April data was opened. Unknown submissions without IDs still
require manual review; there is no automatic cancellation, matching or retry.

The fill-progress state field is additive. An older unresolved journal without
that field cannot recover its historical observations from this change alone;
review such an order rather than clearing its journal. Actual partial fills,
cancellations, contradictory responses, delayed wallet visibility and crash
behavior on EC2 remain unverified. Simulator fills are still immediate and
complete; these tests do not claim to model their performance impact.

Do not delete saved state to unblock trading. Do not repeat the test-order
probe. Keep DRY_RUN enabled. Safe local verification requires no credentials:

```bash
cd /Users/umar/Documents/my_projects/quant_hackathong_bot
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -q
```

Changed code: `client.py`, `engine.py`, `execution_probe.py`.
Changed tests: `test_client.py`, `test_execution_probe.py`, new
`test_order_lifecycle.py`. No deployment, commit or push is part of this update.
