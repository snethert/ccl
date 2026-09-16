# Generated optional and keyword binding — 16 September 2026

The next LL05 implementation unit adds `&optional` and `&key`, supplied-p
flags, explicit keyword aliases and `&allow-other-keys`. The unit was reviewed without defect in Claude’s sixty-sixth audit,
accepted by the user and integrated byte for byte. The
[integration record](integration-b-bindings.json) pins the decision and payload.

CCL's real front-end lambda-list records drive the emitter. Defaults run
in binding order, may use earlier parameters, and can call other generated
functions. Bound values and presence flags occupy explicit rooted slots.
Keyword search preserves the first occurrence, including the first
`:allow-other-keys` value. Bad counts, odd keyword lists and unknown keys
reach the existing checked exception boundary. Default failures restore
VSP, roots and result ownership.

The corpus contains 51 generated functions and 248 cases independently
computed by a Python source interpreter and native CCL. The target repeats
these as 992 comparisons across low/high stacks and direct/observed calls,
with 1,432 ownership inspections. Sixteen recompiled compiler mutants,
nineteen source refusals and twenty resource refusals exercise the checks.
R6/R6a covers a fresh registered build/test and removal build against the
accepted pristine baseline; all 164 FASLs match again after removal.

Final inspection found that lowercasing import names could conflate distinct
escaped keyword spellings. This slice now refuses noncanonical spellings;
the former compiler fails the new refusal case, and that regression capture
is retained. Keywords remain fixture-supplied identities, not production
symbol objects. The unit supplies neither collection nor allocation, and
its checked error tags are not the complete Lisp condition machinery.

No LL05 slot credit is claimed. Next: rest-list allocation and APPLY
validation, followed by closure/function objects and the condition path,
then lazy adapters and bounded tail transfers.

[Source and replay commands](../../../tests/wasm/stage1/b-bindings/README.md).
Packet: `ccl-evidence/2026-09-16-stage1-b-bindings-r1`.
