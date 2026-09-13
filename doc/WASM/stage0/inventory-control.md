# Required-inventory control — 13 September 2026

S0-LL02-a is implemented and executed. Independent review and project acceptance
remain pending. Packet `STANDING-INVENTORY-CONTROL-R1` is indexed in
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
The outer S0-LL02-a envelope is actual control execution evidence and remains
`NOT_REVIEWED`. The production gate validates that real envelope against its
current slot and reports exactly one blocker: independent review/acceptance.
No compiler, image, Wasm engine or other Stage 0 capability is claimed.

The result uses v2 contract binding. Registering this runner changes only the
S0-LL02-a semantic contract; the other 47 variant contracts remain compatible.
The scoped status update adds this result to the existing 28 accepted records:
19 variants still lack results, and this one awaits review. The accepted count
remains 28. The older aggregate and its execution evidence are unchanged; no
archive-wide gate run is claimed.
