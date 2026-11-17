# Paired analysis

| Arm | Verified (Wilson 95%) | Improved / regressed vs A | Paired delta (95%) | Paired sign p | Mean action delta | Invalid calls | Matching identifiers | Delivered | Accepted / rejected |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 2/6 (10% to 70%) | 0/0 | +0% (+0% to +0%) | 1.000 | +0.00 | 17/52 | 74/86 | 0 | 0/0 |
| B | 0/6 (0% to 39%) | 0/2 | -33% (-67% to +0%) | 0.500 | +1.33 | 60/60 | 0/160 | 6 | 0/0 |
| C | 1/6 (3% to 56%) | 0/1 | -17% (-50% to +0%) | 1.000 | +0.33 | 25/54 | 57/85 | 6 | 0/0 |
| D | 0/6 (0% to 39%) | 0/2 | -33% (-67% to +0%) | 0.500 | +1.33 | 48/60 | 40/88 | 6 | 6/0 |
| E | 0/6 (0% to 39%) | 0/2 | -33% (-67% to +0%) | 0.500 | +1.33 | 60/60 | 0/60 | 6 | 0/0 |
| F | 2/6 (10% to 70%) | 0/0 | +0% (+0% to +0%) | 1.000 | +0.00 | 17/52 | 74/86 | 0 | 6/0 |

Intervals for paired deltas resample whole held-out tasks. Estimates are descriptive for the fixed, small task set. The sign tests are unadjusted. Matching identifiers means the executed value matched a public value available before the call. In a public-grounded configuration it measures executed bindings, not the model's ability to reproduce identifiers. Model inference usage is in the comparison and complete call totals in the pilot metadata.

## Verification failures

- A · `case_not_closed` (4), `incorrect_approval` (2), `incorrect_inventory` (1), `incorrect_or_missing_remedy` (4), `incorrect_refund` (2)
- B · `case_not_closed` (6), `incorrect_approval` (2), `incorrect_inventory` (2), `incorrect_or_missing_remedy` (6), `incorrect_refund` (2)
- C · `case_not_closed` (4), `incorrect_approval` (2), `incorrect_inventory` (2), `incorrect_or_missing_remedy` (5), `incorrect_refund` (3)
- D · `case_not_closed` (6), `incorrect_approval` (2), `incorrect_inventory` (2), `incorrect_or_missing_remedy` (6), `incorrect_refund` (2)
- E · `case_not_closed` (6), `incorrect_approval` (2), `incorrect_inventory` (2), `incorrect_or_missing_remedy` (6), `incorrect_refund` (2)
- F · `case_not_closed` (4), `incorrect_approval` (2), `incorrect_inventory` (1), `incorrect_or_missing_remedy` (4), `incorrect_refund` (2)

## Branch-aware vs static capsule

F vs D yielded 2 gains and 0 regressions (+33%, 95% interval +0% to +67%, paired sign p = 0.500).
Across 6 F attempts, 0 activated, 6 abstained, and 0 withdrew.
Capsules remained in 52 D tool-producing prompts after the shadow gate flagged divergence and 0 F prompts after divergence.

| Seed | Verified outcome F minus D |
| ---: | ---: |
| 528 | +0 |
| 529 | +0 |
| 530 | +1 |
| 531 | +0 |
| 532 | +0 |
| 533 | +1 |
