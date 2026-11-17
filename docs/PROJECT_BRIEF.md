# TRAJYN

**Working title:** TRAJYN — Agent Experience Runtime  
**One-line description:** An experimental infrastructure layer that converts verified agent experiences into portable, testable capabilities across different language-model agents.  
**Tagline:** Experience is portable. Capability is earned.  
**Status:** Project charter, 17 November 2026. Proposed research direction; no performance claims yet.

## 1. Problem

Agents routinely solve tasks and encounter failures, but those experiences generally remain locked inside session histories, individual frameworks, or model-specific prompting strategies. Retrieving a previous transcript does not guarantee a different model can reuse the underlying procedure. Transferring poorly specified instructions can even reduce performance.

TRAJYN investigates a more rigorous primitive: a versioned *capability capsule* extracted from observable, scored execution trajectories, with executable preconditions, tool/interface requirements, outcome evidence, and destination-model validation.

**Core question:** Can a verified experience produced by agent A improve agent B on unseen but structurally related tasks, beyond ordinary retrieval and handwritten instructions, without updating B's model weights?

## 2. Research hypothesis

A compact, structured, verifier-grounded procedure selected using task context and model/tool compatibility will yield better held-out transfer than using raw transcripts alone, provided the system can refuse transfers likely to fail.

This is a hypothesis to test, not an established result.

## 3. Long-term architecture

1. **Agent adapters:** Normalized interface to different model providers and agent execution harnesses.
2. **Trajectory recorder:** Store observable task inputs, tool calls/results, feedback, environment changes, provenance, cost, and outcome. Do not capture hidden chain-of-thought.
3. **Capability inducer:** Infer candidate reusable subtask procedures from successes and failures.
4. **Capability capsule:** Portable typed representation of goals, preconditions, procedure, dependencies, verification, evidence, and known failure modes.
5. **Transfer planner:** Adapt procedures to the target model's tools and constraints; decline unsafe or incompatible transfers.
6. **Counterfactual evaluator:** Compare success and cost with/without candidate experience on unseen tasks.
7. **Versioned registry:** Record capability lineage, compatibility, metrics, revocation, and permissions.

## 4. Stage 1 — Cross-model experience transfer laboratory

Build a functioning research prototype, not a mock interface. Demonstrate a reproducible end-to-end loop:

`source model -> task environment -> verified execution trajectory -> capability candidate -> target model -> held-out evaluation -> results`

### Scope and deliverables

- Python 3.12+ package with typed domain models (Pydantic or dataclasses), dependency management, and CLI.
- Two real, configurable model adapters behind one protocol. Credentials must be supplied as environment variables; provide an entirely offline CI path.
- A deterministic multi-step, stateful tool-use test environment that supports multiple seeds, known-correct verifiers, and separate train/validation/test task families. Start with a small service-operations or API-workflow environment; avoid single-hop question answering.
- Execution recorder that saves structured JSONL trajectories with task IDs, seeds, tool calls and outputs, public observations, outcome, timing, cost estimates, and provider/model version metadata when available.
- Initial capability schema with: identifier, version, source trajectory identifiers, goal, applicability conditions, required tool affordances, ordered strategy/steps, verifier, confidence/evidence, limitations, and created timestamp.
- One initial inducer: extract a candidate capability from successful source trajectories, validating schema and grounding references in actual tool results. Include a deliberately simple non-learning baseline.
- Baselines evaluated with the same target model and common held-out tasks: (A) no memory, (B) retrieved source trajectory, (C) direct one-shot procedural summary, (D) structured capability capsule.
- Transfer tests on a *different* model family. Include irrelevant or incompatible memory as a negative-transfer control. Test on held-out tasks that are not reused in extraction.
- CLI commands for dataset generation, a smoke run, a full opt-in evaluation, and comparison report, saving machine-readable CSV/JSON and concise Markdown reports.
- Unit tests, schema validation, reproducible seeded tests, a sample offline run, clear failure cases, and a README that states exactly what is and is not implemented.

