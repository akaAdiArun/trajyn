# TRAJYN

TRAJYN is a Python research runtime for studying whether verified experience from one
agent can help another agent solve structurally related tasks. The
[project charter](docs/PROJECT_BRIEF.md) describes the research program.

Milestone 1 provides a synthetic support API, a state verifier, a bounded agent runner,
a versioned JSONL trajectory format, and a typed capability schema. The offline
reference agent follows fixed rules and makes no model calls. Live model adapters,
capability induction, and comparative transfer evaluation belong to later milestones.

## Get started

Use Python 3.12 or newer. In PowerShell, run these commands from the repository root.

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e '.[dev]'
.venv/Scripts/trajyn.exe generate --seed 42 --split train --count 3
.venv/Scripts/trajyn.exe demo --seed 42 --split test
```

On macOS or Linux, use `.venv/bin/python` and `.venv/bin/trajyn`. The package also
supports `python -m trajyn`. Installation fetches development dependencies. Task
generation, execution, and tests run offline with no API keys.

Generation writes one task per line to `data/generated/tasks.jsonl` by default.
Each seed produces one task in the selected split. The demo writes to `runs/demo.jsonl`
and prints a JSON summary with the step count and verifier result. A successful
demo exits with status 0. Try `demo --max-steps 4` to record an incomplete attempt
and exit with status 1. Both commands accept `--output` and replace the chosen file
only after writing the full result.

## How an attempt works

1. The seed and split generate a target ticket, its order, inventory, and unrelated
   records. Train, validation, and test exercise damaged, missing, and wrong-item
   reports, respectively, with separate SKU pools and a shared workflow.
2. The agent receives the public task, tool specifications, its prior action and
   observation pairs, and the step budget. The reference agent reads the ticket
   and order, checks stock, creates a replacement, and resolves the ticket.
3. The environment checks arguments, order eligibility, and the relationship between
   ticket, order, and SKU. Retrying an existing replacement returns its ID without
   reserving another unit.
4. The verifier checks final state for the expected replacement, a correctly linked
   resolution, exactly one unit reserved, and untouched unrelated tickets and
   inventory. A tool response that reports success cannot substitute for these checks.

`Agent` in `src/trajyn/agent.py` is the provider boundary. An adapter supplies a model
identity and returns one structured `AgentDecision` per turn, or `None` to stop.
The runner keeps environment state private and records only typed public data.
`CapabilityCapsule` defines versioned goal, applicability, tool, procedure,
verifier, evidence, confidence, and limitation fields. At this milestone, validation
covers the shape of a capsule. A future inducer must establish that its evidence
actually supports the procedure.

## Trajectory format

Each file contains one attempt. Every line carries `schema_version` and
`trajectory_id`. The `start` event carries the task, seed, split, agent identity,
and budget. One `step` event per attempted action records its one-based index,
tool arguments, observation, and optional usage and elapsed time. The `finish`
event carries the stop reason and the verifier's pass flag and failure codes.

Identical untimed runs on the same Python version produce identical JSONL and
content-derived trajectory IDs. Add `--timing` to capture elapsed nanoseconds
for each tool step (including the agent decision) and the full attempt. Token
and cost fields are optional adapter metadata. The recorder stores no hidden
reasoning.

## Development checks

```powershell
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m mypy
.venv/Scripts/python.exe -m pytest
.venv/Scripts/python.exe -m build
```

GitHub Actions runs the same quality checks and tests, builds the wheel and
source distribution, and runs a deterministic smoke test through the installed
wheel's CLI.
