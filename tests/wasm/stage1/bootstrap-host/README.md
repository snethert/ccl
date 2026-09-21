# Bootstrap inputs, foreign references and the first target OS module

**349 original definitions execute (+17); 323 have a non-NIL return witness
(+5).** Eight definitions have error-only witnesses. No compiler/runtime change
or slot credit. This proposal keeps `linux-files` in both startup lists.

Audit 151 corrected the earlier advice to remove that file: it contains the
shared platform interface, not just Linux file operations. The reviewed inputs
proposal remains unintegrated. This packet carries its recipes and constant
branches forward, omitting both module-list edits.

## Execution

The new recipes cover thread status, class/package reference state, vector
output close, file-length state, type specialization, and error entry points.
The original bodies are unchanged. A generated caller catches ERROR for the
error rows; the untouched native definition supplies the expectation. These
rows compare arrival at the handler, cleanup and thread/global restoration,
not the detailed condition class or payload. Error sentinel values are excluded
from the non-NIL witness count. `THREAD-TOTAL-RUN-TIME` and
`SHUTDOWN-LISP-THREADS` are native NIL-returning bodies, explicitly not scheduler
implementations.

The complete run has 2,972 rows and 11,888 target comparisons: 11,820 native-compatible comparisons, four declared signed-zero differences, and 64 target-protocol comparisons. There are 6,310 collections. All earlier recipes remain. `progress.json` dispositions every one of the
49 previously closed original definitions without recipes: 17 now execute,
32 remain named with their particular representation, process-state, foreign
interface or transport dependency. The review's count of 56 also included
seven primitive/fixture names; those are listed separately. This does not claim
that all remaining recipes have been supplied.

The original worklist is restored: 57 files, 42 read completely, and a lower
bound of 2,145 parsed / 1,685 admitted definitions. The historical directory
scan changes to 1,871 / 2,509 as additional source becomes readable; it is not
the fixed 2,492 denominator. The backend bytes are unchanged. Neither count
implies dependency closure or a ready image.

## Foreign surface and source branches

`foreign-sites.md` and `foreign-sites.json` in the execution packet list every
one of 409 syntactic foreign constant/function sites in the restored worklist,
including existing-platform-only code. The scanner skips strings, escaped
symbols and comments and admits whitespace after the dispatch character.
CCL independently reads all 57 files with the real Wasm reader conditionals and
acquisition disabled **for inventory only**. That inventory is never compiled.
It joins each of the 100 active foreign calls back to its exact source site.
The three active foreign type reads are listed separately. No active foreign
constant read remains.

One source proposal branches 108 constant sites in twelve CCL files, with 58
explicit target protocol identifiers. These values are not acquired from the
host and must never be passed unchanged to native libc. Providers must translate
errors, flags and results at their boundary. Constants in currently excluded
memory, process and FFI paths do not admit those operations. All unresolved
calls have a disposition; they remain implementation work, not successful
stubs. Ordinary compilation still stops on an unavailable foreign reference.

Native R6/R6a passes 21,843 tests: 146 FASLs unchanged and all 164 restored.
Changed source-file code and non-location data are identical. Source-location
parents are retained in the comparison record. The 204 reader comparisons are
compositional: invert the edits to restore every surrounding byte and compare
each replacement under all seventeen existing target profiles. This is not a
claim that every foreign platform's entire file loads on macOS.

## Target OS first cut

`w32-os.lisp` is the proposed `level-1/WASM32/w32-os.lisp`. CCL's own file compiler
compiles it whole. Seven named entries execute: capability lookup, GETENV,
GET-UNIVERSAL-TIME, signal/wait/timed-wait semaphore calls and YIELD. The owner
supplies Lisp-callable capabilities through `*wasm-host-services*`. A missing
capability signals; no operation silently succeeds without its provider.
The provider must complete the wait before returning. Provider invocation,
argument order/defaults, multiple values and side effects are observed, including
for WAIT-ON-SEMAPHORE, whose public return is T.

The harness installs generated Lisp providers with explicit protocol answers.
Those answers are asserted independently in `host-checks.py`, in addition to
running the target module on native CCL. This is **not** native OS equivalence,
a browser provider, a scheduler, or permission to remove `linux-files`.
These definitions and provider probes are excluded from original-CCL execution
and closure counts.

CPU-COUNT retains the ordinary cache algorithm but refuses compilation at
GLOBAL-SETQ. It is a named unfinished entry, not a supplied stub. The remaining
platform interface, live capability installation, scheduler semantics, source
caller routing and startup selection remain owed. The OS file is retained as
source in this fixture; it is not in the shared tree or its module lists.

## Reproduce

From a clean checkout, with the pinned sibling evidence store:

```sh
python3 tests/wasm/stage1/bootstrap-host/packet.py verify \
  --packet ../ccl-evidence/2026-09-21-stage1-bootstrap-host-r1 \
  --output /tmp/ccl-bootstrap-host-verify
```

The verifier recompiles the corpus in pristine U1, runs both placements before
and after collection, checks protocol rows and prior controls, and replays the
reader matrix. Native qualification is reused by exact proposal/source hashes;
the compiler and all runtime bytes equal the integrated versions. The forty
collector checks are reused by source and binary identity. `development.json`
retains original failures without copying complete temporary trees.
