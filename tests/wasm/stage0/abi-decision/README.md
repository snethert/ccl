# B ABI desk-decision producer

This materializes S0-ABI-selection from the existing 12 September project
direction. It records B's protocol, simplicity rationale, retained alternatives,
bounded correctness references, provisional packaging and reversal criteria.
The evidence kind is **DESK DECISION**. No runtime or timing execution is claimed.

Run from the repository root into a new directory:

```sh
python3 tests/wasm/stage0/abi-decision/run.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --output /private/tmp/ccl-abi-decision-review
```

Replay the retained result:

```sh
python3 tests/wasm/stage0/abi-decision/run.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --verify /Users/buildsomething/Source/ccl-evidence/2026-09-13-abi-decision-r1
```

The producer reads the pinned accepted envelope and its original inventory
snapshots. It checks all 29 existing bindings, and requires every variant of the
desk record's direct and transitive prerequisites: 24 accepted records. Earlier
runtime-artifact verification is reused. The small basis projection identifies
the original records; it does not replace their execution envelopes.

Ten controls reject missing, duplicated, unaccepted or incompatible prerequisite
records; an argument split; benchmark-rule or speed-superiority claims;
unbounded capacity; a frozen production partition; and omission of generated-code
confirmation. These are checks of a desk record, not Lisp semantic executions.

The unchanged production gate validates the new envelope and its artifacts
against the full inventory. Since this envelope contains only the new record,
that direct run reports all other records missing. `gate-result.json` combines
those observations with the pinned accepted set to produce the scoped ledger.
It is explicitly labeled; no full combined artifact rescan occurs.

The output keeps `NOT_REVIEWED`. Review and the user's acceptance of this formal
record remain separate from the already effective choice to implement B.

See the [decision report](../../../../doc/WASM/stage0/abi-decision.md).
