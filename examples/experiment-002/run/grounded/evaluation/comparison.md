# Paired delivery-exception comparison

Target `ollama/granite4:3b` (89962fcc75239ac434cdebceb6b7e0669397f92eaef9c487774b718bc36a3e5f). Source ollama/qwen3:8b.
Partition `test`. Seeds 528, 529, 530, 531, 532, 533. Budget 10 actions per attempt.

| Condition | Verified | Closed | Mean actions | Invalid calls | Tool failures | Recoveries | Mean ms | Delivered / Used | Accepted / Rejected | Improved / Regressed vs A |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A · No memory | 3/6 | 3/6 | 8.67 | 26 | 32 | 6 | 2065.904 | 0 / unknown | — | 0 / 0 |
| B · Raw trajectory | 0/6 | 0/6 | 10.00 | 28 | 31 | 6 | 1744.445 | 6 / unknown | — | 0 / 3 |
| C · Procedural summary | 1/6 | 1/6 | 9.50 | 23 | 28 | 9 | 1452.063 | 6 / unknown | — | 0 / 2 |
| D · Capsule | 1/6 | 1/6 | 9.33 | 25 | 32 | 8 | 1433.027 | 6 / unknown | 6 / 0 | 0 / 2 |
| E · Irrelevant trajectory | 0/6 | 0/6 | 10.00 | 60 | 60 | 0 | 1694.622 | 6 / unknown | — | 0 / 3 |
| F · Branch-aware capsule | 3/6 | 3/6 | 8.67 | 26 | 32 | 6 | 1441.997 | 0 / unknown | 6 / 0 | 0 / 0 |

## Recorded usage

| Condition | Input tokens | Output tokens | Estimated cost (USD) |
| --- | ---: | ---: | ---: |
| A | 42014 | 445 | — |
| B | 80880 | 504 | — |
| C | 54587 | 446 | — |
| D | 64646 | 435 | — |
| E | 67406 | 507 | — |
| F | 42014 | 445 | — |

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
| 530 | C | no | 10 | case_not_closed | — |
| 530 | D | no | 10 | case_not_closed | public_conditions_and_interfaces_match |
| 530 | E | no | 10 | case_not_closed, incorrect_or_missing_remedy | — |
| 530 | F | yes | 5 | — | public_conditions_and_interfaces_match |
| 530 | A | yes | 5 | — | — |
| 530 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy | — |
| 531 | D | no | 10 | case_not_closed, incorrect_or_missing_remedy | public_conditions_and_interfaces_match |
| 531 | E | no | 10 | case_not_closed, incorrect_or_missing_remedy | — |
| 531 | F | yes | 10 | — | public_conditions_and_interfaces_match |
| 531 | A | yes | 10 | — | — |
| 531 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy | — |
| 531 | C | no | 10 | case_not_closed, incorrect_or_missing_remedy | — |
| 532 | E | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 532 | F | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | public_conditions_and_interfaces_match |
| 532 | A | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 532 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 532 | C | no | 10 | case_not_closed | — |
| 532 | D | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | public_conditions_and_interfaces_match |
| 533 | F | yes | 7 | — | public_conditions_and_interfaces_match |
| 533 | A | yes | 7 | — | — |
| 533 | B | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 533 | C | yes | 7 | — | — |
| 533 | D | yes | 6 | — | public_conditions_and_interfaces_match |
| 533 | E | no | 10 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |

## Limits

The suite is synthetic and small. Pairs quantify observed differences on these instances. Recovery counts a failed-call episode followed by a successful call. Invalid calls exclude explicitly modeled service and stock failures. Token and cost totals cover recorded usage only. Runtime depends on the machine.
