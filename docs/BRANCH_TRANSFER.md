# Branch-aware transfer

Static transfer admits a capsule after checking its workflow and required tool
contracts. Those public checks cannot distinguish two delivery cases served by
the same interface. Experiment 001 recorded three paired regressions under
static transfer.

The branch-aware evaluator uses the same ranked candidate as static transfer.
It waits for a live action–observation prefix that matches the source through
its first factual observation guard. A capsule with no factual guard cannot
activate. If the operation, observation, or argument prerequisites diverge
before activation, the gate abstains. After activation the same checks can
withdraw guidance from future requests. The runner preserves all public
actions and observations. Withdrawal cannot erase information that was
already presented to an agent.

The audit records candidate selection, compatibility, conditional waiting,
activation, divergence, withdrawal, abstention, and completion with the
observed step count and reason. The gate receives the public task, published
tool contracts, and live public history. It supplies memory without taking
actions itself.

Run `trajyn evaluate --branch-aware` to add F (branch-aware capsule) to
A–E. D and F use the identical source capsule. `transfer.json` records their
lifecycle and grounded guidance by tool-producing turn. D's lifecycle is a
shadow evaluation of its observed trace. Its continuation count measures
tool-producing turns that still received static memory after the shadow
gate would have withheld it. This is an exposure measure. The verifier
separately measures each task outcome.
