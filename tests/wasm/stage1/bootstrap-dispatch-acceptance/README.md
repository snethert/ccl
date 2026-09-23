# Audit 160 acceptance and integration

549 original definitions execute and match native, 514 with non-NIL witnesses.
Integration adds no execution or LL15 credit. Steve accepted the two reviewed
packets: “I accept the reviewed packages”. The full generic-dispatch proposal
in `761f1cc1` was not covered by audit 160 and remains unintegrated.

This runner copies the final GCD and cached-dispatch proposal files exactly.
It reconstructs the reviewed numeric artifacts from their bound delta chain,
uses the production runtime modules after comparing their bytes, and checks
all 23,916 comparisons. It reuses the native driver with the final integrated
files copied into pristine U1; it never reapplies proposal patches to them.
The recount uses CCL's whole-file environment and the existing 2,231-definition
cohort. All runtime sources are unchanged.

Run from the integrated checkout with fresh output directories:

```sh
python3 tests/wasm/stage1/bootstrap-dispatch-acceptance/run.py native --output /tmp/ccl-dispatch-native-replay
python3 tests/wasm/stage1/bootstrap-dispatch-acceptance/run.py verify --output /tmp/ccl-dispatch-target-replay
python3 tests/wasm/stage1/bootstrap-dispatch-acceptance/run.py recount --output /tmp/ccl-dispatch-count-replay
```

The original GCD and cached-dispatch proposal verifiers retain their historical
source pins; run those from `791b9ba8`. The separate full-GF proposal replays at
`761f1cc1`. The acceptance commands above run after integration.

O-12 is a declared narrowing: generic bignum UVSET accepts nonnegative target
fixnums, not all unsigned 32-bit integers. O-13 records the KERNEL-RESTART arm
as a host adaptation: registered hooks receive NIL for the unavailable native
frame pointer; only the wrong-type code has a built-in restart fallback. Other
kernel codes signal SIMPLE-ERROR. This is distinct from behavioural branch WB-1.
