# Paired delivery-exception comparison

Target `ollama/granite4:3b` (89962fcc75239ac434cdebceb6b7e0669397f92eaef9c487774b718bc36a3e5f). Source ollama/qwen3:8b.
Partition `test`. Seeds 528, 529, 530, 531, 532, 533. Budget 10 actions per attempt.

| Condition | Verified | Closed | Mean actions | Invalid calls | Tool failures | Recoveries | Mean ms | Delivered / Used | Accepted / Rejected | Improved / Regressed vs A |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A · No memory | 2/6 | 2/6 | 8.67 | 17 | 27 | 8 | 4902.052 | 0 / unknown | — | 0 / 0 |
| B · Raw trajectory | 0/6 | 0/6 | 10.00 | 60 | 60 | 0 | 8006.057 | 6 / unknown | — | 0 / 2 |
| C · Procedural summary | 1/6 | 2/6 | 9.00 | 25 | 29 | 8 | 5041.342 | 6 / unknown | — | 0 / 1 |
| D · Capsule | 0/6 | 0/6 | 10.00 | 48 | 51 | 5 | 5150.596 | 6 / unknown | 6 / 0 | 0 / 2 |
| E · Irrelevant trajectory | 0/6 | 0/6 | 10.00 | 60 | 60 | 0 | 3961.079 | 6 / unknown | — | 0 / 2 |
| F · Branch-aware capsule | 2/6 | 2/6 | 8.67 | 17 | 27 | 8 | 4950.279 | 0 / unknown | 6 / 0 | 0 / 0 |

## Recorded usage

| Condition | Input tokens | Output tokens | Estimated cost (USD) |
| --- | ---: | ---: | ---: |
| A | 42147 | 2484 | — |
| B | 84860 | 3886 | — |
| C | 50603 | 2456 | — |
| D | 68889 | 2467 | — |
| E | 67384 | 1647 | — |
| F | 42147 | 2480 | — |

## Per-task outcomes

| Seed | Condition | Verified | Actions | Failure codes | Capsule check |
| --- | --- | --- | ---: | --- | --- |
| 528 | A | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 528 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 528 | C | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 528 | D | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | public_conditions_and_interfaces_match |
| 528 | E | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 528 | F | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | public_conditions_and_interfaces_match |
| 529 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 529 | C | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 529 | D | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | public_conditions_and_interfaces_match |
| 529 | E | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 529 | F | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | public_conditions_and_interfaces_match |
| 529 | A | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 530 | C | yes | 7 | — | — |
| 530 | D | no | 10 | case_not_closed, incorrect_or_missing_remedy | public_conditions_and_interfaces_match |
| 530 | E | no | 10 | case_not_closed, incorrect_or_missing_remedy | — |
| 530 | F | yes | 5 | — | public_conditions_and_interfaces_match |
| 530 | A | yes | 5 | — | — |
| 530 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy | — |
| 531 | D | no | 10 | case_not_closed, incorrect_or_missing_remedy | public_conditions_and_interfaces_match |
| 531 | E | no | 10 | case_not_closed, incorrect_or_missing_remedy | — |
| 531 | F | no | 10 | case_not_closed, incorrect_or_missing_remedy | public_conditions_and_interfaces_match |
| 531 | A | no | 10 | case_not_closed, incorrect_or_missing_remedy | — |
| 531 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy | — |
| 531 | C | no | 10 | case_not_closed, incorrect_or_missing_remedy | — |
| 532 | E | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 532 | F | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | public_conditions_and_interfaces_match |
| 532 | A | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 532 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 532 | C | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 532 | D | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | public_conditions_and_interfaces_match |
| 533 | F | yes | 7 | — | public_conditions_and_interfaces_match |
| 533 | A | yes | 7 | — | — |
| 533 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 533 | C | no | 7 | incorrect_or_missing_remedy, incorrect_inventory, incorrect_refund | — |
| 533 | D | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | public_conditions_and_interfaces_match |
| 533 | E | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |

## Limits

The suite is synthetic and small. Pairs quantify observed differences on these instances. Recovery counts a failed-call episode followed by a successful call. Invalid calls exclude explicitly modeled service and stock failures. Token and cost totals cover recorded usage only. Runtime depends on the machine.
