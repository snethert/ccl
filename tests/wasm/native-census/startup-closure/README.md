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
