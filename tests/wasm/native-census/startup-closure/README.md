# Clean-image candidates and proposed startup seeds

This read-only inspector adds resident native code/binding identities and evaluated backend metadata to the reviewed r7 graph. It prepares a candidate set and seed proposal, not the qualified census exchange graph. All dynamic call bounds remain unqualified and LL15 acceptance remains blocked.

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
