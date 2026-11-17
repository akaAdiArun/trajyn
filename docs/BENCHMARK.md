# Delivery-exception benchmark

The delivery suite adds branching, synthetic support tasks alongside the original
replacement smoke suite. Each task starts with a linked ticket, parcel, product,
inventory count, and outstanding case. The agent sees the request, an opaque
ticket identifier, and the available tools. The runner keeps split and seed in
the trajectory and outside the agent context.

Read the case to locate the parcel. Use authoritative carrier status to decide
between a lost, delivered, or held workflow. Lost parcels require a stock check
and either a warehouse shipment, locker reservation, or refund. Delivered and held
parcels can bypass stock and require confirmation or a pickup arrangement. Closing
the case requires a receipt from the posted remedy. A refund can close an eligible
lost case, while the verifier will still fail it when inventory supported the
preferred replacement.

## Partition rules

The seed modulo the row count selects the profile in the specified partition.
The split and full seed determine opaque identifiers independently. Initial
inventory and refund amount stay in environment state.

| Split | Profiles in modulo order |
| --- | --- |
| Train (5) | Lost with stock, lost without stock, delivered, held, lost with a warehouse retry |
| Validation (3) | Lost with a carrier retry, delivered with a carrier retry, held |
| Test (4) | Lost with locker-only dispatch, lost with a stale stock listing, delivered with a stale customer report, held with a carrier retry |

Only the training partition supplies induction and retrieval data. Validation
and test share the business rules and use distinct instances and branch
combinations. Some elementary actions and task routes recur across partitions
to allow transfer. The locker affordance and the stale-report and stale-stock
cases are held out from training.

The state verifier checks the correct remedy, receipt-linked closure, remaining
inventory, and refund amount. Carrier and warehouse retries resolve after one
failed attempt. Stale stock requires an alternate action instead of a retry.
