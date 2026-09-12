# Native dependencies and redefinitions — 12 September 2026

The dependency extension is executed and independently reviewed by Claude's [seventh audit](claude-review.md) with no defect found and a byte-identical graph reproduction; it remains census input without gate credit. It uses the unchanged three-file observation patch in disposable pristine U1 copies. It adds no shared-source hook, compiler transformation or kernel change. The accepted r5 operator record remains separate; neither this extension nor the complete LL15-b/c census is accepted.

## Call identities

The r7 rebuild records 103,313 calls from 51,342 distinct native compiler function objects. The extension resolves 1,918 of the original 3,647 unnamed call observations: 1,522 lexical calls, 379 self calls and 17 calls through directly identified lexical function values. A weak EQ map assigns function, call-site and variable identities without retaining dead compiler objects. Self calls target their containing function; their first acode operand is an argument list, not a callee. The 1,500 builtin calls use the evaluated native builtin table.

The remaining 1,729 call observations comprise 1,072 function-variable calls and 657 computed callees. These remain unresolved. The graph retains 6,019 function-reference records, all exact function targets have observed bodies, and later empty observations cannot erase earlier dependencies. Global binding names have only unqualified compiled candidates: 951 of 5,989 referenced bindings lack a matching compilation in this capture. That is a worklist, not evidence of 951 missing implementations. No pruning or complete runtime candidate-set claim follows from these counts.

## L0, L1 and L2 redefinitions

The extension records both source declarations and sampled native binding changes. It recognizes top-level definitions, selected expanded definition forms, `%fhave`/`fset` writes and `setf` of function or macro bindings, preserving source position, observation phase and enclosing `eval-when` situations. It uses the compiler's actual expansion hook. It does not interpret quoted data, arbitrary function bodies or local macro bodies as executed definitions.

There are 24,369 declaration observations, 11,053 name/namespace groups and 263 groups with more than one source location. Fifty-five groups span L0, L1 or L2/library boundaries. These include:

| Binding | Earlier source role | Replacement source |
| --- | --- | --- |
| `CCL::FSET` | L0 `l0-def.lisp` installs `BOOTSTRAPPING-FSET` through `%fhave` | L1 `sysutils.lisp` defines `FSET` |
| `CCL::%DEFUN-ENCAPSULATED-MAYBE` | L0 installs a bootstrap alias | L2/library `encapsulate.lisp` defines the replacement |
| `CCL::SET-FUNCTION-INFO` | L0 installs a bootstrap function | L2/library `misc.lisp` defines the replacement |

Compilation order is not load order. The native host is already bootstrapped, and cross-dumping L0 does not install its definitions into that host. Accordingly, source histories do not pick a final active definition. The sampled host history separately records 6,184 changes across 10,973 tracked bindings. Each change retains the previous and current function/macro identity and the sample interval; its installation site is not inferred. Macro and function namespaces remain distinct.

The native probe installs an L0 alias, replaces it in L1, and writes a new function binding in L2. It checks the new result after each load, confirms that a retained old function still works, and replaces a macro through the same three layers. Its four FASLs are byte-identical with and without observation. Eight controls reject damaged dependency or definition histories; a repeated empty-body observation also preserves the original call graph.

This is not exhaustive interception of every installation. Samples can miss transient changes between checkpoints, indirect installation effects and target-image changes during cross-dump. The recognized declaration forms are a subset of Lisp's ways to create definitions. Compiled source-version candidates are retained alongside them. A complete census must account for those gaps before assigning conservative candidates or removing bootstrap versions.

## External startup trace

The user's Terminal r2 capture succeeded. The first PID-only capture is retained as failed coverage evidence. The updated runner selects a byte-identical kernel copy under a unique executable name as well as the held launcher's PID. It checks an actual open before exec, an actual open inside CCL, the clean image open, matching native PID and clean termination. Only `fs_usage` uses administrator access.

The reconciler verifies the retained bytes and successful open records. Five controls reject missing opens, an unsuccessful image open, a wrong PID and unparsed loss output. The trace shows the pinned clean image being opened, with no additional Lisp source or FASL pathname recorded. Host loader/device activity, input-directory metadata, optional missing bundle metadata and harness reads are identified separately. Eleven background disk events are excluded from CCL activity.

The [loader-context follow-up](../evidence/native-loader-contexts.json) classifies the four anonymous/relative operations as host dyld directory activity. The inference requires a same-thread descriptor chain between explicit dyld path witnesses, before the image open; it preserves every original pathname and leaves the anonymous base unknown. Fifteen controls reject missing coverage or retain unresolved contexts when the chain is damaged, including a substituted Lisp path and an unrelated anonymous open. This follow-up needs independent review. No unresolved pathname contexts remain in this capture. The result is `CAPTURE_VERIFIED_PARTIAL_RECONCILIATION`, not full census acceptance. This is one `--no-init` batch image startup, not cold disk caches, a full image rebuild or proof of initializer prerequisite semantics. The clean trace image is distinct from the instrumented image used to record the 35 startup callbacks.

## Restoration and remaining work

Both r6 and r7 execute 21,843 eligible native tests in each of their clean and observed runs; 75 upstream-disabled tests remain disclosed. During observation, 161 of 164 FASLs match and the same three hooked FASLs differ. After reversal all 164 match; all 872 archived source files and 167 clean output files are restored. The source patch hash remains `610934dd76069d1187ebcdc0db53f92b2937ff8fca9985cd0b93abfcd830c493`. The implementation still starts from pristine U1 and its bootstrap.

Next work is conservative resolution of the dynamic calls and global binding versions, a qualified seed set, and the lowering/effect/initializer joins required by [the census contract](../contracts/census.md). The intermediate graph is deliberately separate from that contract's complete exchange format. There is no ABI timing claim or new gate acceptance.

Reproduction commands are in the [fixture README](../../../tests/wasm/native-census/README.md). The [summary](../evidence/native-dependencies-summary.json) and [evidence index](../evidence/index.json) identify r7, the graph, controls, trace and original failures. New tooling and evidence need an independent review.
