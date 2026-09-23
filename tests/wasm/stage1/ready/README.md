# Projected-image READY join — R5

Original-definition credit remains **550 / 515 non-NIL**, with no LL15 slot
claim. R5 fixes a real MAKE-STRING recursion in the READY dependency graph,
moves public table binding into the boot-owner proposal, and tests generated
admission through READY-START. Shared compiler, CCL and runtime files remain
unchanged pending review of this proposal.

## MAKE-STRING and the printer dependency

Auditing the resource-string path exposed an executable defect. CCL's
`lib/sequences.lisp` MAKE-STRING validates arguments and then calls itself in
a form its native compiler expands into allocation. The Wasm backend emitted
that re-entry as recursion. Even `(make-string 30)` never returned. The retained
diagnostic isolates the hang from FIXNUMP and %FIXNUM-TRUNCATE, which return.

`compiler.py` proposes one lowering at that SELF-CALL site, using the existing
checked string allocator. It recognizes the constant keyword/element-type
shape of CCL's own calls. Ordinary calls still enter the unchanged Lisp body
and run its argument checks. No C/JS service or replacement Lisp implementation
is added. `numeric-files.lisp` compiles the complete sequences file environment
and selects MAKE-STRING in class mode, together with its unchanged %BADARG
callee from l1-aprims. Without this second step its type error
would use the poisoned legacy condition registry; that failure is retained too.

Cold startup exercises indirect calls at lengths 0, 1, 30 and 33, character
fills, operand order with collections, and a caught invalid-character error.
CCL's unchanged resource-string fallback returns `Error #0`, `Error #987654`
and `Error #-37`, matching native. The new compiler runs the full existing
corpus: 26,048 fresh comparisons / 19,824 collections pass. R6/R6a on the
complete proposal passes 21,843 tests, 164 restored FASLs and 17 target profiles. The pristine native baseline is
reused by identity, while the registered native build and tests are fresh.

This does **not** implement stream locks or remove their static edges.
%INTEGER-TO-STRING calls %PR-INTEGER with RETURN-IT true, avoiding its stream
write on this path. The conservative graph still includes the printer's other
branches, interactive error reporting and unresolved lock primitives.

## Boot ownership and admission

The proposed `process.mjs` uses the accepted InitializationOwner. Its `start`
entry requires an installed image and a named entry, resolves all four public
GETHASH/PUTHASH/REMHASH/CLRHASH bindings before writing any cell, and invokes
the generated initializer. The binding module uses no Node API. These are
trusted, digest-bound owner inputs, not a sandbox for arbitrary entry names.
Seven small owner checks cover successful installation and each distinct
refusal, including a bad fourth binding leaving all public cells unchanged.

Eight cold controls corrupt class shape, CPL presence/head, own wrapper,
wrapper class/hash, method combination or method function, then invoke
READY-START directly. They bypass the harness's status call. Each must fail
with a checked refusal, leave five startup roots untouched, and leave the
process FAILED. The source-level guard-omission control recompiles only the
submitted file and must fail the startup-root preservation assertion.
The earlier isolated status/refusal checks remain as native comparisons.

The selected projected image has **612 classes and 33 generic functions**.
Class conditions, strong populations, one Worker, disabled scheduler and
termination, and uncached standard dispatch are unchanged. Four cold boots / 46 collections cover both placements, with and without
movement. All 15 refusal controls pass; deleting the generated admission guard
is rejected by the startup-root preservation assertion. They resolve every class,
exercise moving heap-keyed tables, construct/read a condition and catch an
error. The owner publishes READY after return and FAILED on a throw; the
published-last memory check remains a separate harness assertion.

## Census and remaining work

`replacements.json` enumerates **all 548 reached modules** (509 named),
including all 172 without source attribution and anonymous code. It searches the complete upstream
source for antecedents, including compiler/optimizers.lisp compiler macros
and x8632 LAP.
A name match is explicitly **not** a proof of unchanged source. Missing
attribution is reported; the 25-name replacement cap remains undecided until
method/helper/branch attribution is complete. Controls prevent missing source
metadata from shrinking the inventory.

The conservative closure has 109 operators / 24,238 occurrences, 83 missing
edges and 36 indirect-call modules. No edge is pruned because a boot or an
admission test passed. All 35 native startup callbacks remain undischarged: their current
symbol/effect join cannot prove absence from an incomplete walk. LL15-a/c/d
still require that closure, full replacement attribution and callback effects.

## Reproduce

From this revision beside the evidence store, choose the target replay, the
separate native rebuild, or retained-packet verification. These are not three
required passes:

```sh
python3 tests/wasm/stage1/ready/run.py /private/tmp/ccl-work/claude/ready/replay
python3 tests/wasm/stage1/ready/native.py /private/tmp/ccl-work/claude/ready/native
python3 tests/wasm/stage1/ready/packet.py verify ../ccl-evidence/2026-09-23-stage1-ready-join-r5 /private/tmp/ccl-work/claude/ready/verify
```

The compiler session key binds the proposed backend and the complete class
compilation driver. A warm session avoids rebuilding the corpus, but a full
execution remains required for this compiler/driver change. The verifier reuses
the retained native qualification only after equality of every proposed source
file; `native.py` is the separate command to rebuild that qualification. The eight submitted
functions compile through CCL's file compiler. The saved native compiler image
is validation tooling, not the target heap. Retention deletes disposable
outputs; historical packets replay from their own source revisions.
