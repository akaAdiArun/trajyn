# Experiment 003 — Public evidence at an action handoff

Protocol date is November 18, 2026. The machine-readable design is
[EXPERIMENT_003_PLAN.json](EXPERIMENT_003_PLAN.json). Local inference is opt-in.

Experiment 002's original prefix gate withheld advice in all 24 F attempts.
It demonstrated suppression of mismatched guidance. Its delivered advice had
zero opportunities to improve execution. Experiment 003 retains that policy
as F and tests an additional policy using public evidence regardless of the
route taken to obtain it. The primary comparison is G versus A.

## Lesson induction and acceptance

The source is `qwen3:8b`. Collect twelve training cases, preserving verified
successes, failures, raw responses, original proposals, and public grounding.
At most fourteen model source attempts, including infrastructure retries, are
allowed. Two separately labeled scripted training counterexamples stop after
producing a remedy and before closing. The total source cap is sixteen.
Scripted records cannot satisfy the model-success requirement.

The learner sees public tool contracts and a compact deterministic contrast
set, with up to two distinct successful routes and two distinct failed routes.
It proposes a single narrow handoff using a restricted JSON vocabulary. Its
input contains no completed candidate or instruction naming the expected rule.
There are at most four calls, with seeds 17–20, temperature zero, an 8192-token
context, 1100 output tokens, and a 75-second timeout per call. Raw proposals,
including rejected proposals, are saved before validation.

The versioned lesson includes a stable content hash, workflow, tool contracts,
typed activation and exclusion predicates, symbolic argument bindings, and
source trajectory and step references. No learner prose or expressions enter
the target prompt. The first valid proposal in call order is accepted. It must
cite a replay-checked, verified Qwen training success for each producing tool,
with the actual observed value flowing to the later consumer action. The
validator checks every prefix of all twelve separate development references,
including completed refund, acknowledgment, and pickup cases. Unsupported
tools, fields, literal instance bindings, invalid citations, and contradictory
data are rejected. No accepted proposal means zero held-out target attempts.

The implemented language currently supports the replacement-to-closure
handoff. Support for other lessons requires a new protocol and validator.

## Gate and renderer

The gate receives only `AgentContext.task`, public `ToolSpec` values, and
previous executed actions and observations. It checks successful supported
replacement operations, accepted response codes, and a well-formed receipt.
The case binding comes from the producing action's `ticket_id`. The receipt
response does not carry that field. Other remedies cannot activate this lesson.

Earlier retry failures do not poison later successful production. Additional
reads and different lookup routes leave the binding intact. Successful closure
ends delivery. Conflicting receipts, a changed case-to-parcel link, later
authoritative carrier contradictions, or a different posted remedy withdraw it.
The policy supplies memory only. The target chooses every action through the
same JSON adapter and public argument grounding in all four arms.

G and G-static share one fixed renderer. Before valid evidence, G-static uses
an unresolved symbolic value. After valid evidence, both render the same live
binding and text. After withdrawal, neither retains an invalid binding.
The audit distinguishes offered memory, a prompt receiving a model response,
and terminal eligibility with no subsequent call. A timeout records attempted
delivery with unknown consumption. It contributes no confirmed delivery.

## Held-out design

Delivery profile version 3 preserves all v1 and v2 seed semantics and business
rules. Training seeds are 600–611, development seeds 804–815, and held-out seeds
1008–1031. The reference policy verifies all tasks within ten decisions before
inference. Reference traces and case-type labels stay outside model and gate
inputs.

The 24 held-out cases comprise eight familiar routes, eight routes requiring
substantively different work, and eight look-alikes. Familiar routes repeat two
profile families. Different routes repeat four families with missing-parcel
lookup, backup carrier, carrier retry, warehouse retry, and combinations of
those changes. Look-alikes repeat three families requiring delivery
acknowledgment, pickup, or approval followed by refund. All eight negative
reference runs produce genuine alternate-remedy receipts and close the case.
There are nine held-out profile families, with repeated synthetic structures
explicitly recorded in the manifest. Distinct case IDs alone add no route.

| Arm | Intervention |
| --- | --- |
| A | No memory |
| F | Original prefix-gated policy with independently induced training capsules |
| G | Accepted learned lesson while public evidence makes it eligible |
| G-static | Same lesson and renderer offered from the first eligible static call |

Plan 96 target cells, each with a fresh environment and `granite4:3b`. Rotate
A/F/G/G-static order by task index. Every arm uses model seed 17, temperature
zero, context 4096, at most 160 generated tokens per decision, ten decisions,
JSON action mode, public grounding, and a 75-second call timeout. Record full
model digests before freezing. Model substitution is prohibited. An F cell with
no compatible source capsule is explicitly unavailable and is excluded from
matched comparisons. Other available arms can still run.

Before held-out inference, commit the generated frozen manifest. It includes
the design, actual model identities, selected lesson hash, code hashes, input
artifact hashes, source traces, proposals, development references, reference
reachability, and F availability. The runner checks that exact committed object
before contacting a target. Stop each invocation after four hours. Sources and
induction have the same per-invocation cap.

## Analysis and provenance

Score independently verified completion. Report counts and denominators overall
and for each case type. Compute paired gains, regressions, ties, and percentage
point differences for G versus A, G-static, and F using complete matched cells.
Use the existing exact sign test and 10,000 task bootstrap samples with seed
1741 for descriptive 95% paired intervals. Shared profile families limit
independence. A small positive pilot would warrant replication.

