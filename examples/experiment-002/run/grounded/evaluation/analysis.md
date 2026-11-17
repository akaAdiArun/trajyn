# Paired analysis

| Arm | Verified (Wilson 95%) | Improved / regressed vs A | Paired delta (95%) | Paired sign p | Mean action delta | Invalid calls | Matching identifiers | Delivered | Accepted / rejected |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 3/6 (19% to 81%) | 0/0 | +0% (+0% to +0%) | 1.000 | +0.00 | 26/52 | 53/76 | 0 | 0/0 |
| B | 0/6 (0% to 39%) | 0/3 | -50% (-83% to -17%) | 0.250 | +1.33 | 28/60 | 71/104 | 6 | 0/0 |
| C | 1/6 (3% to 56%) | 0/2 | -33% (-67% to +0%) | 0.500 | +0.83 | 23/57 | 63/83 | 6 | 0/0 |
| D | 1/6 (3% to 56%) | 0/2 | -33% (-67% to +0%) | 0.500 | +0.67 | 25/56 | 55/79 | 6 | 6/0 |
| E | 0/6 (0% to 39%) | 0/3 | -50% (-83% to -17%) | 0.250 | +1.33 | 60/60 | 0/60 | 6 | 0/0 |
| F | 3/6 (19% to 81%) | 0/0 | +0% (+0% to +0%) | 1.000 | +0.00 | 26/52 | 53/76 | 0 | 6/0 |

Intervals for paired deltas resample whole held-out tasks. Estimates are descriptive for the fixed, small task set. The sign tests are unadjusted. Matching identifiers means the executed value matched a public value available before the call. In a public-grounded configuration it measures executed bindings, not the model's ability to reproduce identifiers. Model inference usage is in the comparison and complete call totals in the pilot metadata.

## Verification failures

- A · `case_not_closed` (3), `incorrect_approval` (2), `incorrect_inventory` (1), `incorrect_or_missing_remedy` (3), `incorrect_refund` (2)
- B · `case_not_closed` (6), `incorrect_approval` (2), `incorrect_inventory` (2), `incorrect_or_missing_remedy` (6), `incorrect_refund` (2)
- C · `case_not_closed` (5), `incorrect_approval` (1), `incorrect_inventory` (1), `incorrect_or_missing_remedy` (3), `incorrect_refund` (1)
- D · `case_not_closed` (5), `incorrect_approval` (2), `incorrect_inventory` (1), `incorrect_or_missing_remedy` (4), `incorrect_refund` (2)
- E · `case_not_closed` (6), `incorrect_approval` (2), `incorrect_inventory` (2), `incorrect_or_missing_remedy` (6), `incorrect_refund` (2)
- F · `case_not_closed` (3), `incorrect_approval` (2), `incorrect_inventory` (1), `incorrect_or_missing_remedy` (3), `incorrect_refund` (2)

## Branch-aware vs static capsule

F vs D yielded 2 gains and 0 regressions (+33%, 95% interval +0% to +67%, paired sign p = 0.500).
Across 6 F attempts, 0 activated, 6 abstained, and 0 withdrew.
Capsules remained in 47 D tool-producing prompts after the shadow gate flagged divergence and 0 F prompts after divergence.

| Seed | Verified outcome F minus D |
| ---: | ---: |
| 528 | +0 |
| 529 | +0 |
| 530 | +1 |
| 531 | +1 |
| 532 | +0 |
| 533 | +0 |
