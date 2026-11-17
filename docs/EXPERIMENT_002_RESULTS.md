# Experiment 002 · Results

[Preregistered protocol](EXPERIMENT_002.md) ·
[Protocol merge](https://github.com/akaAdiArun/trajyn/pull/19) ·
[Validation traces](../examples/experiment-002/calibration)

The protocol merged into `main` at 20:38:06 UTC on 17 November 2026. The frozen
run sequence began at 20:38:11 UTC. The source was Qwen3 8B. The two targets were
Granite 4 3B and Ministral 3 3B, each tested with public argument grounding and
with unaided tool arguments. Each condition used the same six held-out
delivery-v2 seeds and the independent final-state verifier.

Qwen verified all eight training attempts. Five supported capsule induction.
The remaining verified traces (338, 339, 340) contained tool outcomes outside
the induction rules. All attempts and exclusion reasons are in the archive.
The four cells used identical source traces, capsule IDs, and rankings.

## Verified completion

Every entry is independently verified tasks out of six. Experiment 002
recorded 144 target attempts and 1,274 target model calls, plus 44 source calls.

| Target / argument mode | A · None | B · Raw | C · Summary | D · Static | E · Irrelevant | F · Branch-aware |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Granite / public grounding | 3/6 | 0/6 | 1/6 | 1/6 | 0/6 | 3/6 |
| Granite / unaided | 2/6 | 0/6 | 1/6 | 0/6 | 0/6 | 2/6 |
| Ministral / public grounding | 5/6 | 0/6 | 3/6 | 3/6 | 5/6 | 5/6 |
| Ministral / unaided | 4/6 | 1/6 | 4/6 | 2/6 | 6/6 | 4/6 |

| Target / argument mode | F gains / losses vs D | Paired difference, 95% interval | Sign-test p | D regressions vs A | F regressions vs A | Post-divergence prompts, D → F |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Granite / public grounding | 2 / 0 | +33 pp (0 to +67) | 0.500 | 2/6 | 0/6 | 47 → 0 |
| Granite / unaided | 2 / 0 | +33 pp (0 to +67) | 0.500 | 2/6 | 0/6 | 52 → 0 |
| Ministral / public grounding | 2 / 0 | +33 pp (0 to +67) | 0.500 | 2/6 | 0/6 | 42 → 0 |
| Ministral / unaided | 3 / 1 | +33 pp (−33 to +83) | 0.625 | 3/6 | 0/6 | 46 → 0 |

## Granite with public grounding

Branch-aware transfer verified **3/6** tasks, with two paired gains and zero
regressions relative to static transfer (**1/6**, +33 percentage points,
paired 95% bootstrap interval 0 to +67 points, exact sign-test p = 0.50).
No memory verified the same three tasks as branch-aware transfer. All six
branch-aware attempts abstained before capsule delivery.

- On seed 530 the primary carrier returned `carrier_unavailable`. The static
  arm obtained backup evidence of a delivered parcel, attempted an ineligible
  replacement, then repeatedly acknowledged delivery without closing the case.
  Branch-aware and no-memory arms acknowledged delivery and closed it.
- On seed 531 the initial case required a parcel lookup. The static arm
  repeatedly attempted inspection without the required identifier or re-read
  the case. Branch-aware and no-memory arms recovered the parcel record,
  obtained backup carrier evidence, and ultimately scheduled pickup and closed.

These two seeds show where static guidance accompanied failure and abstention
preserved the no-memory outcome. The paired interval includes zero.
The observations establish what each run executed. The model's internal
reliance on a particular prompt element is unobserved.

## Applicability and tradeoffs

All 24 D and all 24 F candidates passed the initial compatibility checks.
Static transfer delivered guidance in every D trial. F abstained in all 24
trials, 16 on observation mismatches and eight on operation mismatches.
The shadow gate counted 187 tool-producing D prompts that still carried
guidance after divergence. F delivered zero. Activation and withdrawal
each occurred zero times in the model study. Both were exercised in the
[deterministic counterfactual](BRANCH_TRANSFER.md#offline-counterfactual).

F verified exactly the same seeds as A in each cell. Ministral unaided
also solved seed 528 with static guidance after F abstained and failed.
Its irrelevant-memory control verified 6/6, gaining two tasks over A.
The results support withholding mismatched guidance and show where a
conservative gate can miss useful guidance. Each paired interval includes
zero. The six synthetic profiles repeat across the model and mode cells,
so the cells are reported separately and support no pooled uncertainty
estimate. With zero activations, this experiment has no evidence that
delivered branch-aware guidance improves execution.

Grounding increased verified A/F outcomes by one task for each target.
The diagnostic effects differed by model. Granite's D invalid-call
count was 25/56 with grounding and 48/60 unaided. For Ministral, those
counts were 7/51 and 10/55. Public grounding changes executed arguments
and can leave some calls unresolved. Identifier accuracy in the grounded
cell therefore measures executed bindings. An original proposal may use
different values. The complete tables record matching identifiers, counts
of repeated calls and recoveries, action totals, timing, and token usage.

## Reading the artifacts

Each run's `pilot.json` records full model digests, call counts, terminations,
original proposals, and public grounding substitutions. `evaluation/results.csv`
records paired outcomes by seed. `evaluation/analysis.md` gives uncertainty,
invalid calls, executed identifier accuracy, and failure categories.
`evaluation/comparison.md` reports actions, recoveries, recorded tokens, and
timings. `evaluation/transfer.json` records the D/F lifecycle by tool-producing
turn, including each abstention or withdrawal reason. The source manifests and
capsules match across the four cells. CI replays their executions and
reconstructs the gate audits and analysis without Ollama or model weights.

- [Granite with public grounding](../examples/experiment-002/run/grounded)
- [Granite with unaided tool arguments](../examples/experiment-002/run/unaided)
- [Ministral with public grounding](../examples/experiment-002/run/secondary-grounded)
- [Ministral with unaided tool arguments](../examples/experiment-002/run/secondary-unaided)