Keep hint delivery, live binding correctness, missed eligible calls, cases
never reaching the evidence, terminal opportunities, and the next executed
action visible. Following a hint is an observation. Also report step counts,
invalid actions, model errors, infrastructure failures, and input/output tokens.
Missing and incomplete attempts remain unscored. Every attempt has a separate
directory and checksum seal. An OS lock prevents concurrent writers. Resuming
skips finished cells and starts a fresh numbered attempt for incomplete cells.
Previous attempts remain available for offline replay.

Offline replay reconstructs exact model request payloads from public histories,
replays archived replies through the same adapter and grounding code, reruns
the gate, reproduces prompt delivery and independently verifies simulator state.
It checks the frozen artifact hashes and rejects changes or inconsistent audits.
It makes no Ollama requests.

## Operator commands

### Induction revision 3

Revision 3 tests evidence-grounded selection within a predefined
replacement-to-closure handoff. Its positive candidate list is enumerated
from independently replayed, verified Qwen training successes. Each candidate
is a successful `ship_replacement` or `locker_replacement` action returning a
well-formed receipt, followed by a successful `close_case` consuming that
exact receipt for the same ticket. The two producer tools have separate lists.
All qualifying step pairs are included. Inspection, refunds, other remedies,
scripted successes, and unsuccessful model attempts supply no positive
candidates. Training contrasts retain their existing roles.

Qwen receives the candidate references alongside the public contracts and
training contrasts. It selects one or both supported routes and cites the
evidence through the existing structured lesson output. The program supplies
neither a completed lesson nor a manually selected citation subset. The same
provenance, compatibility, symbolic binding, and development checks decide
acceptance. The candidate file and submitted input can be reconstructed
offline. Earlier induction revisions remain independently replayable.

Both failed archives remain intact. This final preparation retry uses the
same twelve replayed source attempts, up to four fresh induction calls, and
the existing deterministic selection rule. Target arms, held-out profiles,
cases, inference limits, and scoring retain the committed design.

```sh
python -m trajyn.lesson_study prepare --output runs/experiment-003-r3 --source-archive runs/experiment-003
```

The retry stops at the preparation result for review of producer coverage and
cited evidence. The proposed freeze remains uncommitted.

### Induction revision 2

The first live preparation collected twelve Qwen source attempts with ten
verified completions. All four induction replies supplied an object in the
`evidence` field and failed validation. That archive stays at
`runs/experiment-003` with its original replies and rejection records.

Revision 2 passes a JSON Schema as Ollama's `format` value. It requires all
lesson fields, structured binding objects, and a nonempty array of citation
objects with string trajectory IDs and positive integer step references.
The schema specifies shapes. The learner must infer the operations, fields,
values, and citations from the same training contrasts. The provenance and
development validators still decide acceptance. Existing revision 1 replies
retain their original format and validation behavior during offline replay.

The retry uses a fresh archive and four fresh induction calls at most. It
reuses all twelve source attempts only after checking their sealed files,
reconstructing their requests and executions offline, and checking source and
target model identities against the installed digests. It copies source
records with an import provenance record. Rejected proposals remain in the
first archive. The held-out cases, profiles, split, arm order, inference limits,
renderer, selection rule, and development validation are unchanged.

```sh
python -m trajyn.lesson_study prepare --output runs/experiment-003-r2 --source-archive runs/experiment-003
```

Preparation generates a proposed freeze only if a lesson passes. This retry
stops after preparation for review of the learned lesson and its citations.

Run from the repository root after installing `.[dev]` in the local environment.
PowerShell can invoke these through `.\.venv\Scripts\python.exe`.

```sh
python -m trajyn.lesson_study demo --output runs/experiment-003-demo
python -m trajyn.lesson_study replay --output runs/experiment-003-demo
```

This demo uses a hand-authored deterministic test learner and rules-based
targets. Its sixteen activations and eight exclusions test the mechanism.
They supply no model-learning or efficacy result.

Start the already-installed loopback Ollama service with local `qwen3:8b` and
`granite4:3b` weights available. The study performs no downloads or paid calls.

```sh
python -m trajyn.lesson_study prepare --output runs/experiment-003
```

Repeat that command to resume source collection or bounded induction. If it
returns `ready_to_freeze`, inspect `lesson.json`, `proposals/`, `validations/`,
the source archive, and `docs/EXPERIMENT_003_FROZEN.json`. Commit the freeze on
the feature branch before starting held-out inference.

```sh
git add docs/EXPERIMENT_003_FROZEN.json
git commit -m "Freeze Experiment 003 protocol and learned lesson"
python -m trajyn.lesson_study run --output runs/experiment-003
```

Repeat the same `run` command to resume. No options override the frozen seeds,
models, or inference settings. Rebuild and verify the results offline using
the next command. It also works before inference to verify reference records.

```sh
python -m trajyn.lesson_study replay --output runs/experiment-003
```

Generated archives stay under the ignored `runs/` directory. Each finished
attempt contains `trace.jsonl`, exact `calls/*.json` requests and replies,
incremental `progress.json`, `result.json`, and `seal.json`. The root contains
the frozen manifest, lesson, proposals, validations, source metadata, reference
traces, paired `report.json`, and a readable `report.md`.

## Baseline and research context

The baseline is recorded in [Experiment 002 results](EXPERIMENT_002_RESULTS.md).
Contrasting earlier success and failure follows the experience-comparison idea
in [ExpeL](https://arxiv.org/abs/2308.10144). Explicit applicability and exclusion
boundaries are informed by [When Not to Imitate](https://aclanthology.org/2026.findings-emnlp.1141/).

The local release environment initially refused connections at
`127.0.0.1:11434`. Model digests, Qwen source attempts, induction proposals, and
96 Granite target attempts remain unavailable until local inference can run.
No model result or efficacy claim is attached to the deterministic demo.
