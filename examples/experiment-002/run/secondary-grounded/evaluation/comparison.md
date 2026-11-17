# Paired delivery-exception comparison

Target `ollama/ministral-3:3b` (f04aa1c738f64e13c625b82ae92504fc0260fa6723b509ed1ece0fa188179b1d). Source ollama/qwen3:8b.
Partition `test`. Seeds 528, 529, 530, 531, 532, 533. Budget 10 actions per attempt.

| Condition | Verified | Closed | Mean actions | Invalid calls | Tool failures | Recoveries | Mean ms | Delivered / Used | Accepted / Rejected | Improved / Regressed vs A |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A · No memory | 5/6 | 6/6 | 7.67 | 7 | 14 | 13 | 2432.774 | 0 / unknown | — | 0 / 0 |
| B · Raw trajectory | 0/6 | 0/6 | 10.00 | 60 | 60 | 0 | 2255.655 | 6 / unknown | — | 0 / 5 |
| C · Procedural summary | 3/6 | 3/6 | 8.33 | 7 | 17 | 11 | 1842.858 | 6 / unknown | — | 0 / 2 |
| D · Capsule | 3/6 | 3/6 | 8.50 | 7 | 15 | 10 | 1911.850 | 6 / unknown | 6 / 0 | 0 / 2 |
| E · Irrelevant trajectory | 5/6 | 5/6 | 6.83 | 1 | 7 | 7 | 1656.925 | 6 / unknown | — | 1 / 1 |
| F · Branch-aware capsule | 5/6 | 6/6 | 7.67 | 7 | 14 | 13 | 1625.499 | 0 / unknown | 6 / 0 | 0 / 0 |

## Recorded usage

| Condition | Input tokens | Output tokens | Estimated cost (USD) |
| --- | ---: | ---: | ---: |
| A | 41373 | 438 | — |
| B | 89847 | 540 | — |
| C | 53297 | 482 | — |
| D | 67331 | 472 | — |
| E | 55837 | 406 | — |
| F | 41373 | 434 | — |

## Per-task outcomes

| Seed | Condition | Verified | Actions | Failure codes | Capsule check |
| --- | --- | --- | ---: | --- | --- |
| 528 | A | no | 7 | incorrect_or_missing_remedy, incorrect_inventory, incorrect_refund | — |
| 528 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 528 | C | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 528 | D | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | public_conditions_and_interfaces_match |
| 528 | E | yes | 8 | — | — |
| 528 | F | no | 7 | incorrect_or_missing_remedy, incorrect_inventory, incorrect_refund | public_conditions_and_interfaces_match |
| 529 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 529 | C | no | 10 | case_not_closed | — |
| 529 | D | yes | 8 | — | public_conditions_and_interfaces_match |
| 529 | E | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 529 | F | yes | 9 | — | public_conditions_and_interfaces_match |
| 529 | A | yes | 9 | — | — |
| 530 | C | yes | 5 | — | — |
| 530 | D | yes | 5 | — | public_conditions_and_interfaces_match |
| 530 | E | yes | 5 | — | — |
| 530 | F | yes | 6 | — | public_conditions_and_interfaces_match |
| 530 | A | yes | 6 | — | — |
| 530 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy | — |
| 531 | D | yes | 8 | — | public_conditions_and_interfaces_match |
| 531 | E | yes | 6 | — | — |
| 531 | F | yes | 7 | — | public_conditions_and_interfaces_match |
| 531 | A | yes | 7 | — | — |
| 531 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy | — |
| 531 | C | no | 10 | case_not_closed, incorrect_or_missing_remedy | — |
| 532 | E | yes | 7 | — | — |
| 532 | F | yes | 9 | — | public_conditions_and_interfaces_match |
| 532 | A | yes | 9 | — | — |
| 532 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 532 | C | yes | 7 | — | — |
| 532 | D | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | public_conditions_and_interfaces_match |
| 533 | F | yes | 8 | — | public_conditions_and_interfaces_match |
| 533 | A | yes | 8 | — | — |
| 533 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 533 | C | yes | 8 | — | — |
| 533 | D | no | 10 | case_not_closed | public_conditions_and_interfaces_match |
| 533 | E | yes | 5 | — | — |

## Limits

The suite is synthetic and small. Pairs quantify observed differences on these instances. Recovery counts a failed-call episode followed by a successful call. Invalid calls exclude explicitly modeled service and stock failures. Token and cost totals cover recorded usage only. Runtime depends on the machine.
