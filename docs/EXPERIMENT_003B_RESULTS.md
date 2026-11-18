# Experiment 003B recorded results

Experiment 003B completed all 96 target cells with `granite4:3b`. Its compiled,
gated lesson verified 18/24 cases, matching no memory and the original prefix
gate. The same lesson offered up front verified 12/24. G saved two model calls
relative to no memory, with identical verified outcomes on all 24 paired tasks.

The lesson was deterministically extracted from the existing Qwen training
executions. The earlier three Qwen induction revisions remain recorded as
failed induction attempts with no accepted lesson and zero target inference.
003B performed no new source or induction inference.

## Protocol and lesson

The protocol was committed before the first target attempt in
`328acc613fe50fdb8d05e634c04fcf4de419225d`. Its implementation commit is
`28b2afb`. The [frozen manifest](EXPERIMENT_003B_FROZEN.json) records all model
identities, input and code hashes, task cases, and compiler support.

- Manifest ID `797eb315ff8b2f347cfa541d83ef4509db93cd37a4414ee7c861eb18398124c6`.
- Lesson ID `lesson:2d948c50b4e034fb4a02d0912a18ce2478b367ae82790e4298c7e156bdb68858`.
- Target digest `89962fcc75239ac434cdebceb6b7e0669397f92eaef9c487774b718bc36a3e5f`.

The supported producers are `ship_replacement` and `locker_replacement`, both
with the observed producer code `remedy_posted`. The fixed semantics bind
`ticket_id` from the producing action and `receipt_id` from its observation
for a later `close_case`. Applicability, exclusions, and argument bindings
are predefined parts of this handoff. The compiler derives route/code support
and citations from verified model-generated traces.

| Producer | Training seeds | Cited producer → consumer steps |
| --- | --- | --- |
| Warehouse shipping | 600, 606 | 3 → 4 in each source |
| Locker replacement | 601, 607 | 3 → 4 in each source |

The source trajectory IDs and complete support records are in the frozen
manifest and local `runs/experiment-003b/compiler-audit.json`. All twelve
original source attempts were reused verbatim. All three induction archives
remained byte-identical to their pre-study snapshots.

## Independently verified completion

All denominators below are completed target attempts. F had a compatible
capsule for every task.

| Case type | A, no memory | F, prefix gate | G, evidence gate | G-static, up front |
| --- | ---: | ---: | ---: | ---: |
| Familiar | 8/8 | 8/8 | 8/8 | 8/8 |
| Alternate route | 8/8 | 8/8 | 8/8 | 4/8 |
| Look-alike | 2/8 | 2/8 | 2/8 | 0/8 |
| Overall | 18/24 | 18/24 | 18/24 | 12/24 |

| Paired comparison | Gains | Regressions | Ties | Difference |
| --- | ---: | ---: | ---: | ---: |
| G versus A, primary | 0 | 0 | 24 | 0 pp |
| G versus G-static | 6 | 0 | 18 | +25 pp |
| G versus F | 0 | 0 | 24 | 0 pp |

The G versus G-static descriptive paired 95% bootstrap interval is +8.33 to
+41.67 percentage points, with an unadjusted exact sign-test p of 0.03125.
The other two comparisons have zero observed paired differences throughout
this fixed task set. The 24 tasks reuse nine synthetic profile families.
The intervals describe task resampling, and repeated profiles limit
independence. These observations support neither a general workflow efficacy
claim nor a completion improvement above no memory.

## Delivery, behavior, and efficiency

G reached qualifying evidence in 16 cases, delivered the hint on all 16 next
model decisions, and selected `close_case` immediately in every one. It missed
zero eligible prompts and delivered zero hints on look-alikes. Eight G cases
never produced qualifying replacement evidence. All 16 receipt-producing G
cases closed, while six look-alike cases failed before qualifying evidence.

A also obtained qualifying evidence in 16 cases. It closed immediately in
14 and made one extra, unsuccessful `acknowledge_delivery` call in each of
two cases before closing. F had the same first-action counts and two extra
post-receipt calls. The compiled hint accompanied removal of those two calls.
Verified completion remained tied.

G-static reached evidence in 12 cases and closed immediately in all 12.
Its other 12 attempts never obtained a qualifying receipt. It offered the
conditional lesson on 183 model calls, including 80 calls across eight
look-alikes. Those 80 are counted by the audit's `incorrect_deliveries`
field as out-of-scope delivery. They are conditional symbolic hints before
evidence, as distinct from valid resolved receipt bindings.

| Arm | Model calls | Invalid calls | Input tokens | Output tokens |
| --- | ---: | ---: | ---: | ---: |
| A | 173 | 38 | 134,917 | 1,433 |
| F | 171 | 38 | 136,058 | 1,412 |
| G | 171 | 36 | 135,603 | 1,413 |
| G-static | 183 | 66 | 167,598 | 1,413 |

The completed attempts recorded no model parsing errors. Invalid calls exclude
the predefined recoverable carrier, warehouse, and out-of-stock responses.
Call counts equal tool-step counts in these completed attempts. One initial
A-arm request for seed 1011 returned HTTP 500. That attempt was retained as
incomplete and excluded from scoring. A fresh numbered retry completed, giving
97 archived starts and 96 scored cells.

G used fewer calls than A on two tasks and tied on 22, for two fewer calls
overall. Among the 18 pairs where both verified, the mean difference was
−0.111 calls. G and F used the same total calls. G used 12 fewer calls than
G-static overall, while on the 12 pairs where both verified, G used two more
calls. This efficiency analysis remains separate from the primary completion
outcome and from failures exhausting the call budget.

## Paired executions

On seed 1008, A and G both read the case, inspected the parcel, checked stock,
and shipped a replacement at step 4. A then called `acknowledge_delivery`,
received `remedy_already_posted`, and closed at step 6. G's step-5 prompt
received the bound hint, and Granite chose `close_case` directly. Both
independent verifications passed. Seed 1010 showed the same difference.

On alternate-route seed 1016, A and G recovered from an initially missing
parcel identifier, obtained it through `find_parcel`, retried a warehouse
response, and closed at step 9. G-static alternated case reads with inspections
lacking the required parcel identifier and exhausted ten decisions. It never
reached receipt evidence. Its failure therefore supplies no post-receipt
comparison. The G versus A completion tie shows that this success also occurred
without the hint.

## Verification and operation

All 160 Python tests, lint, formatting, mypy, and CI passed. The original
Experiment 001 and four Experiment 002 reports reproduce from their archives.
The completed 003B archive was replayed offline, reconstructing compilation,
exact prompts, model replies, grounding, gate decisions, and independent
verification. A separate direct aggregation of replayed traces matched every
completion count in the report.

The local archive is `runs/experiment-003b`, with the complete JSON report,
readable report, source support audit, calls, retries, and trajectories.
The [operator guide](EXPERIMENT_003B.md) gives preparation and freeze details.

```sh
python -m trajyn.compiled_study replay
python -m trajyn.compiled_study run
```

The second command is the exact resume command. All 96 cells are complete,
so it skips their finished attempts. The source gate and target design retain
their pre-inference freeze.
