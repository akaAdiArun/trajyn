# Experiment 003B — Compiled evidence at a delivery handoff

Experiment 003B uses deterministic extraction from model-generated training
traces. Experiment 003's three Qwen induction revisions ended without an
accepted lesson and with zero Granite target attempts. Those results and all
three archives remain preserved under `runs/experiment-003`,
`runs/experiment-003-r2`, and `runs/experiment-003-r3`.

The new question is whether an evidence-backed hint improves verified task
completion, and whether showing the same hint after its prerequisites become
publicly available improves on showing it up front.

## Compilation and preparation

The compiler reuses all twelve original Qwen source attempts. The verified
archive importer checks their seals, reproduces their exact requests, replays
the saved replies through the existing adapter and argument grounding, and
checks source and target model identities against the installed digests.
Preparation performs no Qwen inference and imports no induction proposals.

The revision 3 extractor enumerates successful warehouse-shipping and
locker-replacement actions from independently verified Qwen training runs.
A positive handoff requires a well-formed receipt returned by the producing
action and consumed by a later successful `close_case` for the same ticket.
The compiler derives producer coverage, producer observation codes, and all
citations from these pairs. `case_closed` is a consumer observation.

Receipt bindings, activation predicates, exclusions, compatibility, and the
fixed hint renderer are predefined semantics of the supported handoff.
Compilation preserves them. It rejects missing evidence and inconsistent
workflow support. The lesson schema shares a success-code set across its
producers, so preparation rejects a cross-product of producer/code pairs that
the traces do not support. It never widens one route's observed code support
to match another route.

The existing provenance validator independently checks cited executions and
value flow, and the development replay checks all prefixes of twelve separate
development examples. `compiler-audit.json` records every supporting producer,
observation code, source trajectory, and pair of step references. Compiling
the same verified records in a different input order yields the same artifact.

## Frozen target comparison

The 24 held-out tasks, nine shared synthetic profile families, splits, case
types, and reference reachability come from the committed Experiment 003
design. There are eight familiar cases, eight alternate-route cases, and eight
look-alikes. Positive route differences include parcel lookup, backup carrier,
carrier retry, warehouse retry, and combinations of those operations. All eight
look-alike reference executions produce alternate-remedy receipts and close.

| Arm | Memory intervention |
| --- | --- |
| A | No memory |
| F | Original prefix-gated policy using compatible capsules induced from verified training traces |
| G | Compiled lesson offered when the existing public evidence gate activates |
| G-static | Same compiled lesson and renderer offered from the start |

Arm order rotates by task index. A missing compatible F capsule is explicitly
unavailable. It never becomes a no-memory F attempt. Every available arm starts
with a fresh identical simulator instance.

The target remains `granite4:3b` at the source archive's recorded digest.
Each model decision uses temperature zero, seed 17, context 4096, at most 160
output tokens, JSON action mode, public argument grounding, a 75-second call
timeout, and a ten-decision attempt limit. The shared gate, renderer, public
task interface, and adapter retain their existing behavior.

The separate freeze is `docs/EXPERIMENT_003B_FROZEN.json`. It contains the
compiler revision, actual model identities, source import provenance, compiled
lesson hash, exact route/code support, code and input hashes, all source
references, task manifest, arm order, settings, F availability, and analysis
rules. Commit that exact freeze on the feature branch before target inference.
Preparation and run reject another live execution of these held-out task
instances. A shared OS lock prevents duplicate 003B writers.

## Outcomes and diagnostics

The primary outcome is independently verified completion, G versus A.
Secondary comparisons are G versus G-static for timing and G versus F for
the historical policy. Report verified counts and observed denominators
overall and for each case type. Paired analysis uses complete matched cells
and reports gains, losses, ties, percentage-point differences, the existing
exact sign test, and the existing descriptive 95% paired bootstrap interval
with 10,000 resamples and seed 1741. Repeated synthetic profile families limit
independence. Missing or infrastructure-incomplete attempts remain unscored.

Grounding already supplies `receipt_id` after Granite chooses `close_case`.
The post-receipt audit therefore records the first chosen action after public
evidence qualifies, whether that model call actually received the hint, calls
before closure, extra calls beyond direct closure, and cases that never close.
It distinguishes never reaching the evidence, an eligible call without advice,
and terminal eligibility after the last tool call with no next model call.
Delivery on look-alikes remains visible. G-static's conditional symbolic hints
before evidence are recorded separately from resolved bindings.

Call efficiency is secondary and separate from verified completion. Report
paired call differences for complete matched attempts and separately for pairs
where both arms verified. An early failed attempt can consume fewer calls.
Observed actions after hints establish the recorded sequence of behavior.
They do not establish the model's internal reliance on the hint. Hint delivery
alone supplies no completion or efficiency benefit.

## Operator commands

From the repository root, use the existing environment and loopback Ollama
service. Preparation imports the original source archive and creates a new
003B output directory and proposed freeze. It refuses existing output artifacts
or earlier target inference for the same dataset.

```sh
python -m trajyn.compiled_study prepare
```

After tests and the pre-inference offline replay pass, commit the freeze.

```sh
git add docs/EXPERIMENT_003B_FROZEN.json
git commit -m "Freeze Experiment 003B compiled lesson and target protocol"
python -m trajyn.compiled_study run
```

Run the same command to resume after interruption or the four-hour invocation
cap. Finished attempts remain immutable. Each incomplete retry gets a new
numbered directory, preserving its earlier calls and errors. Source and target
digests and the committed freeze are checked again before inference.

```sh
python -m trajyn.compiled_study run
python -m trajyn.compiled_study replay
```

The output is `runs/experiment-003b`. Each attempt retains exact requests,
raw replies, incremental progress, the replayable execution, delivery audit,
usage, termination, and a checksum seal. `target-progress.json` includes the
latest post-receipt diagnostic. `report.json` includes all per-attempt
diagnostics, paired completion and efficiency summaries, missing cells,
incorrect delivery counts, model errors, invalid calls, steps, and token usage.
`report.md` provides the corresponding readable completion tables and summaries.
Offline replay rebuilds the compiler audit, exact prompts, adapter outputs,
grounding, gate lifecycle, simulator verification, and results without Ollama.
