# Paired delivery-exception comparison

Target `ollama/ministral-3:3b` (f04aa1c738f64e13c625b82ae92504fc0260fa6723b509ed1ece0fa188179b1d). Source ollama/qwen3:8b.
Partition `test`. Seeds 528, 529, 530, 531, 532, 533. Budget 10 actions per attempt.

| Condition | Verified | Closed | Mean actions | Invalid calls | Tool failures | Recoveries | Mean ms | Delivered / Used | Accepted / Rejected | Improved / Regressed vs A |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A · No memory | 4/6 | 5/6 | 7.83 | 8 | 15 | 12 | 5828.215 | 0 / unknown | — | 0 / 0 |
| B · Raw trajectory | 1/6 | 1/6 | 9.67 | 51 | 52 | 2 | 6244.316 | 6 / unknown | — | 1 / 4 |
| C · Procedural summary | 4/6 | 4/6 | 8.83 | 6 | 14 | 12 | 6441.147 | 6 / unknown | — | 2 / 2 |
| D · Capsule | 2/6 | 2/6 | 9.17 | 10 | 19 | 10 | 6532.849 | 6 / unknown | 6 / 0 | 1 / 3 |
| E · Irrelevant trajectory | 6/6 | 6/6 | 7.50 | 4 | 12 | 12 | 5795.072 | 6 / unknown | — | 2 / 0 |
| F · Branch-aware capsule | 4/6 | 5/6 | 7.83 | 8 | 15 | 12 | 5884.535 | 0 / unknown | 6 / 0 | 0 / 0 |

## Recorded usage

| Condition | Input tokens | Output tokens | Estimated cost (USD) |
| --- | ---: | ---: | ---: |
| A | 43297 | 2816 | — |
| B | 91422 | 2835 | — |
| C | 57878 | 3056 | — |
| D | 73394 | 3071 | — |
| E | 60993 | 2678 | — |
| F | 43297 | 2816 | — |

## Per-task outcomes

| Seed | Condition | Verified | Actions | Failure codes | Capsule check |
| --- | --- | --- | ---: | --- | --- |
| 528 | A | no | 6 | incorrect_or_missing_remedy, incorrect_inventory, incorrect_refund | — |
| 528 | B | yes | 8 | — | — |
| 528 | C | yes | 8 | — | — |
| 528 | D | yes | 9 | — | public_conditions_and_interfaces_match |
| 528 | E | yes | 8 | — | — |
| 528 | F | no | 6 | incorrect_or_missing_remedy, incorrect_inventory, incorrect_refund | public_conditions_and_interfaces_match |
| 529 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 529 | C | no | 10 | case_not_closed | — |
| 529 | D | no | 10 | case_not_closed | public_conditions_and_interfaces_match |
| 529 | E | yes | 8 | — | — |
| 529 | F | yes | 9 | — | public_conditions_and_interfaces_match |
| 529 | A | yes | 9 | — | — |
| 530 | C | yes | 8 | — | — |
| 530 | D | no | 10 | case_not_closed | public_conditions_and_interfaces_match |
| 530 | E | yes | 6 | — | — |
| 530 | F | no | 10 | case_not_closed, incorrect_or_missing_remedy | public_conditions_and_interfaces_match |
| 530 | A | no | 10 | case_not_closed, incorrect_or_missing_remedy | — |
| 530 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy | — |
| 531 | D | yes | 6 | — | public_conditions_and_interfaces_match |
| 531 | E | yes | 6 | — | — |
| 531 | F | yes | 7 | — | public_conditions_and_interfaces_match |
| 531 | A | yes | 7 | — | — |
| 531 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy | — |
| 531 | C | yes | 10 | — | — |
| 532 | E | yes | 10 | — | — |
| 532 | F | yes | 9 | — | public_conditions_and_interfaces_match |
| 532 | A | yes | 9 | — | — |
| 532 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 532 | C | yes | 7 | — | — |
| 532 | D | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | public_conditions_and_interfaces_match |
| 533 | F | yes | 6 | — | public_conditions_and_interfaces_match |
| 533 | A | yes | 6 | — | — |
| 533 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 533 | C | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 533 | D | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | public_conditions_and_interfaces_match |
| 533 | E | yes | 7 | — | — |

## Limits

The suite is synthetic and small. Pairs quantify observed differences on these instances. Recovery counts a failed-call episode followed by a successful call. Invalid calls exclude explicitly modeled service and stock failures. Token and cost totals cover recorded usage only. Runtime depends on the machine.
