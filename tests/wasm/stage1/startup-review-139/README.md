# Audit 139 residual admission cases

Small test-only supplement for the next LL15 work. The three service sources and binaries are copied by hash from the audit-138 packet; no runtime or compiler changes, new acceptance or slot credit. Audit 139 closes the prior findings and recommends carrying these remaining checks without another service hold.

The new probe refuses cons keys overlapping the table and static data/stack region, and empty/deleted markers nested in complex components (both EQL/EQUAL) and cons cars (EQUAL). The population SET refusal now supplies a backed cons distinct from the old NIL contents, so preservation detects a write performed before the result-range refusal. Checked status, preserved table/population/key state and poisoned result words are required; traps are failures. Both memory placements execute. Five separately compiled faults remove the two overlap clauses, remove recursive marker validation in each table binary, or move the result-range refusal after the SET.

The clause inventory now lists all four forbidden-region sub-clauses and replaces the incorrect recursive-sentinel equivalence argument with directed cases. Its result-range row refers to the observable SET. Original fixtures and packets are unchanged.

Validation: 26 directed observations at two placements, five faults rejected. The parent’s 45 plus 258 deterministic files and native/browser qualification are reused by pinned packet and source hashes, as independently replayed in audit 139. This supplement does not rerun unchanged parent suites. Compiler/native R6/R6a and service semantic coverage remain bound through that parent.

```
python3 tests/wasm/stage1/startup-review-139/run.py --output /new/execution
python3 tests/wasm/stage1/startup-review-139/packet.py verify --packet ../ccl-evidence/2026-09-21-stage1-startup-review-139-r1 --output /new/replay
```

The previously recorded real-image installation, population consumers and full LL15 initializer/worklist obligations remain open.
