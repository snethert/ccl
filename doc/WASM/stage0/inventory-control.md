# Required-inventory control — 13 September 2026

S0-LL02-a is ACCEPTED at its reviewed scope. [Claude's twenty-third audit](claude-review.md)
of 24f8805e, committed as 4f5fdcb6, found no defect. The user then explicitly
accepted the slot: “I accept it.” A separate [acceptance decision](project-acceptance.md)
and envelope preserve the original execution. Packet `STANDING-INVENTORY-CONTROL-R1` is indexed in
[evidence/index.json](../evidence/index.json).

The [runner](../../../tests/wasm/stage0/inventory-control/README.md) invokes the
unchanged production gate CLI with a fixed, quarantined synthetic inventory:
three required IDs, one with two variants. Both complete result orders pass.
The following seven defects are rejected with their exact expected diagnostics:

| Mutation | Production gate result |
| --- | --- |
| Omit the first ID | BLOCKED; names the missing ID/variant |
| Omit the middle ID | BLOCKED; names both missing variants |
| Omit the last ID | BLOCKED; names the missing ID/variant |
| Omit one variant | BLOCKED; names that variant |
| Keep the count, substitute an unrequested variant | BLOCKED; the required variant remains missing |
| Keep the count, duplicate another record | FAIL; reports both the duplicate and missing record |
| Omit all results | BLOCKED; names all four required ID/variant pairs |

These results establish the gate's required-ID/variant check; matching counts
alone is insufficient. The inner `CONTROL-*` envelopes are synthetic test data.
The original outer S0-LL02-a envelope is actual control execution evidence and
retains its original `NOT_REVIEWED` flag. The separate accepted envelope adds
only the disposition and provenance; it now passes the production gate for its
current slot.
No compiler, image, Wasm engine or other Stage 0 capability is claimed.

The result uses v2 contract binding. Registering this runner changes only the
S0-LL02-a semantic contract; the other 47 variant contracts remain compatible.
The combined envelope preserves all 28 earlier accepted result objects and adds
this accepted record. The scoped ledger is now 29 accepted, 19 missing and zero
unreviewed. All 29 contract bindings were checked; prior runtime-artifact
verification was reused. The older aggregate and original execution evidence
are unchanged; no archive-wide gate run or new fixture execution is claimed.
