# Experiment 002 · Observation-gated cross-model transfer

This preregistration freezes the task set, models, inference settings, controls,
and metrics before held-out inference. Experiment 001's archive remains the
historical baseline. This is a small cross-model replication on seeded delivery
workflows with an independent final-state verifier.

## Questions and endpoints

1. Does F reduce post-divergence guidance exposure compared with D? Count
   tool-producing turns that still carry a capsule at or after the first public
   operation, observation, or binding mismatch. D's observed trace is scored by
   the same branch gate in shadow mode. Exposure and verified task harm are
   different outcomes.
2. Does F recover verified completion compared with D on the same seeds? Report
   gains, regressions, ties, the paired absolute difference, the percentile
   interval from 10,000 seeded task bootstrap draws, and the exact paired sign
   test. Compare each arm against A as an additional reference. For harm, count
   seeds where A succeeded and the comparison arm failed, and the corresponding
   paired regressions of F against D. Report raw counts and denominators.

The primary comparison is Granite with public grounding. The unaided Granite
run and both Ministral modes are prespecified supplementary comparisons.
Summarize rates with Wilson intervals. Interpret the six fixed profiles per run
descriptively. Report all cells and failed attempts.

## Model selection and inference

| Role | Ollama model | Family | Full digest |
| --- | --- | --- | --- |
| Source | `qwen3:8b` | Qwen3 | `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41` |
| Primary target | `granite4:3b` | Granite | `89962fcc75239ac434cdebceb6b7e0669397f92eaef9c487774b718bc36a3e5f` |
| Second target | `ministral-3:3b` | Ministral | `f04aa1c738f64e13c625b82ae92504fc0260fa6723b509ed1ece0fa188179b1d` |

Qwen and Granite carry forward from Experiment 001. Validation seeds
`414,415,416` cover missing parcel data, carrier retry, a backup carrier,
and a locker remedy. Granite verified 3/3 with public grounding and 2/3 unaided.
Ministral verified 2/3 grounded and 3/3 unaided. These outcomes establish
feasibility for both targets and modes. The complete validation traces and
proposals accompany this protocol.

Use Ollama 0.40.16 over loopback on one RTX 4070 Laptop GPU with 8 GiB VRAM.
Use prompt revision 3, JSON action schema, temperature 0, seed 17,
`num_ctx=4096`, `num_predict=160`, ten steps per attempt, and a 75-second
per-call timeout. Disabled thinking follows the existing adapter on supporting
models. One call per decision. The model always picks the tool. In public
grounding, the adapter fills matching arguments from the public task and
successful tool responses, preserving original proposals and substitutions.
In unaided mode the executed arguments come directly from the proposal.

## Partition, run order, and controls

- **Training** uses delivery-v2 seeds `336,337,338,339,340,341,342,343`,
  one per source profile. Collect once using Qwen with public grounding.
  Independently replay each source. Only verified and inducible executions can
  supply capsules. If none can be induced, archive the attempts and stop.
- **Validation** uses only `414,415,416`. It supplies no memory to held-out runs.
- **Test** uses delivery-v2 seeds `528,529,530,531,532,533`, disjoint from the
  training, validation, and Experiment 001 seeds. They cover combined missing
  parcel, locker and warehouse retry, stale-stock refund approval, stale report
  with backup carrier, held parcel with missing record and backup carrier,
  refund approval after backup carrier, and locker after carrier retry. Six of
  eight test profiles fit the four-mode grid on this hardware. The two
  remaining held/delivered retry profiles are omitted.
- Run Granite grounded first, then Granite unaided, Ministral grounded, and
  Ministral unaided. Reuse the independently replayed Qwen archive for the last
  three via `--source-archive`. Verification and induction must reproduce the
  same source and capsule IDs. Each run restarts each task under each arm, with
  the existing cyclic rotation by seed position and no state across trials.

| Arm | Public memory |
| --- | --- |
| A | None |
| B | Retrieved raw source trajectory |
| C | Procedural summary of the same source |
| D | Statically compatible capsule, shown from the first call |
| E | Irrelevant-memory control |
| F | Same candidate as D, shown only after the public prefix matches its first factual guard and withheld on divergence |

For D and F static compatibility uses public workflow and tool interfaces.
F observes execution and can abstain, activate, withdraw, or finish. No gate
reads private simulator state or chooses the agent's actions. This study
isolates delivery policy by using one ranked candidate in both arms. The
offline multiple-branch fixture is outside this test.

## Collection and analysis

Archive the source manifest, capsules, inference metadata, per-call model
proposals, tool calls and observations, independent verification, timings,
paired comparisons, and D/F transition reasons and prompt turns. Report
invalid calls per executed action, matching public identifier values per
identifier argument, missing identifiers, repeated calls, recoveries, action
and token usage, initial compatibility, delivery, activation, abstention,
and withdrawal. Fit no settings to test outcomes. Keep model errors or
timeouts recorded as attempts. Any infrastructure interruption or incomplete
cell will be disclosed with any available artifacts.

Run `trajyn pilot --suite delivery-v2 --branch-aware --tool-mode json
--inference-timeout 75 --max-steps 10 --source-seeds 336,337,338,339,340,341,342,343
--target-seeds 528,529,530,531,532,533` with the model names and digests above,
the assigned `--grounding public` or `none`, loopback `--ollama-url`, and a
distinct output directory. The last three runs also pass
`--source-archive <grounded Granite output>`. Regenerate offline reports with
`trajyn analyze --results <run>/evaluation/results.json --output <run>/evaluation`.
