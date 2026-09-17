# Multiple-value producer storage correction — 17 September 2026

The user withdrew acceptance of the multiple-value unit and directed Codex to
fix all three observations immediately. Commit `610eec09` reversed the prior
integration; shared source remains at the accepted lexical-exit/CONS unit.
The original execution and Claude's review remain historical evidence.

The [isolated correction](../../../tests/wasm/stage1/b-mv-storage/README.md)
removes the inherited MVC producer budget, moves nonescaping literal callables
and their environments to stack storage, and removes the intermediate return
buffer copy. Producers use demand-sized temporary buffers independent of the
public output reservation; completed buffers change ownership rather than being
copied into another temporary buffer. Calls and literal VALUES can publish into
the continuation destination directly. Captured variable cells and escaping
inner closures retain their required heap storage.

Dynamic catch, block and cleanup records retain result buffers by ownership
transfer. A successfully completed protected form needs no further allocation to
retain its values before cleanup. Temporary storage is bounded separately and
reclaimed on normal return, exception and tail transfer. Indirect root records
have explicit ownership and extent checks. The internal loader profile is
versioned for the two new continuation metadata words and this storage contract.

The final run has 581 modules, 1,829 native/model cases and
7,316 target comparisons, with 17 rejected compiler mutants and
four inherited regressions. 40 temporary-storage checks exercise exact
bounds, guard bytes, cleanup effects and reclamation. Sixteen copy-observer cases
count executed instructions, including a semantically equivalent extra-copy
regression for those cases. 48 chains of 100,000 tail transfers use 2 KiB
stacks. Native R6/R6a and lazy composition pass; the retained verifier replays the
compiler, oracles and controls. No timing claim or LL05/LL19 credit is made.

This is a new proposal, **not accepted or integrated**. Claude review and renewed
acceptance precede integration. Final public results still obey their output
reservation. The collector must learn the indirect temporary-root format and
stack callable objects; production temp-stack integration and the existing
collector-time obligations remain open. Conditions and handlers follow this
correction's review/integration, not the withdrawn unit.

Packet: `ccl-evidence/2026-09-17-stage1-b-mv-storage-r1`.
