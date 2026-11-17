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

## Beyond Milestone 2

- Run preregistered comparisons with distinct real model families and larger task partitions.
- Explore learned compatibility, stricter evidence provenance, and negative-transfer analysis.
- Add a versioned capability registry and broader tool and provider coverage.

Offline fixture results measure the deterministic framework. Cross-model
learning requires separate evaluations with real model adapters, larger
partitions, and evidence beyond these fixtures.
