# Paired analysis

| Arm | Verified (Wilson 95%) | Improved / regressed vs A | Paired delta (95%) | Paired sign p | Mean action delta | Invalid calls | Matching identifiers | Delivered | Accepted / rejected |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 4/6 (30% to 90%) | 0/0 | +0% (+0% to +0%) | 1.000 | +0.00 | 8/47 | 64/73 | 0 | 0/0 |
| B | 1/6 (3% to 56%) | 1/4 | -50% (-100% to +17%) | 0.375 | +1.83 | 51/58 | 16/72 | 6 | 0/0 |
| C | 4/6 (30% to 90%) | 2/2 | +0% (-67% to +67%) | 1.000 | +1.00 | 6/53 | 75/80 | 6 | 0/0 |
| D | 2/6 (10% to 70%) | 1/3 | -33% (-83% to +33%) | 0.625 | +1.33 | 10/55 | 70/80 | 6 | 6/0 |
| E | 6/6 (61% to 100%) | 2/0 | +33% (+0% to +67%) | 0.500 | -0.33 | 4/45 | 68/72 | 6 | 0/0 |
| F | 4/6 (30% to 90%) | 0/0 | +0% (+0% to +0%) | 1.000 | +0.00 | 8/47 | 64/73 | 0 | 6/0 |

Intervals for paired deltas resample whole held-out tasks. Estimates are descriptive for the fixed, small task set. The sign tests are unadjusted. Matching identifiers means the executed value matched a public value available before the call. In a public-grounded configuration it measures executed bindings, not the model's ability to reproduce identifiers. Model inference usage is in the comparison and complete call totals in the pilot metadata.

## Verification failures

- A · `case_not_closed` (1), `incorrect_inventory` (1), `incorrect_or_missing_remedy` (2), `incorrect_refund` (1)
- B · `case_not_closed` (5), `incorrect_approval` (2), `incorrect_inventory` (1), `incorrect_or_missing_remedy` (5), `incorrect_refund` (2)
- C · `case_not_closed` (2), `incorrect_inventory` (1), `incorrect_or_missing_remedy` (1)
- D · `case_not_closed` (4), `incorrect_approval` (1), `incorrect_inventory` (1), `incorrect_or_missing_remedy` (2), `incorrect_refund` (1)
- E · none
- F · `case_not_closed` (1), `incorrect_inventory` (1), `incorrect_or_missing_remedy` (2), `incorrect_refund` (1)

## Branch-aware vs static capsule

F vs D yielded 3 gains and 1 regressions (+33%, 95% interval -33% to +83%, paired sign p = 0.625).
Across 6 F attempts, 0 activated, 6 abstained, and 0 withdrew.
Capsules remained in 46 D tool-producing prompts after the shadow gate flagged divergence and 0 F prompts after divergence.

| Seed | Verified outcome F minus D |
| ---: | ---: |
| 528 | -1 |
| 529 | +1 |
| 530 | +0 |
| 531 | +0 |
| 532 | +1 |
| 533 | +1 |
