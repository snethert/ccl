# Clean-image candidates and proposed startup seeds

This read-only inspector adds resident native code/binding identities and evaluated backend metadata to the reviewed r7 graph. It prepares a candidate set and seed proposal, not the qualified census exchange graph. All dynamic call bounds remain unqualified and LL15 acceptance remains blocked.

The current revision adds kernel callback slots, the builtin vector and applicable
toplevel methods in the same snapshot. See the [seed revision and reachability
diagnosis](../../../../doc/WASM/stage0/startup-seed-revision.md). `seeds.json` is
revision 2; `seeds-v1.json` preserves the historical proposal used by the pinned
exchange assembler. New snapshot IDs are never substituted into older graphs.
The callback table is observed after restore; image-save equality remains open.
The checker retains all callback slots, including the foreign-thread callback.

To reproduce the membership diagnosis, materialize the reviewed wrapper graph
using its existing verifier, then pass that graph and its recorded digest:

```sh
python3 tests/wasm/native-census/startup-closure/diagnose_reachability.py \
  --graph FULL-REVIEWED-GRAPH.json.gz --graph-sha256 RECORDED-SHA256 \
  --output NEW-DIAGNOSTIC.json
```

It evaluates the original seed set and counterfactual edge removals. It writes
only a diagnostic report, never a replacement graph or a closure result. The
retained revision-2 packet compresses `image.json` and `candidates.json`; its
manifest records the original filenames and uncompressed hashes. Decompress
these for comparison with fresh runner output.

If the retained kernel has no executable bit, make an executable disposable copy
with `install -m 755 RETAINED-KERNEL NEW-KERNEL` and pass that copy below. Preserve
the archive's permissions and bytes.

From the repository root:

```sh
python3 tests/wasm/native-census/startup-closure/run.py \
  --kernel /tmp/ccl-native-census-r7/ccl/dx86cl64 \
  --image /Users/buildsomething/Source/ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64.image \
  --graph /Users/buildsomething/Source/ccl-evidence/2026-09-12-dependencies-analysis-r3/graph.json \
  --output NEW-DIRECTORY
```

The kernel may be relocated; it must match the retained clean baseline kernel. The image must retain its `baseline/build` location below its original successful U1 `results.json`. The runner checks those direct identities once. It loads the existing JSON writer but never enables its observation hook, patches shared source, rebuilds CCL, writes a FASL or saves an image. Inspector definitions exist only in the disposable process and are included in the inventory. No observed image becomes an implementation baseline.

The six output files are `image.json`, `candidates.json`, `summary.json`, `controls.json`, `native.log` and `run.json`. The run record retains exact commands and input/source/output identities. Source is retained by the main repository; unchanged inputs and whole prerequisite trees are not copied. Original failures remain in their output directory. Only finalize one successful packet per deliverable.

`image-inventory.lisp` uses U1's `%map-lfuns`, `closure-function`, `%map-lfimms`, existing SETF maps and evaluated backend tables. Local numeric identities have meaning only in that snapshot. `candidates.py` retains the two identity namespaces separately and joins named candidates without claiming past binding state. `seeds.json` is a proposal requiring independent review. `test_candidates.py` checks retained input witnesses and fourteen omission/identity controls; its synthetic SETF collision is explicitly an analysis case.

Read the [scope and findings](../../../../doc/WASM/stage0/startup-candidates.md) before interpreting counts. No timing, Wasm implementation, complete lowering, initializer-prerequisite or acceptance claim follows from this packet.

## Assemble the retained-input census projection

```sh
python3 tests/wasm/native-census/startup-closure/assemble.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --output /tmp/ccl-census-projection-new
```

The output directory must not exist. `exchange-inputs.json` pins only direct inputs, using their existing committed identities. The runner reads no full archive catalog and rebuilds no native prerequisite. It verifies the accepted LL08-a session, preserves all three function identity namespaces, pairs raw effects, decodes the evaluated opcode alists, reproduces the trace classification and runs specific omission controls. A successful analysis exits zero with `ASSEMBLED_UNQUALIFIED`; **the census contract remains BLOCKED**. Failure to cover an input or an unexpected graph error exits nonzero.

The output is `census.json.gz`, `joins.json.gz`, `summary.json`, `controls.json` and `run.json`. The finalized packet also retains a short development-failure record and the finalization environment (including the interpreter identity). Gzip uses a zero timestamp. The first file expands directly to the existing census exchange schema, without extra fields; the second carries source witnesses and unresolved work. `effects.py`, `opcodes.py` and `exchange.py` produce the projection; `check_exchange.py` independently checks its input coverage; `test_exchange.py` requires a distinct rejection reason for each mutation of the actual projection. The two shared U1 source files read as ordering witnesses are pinned and never edited.

To invoke the existing checker separately without flooding the terminal with repeated unresolved-node diagnostics:

```sh
gzip -dc /tmp/ccl-census-projection-new/census.json.gz > /tmp/ccl-census-projection.json
python3 doc/WASM/tools/check-census.py /tmp/ccl-census-projection.json > /tmp/ccl-census-check.json
```

