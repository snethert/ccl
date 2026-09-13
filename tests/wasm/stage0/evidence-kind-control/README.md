# Evidence-kind gate control — S0-LL03-a

Execute the unchanged production gate on 24 retained synthetic inputs:

```sh
python3 tests/wasm/stage0/evidence-kind-control/run.py --output NEW-DIRECTORY
python3 tests/wasm/stage0/evidence-kind-control/run.py --verify RETAINED-PACKET
```

The quarantined inventory declares generated-target, hand-built and synthetic
control classes over C/C4/B and full/reduced profiles. Its eighteen records each
carry a distinct fixture payload and hash. All of them, including the inputs
labelled compiler-generated, are synthetic checker data. Internal ACCEPTED
flags exercise validation and confer no project acceptance.

Two complete orders pass. Twelve controls offer the full hand-built or synthetic
record for a generated requirement, one per candidate/profile; all fail with
the exact wrong-kind diagnostic. The other ten exercise candidate/profile
substitution, substituted imports, absent substitution disclosure, skipped
execution, failed records in each class, mismatched payload identity and missing
review. Candidate/profile, fixture, substitution and artifact labels remain
present on failed records, independently of their status.

This tests declared evidence-kind and required-variant enforcement. The gate
does not infer production origin from arbitrary bytes or authenticate a false
kind declaration. Actual compiler/runtime acceptance still requires identified
execution artifacts and independent review. The positive synthetic controls
deliberately demonstrate schema acceptance, not that production execution occurred.

The outer `results.json` is actual CONTROL EXECUTION evidence for S0-LL03-a;
it remains NOT_REVIEWED. Its separate production-slot assessment must be blocked
only for review/acceptance. No accepted envelope, production gate, binding tool,
shared compiler source or runtime fixture is changed.

The verifier reconstructs the fixed base, checks the retained mutations and
classification observations, reruns all gate invocations and validates the real
slot and direct artifact/source bindings. See the
[scope report](../../../../doc/WASM/stage0/evidence-kind-control.md).
