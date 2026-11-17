# Paired analysis

| Arm | Verified (Wilson 95%) | Improved / regressed vs A | Paired delta (95%) | Paired sign p | Mean action delta | Invalid calls | Matching identifiers | Delivered | Accepted / rejected |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 3/10 (11% to 60%) | 0/0 | +0% (+0% to +0%) | 1.000 | +0.00 | 62/104 | 90/142 | 0 | 0/0 |
| B | 1/10 (2% to 40%) | 1/3 | -20% (-50% to +20%) | 0.625 | +1.30 | 58/117 | 128/212 | 10 | 0/0 |
| C | 1/10 (2% to 40%) | 1/3 | -20% (-50% to +20%) | 0.625 | +1.60 | 76/120 | 89/164 | 10 | 0/0 |
| D | 0/10 (0% to 28%) | 0/3 | -30% (-60% to +0%) | 0.250 | +1.60 | 80/120 | 83/163 | 10 | 10/0 |
| E | 0/10 (0% to 28%) | 0/3 | -30% (-60% to +0%) | 0.250 | +1.60 | 120/120 | 2/122 | 10 | 0/0 |

Intervals for paired deltas resample whole held-out tasks. Estimates are descriptive for the fixed, small task set. The sign tests are unadjusted. Matching identifiers means the executed value matched a public value available before the call. In a public-grounded configuration it measures executed bindings, not the model's ability to reproduce identifiers. Model inference usage is in the comparison and complete call totals in the pilot metadata.

## Verification failures

- A · `case_not_closed` (6), `incorrect_approval` (3), `incorrect_inventory` (3), `incorrect_or_missing_remedy` (7), `incorrect_refund` (4)
- B · `case_not_closed` (9), `incorrect_approval` (2), `incorrect_inventory` (3), `incorrect_or_missing_remedy` (9), `incorrect_refund` (2)
- C · `case_not_closed` (9), `incorrect_approval` (2), `incorrect_inventory` (3), `incorrect_or_missing_remedy` (8), `incorrect_refund` (2)
- D · `case_not_closed` (10), `incorrect_approval` (3), `incorrect_inventory` (3), `incorrect_or_missing_remedy` (9), `incorrect_refund` (3)
- E · `case_not_closed` (10), `incorrect_approval` (3), `incorrect_inventory` (3), `incorrect_or_missing_remedy` (10), `incorrect_refund` (3)
