# TRAJYN roadmap

## Milestone 1 · Offline runtime

Implemented and integrated. The runtime generates seeded replacement tasks, runs an agent
against a synthetic support API, verifies resulting state, and writes typed JSONL
trajectories. Ruff, strict mypy, pytest, package builds, and a deterministic wheel smoke
test run in CI.

## Milestone 2 · Comparative research framework

Implemented. The delivery benchmark varies remedy sequences, missing or stale
information, retry paths, and tool availability across separate partitions.
The inducer replays successful training traces and extracts one guarded
procedure per trace. Transfer checks the public task and tool interface.
The paired evaluation runs no-memory, raw-trajectory, summary, capsule, and
irrelevant-memory conditions and exports JSON, CSV, and Markdown.
An opt-in Ollama adapter can use two distinct local model families with call
and inference limits and a separate experiment directory.
The [local pilot](docs/LOCAL_PILOT.md) completed source induction and all
paired target trials. Target completion was zero under each condition.

## Milestone 3 · Cross-family evaluation and public documentation

Implemented. The product README includes an original visual identity,
animated execution pipeline, architecture, replayed source trace, and
recorded experiment chart. The runtime supports explicit public argument
grounding, model-proposal diagnostics, audited multi-source retrieval,
and composed delivery v2 profiles with independent state verification.
Experiment 001 ran all five arms after validation and preregistration.
The capsule arm verified 0/10 held-out tasks against 3/10 without memory.
[Protocol](docs/EXPERIMENT_001.md) · [Results](docs/EXPERIMENT_001_RESULTS.md)

## Milestone 4 · Public site and branch-aware transfer

The static project site on GitHub Pages presents the architecture, a stepwise
replay of a verified execution, and reproducible charts. Search Console verified
the project URL and accepted its sitemap. The runtime can also wait for a
matching public observation prefix, abstain, or withdraw capsule guidance on
divergence. The multiple-branch API preserves independently replayable
alternatives and waits when they offer conflicting actions.
[Website](https://akaadiarun.github.io/trajyn/) · [Runtime](docs/BRANCH_TRANSFER.md) ·
[Experiment 002 protocol](docs/EXPERIMENT_002.md) · [Results](docs/EXPERIMENT_002_RESULTS.md)

## Next · Measure when guidance helps

- Build a validation task set with observed alternative routes and measure both
  correct activations and missed activations.
- Preregister a paired test of one ranked candidate versus multiple independently
  verified alternatives.
- Explore a versioned registry with provenance and revocation after establishing
  workable applicability across task families.

Offline fixture results measure the deterministic framework. Assessing
cross-model learning requires larger partitions, multiple model pairs, and
stronger evidence than a local hardware pilot can provide.
