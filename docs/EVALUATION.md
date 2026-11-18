# Paired offline evaluation

The evaluator below uses deterministic target fixtures. Experiment 003B used
live Granite inference with a separate frozen protocol, comparing no memory,
the original prefix gate, and the same compiled hint shown on evidence or up
front. [Experiment 003B protocol](EXPERIMENT_003B.md) · [Results](EXPERIMENT_003B_RESULTS.md)

The default experiment uses training seeds 0–7, validation seeds 100–105 when
requested, and test seeds 200–207. Condition order rotates by one position for
each fresh held-out task. Each receives the same goal, public tools, target
agent, and eight-action budget. See [benchmark partitions](BENCHMARK.md).

1. Collect one delivery trajectory per training seed. Every trajectory preserves
   its agent identity, seed, split, actions, observations, and independently
   verified outcome.
2. Replay each successful trajectory. The inducer binds arguments to matching
   task fields and observations from earlier steps. It keeps result codes and
   public branch conditions, including carrier status and positive stock. It
   rejects unsupported actions, unobserved IDs, held-out examples, and records
   whose replay disagrees with the file.
3. Rank verified training sources in the same workflow by capsule applicability
   and tool compatibility, the fraction of required tool contracts available,
   and token overlap between public goals. Goals omit the instance ticket ID.
   Break ties by source seed and content ID. Conditions B, C, and D receive
   different representations of the same top-ranked source. When every
   candidate is incompatible, D rejects memory while B and C still receive
   the top candidate's corresponding representations. Scores and reasons
   appear in `retrieval.json`.
4. Start a new environment and new target instance for each task-condition pair.
   Use this exact paired matrix.

| Condition | Context delivered to the target |
| --- | --- |
| A | Current task, tools, and its own action history |
| B | A plus the selected source's public trajectory |
| C | A plus a generalized tool sequence and argument-role summaries derived from the source |
| D | A plus the selected capsule's goal, guarded steps, and argument bindings if compatible |
| E | A plus a verified trajectory from the original replacement suite |

The target fixture interprets the context it receives and falls back to its
public-observation policy when a suggestion cannot continue. It checks raw
trajectory branch observations and capsule guards using the same public facts.
A summary offers tool order and argument roles. The irrelevant control uses
different tools. The fixture ignores unsupported suggestions.

The evaluator records provenance and capsule decisions outside the agent context.
It records fixture memory use when the target emits an action from that memory.
Success and completion come from environment state. Invalid calls exclude
explicitly modeled service and stock errors. Recovery episodes count a failed
call followed by a successful call. Improvements and regressions compare each
seed with A. Changes in effort are also reported for unchanged outcomes.

The default evaluation records elapsed time. For byte reproducibility, use
`evaluate --no-timing` and supply an explicit `induce --created-at` timestamp.
JSON captures paired outcomes and execution settings, CSV contains trial rows,
and Markdown summarizes metrics and failures. Per-attempt JSONL files allow
the outcomes to be replayed from state. Store generated runs under ignored
`runs/` and `capsules/` directories.

Fixed policies verify context isolation, applicability decisions, and fallback
behavior on this synthetic sample. Cross-model estimates require separate
model experiments. The single-trace inducer represents one observed branch
per capsule.

The checked-in [offline comparison](../examples/offline/comparison.md)
records one run of the default plan. The [seed 0 source trace](../examples/offline/train-0.jsonl)
and its [capsule](../examples/offline/train-0-capsule.json) show the evidence
and bindings used by that run.
