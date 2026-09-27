# Target loader review checkpoint

Development stopped at the user's request on 26 September. This change is for
review against `6b834922e6ad0e2c8e14940317174bad72caef24`; it does **not** claim
READY or loader completion. Product Lisp delta: **912 added / 165 removed**.

The level-0-only image enters the original `%toplevel-function%`, reaches the
original `%fasload`, executes the new opcode-72 handler and completes **21
target file loads**, through `l1-files`. CLOS initialization runs on the target.
The next load, `l1-typesys`, stops with checked 4 in `%extend-vector`, called by
`copy-uvector` for a numeric ctype. The diagnostic points to the allocator's
admitted vector representations; extending that support remains future work.
Before the error system loads, undefined `make-condition` recursively masks
that first check and the final reported error is checked 2.

The source-derived runtime sequence compiles **56 files** into bundles, then
stops in `lib/foreign-types.lisp` on `%PTR-EQL`. This is distinct from target
execution. The 21 level-0 files are the only cross-loaded boot inputs.
Historical 36 compiled / 36 cross-loaded totals describe the earlier producer;
none of its 15 cross-loaded level-1 files is used to supplement this boot.
`level-1.lisp` itself is still in progress and is not counted as a completed
load. The profile exclusions below mean 56 is not a completion fraction of
the original 95-file runtime list.

## Implementation

The target FASL handler preserves expression-table identity, reads the
function's constants and metadata, assigns special binding indices and asks
the code installer for a logical code ID. Logical IDs remain distinct from
paired engine table slots. The installer validates the complete nested graph
before publishing it. Imported Lisp values occupy collector-owned root cells
and can move during collection. The bundle producer compiles level-1 without
host cross-loading it; the namespace and file service supply its bytes to the
original target loader.

Backend additions admit the native arithmetic, MAKE-ARRAY and MAKE-STRING
compiler macros, portable REQUIRE operations, literal membership, function
metadata and uncached class dispatch. Default node-vector initialization now
matches the native allocator's zero contract. Target-width numeric boundaries,
hash values and dynamic binding restoration are handled at their backend or
primitive boundaries. The new FASL pool length has a fixnum declaration so
its allocation does not call a level-1 array constructor during level-0 boot.

The two premature `standard-generic-function-p` dependencies in `l0-def.lisp`
are removed: `function-name` uses native code and `lfun-vector-name` checks
the native function bits before reaching the CLOS name accessor.

Native load order is retained for included modules. Native targets already
supply allocator/compiler primitives, kernel process services, foreign calls
and OS streams. The original boot failures exposed missing Wasm implementations
of those contracts; moving level-1 definitions earlier would hide those gaps.
The explicit startup-profile change below is separate from that ordering.

## READY profile and unexecuted code

The user approved host-backed stdout/stderr, `startup-ccl` in the initial
process, and deferring the interactive listener and in-image compiler. See
[decision A2](../../../../../doc/WASM/stage1/ready-decision.json).
This change adds the process service and Wasm output streams, but the real
bootstrap stops before their initialization or startup. Service tests alone
do not establish ordinary stream behavior after boot.

The author selected these module exclusions for that profile; they remain
subject to review and are not additional user quotations:

- In-image compiler: SUBPRIMS, VREG, VINSN, REG, BACKEND, NX2, ACODE-REWRITE,
  NX, OPTIMIZERS, NFCOMP and COMPILE-CCL.
- Native debugger/platform tools: BACKTRACE-LDS, BACKTRACE, DB-IO, MISC,
  DUMPLISP, PATHNAMES, TIME, EDIT-CALLERS and REMOTE-LISP.
- L1-SOCKETS and SOCKETS; native terminal setup, scheduler and finalization
  startup are excluded by the one-Worker profile.

Native pointer eval entrypoints in `lib/level-2.lisp` and native PC-map argument
recovery in `lib/arglist.lisp` are excluded on Wasm. The portable definitions
remain. Home-directory and error-string services are supplied in `w32-files`.
These choices do not establish the complete callable dependency closure.
The target definition-body replacement inventory still needs reconciliation
with the unchanged 25-replacement cap before READY can be claimed.

