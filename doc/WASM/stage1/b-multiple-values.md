# Multiple-value calls and bindings — 17 September 2026

The [isolated proposal](../../../tests/wasm/stage1/b-multiple-values/README.md)
implements MULTIPLE-VALUE-CALL and MULTIPLE-VALUE-BIND from U1's actual IR.
The reviewed lexical-exit/CONS unit was accepted and integrated separately as
`e82f01ba` on the user's “accept, integrate and proceed”.

Value producers append directly into a rooted continuation argument area,
after the callable is evaluated and before it is resolved. Earlier arguments
survive later producers; zero values add nothing. Extent checks use i64 before
writes. Ordinary compiled calls enter the internal B body, and legal tail calls
use Wasm tail transfer. There is no intermediate heap list, extra argument-vector
copy or public wrapper on this path.

Value binding evaluates its source before entering any new bindings, supplies
NIL for missing values and discards excess values. Captured lexical variables
use shared cells; SPECIAL bindings unwind through the existing extent. The
pre-emitter IR witness and independent Python root analysis include these locals.

The finalized corpus has 547 modules, 1,808 native/model cases and
7,232 target comparisons. 17 compiler mutants and four inherited
regressions are rejected. 12 target-only capacity checks preserve
stack fences and restore partial argument ownership. 48 chains of 100,000 steps
run in 2 KiB stacks, including multiple-value calls and bindings. Native R6/R6a,
byte-identical retained recompilation and unchanged-loader lazy composition pass.
All compiled calls use zero public wrapper dispatches.

Each producer still shares the caller's explicit result reservation; the total
argument count can exceed that per-producer budget. This does not provide
unlimited memory, result growth, a collector, condition signalling or handler
dispatch. Literal MVC lambdas use ordinary heap closures with exact allocation
checks; the literal APPLY stack-storage optimization is not generalized here. It supplies the multiple-value prerequisite of U1's HANDLER-CASE
:NO-ERROR expansion. No LL05/LL19 slot credit is claimed. The new backend remains
a proposal awaiting Claude review before integration.

Packet: `ccl-evidence/2026-09-17-stage1-b-multiple-values-r1`.
