# TRAJYN roadmap

## Milestone 1 · Offline runtime

Implemented and integrated. The runtime generates seeded replacement tasks, runs an agent
against a synthetic support API, verifies resulting state, and writes typed JSONL
trajectories. Ruff, strict mypy, pytest, package builds, and a deterministic wheel smoke
test run in CI.

## Milestone 2 · Comparative research framework

In progress. Expand the benchmark with branching fulfillment scenarios, replay verified
experience to induce portable capsules, and compare four memory conditions and an
irrelevant-memory control on the same held-out tasks. Use offline fixtures for continuous
verification and a separate small local-model pilot if feasible.

## Beyond Milestone 2

- Run preregistered comparisons with distinct real model families and larger task partitions.
- Explore learned compatibility, stricter evidence provenance, and negative-transfer analysis.
- Add a versioned capability registry and broader tool and provider coverage.

The replacement reference agent is deterministic. Its smoke-test performance measures
runtime correctness and provides no estimate of cross-model transfer.
