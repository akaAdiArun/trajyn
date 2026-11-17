# Paired delivery-exception comparison

Target `ollama/llama3.2:3b` (a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72). Source ollama/qwen3:8b.
Partition `test`. Seeds 200, 202. Budget 8 actions per attempt.

| Condition | Verified | Closed | Mean actions | Invalid calls | Tool failures | Recoveries | Mean ms | Delivered / Used | Accepted / Rejected | Improved / Regressed vs A |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A · No memory | 0/2 | 0/2 | 8.00 | 16 | 16 | 0 | 5065.920 | 0 / unknown | — | 0 / 0 |
| B · Raw trajectory | 0/2 | 0/2 | 8.00 | 16 | 16 | 0 | 3415.623 | 2 / unknown | — | 0 / 0 |
| C · Procedural summary | 0/2 | 0/2 | 8.00 | 3 | 3 | 3 | 3500.041 | 2 / unknown | — | 0 / 0 |
| D · Capsule | 0/2 | 0/2 | 8.00 | 16 | 16 | 0 | 3282.644 | 1 / unknown | 1 / 1 | 0 / 0 |
| E · Irrelevant trajectory | 0/2 | 0/2 | 8.00 | 16 | 16 | 0 | 2408.077 | 2 / unknown | — | 0 / 0 |

## Recorded usage

| Condition | Input tokens | Output tokens | Estimated cost (USD) |
| --- | ---: | ---: | ---: |
| A | 11175 | 578 | — |
| B | 19738 | 520 | — |
| C | 14381 | 606 | — |
| D | 13990 | 584 | — |
| E | 16778 | 340 | — |

## Per-task outcomes

| Seed | Condition | Verified | Actions | Failure codes | Capsule check |
| --- | --- | --- | ---: | --- | --- |
| 200 | A | no | 8 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 200 | B | no | 8 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 200 | C | no | 8 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory, incorrect_refund | — |
| 200 | D | no | 8 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | missing_tool:ship_replacement |
| 200 | E | no | 8 | case_not_closed, incorrect_or_missing_remedy, incorrect_inventory | — |
| 202 | A | no | 8 | case_not_closed, incorrect_or_missing_remedy | — |
| 202 | B | no | 8 | case_not_closed, incorrect_or_missing_remedy | — |
| 202 | C | no | 8 | case_not_closed | — |
| 202 | D | no | 8 | case_not_closed, incorrect_or_missing_remedy | public_conditions_and_interfaces_match |
| 202 | E | no | 8 | case_not_closed, incorrect_or_missing_remedy | — |

## Limits

The suite is synthetic and small. Pairs quantify observed differences on these instances. Recovery counts a failed-call episode followed by a successful call. Invalid calls exclude explicitly modeled service and stock failures. Token and cost totals cover recorded usage only. Runtime depends on the machine.