### Proposed interfaces (illustrative, subject to implementation)

```
trajyn generate --seed 42 --output data/generated/
trajyn collect --config configs/stage1.yaml --split train
trajyn induce --trajectories runs/source.jsonl --output capsules/
trajyn evaluate --config configs/stage1.yaml --capsules capsules/ --split test
trajyn compare --runs runs/ --output reports/stage1.md
```

### Experimental discipline

- Declare data splits and seeds before running headline evaluations; don't choose favorable results after the fact.
- Verify success using environment state, not an evaluator model's impression.
- Control target model, task instances, tool access, and budget across comparisons.
- Report both benefits and regressions, with uncertainty (per-task outcomes and multiple seeds where feasible).
- Record cost and token usage. Require a configurable maximum spend/call count.
- Never assert that transfer works unless the data supports it.
- Keep synthetic fixtures in the repository; exclude raw personal conversations, private data, and secrets.

### Definition of done

1. From a fresh clone, `pytest` and quality checks pass without external API keys.
2. A seeded offline demonstration works end-to-end with a fixture adapter.
3. With credentials and an explicit manual command, two real model adapters can execute the same instrumented task suite.
4. The source model can generate a verified trajectory and a portable capsule; the target model can consume it on held-out tasks.
5. An evaluation produces four comparable baseline result sets and a per-task failure breakdown, even if the method fails to outperform baselines.
6. No README claims or plotted gains are presented without the actual corresponding run artifacts.

## 5. GitHub workflow and CI

- `main` stays protected by review; work happens in focused branches and PRs.
- GitHub Actions on PRs: install, lint/format, type check, unit tests, seeded offline smoke evaluation, package build, and artifact/schema validation. No paid model calls on PRs.
- A manually triggered and appropriately restricted evaluation workflow may run live provider calls using repository/environment secrets, hard call/expense/time limits, and upload redacted report artifacts. Do not run untrusted PR code with secrets.
- Publish concise run summaries and artifact links after evaluations. Never auto-merge based solely on an agent-produced review.

## 6. Documentation and commit conventions

- Keep the public repository focused on the technology, experiments, architecture, performance, and limitations.
- Distinguish scientific model/provider IDs required for reproducibility from authorship attributions; avoid unnecessary promotional provider branding.
- Keep code reviewable with descriptive human-readable commit messages and practical technical documentation.

## 7. Out of scope for Stage 1

Web app, consumer memory sync, production multi-tenancy, privacy-preserving federated aggregation, generalized agent operating system, neural weight training, automatic self-modifying production agents, or unsupported claims of novel algorithms.

## 8. Research starting points

- Microsoft Research, SkillOpt: https://github.com/microsoft/SkillOpt
- MultiEvoSkill: https://arxiv.org/abs/2610.34260
- EvoSkill: https://github.com/sentient-agi/EvoSkill
- SkillCommit: https://arxiv.org/abs/2608.15165
- AppWorld benchmark: https://appworld.dev/

These are prior-art references, not claimed contributions of TRAJYN.

## 9. Future stages

- **Stage 2:** Optimize transfer policies, automatic subtask discovery, stronger provenance, risk-aware refusal, counterfactual credit assignment, and learned compatibility models.
- **Stage 3:** Developer SDK, registry service, typed APIs, compatibility tests, adapters, and operational observability.
- **Stage 4:** Distributed replicated registries, fine-grained permissions, redaction/revocation, collaborative capability exchange, and privacy-preserving evaluation.

## 10. Initial repository proposal

**Repository name:** `trajyn`  
**Description:** `A research runtime for verified experience transfer between heterogeneous AI agents.`  
**License:** Apache-2.0, subject to chosen dependency/license compatibility.  
**Language:** Python.  
**Visibility:** Start private until the initial benchmark, documentation, and secret hygiene have been reviewed; publish when ready.
