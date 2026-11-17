# Branch-aware transfer

Static transfer admits a capsule after checking its workflow and required tool
contracts. Those public checks cannot distinguish two delivery cases served by
the same interface. Experiment 001 recorded three paired regressions under
static transfer.

The branch-aware evaluator uses the same ranked candidate as static transfer.
It waits for a live action–observation prefix that matches the source through
its first factual observation guard. A capsule with no factual guard cannot
activate. If the operation, observation, or argument prerequisites diverge
before activation, the gate abstains. After activation the same checks can
withdraw guidance from future requests. The runner preserves all public
actions and observations. Withdrawal cannot erase information that was
already presented to an agent.

The audit records candidate selection, compatibility, conditional waiting,
activation, divergence, withdrawal, abstention, and completion with the
observed step count and reason. The gate receives the public task, published
tool contracts, and live public history. It supplies memory without taking
actions itself.

Run `trajyn evaluate --branch-aware` to add F (branch-aware capsule) to
A–E. D and F use the identical source capsule. `transfer.json` records their
lifecycle and grounded guidance by tool-producing turn. D's lifecycle is a
shadow evaluation of its observed trace. Its continuation count measures
tool-producing turns that still received static memory after the shadow
gate would have withheld it. This is an exposure measure. The verifier
separately measures each task outcome.

## Multiple verified source branches

`assemble_branches(sources, created_at=...)` independently replays and induces
each supplied training trace for one workflow, normalized goal, and verifier.
It keeps the existing single-trace capsule format, with each capsule retaining
its source ID and step references. It rejects duplicate evidence and mixed
workflows. A caller can pass the resulting candidates to `BranchTransfer`.
When different procedures still match the same public prefix, the gate waits
for distinguishing evidence. Identical procedures can corroborate a matching
branch without changing its actions. Experiment 002 uses one candidate per
attempt in both D and F to isolate the effect of timing and withdrawal.

## Offline counterfactual

Collect source seed 0 for delivery v1, induce with
`--created-at 2026-01-01T00:00:00+00:00`, and evaluate with
`--branch-aware --no-timing --seeds 200,201,202,203`. Analyze the resulting
`results.json` with `trajyn analyze`.

| Arm | Independently verified | Actions | Invalid actions |
| --- | ---: | ---: | ---: |
| A · No memory | 4/4 | 20 | 0 |
| B · Raw trajectory | 4/4 | 20 | 0 |
| C · Procedural summary | 4/4 | 22 | 1 |
| D · Static capsule | 4/4 | 20 | 0 |
| E · Irrelevant memory | 4/4 | 20 | 0 |
| F · Branch-aware capsule | 4/4 | 20 | 0 |

F rejected an unsupported tool on seed 200, activated then withdrew on stale
stock in 201, and abstained when the live carrier response differed on 202 and
203. D continued delivering memory on seven tool-producing turns past those
divergences. F delivered none past divergence and the fixture still recovered
from the stale listing and carrier retry. This exercises the runtime with
deterministic policies. Experiment 002 separately measures model behavior.
