# Testing-account execution validation — October 1, 2026

## Authorization and scope

The user explicitly approved one BTC buy of at most US$10 followed by a sale of
only the acquired quantity, using testing credentials. No EC2 changes,
competition keys, deployment or real `.env` edits were authorized. The separate
probe keeps normal settings `DRY_RUN=true` and uses a price-capped LIMIT buy with
at most $9 principal, leaving room under the approved cap for fees. It journals
each leg before submission, never retries an uncertain submission, and queries
or cancels only its own identified order. Requests are spaced four seconds apart.

## First attempt: no executed order found

- Requested quantity: 0.00010 BTC, limit price $84,316.49, capped principal $8.431649.
- The submit response was uncertain and provided no order ID. The probe stopped
  without another buy, sell or cancellation. Its journal remains blocked.
- Read-only balance and pending checks: $50,000 cash, no BTC, no locked cash,
  zero pending orders.
- Pair-specific order history initially returned HTTP 401. Inspection against
  the [official Python demo](https://raw.githubusercontent.com/roostoo/Roostoo-API-Documents/master/python_demo.py)
  found that our client signed percent-encoded `BTC%2FUSD`, whereas the API expects
  canonical decoded `BTC/USD` values. HTTP transport still uses form encoding.
- Corrected the signature calculation and added regression tests that check the
  actual POST body and signature header separately. The old self-consistency
  signature test was insufficient to detect this compatibility bug.
- After the fix, an authenticated read-only history query succeeded with an
  empty order list; balance remained $50,000 and pending count remained zero.
  This verifies the signing fix for a pair-specific read, not order execution.

The original submit error did not preserve its HTTP status, so its exact failure
is not proven; the signing bug is a likely explanation. Future probe errors now
save the client's safe error message. No raw response bodies or credentials are
logged. The user separately approved one fresh attempt after the read-only checks.
The original journal was not reset or silently reused.

## Separately approved fresh attempt: completed

The second attempt completed and was reconciled by exact order ID. Saved terminal
evidence is in `data/approved_test_roundtrip_20261001_retry1/`.

| Leg | Order ID | Quantity BTC | Average fill price | Notional | Fee, USD | Status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| LIMIT buy | 3405218 | 0.00010 | $84,250.06 | $8.425006 | $0.008425 | FILLED |
| MARKET sell | 3405219 | 0.00010 | $84,240.00 | $8.424000 | $0.008424 | FILLED |

The buy limit was $84,334.32; principal plus reported fee was $8.433431, within
the approved $10. Both reported commission rates were 0.001 (0.1%) and the fee
currency was USD. In this test, the marketable LIMIT buy did NOT receive a 0.05%
fee. Do not assume that choosing LIMIT alone guarantees the event's advertised
lower limit-order fee. Current market-order research correctly retains 0.1%.

Final observed account: USD $49,999.98 free, no locked cash, zero BTC, zero ETH,
and zero pending orders. The $0.02 cash reduction reflects the reported fees,
price change and account rounding. No further orders are authorized by these
completed approvals. Repeating the completed probe journal returns its saved
report without submitting another order.

## Validation boundaries

This verifies one BTC quantity accepted at the published precision, a filled
marketable LIMIT buy, a filled MARKET sell, exact-ID history reconciliation and
USD-denominated fees on the testing backend. It does not validate ETH execution,
actual partial fills, resting-limit fees, cancellations, accepted-but-lost order
responses, competition-account behavior or production reliability.

Offline fixtures cover full/partial fills, exact-ID cancellation, unknown buy/sell
outcomes, capped sizing, refusal to use pre-existing BTC, and idempotent restart.
This is useful safety evidence, not a substitute for backend execution evidence.
No strategy has been approved for deployment.

The normal read-only preflight now includes pair-specific authenticated order
history so future signing regressions cannot hide behind a successful balance
request. Do not run the order probe as an ordinary health check or reset its
journal to obtain another test trade.
