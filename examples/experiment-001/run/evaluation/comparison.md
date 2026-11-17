# Paired delivery-exception comparison

Target `ollama/granite4:3b` (89962fcc75239ac434cdebceb6b7e0669397f92eaef9c487774b718bc36a3e5f). Source ollama/qwen3:8b.
Partition `test`. Seeds 512, 513, 514, 515, 516, 517, 518, 519, 520, 521. Budget 12 actions per attempt.

| Condition | Verified | Closed | Mean actions | Invalid calls | Tool failures | Recoveries | Mean ms | Delivered / Used | Accepted / Rejected | Improved / Regressed vs A |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A · No memory | 3/10 | 4/10 | 10.40 | 62 | 72 | 11 | 1977.405 | 0 / unknown | — | 0 / 0 |
| B · Raw trajectory | 1/10 | 1/10 | 11.70 | 58 | 61 | 11 | 1872.199 | 10 / unknown | — | 1 / 3 |
| C · Procedural summary | 1/10 | 1/10 | 12.00 | 76 | 80 | 16 | 1692.962 | 10 / unknown | — | 1 / 3 |
| D · Capsule | 0/10 | 0/10 | 12.00 | 80 | 90 | 10 | 1700.110 | 10 / unknown | 10 / 0 | 0 / 3 |
| E · Irrelevant trajectory | 0/10 | 0/10 | 12.00 | 120 | 120 | 0 | 1938.337 | 10 / unknown | — | 0 / 3 |

## Recorded usage

| Condition | Input tokens | Output tokens | Estimated cost (USD) |
| --- | ---: | ---: | ---: |
| A | 86547 | 901 | — |
| B | 160431 | 990 | — |
| C | 117874 | 942 | — |
| D | 141424 | 942 | — |
| E | 138089 | 1013 | — |

## Per-task outcomes

| Seed | Condition | Verified | Actions | Failure codes | Capsule check |
| --- | --- | --- | ---: | --- | --- |
| 512 | A | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 512 | B | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 512 | C | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 512 | D | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | public_conditions_and_interfaces_match |
| 512 | E | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 513 | B | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 513 | C | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 513 | D | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | public_conditions_and_interfaces_match |
| 513 | E | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 513 | A | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 514 | C | no | 12 | case_not_closed | — |
| 514 | D | no | 12 | case_not_closed | public_conditions_and_interfaces_match |
| 514 | E | no | 12 | case_not_closed, incorrect_or_missing_remedy | — |
| 514 | A | yes | 5 | — | — |
| 514 | B | no | 12 | case_not_closed, incorrect_or_missing_remedy | — |
| 515 | D | no | 12 | case_not_closed, incorrect_or_missing_remedy | public_conditions_and_interfaces_match |
| 515 | E | no | 12 | case_not_closed, incorrect_or_missing_remedy | — |
| 515 | A | no | 12 | case_not_closed, incorrect_or_missing_remedy | — |
| 515 | B | no | 12 | case_not_closed, incorrect_or_missing_remedy | — |
| 515 | C | no | 12 | case_not_closed, incorrect_or_missing_remedy | — |
| 516 | E | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 516 | A | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 516 | B | yes | 9 | — | — |
| 516 | C | yes | 12 | — | — |
| 516 | D | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | public_conditions_and_interfaces_match |
| 517 | A | no | 8 | incorrect_or_missing_remedy, incorrect_inventory, incorrect_refund | — |
| 517 | B | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 517 | C | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 517 | D | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | public_conditions_and_interfaces_match |
| 517 | E | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 518 | B | no | 12 | case_not_closed, incorrect_or_missing_remedy | — |
| 518 | C | no | 12 | case_not_closed, incorrect_or_missing_remedy | — |
| 518 | D | no | 12 | case_not_closed, incorrect_or_missing_remedy | public_conditions_and_interfaces_match |
| 518 | E | no | 12 | case_not_closed, incorrect_or_missing_remedy | — |
| 518 | A | yes | 12 | — | — |
| 519 | C | no | 12 | case_not_closed, incorrect_or_missing_remedy | — |
| 519 | D | no | 12 | case_not_closed, incorrect_or_missing_remedy | public_conditions_and_interfaces_match |
| 519 | E | no | 12 | case_not_closed, incorrect_or_missing_remedy | — |
| 519 | A | yes | 7 | — | — |
| 519 | B | no | 12 | case_not_closed, incorrect_or_missing_remedy | — |
| 520 | D | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | public_conditions_and_interfaces_match |
| 520 | E | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 520 | A | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 520 | B | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 520 | C | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 521 | E | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 521 | A | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 521 | B | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 521 | C | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | — |
| 521 | D | no | 12 | case_not_closed, incorrect_or_missing_remedy, incorrect_refund, incorrect_approval | public_conditions_and_interfaces_match |

## Limits

The suite is synthetic and small. Pairs quantify observed differences on these instances. Recovery counts a failed-call episode followed by a successful call. Invalid calls exclude explicitly modeled service and stock failures. Token and cost totals cover recorded usage only. Runtime depends on the machine.
