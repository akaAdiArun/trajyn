# Paired delivery-exception comparison

Target `offline/delivery-target` (1). Source offline/delivery-reference.
Partition `test`. Seeds 200, 201, 202, 203, 204, 205, 206, 207. Budget 8 actions per attempt.

| Condition | Verified | Closed | Mean actions | Invalid calls | Tool failures | Recoveries | Mean ms | Delivered / Used | Accepted / Rejected | Improved / Regressed vs A |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A · No memory | 8/8 | 8/8 | 5.00 | 0 | 4 | 4 | 0.055 | 0 / 0 | — | 0 / 0 |
| B · Raw trajectory | 8/8 | 8/8 | 5.00 | 0 | 4 | 4 | 0.087 | 8 / 8 | — | 0 / 0 |
| C · Procedural summary | 8/8 | 8/8 | 5.50 | 2 | 6 | 6 | 0.063 | 8 / 8 | — | 0 / 0 |
| D · Capsule | 8/8 | 8/8 | 5.00 | 0 | 4 | 4 | 0.065 | 6 / 6 | 6 / 2 | 0 / 0 |
| E · Irrelevant trajectory | 8/8 | 8/8 | 5.00 | 0 | 4 | 4 | 0.055 | 8 / 0 | — | 0 / 0 |

## Recorded usage

| Condition | Input tokens | Output tokens | Estimated cost (USD) |
| --- | ---: | ---: | ---: |
| A | — | — | — |
| B | — | — | — |
| C | — | — | — |
| D | — | — | — |
| E | — | — | — |

## Per-task outcomes

| Seed | Condition | Verified | Actions | Failure codes | Capsule check |
| --- | --- | --- | ---: | --- | --- |
| 200 | A | yes | 5 | — | — |
| 200 | B | yes | 5 | — | — |
| 200 | C | yes | 5 | — | — |
| 200 | D | yes | 5 | — | missing_tool:ship_replacement |
| 200 | E | yes | 5 | — | — |
| 201 | A | yes | 6 | — | — |
| 201 | B | yes | 6 | — | — |
| 201 | C | yes | 6 | — | — |
| 201 | D | yes | 6 | — | public_conditions_and_interfaces_match |
| 201 | E | yes | 6 | — | — |
| 202 | A | yes | 4 | — | — |
| 202 | B | yes | 4 | — | — |
| 202 | C | yes | 6 | — | — |
| 202 | D | yes | 4 | — | public_conditions_and_interfaces_match |
| 202 | E | yes | 4 | — | — |
| 203 | A | yes | 5 | — | — |
| 203 | B | yes | 5 | — | — |
| 203 | C | yes | 5 | — | — |
| 203 | D | yes | 5 | — | public_conditions_and_interfaces_match |
| 203 | E | yes | 5 | — | — |
| 204 | A | yes | 5 | — | — |
| 204 | B | yes | 5 | — | — |
| 204 | C | yes | 5 | — | — |
| 204 | D | yes | 5 | — | missing_tool:ship_replacement |
| 204 | E | yes | 5 | — | — |
| 205 | A | yes | 6 | — | — |
| 205 | B | yes | 6 | — | — |
| 205 | C | yes | 6 | — | — |
| 205 | D | yes | 6 | — | public_conditions_and_interfaces_match |
| 205 | E | yes | 6 | — | — |
| 206 | A | yes | 4 | — | — |
| 206 | B | yes | 4 | — | — |
| 206 | C | yes | 6 | — | — |
| 206 | D | yes | 4 | — | public_conditions_and_interfaces_match |
| 206 | E | yes | 4 | — | — |
| 207 | A | yes | 5 | — | — |
| 207 | B | yes | 5 | — | — |
| 207 | C | yes | 5 | — | — |
| 207 | D | yes | 5 | — | public_conditions_and_interfaces_match |
| 207 | E | yes | 5 | — | — |

## Limits

The suite is synthetic and small. Pairs quantify observed differences on these instances. Recovery counts a failed-call episode followed by a successful call. Invalid calls exclude explicitly modeled service and stock failures. Token and cost totals cover recorded usage only. Runtime depends on the machine.

The source and target are fixed fixture policies. Their outcomes test the evaluation plumbing and provide no evidence of cross-model improvement.
