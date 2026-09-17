# Generated lexical exits and CONS

This auxiliary proposal implements BLOCK and RETURN-FROM from CCL's real
front-end IR. It is the lexical-exit prerequisite for U1's HANDLER-CASE macro
(lib/macros.lisp); it does not yet implement handlers or claim LL05/LL19.

Local returns name the exact identity cell created by pass 1, never the printed
block name. A referenced block publishes a kind-3 control record, distinct from
CATCH (kind 1) and cleanup (kind 2). RETURN-FROM evaluates its complete values,
copies them to that record's rooted reservation, and raises the shared exit tag.
The exact target handles the exit after intervening cleanup and special-binding
extents restore themselves. A Lisp THROW ignores kind-3 records, including when
both lexical and dynamic tags are NIL. Active local blocks inhibit tail transfer;
a block without local-return IR adds no redundant record.

CCL lowers cross-function RETURN-FROM to a fresh CONS tag, a captured lexical
binding, and CATCH/THROW (compiler/nx1.lisp). This unit preserves that IR and uses
the reviewed closure and control machinery. CONS roots its two operands,
evaluates them once in order, checks the complete eight-byte allocation, then
stores CDR first and CAR second using D1. There is no poll between construction
and publication. Escaped block closures are tested after their extent ends and
with another block live: the target reports checked CONTROL. This is a safety
check outside the defined dynamic extent, not a native semantics comparison.

The corpus retains all earlier call, binding and cleanup cases and adds local,
nested, shadowed and closure-mediated exits, local-function implicit blocks,
inline lambdas, partial arguments, defaults, PROGV, redirected exits, cleanup
errors, zero and 130 values, and 3,000-step tail children. Native CCL, an
independent Python evaluator and generated Wasm agree at low and above-2-GiB
stack placements. Explicit allocation expectations include hidden tag cells.
Target-only checks cover expired exits and exact/insufficient CONS capacity.
Compiler mutants use the same oracle as the positive corpus. Four exploratory
omissions of unwind state and root/VSP/result checkpoints were unobservable
before enclosing restoration; they receive no rejection credit and remain
collector-time inspection obligations.

The unread registry at address 512 is removed from both eager and lazy harnesses.
The corpus exceeds its former 447-module collision point; a regression restores
the old writes and must fail. Actual registry and symbol ranges have explicit
capacity assertions. This does not claim unlimited fixture capacity.

The loader changes only its profile to `wasm32-shared-B-exnref-tail-block-v1`,
because kind-3 records require a compatible chain walker. The binary reader and
stub are unchanged. A control refuses the predecessor profile. Lazy execution
runs the same generated corpus, while eager execution additionally poisons public
entries and inspects roots, control records and dynamic bindings. Native R6/R6a
and the retained verifier are required; the non-B emitter prefix is unchanged.

Remaining scope: condition classes, signalling, handlers, MULTIPLE-VALUE-CALL,
TAGBODY/GO, symbol installation, binding-vector growth, collector relocation,
allocator slow paths, host re-entry and multi-Worker execution. Control records
share the explicit value stack and scale with the caller's result reservation.
The existing no-GC and exception-payload rooting obligations remain. No speed
claim is made for the exception-based implementation of local returns.

```sh
python3 tests/wasm/stage1/b-block-exits/native.py --evidence ../ccl-evidence --work /tmp/block-native-work --output /tmp/block-native
python3 tests/wasm/stage1/registration/qualify.py --output /tmp/block-native --inputs ../ccl-evidence/macos-u1-inputs --kernel ../ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 --destination /tmp/block-qualified
python3 tests/wasm/stage1/b-block-exits/run.py --evidence ../ccl-evidence --native /tmp/block-native --qualification /tmp/block-qualified --output /tmp/block-run
python3 tests/wasm/stage1/b-block-exits/verify.py --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-17-stage1-b-block-exits-r1
```

Developed only in disposable pristine U1 copies. The predecessor is accepted
and integrated; this proposal awaits Claude's review before integration.
