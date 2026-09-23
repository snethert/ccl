# Projected-image READY join — R6

Original-definition credit remains **550 / 515 non-NIL**, with no LL15 slot
claim. This revision executes CCL's native bignum printer and list helpers
through cold READY, and builds the printer's radix tables on the target.
It carries the unintegrated R5 compiler/owner proposal without changing its
compiler, runtime or CCL source bytes.

## Native printer and startup state

R5's fixnum resource strings hid a file-environment gap: the standalone
`%PR-INTEGER` module called `WITH-ONE-NEGATED-BIGNUM-BUFFER` as a function.
`numeric-files.lisp` now compiles all of `l0-int.lisp` through CCL's file
compiler and selects `%INTEGER-TO-STRING`, `%PR-INTEGER` and `PRINT-BIGNUM-2`
in class mode. The macro expands normally. The selected module names, source
files and binary hashes are asserted in `startup-support.json`.

`READY-INITIALIZE` runs the native top-level radix-table initializer after
image admission. The native reader compares the submitted body with the
original DO* in `l0-int.lisp`, allowing only its six lexical variable symbols
to differ by package. The body allocates and publishes `*BASE-POWER*` and
`*FIXNUM-POWER--1*` using the target's 30-bit fixnums. The oracle runs the same
body with its 61-bit fixnums; the tables deliberately differ, while formatted
strings must match exactly. This is a level-0 top-level effect, not one of the
35 registered startup callbacks.

Every boot starts with both radix globals cleared. The native comparison covers
11 signed integers in bases 2, 8, 10, 16 and 36: zero, target fixnum boundaries,
±2^60 and dense larger bignums. Each of the 55 results survives a collection.
Replacing the initializer's function cell with a non-initializing entry must
refuse. The harness cannot satisfy this check using projected host tables.

## Native list dependencies

The complete `lib/lists.lisp` environment supplies unchanged `LDIFF`, `MAPC`
and `MAP1`. The caller reaches their public function cells indirectly, checks
LDIFF's identity stop and dotted-tail copying, then calls MAPC with unequal
length lists. Its closure accumulates results and collects on each callback;
the result must preserve the first list's identity and stop at the shorter
list. The dependency census includes both explicitly exercised public cells.

The writer and all four cold readers execute both support callers, giving ten
native comparisons containing 275 string results and fifteen MAPC callbacks.
The four cold boots complete 282 collections; all 16 refusal controls pass.
Native PROGV restores all five affected oracle globals after each of the eleven
submitted entries, including the new radix tables.

## Carried READY contract

The R5 proposal fixes MAKE-STRING's native allocation self-call using the
existing checked allocator. The boot owner installs all four public EQ table
bindings before invoking generated admission. Eight corrupted class/method
images enter READY-START directly; refusal preserves seven startup roots,
including the radix globals. Deleting the generated admission guard must fail
root preservation. The seven owner checks, 31 loader checks, moving heap-key
control and poisoned legacy condition registry remain in force.

The image contains 612 classes and 33 generic functions. READY uses class
conditions, strong populations, one Worker, disabled scheduler/finalization,
and uncached dispatch. The owner publishes READY after return and FAILED on
throw. R6 adds no new C or JS implementation of Lisp library functions.

## What remains

The conservative walk includes **646 modules, 113 operators and 30,682
occurrences**, with 86 missing edges naming 61 callees and 38 indirect-call
modules. It closes the spurious macro call, LDIFF and MAPC. Proper macro
expansion and the additional library paths expose ABS and four float helpers;
they remain explicit, as do printer stream-lock branches. RETURN-IT is true
for these formatting calls; this packet does not implement stream support.

The replacement census includes all 602 named modules and all 175 modules
without source attribution. A candidate upstream name is not form equality;
the replacement cap is not claimed. All 35 registered startup callbacks remain
undischarged against this incomplete closure. LL15-a/c/d remain open.

## Reproduce and qualification reuse

```sh
python3 tests/wasm/stage1/ready/run.py /private/tmp/ccl-work/claude/ready/replay
python3 tests/wasm/stage1/ready/packet.py verify ../ccl-evidence/2026-09-23-stage1-ready-join-r6 /private/tmp/ccl-work/claude/ready/verify
```

Choose either command; they are not two required passes. The changed whole-file
driver passes 26,048 fresh corpus comparisons (zero inherited), plus the
writer, cold readers and controls. All 33 proposed compiler/CCL source files equal R5, so its 21,843-test
R6/R6a qualification is reused by complete source identity. `native-reuse.json`
binds that packet and its native reports; no native rebuild is claimed.

Caches are disposable. The saved native compiler image is review tooling,
not the target heap. Retention keeps the clean author execution and removes
its disposable output. Historical packets replay from their own revisions.
