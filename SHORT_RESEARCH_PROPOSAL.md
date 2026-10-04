# Long/short research proposal — permission pending

Status on October 2, 2026: **NOT implemented, NOT tested, NOT approved.**
The existing seven portfolio candidates and funding-rebound information screen
remain rejected. No short orders or short simulations were run in this review.

## Why consider this path

The current strategies can own coins or hold cash. They cannot profit directly
from a falling price. A short instead benefits from a decline and loses when
the price rises. That extra direction might help a trend strategy, but it does
not cure false signals, reversals or trading costs. We have not established that
it will be profitable, and will not simply reverse the failed funding signal.

The [event rules](https://luma.com/coghwiyt) permit 1x long/short positions but
prohibit leverage, arbitrage, market making and HFT. The user has so far
authorized the five-asset offline expansion; this proposal asks separately for
offline long/short simulation. It does not seek live-bot or order permission.

## Public API facts checked

The [official short API](https://github.com/roostoo/Roostoo-API-Documents#open-short-position-trade)
documents collateral-based sizing, quantity rounding, bid entry and ask exit.
Opening fees are 0.1% for market AND limit requests; closing costs 0.1% of exit
notional. Free cash must cover collateral plus entry fee. Partial closes release
proportional collateral; repeat entries merge. Reported position value includes
collateral and unrealized P&L. Realized loss is capped at collateral, but close
fees can make returned cash negative. Pending and filled IDs have different
meanings. Some zero fields are omitted. Competition permissions can reject shorts.
This is documentation evidence, not verified account behavior.

## Why the current simulator cannot just accept negative quantities

Local inspection confirms that `portfolio.py` and `portfolio_backtest.py` value
spot balances only. `client.balance()` selects SpotWallet, and the existing
preflight does not query short positions. They do not establish complete account
equity for an account with shorts. The completed BTC execution probe verified
only a spot buy/sell. The current bot must remain a clean-spot-account bot.

A future offline ledger would need explicit free cash, spot holdings, committed
short collateral and unrealized/realized short P&L. Short-sale proceeds must not
be invented as freely spendable cash. Cash and collateral cannot be counted
twice. Reducing a position must release only the matching share of collateral;
fees and realized losses must reconcile to the equity curve. Exposure must be
measured gross across both directions, not netted to hide risk.

The test design would need both rising and falling synthetic paths, position
reversal through flat, additions, reductions, gap losses, cost/rounding effects,
cash exhaustion and persistent risk stops. Any isolated research simulator must
remain unable to import credentials or submit orders. Live code stays untouched.

## Proposed research sequence if the user approves

1. Freeze one symmetric trend hypothesis, using the same five assets and
   previously established history/cadence rather than a new parameter sweep.
   Its long-only counterpart remains a rejected control, not a candidate to
   relabel as successful.
2. Specify collateral/equity accounting and cost sensitivities before outcomes.
   Independently verify the ledger with hand-calculated synthetic cases.
3. Screen on already-inspected data, with cash and clearly labeled exposure
   controls. Require profitability, bounded risk and natural activity. Retain
   every failure and do not relax gates afterward.
4. Only a complete screen pass may unlock a predeclared untouched validation
   stage. Passing research would still NOT authorize orders or deployment.

This sequence is a proposal, not a frozen experiment: no performance claims or
approval can be inferred from it. The detailed protocol would be saved and
fingerprinted before any new simulation after permission is received.

## Unresolved questions before exchange-faithful implementation

- How do SpotWallet and MarginWallet represent committed collateral, and which
  values are already included in an account-level equity figure?
- Are there holding charges or automatic liquidation rules beyond the documented
  close behavior? Absence from the README does not prove there are none.
- What minimum remainder triggers a full rather than partial close?
- Does this specific competition account enable shorts, and do its fees match
  the endpoint-specific documentation rather than the event's general maker fee?
- How is the 1x restriction enforced after prices move?

An initial offline study could label and stress unresolved accounting assumptions;
it could not claim backend parity. Organizer answers and separately approved
execution checks would be required before any eventual short-capable release.

No private API requests, credentials, news/LLM calls, orders, reserved validation
data, EC2 changes, commits, pushes or deployments were used in this review.
