# Original-source constants, specials and OR

Throughput: **426 → 472 → 574 → 639 / 2,492 unchanged DEFUNs admitted**,
respectively integrated entry, quoted symbols in pools, special references,
and OR. **Eight original definitions execute against native**, versus four in
the accepted entry packet. No LL15 or BT-0 slot credit: most of the source
worklist and production dependency installation remain open.

This proposal follows the user's order after audit 142. It changes only the
bootstrap entry's backend behavior. The legacy entry's ten retained modules
remain byte-identical. There is no source rewriter, C implementation or new
production JS service. `symbols.lisp` and `or.lisp` follow CCL's Lisp style.
The shared compiler and runtime are untouched by this proposal.

## Implementation

* Quoted symbols, including condition names, use the existing identity-based
  rooted literal pools. They no longer become condition-mask integers in this
  entry. Conses, cycles, sharing, vectors and the previously admitted literal
  families use the same pool planner/exporter/linker. This does not extend the
  encoder's object-family allowlist (e.g. ratio literals remain unsupported).
* Special reads, SETQ and bindings use the integrated checked binding runtime.
  A module's `:symbols` list maps private wire names to actual Lisp symbols;
  neither package names nor uninterned identities are discarded. Function
  symbols and keywords use the same owner identities, so imports and quoted
  references agree. The owner must supply stable pinned symbol objects and
  their binding indices. The fixture materializes cells from this explicit
  identity inventory; this is not the production package installer.
* CCL NX1 emits OR as a list of acode forms. Nonfinal operands evaluate once,
  in single-value, nontail context. A successful operand publishes one primary
  value. The final operand preserves all values and inherits tail position.
  There is no Lisp call or collecting safepoint between testing a successful
  primary and publishing it; the existing result assurance cannot collect.
  Compare `nx1-or` and `x862-or` in the pinned native compiler.

## Execution

The eight unchanged definitions are MEMQ, APPEND-2, ADJOIN-EQ, UNION-EQ,
LOADING-FILE-SOURCE-FILE, DEFAULT-PRINT-LEVEL, DEFAULT-PRINT-LENGTH and BITP.
Their native references are their untouched fdefinitions. The oracle binds
loading-file-source-file to NIL, print-level to 7 and print-length to 9;
the target owner supplies those same global values.

Fifty modules cover these definitions and additional semantic witnesses:
package-distinct and uninterned symbols, keyword spelling, cyclic literals,
closure pools, global reads, parallel/sequential binding, special parameters,
SETQ, PROGV, THROW/cleanup, OR evaluation order, short-circuiting, tail calls,
and zero/one/five values. The corpus has 114 rows (113 native-derived and the
inherited explicit target-word-size witness), each at two heap placements
and before/after movement: 456 comparisons, 228 between-call collections.

A **test-only** hook inserted at the entry of a generated NIL leaf invokes the
unchanged collector at an ordinary call boundary. It adds 28 collections
inside calls, with live binding values and cyclic/shared pools. Native calls
use GC and return NIL. The hook is not an emitted compiler feature and is not
proposed for integration. After each copy the old space is poisoned. All
function pool fields and symbol value cells are explicit external root slots;
arguments are rooted, and all 64 TCR words except allocation/results outputs
and every binding-vector slot are checked on return. Pinned imported symbol
identities stay fixed; pools and cons values move.

Five compiled faults are rejected at focused native-derived cases: restoring
condition-mask literals, bypassing dynamic bindings, reversing OR's test,
dropping final multiple values, and reevaluating a successful OR operand.
Twenty-two inherited admission controls still pass. R6/R6a is rebuilt for the
proposal: 21,843 tests, 162/164 unchanged FASLs (only the two permitted module
registration artifacts differ), all 164 restored.

## Audit-142 carry items

`throughput.json` retains host error class **and message** for all 278 errors.
Only printed host object addresses are normalized (`#xOBJECT`); all other
message text is retained. Unsupported acode refusals remain
separate from host errors. The 268 explicit reader/name skips remain visible.

`frontier.json` reports **82 statically dependency-closed definitions** from
the 639 admissions. Dependencies are recorded as the emitter uses named
callables, across the root and child modules. A fixed point removes functions
whose callees are missing; recursive components may remain. No external
primitive is assumed implemented just because its name is linked. Dynamic
calls, source references to APPLY/FUNCALL and duplicate definitions are
conservatively excluded. This figure is not an assembly, runtime or image
installation claim. The actual native-matched definition count is eight.

The reader also records calls to macros declared at file top level, including
PROGN/EVAL-WHEN wrappers. It flags 62 definitions, none admitted. This is a
conservative source diagnostic, not execution of compile-time environments.
Whole-file compilation with file-local macro definitions remains owed.

## Replay

```
python3 tests/wasm/stage1/bootstrap-values/packet.py verify \
  --packet ../ccl-evidence/2026-09-21-stage1-bootstrap-values-r1 \
  --output /tmp/ccl-bootstrap-values-review
```

The verifier recompiles positive, ordered-census and fault compilers in
pristine U1 copies, runs native and target cases, and compares deterministic
artifacts. The already rebuilt native R6 proof is reused by exact compiler
hash; add `--native` to rebuild it again. Development failures are retained;
none is hidden by the final passing record. Native R6/R6a and the accepted
compiler/runtime hashes are bound independently of the census counts.
