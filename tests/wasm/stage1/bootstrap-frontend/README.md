# Bootstrap front end R1

This proposal raises admission of unchanged source from 33 to 426 in a common
2,492-definition inventory. Four original definitions execute and match native:
CCL::MEMQ, CCL::APPEND-2, CCL::ADJOIN-EQ and CCL::UNION-EQ. This is front-end
progress, not LL15 completion. Shared compiler/runtime files are untouched.

The new, separate bootstrap entry reads trusted CCL source inside
CALL-WITH-TARGET, including its TARGET nickname binding. CCL's own DEFUN expansion
supplies the implicit block, declarations and global function name. NX1 handles
ordinary macros, lexical MACROLET/SYMBOL-MACROLET environments, lambda defaults
and declarations. There is no consumer walker, source symbol substitution,
handwritten membership routine, or new C/JS Lisp service. Authored Lisp follows
the surrounding CCL conventions.

Symbol identities and safe wire identifiers are separate in the link map. Original
CCL names reach the existing symbol-cell call path. NX1's builtin-call indices
resolve through CCL's builtin name vector into that same path. No name is rewritten
in a variable binding or quoted datum. Compound SETF function identities remain
refused; this is partial BT-3, not a production namespace or installation claim.

The emitter now handles NOT's two condition senses, inverted EQ, and SET-CAR/
SET-CDR's value-return convention. Unchecked TYPED-FORM delegates to its child,
including all multiple values, as native pass 2 does. A requested runtime type
check refuses explicitly; THE is not indiscriminately erased. Host compiler
macros are disabled for this entry. LOAD-TIME-VALUE refuses at its NX1 dispatch
entry, even when a lexical macro expands into it: NX1 otherwise recursively
compiles before creating that acode and could escape through the outer module's
result tag. The original API keeps its whitelist and legacy byte output.

## Evidence

- 16 modules; 46 native cases, 184 comparisons at low and above-2-GiB placements,
  92 real collections. Four source definitions use untouched native functions
  as the oracle. Additional witnesses exercise lexical macro scope, SETF order
  and returned value, zero/multiple values, NIL CASE clauses, declarations,
  optional defaults, and both boolean condition senses.
- Collection occurs between invocations, with arguments rooted and old space
  poisoned. This does not claim new internal allocation-retry qualification.
  Every invocation checks all TCR words except the declared allocation/result
  outputs. The collector is built from the unchanged integrated source.
- The target word-size witness reads TARGET::NODE-SIZE through the actual source
  entry and returns 4. It is a target-layout assertion, not native word-size
  equality. The other cases use the pinned native kernel/image.
- Ten legacy module texts (including children) are freshly compiled through both
  the integrated compiler and proposal and must match byte for byte.
- Admission controls cover the source reader, link shape/identity/name bounds,
  unsupported checked types, unknown calls, host compiler macros, and direct
  and macro-generated LOAD-TIME-VALUE. Legacy WHEN, CASE and THE still refuse.
- R6/R6a rebuilt in pristine U1: 21,843 native tests, 162/164 FASLs unchanged,
  only the two permitted registration artifacts differing; all 164 restored,
  five existing architectures and seventeen module profiles unchanged.

## Throughput method and limits

`measure.lisp` streams complete files under the target reader context, honoring
reader conditionals and IN-PACKAGE. It never rewrites source identifiers, quoted
objects, declarations or THE. A failure is retained by file/offset/reason;
recovery at the next column-zero form is a diagnostic aid, not proof that the
whole file was read. There are 268 explicit read/name skips, including compound
function names. The 2,492 readable top-level DEFUNs are a stable local denominator,
not the complete startup worklist. Both entries see this same inventory.

The legacy entry receives original source, without the old instrument's SUBLIS
aliases. Hence its 33 is not comparable to the historical 178/2,823 proxy.
The proposal is offered explicit symbol links discovered in the form; admission
means the emitter returned a module, not that its dependency closure is installed,
or that all 426 functions execute. Full-file assembly, target-specific macro
qualification and a complete read/load environment remain owed. Target binding
while reading cannot repair host constants already captured in previously
compiled target-specific macro definitions. The execution corpus uses portable
macros and no such definitions. Undefined behavior from false unchecked type
declarations is not a compatibility claim.

No population layout or rewriter is integrated. The adopted next population
shape is native's three fields: zero GC link, type and data, with strong tracing
of type/data. MEMEQL/ADJOIN-EQL still need their actual dependencies admitted;
the shared EQL service remains the comparison implementation when required.

## Replay

```
python3 tests/wasm/stage1/bootstrap-frontend/run.py --output /tmp/frontend-run
python3 tests/wasm/stage1/bootstrap-frontend/packet.py verify --packet ../ccl-evidence/2026-09-21-stage1-bootstrap-frontend-r1 --output /tmp/frontend-replay
```

The ordinary verifier regenerates the compiler, recompiles all executed modules
and both legacy cohorts, reruns native oracles and moving execution, and checks
all pins and retained bytes. `--native` additionally rebuilds R6/R6a using
`native.py`; otherwise its already-executed report is reused by exact compiler
hash. The separate native command requires `--evidence`, `--work`, and `--output`.
