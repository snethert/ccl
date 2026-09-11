# Evidence binding v2

Status: implemented tooling, pending independent review. Version 2 results bind each executed test to its complete semantic contract and inventory version. The original whole-inventory SHA-256 remains provenance. Adding an unrelated test does not invalidate an existing result; the gate still blocks on the missing new result. Existing results cannot satisfy changed contracts merely by receiving a new inventory hash.

## Identity

Each result has `contract_binding` with exactly these fields:

| Field | Meaning |
| --- | --- |
| version | Binding algorithm version, currently integer 1. |
| inventory_version | The original inventory's positive integer `version`; must equal the current inventory version. |
| inventory_path | Canonical relative path to the retained original inventory snapshot. |
| inventory_sha256 | SHA-256 of that snapshot's exact original bytes. |
| contract_sha256 | SHA-256 of the canonical semantic contract described below. |

The envelope is version 2 and names the inventory version and original whole-file inventory hash. When aggregating different executions, each result keeps its own binding and snapshot; prefix the snapshot path along with its artifact paths. The aggregator's whole-file hash identifies the inventory at aggregation time, not every earlier execution.

The semantic digest includes the binding version, every inventory-level field except `tests` and the presentation-only `acceptance_note`, the test ID, the entire test entry except `status` and `review_disposition`, and the transitive prerequisite entries with the same exclusions. It therefore covers assertions including descriptions, variants, runner identity, evidence kind, source revision, prerequisite relationships, required artifact roles and any newly introduced semantic fields. Cycles, missing prerequisites and duplicate IDs fail. Test-list/object-key ordering is not identity; ordering inside contract arrays is retained.

Canonical encoding is Python's JSON representation with sorted object keys, ASCII escapes, no extra whitespace and nonfinite numbers rejected. `tools/evidence_binding.py` is the single producer/validator implementation. Its source is retained with each new bound report. Inventory-version changes deliberately invalidate compatibility globally; adding a test does not require changing the version. A changed runner identity or contract entry invalidates that test and its dependents, while review/status bookkeeping does not.

External specification or policy changes must update the affected contract entry, for example its version, description or declared policy digest. A prose link alone is not an automatically followed semantic dependency. The binding identifies the declared contract; it does not infer new requirements from arbitrary linked documents or replace the retained source, toolchain, configuration and artifact hashes. This is also why acceptance still requires review of those artifacts and the contract's completeness.

## Validation and migration

The gate checks each binding against both the exact retained inventory snapshot and the current contract. Missing or rewritten snapshots, mismatched digests, changed semantics, incompatible versions and escaping paths fail. Artifact verification, failed executions, missing results, substitutions, skips and acceptance-review requirements continue to apply. This changes compatibility checking, not what passes.

Legacy version 1 envelopes retain the strict whole-file check. An explicit upgrade reads the original report and original inventory, verifies every declared artifact, derives the binding from that original contract, and compares it with the current contract. It writes a separate envelope, retains the original report/snapshot/producer by content hash, preserves execution timestamps and review dispositions, and labels the operation `FORMAT_UPGRADE_NO_EXECUTION`. It refuses to overwrite evidence or to upgrade a semantically changed test. No native rebuild is needed merely to change envelope format.

```sh
python3 doc/WASM/tools/bind-evidence.py \
  --results /path/to/original/results.json \
  --inventory /path/to/original/inventory.json \
  --current doc/WASM/stage0/inventory.json \
  --output /path/to/empty-upgrade/results.json
```

The three Wasm acceptance runners attach v2 bindings to fresh reports, including their prerequisite records. The native `record.py` emits v2 after verifying the completed native execution. Probes remain diagnostics rather than acceptance IDs; their original inventory hashes are historical provenance and the index labels them `CURRENT_DIAGNOSTIC`. They cannot discharge an S0 contract.

`test-bindings.py` exercises compatibility after unrelated additions, missing-new-test blocking, semantic/prerequisite/global changes, snapshot tampering and migration preservation. `test-controls.py` continues to exercise the existing gate and archive checks. New binding tooling is not covered by Claude's earlier frame audit and needs its own independent review before acceptance.