## Verification and limits

The finalized evidence pack is the sibling directory
`ccl-evidence/2026-09-26-stage1-loader-target-runtime-r1`. Its review record
binds source and tool identities, reports, original failures and reproduction
commands. The earlier `loader-target-bootstrap-r1` pack is historical and
has not been overwritten.

| Check | Result |
| --- | --- |
| Focused loader | PASS: 12 compiled modules; generated result 42; native matches for six MIN/MAX, four keyword, five MEMBER, 49 REQUIRE and four vector-initialization cases; nested outermost-binding result `(30 99 99)`; seven installer refusal controls. |
| Process service | PASS: clock/wait/configuration/startup strings, Unicode stdout/stderr, exit and READY signal; twelve refusal cases. This does not execute Lisp startup. |
| Collector owner | PASS: 18 checks for movable imports, alias identity, release, snapshots, capacity and workspace growth. |
| Namespace primitives | PASS: 196 comparisons, 49 controls and five injected faults. |
| Existing readers | PASS: 612 file/profile comparisons across all 17 profiles. |
| Native R6/R6a | PASS: 21,843 tests, 75 upstream-disabled tests; all 164 FASLs compared and restored (43 byte-identical, 121 decoded/declared comparisons). Original failing comparisons are retained. |
| Compiler corpus | FAIL: fresh replay still stops at `CORE-CONDITION-INITARGS`, checked 15. Original failure and fresh replay are retained; no passing regression-floor claim. |
| Real bootstrap | STOPPED after 21 completed loads; first checked 4 in `%extend-vector`; READY not reached. |

The condition-fixture diagnostic follows `function-name` through
`lookup-lfun-name` to a NIL `*lfun-names*` table. The selected fixture does not
initialize that level-0 dependency, while the real bootstrap does. This is the
current diagnosis, not a waived test or a repaired regression baseline. The
fixture and product are left unchanged at this stop-development checkpoint.

Native verification also caught initialization-code grouping changes caused by
placing reader conditionals around `%eval-redef` calls. The Wasm exclusions
now live in the local macro expansion, preserving native call source notes.
No native executable-difference allowance was added to the comparator.

Directed refusal coverage is not exhaustive. Binding-chain corruption clauses,
remaining heap-snapshot metadata refusals, cached-materialization tampering,
required-bundle omission and the complete READY dependency closure remain open.
Existing acceptance and coverage totals are not advanced. Independent Claude
review remains required before acceptance.

## Reproduction

Use separate fresh output directories under `/private/tmp/ccl-work/codex`.
The optional `--reuse=DIR` verifies matching WAT, bundle identities and cached
artifact hashes; it does not substitute a prior source compilation.

```sh
python3 tests/wasm/stage1/loader-target/build.py /private/tmp/ccl-work/codex/loader-focus
node tests/wasm/stage1/loader-target/check.mjs /private/tmp/ccl-work/codex/loader-focus
python3 tests/wasm/stage1/loader-target/build.py /private/tmp/ccl-work/codex/loader-boot --boot0
python3 tests/wasm/stage1/loader-target/build.py /private/tmp/ccl-work/codex/loader-bundles --level1
node tests/wasm/stage1/loader-target/boot0.mjs /private/tmp/ccl-work/codex/loader-boot /private/tmp/ccl-work/codex/loader-boot/runtime-binaries --bundles=/private/tmp/ccl-work/codex/loader-bundles
python3 tests/wasm/stage1/loader-level1/qualify.py native /private/tmp/ccl-work/codex/loader-native
python3 tests/wasm/stage1/loader-level1/qualify.py readers /private/tmp/ccl-work/codex/loader-readers
python3 tests/wasm/stage1/loader-level1/qualify.py corpus /private/tmp/ccl-work/codex/loader-corpus
node tests/wasm/stage1/loader-target/process-check.mjs
```

Add `--trace --inspect-code=290` to the boot command to observe the first
implicit check in `%extend-vector`. The observer preserves the checked
operation and exception propagation, records original/observed hashes, and
is diagnostic evidence distinct from the uninstrumented boot result.
