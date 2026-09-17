# Multiple-value producer storage correction — 17 September 2026

The user withdrew acceptance of the multiple-value unit and directed Codex to
fix all three observations immediately. Commit `610eec09` reversed the prior
integration; shared source remains at the accepted lexical-exit/CONS unit.
The original execution and Claude's review remain historical evidence.

The [isolated correction](../../../tests/wasm/stage1/b-mv-storage/README.md)
removes the inherited MVC producer budget, moves nonescaping literal callables
and their environments to stack storage, and removes the intermediate return
buffer copy. Producers use demand-sized temporary buffers independent of the
public output reservation. R2 gives each descriptor four inline words, so small
results and scalar callees need no arena allocation. On frame retirement those
inline values copy at most four words; larger buffers still transfer ownership
without an intermediate result copy. Calls and literal VALUES can publish into
the continuation destination directly. Captured variable cells and escaping
inner closures retain their required heap storage.

Dynamic catch, block and cleanup records retain large buffers by ownership
transfer and small values in their own inline slots. A successfully completed protected form needs no further allocation to
retain its values before cleanup. Temporary storage is bounded separately and
reclaimed on normal return, exception and tail transfer. Indirect root records
have explicit ownership and extent checks. The internal loader profile is
versioned for the two new continuation metadata words and this storage contract.

The R2 run has 587 modules, 1,833 native/model cases and
7,332 target comparisons, with 19 rejected compiler mutants and
four inherited regressions. 56 temporary-storage checks exercise exact
bounds, guard bytes, cleanup effects and reclamation. Sixteen copy-observer cases
count executed instructions, including a semantically equivalent extra-copy
regression for those cases. Eight direct-delivery boundary observations require
a valid root chain and unchanged descriptor bytes before and after the copy.
Producer descriptors now precede the growing argument area, and direct delivery
retires callee roots before overwriting their storage. New controls force scalar
arena allocation and omit root retirement; both are rejected. 48 chains of 100,000 tail transfers use 2 KiB
stacks. Native R6/R6a and lazy composition pass; the retained verifier replays the
compiler, oracles and controls. No timing claim or LL05/LL19 credit is made.

This is a new proposal, **not accepted or integrated**. Claude review and renewed
acceptance precede integration. Final public results still obey their output
reservation. The collector must learn the indirect temporary-root format and
stack callable objects; production temp-stack integration and the existing
collector-time obligations remain open. Conditions and handlers follow this
correction's review/integration, not the withdrawn unit.

R1 remains retained with Claude’s eightieth-audit review. R2 addresses that audit’s
scalar-allocation and descriptor-overwrite observations; it adds 16 inline stack
bytes per indirect descriptor. The dynamic mode still propagates to descendants,
but arena allocation is now the overflow path. Arena exhaustion remains a checked
refusal. The collector obligations are unchanged.

Packet: `ccl-evidence/2026-09-17-stage1-b-mv-storage-r2`.