That checker is expected to exit 1 for this unqualified projection. See the [joined census report](../../../../doc/WASM/stage0/joined-census.md) for what the inputs prove and the remaining observation work. No LL15 result or project acceptance is inferred from a successful assembly.

## Integrate reviewed compiler/loader identities

```sh
python3 tests/wasm/native-census/startup-closure/join_identities.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --output /tmp/ccl-initializer-joins-new
```

`identity-inputs.json` pins the reviewed original graph, build/cold joins and cold
callback stream. The rich packet's manifest binds the distinct executed observer
versions. Only direct inputs are verified; the runner does not scan the catalog,
repeat native builds or rerun old controls. The output directory must be new.

`identity_join.py` adds process-scoped code identities, exact callee/materialization
and FASL links, returned-value witnesses and conservative entry/return ordering.
It preserves all original graph records. Image-reader completion never becomes
execution of its queued Lisp initializer. `test_identity_join.py` supplies twenty-four
specific corruption controls. The checker derives the exact complete added node records,
edge relations with multiplicity, initializer IDs and module inventory from the
captures; surplus graph records also reject. The new graph still fails full
closure, with its existing unresolved obligations and three explicit integration-scope nodes.

The five output files are the extended exchange graph, its identity witnesses,
summary, controls and producer record. Gzip timestamps are fixed for reproducible
graph/witness bytes. See the [initializer integration report](../../../../doc/WASM/stage0/initializer-joins.md).

To verify the checker fixes against the existing graph without regenerating it:

```sh
python3 tests/wasm/native-census/startup-closure/verify_identity_join.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --output /tmp/ccl-initializer-check-new
```

The focused verifier pins the original graph and witnesses, verifies the unchanged
producer, and reproduces five former-checker escapes using its source at
`f3b4b07e` and six metadata escapes at `c421e39a`. All twenty-four cases must
reject in the corrected checker. It retains
the comparison in its control report and never copies the graph or native packs.

## Native emission dependencies

Join the retained compiler's emissions and parameterized subprimitive operands:

```sh
python3 tests/wasm/native-census/startup-closure/join_lowering.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --output /tmp/ccl-emission-joins-new
```

`lowering-inputs.json` pins the reviewed graph, full compiler capture, reviewed
join file, evaluated subprimitive table and the two kernel provenance records.
The U1 template definitions are a separate source pin. No native process or
shared-source patch is involved. Only these direct inputs are verified.

The packet retains `delta.json.gz` and `joins.json.gz`, the controls, sampled raw
operand events, summary and run record. It references the original graph in
place. To produce a complete exchange-format file from a finalized packet:

```sh
python3 tests/wasm/native-census/startup-closure/join_lowering.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --materialize /absolute/path/to/emission-packet \
  --output /tmp/ccl-emission-census-new.json.gz
```

Materialization verifies the fragment and base identities and the exact graph
additions. It writes a new file and preserves all original graph records.
Format 2 also verifies the pinned image and both kernel records, and requires
an explicit equality-witness edge for every observed build operator slot.
ID, name, flags, encoded value and handler must match the image slot; process-local
handler code identities remain separate. Historical format-1 packets require the
original sources at 363fc2d4 and must be reconciled before feeding closure.
Observed handler ancestry remains distinct from exact leaf dispatch and static
coverage. Six parameterized subprimitive operand layouts have decoding rules;
the report separates actual execution from synthetic layout cases. See the
[scope and remaining work](../../../../doc/WASM/stage0/native-emission-joins.md).


## Boot execution and cold source origins

```sh
python3 tests/wasm/native-census/startup-closure/join_boot.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --output /tmp/ccl-boot-integration-new \
  --materialize /tmp/ccl-boot-census-new.json.gz
```

`boot-inputs.json` pins the reviewed initializer base, emission fragment, boot
capture and cold-origin witness. The runner reconstructs the prior graph and
checks its already reviewed materialization identity, reproduces the boot
analysis from the retained event stream, and integrates every observed boundary,
function-cell checkpoint/change, load and cold source origin. No native process,
new patch, full build stream or archive catalog is needed.

`boot_join.py` produces the additive fragment. `check_boot.py` independently
builds full node records and edge multiplicities from the retained inputs,
checks every event prerequisite and origin witness, and bounds all additions.
Source paths, code objects and binding values retain the boot namespace.
Absolute and relative loader aliases combine only when their retained bytes
agree. Source inventory membership has explicit conservative edges; it is not
cross-run callable or source-byte equality. Opaque function-cell values remain
unresolved, and the active handoff frames receive no invented return.

The producer runs corruption controls and the generic census checker. A passing
integration still reports `BOOT_INTEGRATED_UNQUALIFIED` and a blocked complete
closure. The optional full graph is disposable; retain only the fragment,
controls, summary and run record. To check and materialize a retained packet:

```sh
python3 tests/wasm/native-census/startup-closure/materialize_boot.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --packet /absolute/path/to/boot-integration-packet \
  --output /tmp/ccl-boot-materialization-new
```

That command produces `census.json.gz` and `materialization.json`. It verifies the
input and fragment bindings, independently checks all added records, preserves
the base, and compares the complete graph with the producer's materialization
when one is recorded. See the [integration report](../../../../doc/WASM/stage0/boot-integration.md).
