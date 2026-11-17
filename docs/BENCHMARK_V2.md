# Composed delivery workflows

`delivery-v2` extends the original delivery benchmark. Version 1 remains
available as `delivery` and replays the previously published experiments.

The simulator combines a carrier outcome with independent sources of
workflow variation. A case may require a parcel lookup. The primary carrier
can fail transiently or require an alternate carrier interface. Warehouse
or locker inventory may disagree with the listing. Some refund interfaces
also require a stored approval and its observed ID. The verifier checks
that approval and the persisted receipt, inventory, refund, and remedy.

| Split | Composition policy |
| --- | --- |
| Train | Eight profiles expose single mechanisms, including lookup, backup carrier, refund approval, and locker dispatch. |
| Validation | Six profiles combine known operations in different sequences or add recoverable failures. |
| Test | Eight structural profiles compose missing data, backup carrier, approval, stale listings, and service retry in combinations distinct from training and validation. |

The seed modulo the partition's profile count picks a structural profile.
The full split and seed determine opaque identifiers, refund amount,
and stock variation independently. Those parameter variations do not count
as new structural profiles. The protocol lists the fixed seed ranges.
Only public tool interfaces and observations reach the target. Incorrect
but API-legal remedies can still fail independent verification.

```sh
trajyn demo --suite delivery-v2 --split test --seed 513 --max-steps 12
```
