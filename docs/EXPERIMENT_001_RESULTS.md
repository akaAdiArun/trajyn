# Experiment 001 · Results

The [preregistered protocol](EXPERIMENT_001.md) was committed at
[`349ecc5`](https://github.com/akaAdiArun/trajyn/commit/349ecc586c92dfcde318c98fc7b755d1538e8183)
before held-out model inference. The experiment used Qwen3-8B as source
and Granite 4 3B as target on delivery v2, with explicit public argument
grounding in every condition.

## Verified outcomes

Qwen3 verified **8/8** training attempts. Five traces yielded capsules.
Three verified traces (seeds 322–324) contained unsupported intermediate
errors and were excluded from induction. Their complete traces remain in
the source archive.

| Target arm | Verified | Improvements / regressions vs A | Invalid calls / actions |
| --- | ---: | ---: | ---: |
| A · No memory | 3/10 | 0 / 0 | 62 / 104 |
| B · Raw trajectory | 1/10 | 1 / 3 | 58 / 117 |
| C · Procedural summary | 1/10 | 1 / 3 | 76 / 120 |
| D · Capability capsule | 0/10 | 0 / 3 | 80 / 120 |
| E · Irrelevant trajectory | 0/10 | 0 / 3 | 120 / 120 |

The primary D–A difference was **−30 percentage points** on the fixed
sample. The paired bootstrap interval was **−60 to 0 points** and the
exact paired sign test gave **p = 0.25**. A verified seeds 514, 518, and
519. B and C each verified seed 516. D and E lost the three baseline
successes and gained none.

All ten D prompts received a capsule. Compatibility checked the available
tool contracts and the workflow. The target still made 80 invalid calls
and repeated an earlier action 92 times under D. Acceptance records
admissibility of memory. The model's internal use remains unobserved.
The strict binder resolved 83 of 163 requested identifier positions in D
from prior public values. That fraction measures executable action
grounding, including missing prerequisites. It does not measure the
model's ability to copy identifiers unaided.

## Interpretation

This model pair and retrieval policy produced observed negative transfer
on three paired tasks. Ten tasks, one target family, and one public-binding
configuration leave the size and generality of the effect uncertain.
A subsequent study should test branch relevance beyond interface matching
and measure whether the runtime can identify when to abstain from transfer.

## Artifacts

- [Analysis and uncertainty](../examples/experiment-001/run/evaluation/analysis.md)
- [Paired JSON](../examples/experiment-001/run/evaluation/results.json) and [CSV](../examples/experiment-001/run/evaluation/results.csv)
- [Source trajectories](../examples/experiment-001/run/source), [capsules](../examples/experiment-001/run/capsules.jsonl), and [all target traces](../examples/experiment-001/run/evaluation/trajectories)
- [Retrieval scores and condition order](../examples/experiment-001/run/evaluation/retrieval.json)
- [Model digests, proposals, and inference totals](../examples/experiment-001/run/pilot.json)
- [Validation configurations](CALIBRATION.md) and [Milestone 2 pilot](LOCAL_PILOT.md)
