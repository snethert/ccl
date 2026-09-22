# Whole-file environments and numeric execution

**460 original definitions execute against native (+2), 429 with a non-NIL
witness (+2). Corrected admission on the same 2,231-definition cohort is
1,895, down from the previously reported upper bound of 1,986.** This packet
repairs audit 156 F1 and executes the three requested numeric files through
CCL's file compiler. No shared compiler, runtime or CCL source changes.

The closure proposal remains the compiler prerequisite. This packet records
no acceptance, integration or LL15 credit.

## Recount

`run.py` starts from the pinned pristine U1 archive, applies the unchanged
proposal, and builds the compiler once. Each of the 57 target worklist files
then runs in a fresh process from that image. `compile-file` handles its own
EVAL-WHEN, REQUIRE, macros, symbol macros and lexical environment. The observer
intercepts `fcomp-named-function` only for Wasm output, and passes its actual
lexical environment to the bootstrap entry. The output sink stops before the
native FASL writer. No target function or placeholder is installed in the host.

There are 44 complete file compiles. The thirteen stops retain their conditions
and messages. Successfully processed prefixes are counted, not unvisited text.
The old 2,231 definitions all join by file and name to the new records; duplicate
or missing joins refuse the report. Their admission is **1,895**. The file
compiler additionally encounters **893** definitions omitted by the old walk,
including macro-generated definitions, compound SETF names and previously
unvisited source. These are separate: **2,747 of 3,124** total encountered
DEFUN records lower. Neither denominator is a complete bootstrap inventory.
Anonymous initializer records are retained but excluded from these counts.

`audit156-cohort.json` gives all 57 reported macro-callee cases their current
outcome and expansion trace. Six belonged to architecture-excluded sources,
not the 2,231-definition target cohort; 51 are measured here. None of the
thirteen suspect macro names remains a callee in any new record. The seven
lock-free hash refusals from the prior packet remain refused. No execution
credit was attributed to the old macro-callee cases.

The controls compile one source with and without its compile-time environment.
They distinguish a local macro, a symbol macro and a required macro from the
old fake function/global reads. Separate cases retain the empty-under-Wasm and
self-call-only refusals. The control processes are separate, so the first run
cannot install macros for the second.

## Numeric files and execution

| File | DEFUNs | Lowered |
| --- | ---: | ---: |
| l0-numbers.lisp | 107 | 66 |
| l0-float.lisp | 49 | 21 |
| l0-bignum32.lisp | 68 | 60 |

All three files compile through to the end. Their 155 emitted modules, including
anonymous records and closures, assemble. Remaining lowerings are explicit;
whole-file completion does not mean every function is admitted. Expansion now
exposes missing target macros such as `%NUMERATOR`, `%MAKE-DFLOAT` and
`%MAKE-SFLOAT`, rather than hiding them behind a `NUMBER-CASE` call.

The execution driver replaces standalone candidates from these files with their
file-compiler output. A refused numeric definition cannot fall back to its
standalone module. **21 numeric definitions execute in 161 cases, compared
644 times at both placements before and after collection.** Every row is joined
to its actual whole-file module name. The full inherited corpus passes
**16,560 target comparisons** with the existing separately declared numerical
differences. No earlier executed original is lost.

The two additional definitions are `MULTIPLY-FIXNUMS` (48 signed/common-domain
fixnum pairs, including products requiring bignums) and
`UPGRADED-COMPLEX-PART-TYPE` (seven type inputs). The native references for
l0-numbers and l0-float are compiled from those same unmodified files in their
native file environments. This matters: the saved image contains a later
definition of UPGRADED-COMPLEX-PART-TYPE, while the level-0 source returns REAL.
The initial comparison against that later image definition failed and is
retained. This is source-stage qualification, not a claim that the level-0
entry is the final CL API. For bignum32 mathematical entries, the pinned image's
64-bit counterparts supply native answers. MULTIPLY-FIXNUMS uses inputs that
are fixnums on both architectures; `%BIGNUM-LENGTH` is not credited by comparing
incompatible digit counts. Full Lisp bignum arithmetic still lacks callees.

Other corpus definitions keep their previous compilation provenance. The
recount does not claim that all 460 prior/new executions now come from whole
files. No new compiler implementation or numeric service is supplied here.
Native R6/R6a is reused by exact compiler/source identity from the reviewed
closure packet; no redundant native rebuild is run.

## Replay

From a checkout of this commit, with the sibling evidence repository:

```sh
python3 tests/wasm/stage1/bootstrap-file-environments/packet.py verify \
  --packet ../ccl-evidence/2026-09-22-stage1-bootstrap-file-environments-r1 \
  --output /tmp/ccl-file-environments-replay
```

The packet retains source/tool/dependency pins, every definition/condition,
expansion and callee records, hashes of all emitted modules, and a compressed
archive of the three numeric files' modules and the execution artifacts. It
omits the disposable source tree, saved compiler image and the other files'
repetitive WAT, which the verifier regenerates and checks by digest.
Development failures are retained separately. `compile.lisp` and `cases.lisp`
are written drivers based on the recipes fixture; the unchanged runner and
runtime harness are reused from that pinned fixture.
