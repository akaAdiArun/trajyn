# Paired analysis

| Arm | Verified (Wilson 95%) | Improved / regressed vs A | Paired delta (95%) | Paired sign p | Mean action delta | Invalid calls | Matching identifiers | Delivered | Accepted / rejected |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 5/6 (44% to 97%) | 0/0 | +0% (+0% to +0%) | 1.000 | +0.00 | 7/46 | 62/69 | 0 | 0/0 |
| B | 0/6 (0% to 39%) | 0/5 | -83% (-100% to -50%) | 0.062 | +2.33 | 60/60 | 2/62 | 6 | 0/0 |
| C | 3/6 (19% to 81%) | 0/2 | -33% (-67% to +0%) | 0.500 | +0.67 | 7/50 | 59/66 | 6 | 0/0 |
| D | 3/6 (19% to 81%) | 0/2 | -33% (-67% to +0%) | 0.500 | +0.83 | 7/51 | 63/69 | 6 | 6/0 |
| E | 5/6 (44% to 97%) | 1/1 | +0% (-50% to +50%) | 1.000 | -0.83 | 1/41 | 58/59 | 6 | 0/0 |
| F | 5/6 (44% to 97%) | 0/0 | +0% (+0% to +0%) | 1.000 | +0.00 | 7/46 | 62/69 | 0 | 6/0 |

Intervals for paired deltas resample whole held-out tasks. Estimates are descriptive for the fixed, small task set. The sign tests are unadjusted. Matching identifiers means the executed value matched a public value available before the call. In a public-grounded configuration it measures executed bindings, not the model's ability to reproduce identifiers. Model inference usage is in the comparison and complete call totals in the pilot metadata.

## Verification failures

- A · `incorrect_inventory` (1), `incorrect_or_missing_remedy` (1), `incorrect_refund` (1)
- B · `case_not_closed` (6), `incorrect_approval` (2), `incorrect_inventory` (2), `incorrect_or_missing_remedy` (6), `incorrect_refund` (2)
- C · `case_not_closed` (3), `incorrect_inventory` (1), `incorrect_or_missing_remedy` (2)
- D · `case_not_closed` (3), `incorrect_approval` (1), `incorrect_inventory` (1), `incorrect_or_missing_remedy` (2), `incorrect_refund` (1)
- E · `case_not_closed` (1), `incorrect_approval` (1), `incorrect_or_missing_remedy` (1), `incorrect_refund` (1)
- F · `incorrect_inventory` (1), `incorrect_or_missing_remedy` (1), `incorrect_refund` (1)

## Branch-aware vs static capsule

F vs D yielded 2 gains and 0 regressions (+33%, 95% interval +0% to +67%, paired sign p = 0.500).
Across 6 F attempts, 0 activated, 6 abstained, and 0 withdrew.
Capsules remained in 42 D tool-producing prompts after the shadow gate flagged divergence and 0 F prompts after divergence.

| Seed | Verified outcome F minus D |
| ---: | ---: |
| 528 | +0 |
| 529 | +0 |
| 530 | +0 |
| 531 | +0 |
| 532 | +1 |
| 533 | +1 |
