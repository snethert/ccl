# Lexical exits and CONS — 17 September 2026

The [isolated proposal](../../../tests/wasm/stage1/b-block-exits/README.md)
adds BLOCK/RETURN-FROM through U1's actual front-end IR, plus the rooted CONS
operation U1 uses for closed block tags. It is a prerequisite of U1's
HANDLER-CASE expansion, not a claim to complete signalling or the LL05/LL19
slots. The reviewed special-parameter/PROGV unit is already integrated.

Local returns select the exact compiler identity and a kind-3 control record;
Lisp THROW searches only kind-1 CATCH records. Complete values survive cleanup,
dynamic unbinding and redirected exits. Cross-function returns keep U1's fresh
tag, captured cell and CATCH/THROW expansion. A block without local-return IR
adds no redundant record. Active local exit extents inhibit tail transfer;
callees can still run bounded tail chains. Local returns currently use Wasm
exceptions, with no performance claim.

CONS evaluates and roots its operands once in order, checks the complete
allocation, writes D1's CDR/CAR fields and publishes the allocation pointer.
Expired block closures are checked target refusals, including when another
block is active. They are not native comparisons outside a valid extent.
The corpus retains all predecessor cases and adds nested, shadowed, local and
closure-mediated returns, effects in argument/default evaluation, PROGV,
cleanup replacement, zero/130 values and 3,000-step tail children.

The obsolete unread registry that collided above 447 modules is removed from
both harnesses. The larger corpus crosses that threshold, and a regression
restoring the old writes is rejected. Actual owned registry ranges now have
explicit capacity assertions. The loader's only change is a profile bump for
the expanded control-kind vocabulary; incompatible predecessor catalogs are
refused. The binary reader and stub remain unchanged.

The first incorrect-target mutant exposed a test gap: the original nested
blocks did not keep both targets live. The added two-live-block case rejects
it. Unwind-state and root/VSP/result-restoration omissions with no intervening observer
are disclosed rather than counted as rejections; collector qualification must
cover those windows. The finalized corpus contains 492 modules, 1,639 native/model
cases and 6,556 target comparisons, with 20 target-only
checks, 16 rejected compiler mutants and four regressions. Native
R6/R6a, lazy composition, loader controls and the retained verifier pass. Replay
recompiles all modules and mutants byte-identically and reproduces their first
failures. The 36 inherited 100,000-transfer tail chains still pass; all compiled
calls use zero public wrapper dispatches.

Final inspection also corrected the evaluator’s literal-body guard for FLET
and LABELS. The complete declared corpus and source forms are unchanged;
original producer snapshots remain retained, and replay uses the corrected model.

Condition objects, signalling, handler dispatch, MULTIPLE-VALUE-CALL,
TAGBODY/GO, symbol installation, binding growth and collector integration
remain open. All control records still share the explicit stack and its
result-reservation cost. The user accepted this unit after Claude’s seventy-eighth audit; its exact reviewed bytes are integrated.

Packet: `ccl-evidence/2026-09-17-stage1-b-block-exits-r1`.
