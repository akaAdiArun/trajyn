# Local-model validation for Experiment 001

These are no-memory attempts on validation splits. Every configuration
retains per-seed tool traces, original parsed proposals, model digests,
inference settings, error counts, and independently verified outcomes.
Ollama 0.40.16 ran one loaded model at a time. The GPU reported 8,188 MiB
total and 7,948 MiB free before the model work, which supported the
quantized candidates. The project installs no model weights as dependencies.

| Validation workflow and settings | Qwen3-8B | Llama 3.2 3B | Granite 4 3B | Ministral 3B |
| --- | ---: | ---: | ---: | ---: |
| Delivery v1, unaided JSON, seeds 100–102 | 2/3 | 0/3 | 0/3 | — |
| Delivery v1, public-grounded JSON, seeds 100–102 | 3/3 | 0/3 | 1/3 | — |
| Delivery v2, public-grounded JSON, seeds 400–405 | 5/6 | — | 5/6 | 5/6 |

The v1 budget was 10 actions. The v2 budget was 12. Both used prompt revision 3
with the recorded inference settings. Llama continued to select calls whose
required inputs were unavailable under public grounding. The experiments
retain those attempts. The expanded candidate pool compared Granite
and Ministral under the same no-memory settings, alongside the intended
Qwen source. Granite won the deterministic model-tag tie break.

- [Unaided validation](../examples/experiment-001/calibration/unaided/calibration.json)
- [Grounded validation](../examples/experiment-001/calibration/grounded/calibration.json)
- [Expanded validation](../examples/experiment-001/calibration/expanded/calibration.json)

The earlier Milestone 2 pilot also remains in the [historical record](LOCAL_PILOT.md).
