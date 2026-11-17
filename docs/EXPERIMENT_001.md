# Experiment 001 · Cross-family transfer on composed workflows

**Protocol revision 1 · 17 November 2026**

## Question and hypotheses

Can a verified, compatibility-checked capsule improve independently verified
completion by a different model family on composed delivery workflows?
The primary contrast is D (capsule) minus A (no memory), paired by task.
The directional hypothesis is that D improves completion. B (raw experience)
and C (procedural summary) test whether any effect depends on representation.
E (irrelevant experience) measures negative transfer. Differences between
D and B/C are descriptive. Tool compatibility alone may leave deeper branch
mismatches in place, so ties and regressions are plausible outcomes.

## Frozen setup

| Item | Configuration |
| --- | --- |
| Source | `qwen3:8b`, `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41` |
| Target | `granite4:3b`, `89962fcc75239ac434cdebceb6b7e0669397f92eaef9c487774b718bc36a3e5f` |
| Runtime | Ollama 0.40.16, prompt revision 3, action-first JSON |
| Argument mode | Explicit public grounding for source and every target arm. Models propose the tool name. The runtime binds available arguments from the live task and successful observations. Both forms are recorded. |
| Inference | Temperature 0, sampler seed 17, 4,096 context tokens, up to 160 output tokens, 75-second HTTP timeout |
| Workflow | [Delivery v2](BENCHMARK_V2.md), state verification and replay enabled |
| Training seeds | 320–327 inclusive, eight task instances |
| Validation seeds | 400–405 inclusive, six task instances |
| Held-out seeds | 512–521 inclusive, ten task instances covering all eight test profiles |
| Action budget | 12 for every source and target attempt, at most 696 inference calls |
| Source evidence | Keep every attempt. Induce only from independently verified and replayable training traces with grounded arguments. Record all exclusions. Stop before testing if no capsule qualifies. |
| Retrieval | Rank verified training sources by applicability and tool compatibility, required tool coverage, and public goal token overlap. Break ties by source seed and content ID. B, C, and D share the top candidate. |
| Arms | A, current task and tools. B, raw trace. C, procedural summary. D, capsule subject to admissibility. E, archived irrelevant replacement trajectory. |
| Condition order | Rotate A–E one position per successive target seed. Each arm appears in each order position twice. |
| Trial isolation | Fresh target agent and environment for every seed and arm. Each sees the same public task and tool menu. |

Validation selected the model pair without held-out outcomes. Qwen3-8B was
the planned source based on the previous verified source runs and verified
5/6 expanded cases. Granite and Ministral both verified 5/6 expanded cases
with no memory and public grounding. Ascending model tag breaks that tie.
The [calibration record](CALIBRATION.md) preserves earlier failures and
all validation configurations.

## Measures and analysis

The primary measure is independent verifier success. Compare the same target
seed across arms. Report paired improvements, regressions, and ties with rates
and counts. Give per-arm Wilson 95% intervals, descriptive paired-bootstrap
95% intervals (10,000 resamples of whole tasks from RNG seed 1741), and
two-sided exact paired sign tests. Tests are unadjusted and exploratory.

Secondary measures include action count, runtime, invalid-call rate,
failure and recovery codes, repeated actions, matching public identifiers
over requested identifiers, missing fields, capsule acceptance or rejection,
and inference token counts. Actual internal use of delivered memory remains
unobserved for these models. Success or a matching action alone cannot
identify internal memory use.

The benchmark is synthetic, covers eight held-out structural profiles,
and uses one hardware/runtime configuration and one model pair. Bootstrap
intervals can be degenerate with small fixed samples. These runs estimate
performance on the declared tasks with the stated argument binder. They
cannot estimate unaided identifier copying or population-level transfer.

## Reproduce

With both recorded model digests installed and Ollama running locally:

```sh
trajyn pilot --tool-mode json --grounding public --suite delivery-v2 \
  --source-model qwen3:8b --target-model granite4:3b \
  --source-digest 500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41 \
  --target-digest 89962fcc75239ac434cdebceb6b7e0669397f92eaef9c487774b718bc36a3e5f \
  --source-seeds 320,321,322,323,324,325,326,327 \
  --target-seeds 512,513,514,515,516,517,518,519,520,521 \
  --max-steps 12 --inference-timeout 75 --output runs/experiment-001
trajyn analyze --results runs/experiment-001/evaluation/results.json --output runs/experiment-001/evaluation
```

Commit this protocol before held-out execution. Preserve the original revision
and state the reasons for any later amendment.
