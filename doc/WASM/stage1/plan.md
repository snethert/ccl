# Stage 1 work plan — adopted 16 September 2026

Status: ADOPTED. The [inventory](inventory.json) of 31 tests is the
criterion of the [Stage 1 ledger](../evidence/current-stage1-gate-result.json)
by the user's decision of 16 September; Codex is the authorized author of
the shared-compiler changes with Claude as reviewer; the single-thread JSPI
profile is deferred. The entry condition is met: all 48 Stage 0 variants are
accepted. The [1A packet](1a.md) has three accepted records after Claude’s review and the user’s
[acceptance](acceptance-1a.json); the ledger now has eight accepted records, 23 missing and
zero unreviewed records. [LL04 generated representation](representation.md)
is reviewed and accepted. The [reviewed unit](integration-1a.json) is integrated;
[LL07’s generated typed conversions](conversions.md) are reviewed, accepted and [integrated](integration-ll07.json).
The [generated B call core](b-call-core.md) now executes required-argument
direct/indirect calls and full values and is accepted and integrated.
The accepted and integrated [optional/keyword binding unit](b-bindings.md)
adds defaults, supplied-p values and keyword validation. The
accepted and integrated [rest/APPLY unit](b-rest-apply.md) supplies real cons allocation and
runtime-sized arguments, removing the 64-argument ceiling. The accepted and integrated
[runtime result-capacity unit](b-results.md) removes the fixed 64-value
ceiling. The accepted and integrated [callable-object unit](b-callables.md) now supplies
checked object/symbol dispatch, live function cells and recursive calls.
The accepted and integrated [lexical closure unit](b-closures.md) executes
escaping shared mutable captures. The accepted and integrated [local-function unit](b-local-calls.md)
adds FLET/LABELS, lexical recursion, inline lambda calls and literal APPLY.
The accepted and integrated [proper tail-call unit](b-tail-calls.md) adds bounded Wasm
tail transfers and stack-temporary literal APPLY callables. The accepted and integrated
[lazy installer](b-lazy-calls.md) authenticates paired entries against
a trusted catalog and preserves the generated corpus through first-use loading.
By the user’s 16 September direction, the accepted and integrated [direct-context unit](b-direct-context.md)
places compiled-call arguments directly in the continuation and enters the internal
body, retaining the public wrapper at boundaries. It removes the extra argument
copy and wrapper. Both units were approved after Claude’s seventy-third audit.
The accepted and integrated [UNWIND-PROTECT unit](b-unwind-protect.md)
now supplies cleanup on normal/checked-exception exits and inhibits tail transfer
while cleanup or retained values are pending. The accepted and integrated [CATCH/THROW unit](b-catch-throw.md)
adds generated nonlocal exits and a published catch/cleanup chain.
The accepted and integrated [dynamic special-binding unit](b-special-bindings.md) now covers LET/LET*,
references, SETQ and restoration across those exits. The accepted and integrated
[special-parameter and PROGV unit](b-dynamic-bindings.md) extends that mechanism
to lambda lists and runtime symbol lists. The accepted and integrated [lexical-exit unit](b-block-exits.md)
adds BLOCK/RETURN-FROM and U1’s fresh CONS tags, a prerequisite of the real
HANDLER-CASE expansion. The original [multiple-value unit](b-multiple-values.md), whose acceptance was withdrawn,
supplies MULTIPLE-VALUE-CALL and MULTIPLE-VALUE-BIND for its :NO-ERROR path.
The [storage correction](b-mv-storage.md) removes the inherited producer budget,
intermediate large-result copy and nonescaping literal MVC allocation. Its R2
follow-up adds inline small results and retires roots before destructive delivery.
R2 is now accepted and integrated after Claude’s eighty-first audit, under the
[new integration record](integration-b-mv-storage.json). The [explicit condition/handler proposal](b-conditions.md) now executes U1’s handler macros and SIGNAL/ERROR over supplied condition proxies. The R2 correction closes the user-CASE scope leak. The [result-scratch proposal](b-result-scratch.md) narrows inherited storage with an independently checked per-callee four-word proof, while preserving dynamic delivery. General first-value/discard propagation remains open for unknown or large-result paths; it must preserve internal multiple-value consumers and nonlocal transfers. Both units are accepted and integrated under [the integration record](integration-b-result-scratch.json). The [combined LL05 qualification](ll05.md) now executes both call-protocol and
stub/tail slots, including implicit arity/designator signalling before unwind.
Both are accepted after Claude’s eighty-fourth audit under [the LL05 acceptance](acceptance-ll05.json); [the exact reviewed implementation is integrated](integration-ll05.json). **Subgate 1B is accepted and integrated, including S1-LL10-a constants after Claude audits 85 and 86.** The [constant-pool plan and qualification](ll10-plan.md) cover shared pools, generated loads, fresh-Worker persistence and the inherited corpus. The [acceptance](acceptance-ll10.json) and [integration](integration-ll10.json) bind the exact reviewed bytes. Production CLOS condition construction, other implicit errors,
binding-vector growth, debugger and collector integration remain later subgates.

**1C current:** [S1-LL19-a](control.md) is accepted and integrated after Claude
audit 88. Its proposal adds bootstrap condition
instances, restarts, the debugger-hook boundary, recoverable stack limits and
interrupt masking. The exact reviewed proposal is integrated. [S1-LL17-a](binding-vector.md) now executes generated SYMBOL-VALUE/SET,
binding-vector growth, restoration and host suspension; it is accepted and
integrated after Claude’s ninetieth audit. Forty native cases, 160 comparisons, 96 resource checks, twelve
compiler mutants and native R6/R6a qualify its bounded scope. The debugger-boundary
follow-up executes ordinary service decline and names persistent fields in TCR v2. General CLOS and
moving-collector work retain their own slots. Next is the precise collector
needed for LL06’s legal-collection temporary tests (LL18-a is an explicit
prerequisite). The [collector core](../../../tests/wasm/stage1/collector-core/README.md) now
executes `v_many`, uses a non-growing unbind lookup, and moves live objects at
explicit poll-service entries. Movement exposed cached capture/self addresses;
the accepted integrated core reloads both through rooted SELF. It has no LL18 credit.
The [movement follow-up](../../../tests/wasm/stage1/collector-live/README.md) now
admits the emitted restart layout and fixes three actual stale-reference paths:
EQ operands, captured initializers and implicit conditions across declining
handlers. It is accepted and integrated after Claude’s ninety-second audit. The [owner boundary](../../../tests/wasm/stage1/collector-owner/README.md)
now executes explicit image/callback/registry/host and TCR root admission,
collection before allocation growth and refreshed host views, including real
memory growth beyond 2 GiB. It is accepted and integrated after Claude’s ninety-third audit.
The [internal retry proposal](../../../tests/wasm/stage1/allocation-retry/README.md)
now connects fixed heap construction and rest lists to the owner, with rooted
operands, reloaded addresses, failure after movement and native R6/R6a tested.
It is accepted, integrated and opt-in; the owner loader profile explicitly admits its service
capability. The [constructor and loader proposal](../../../tests/wasm/stage1/constructor-retry/README.md)
now retries binding-vector, restart and condition allocation, roots their live operands and PROGV cursor,
and admits the owner import under an explicit profile. It is accepted and integrated after audit 95.
[LL18-a qualification](../../../tests/wasm/stage1/collector-qualification/README.md)
now executes those declared root populations, specialized literal layouts,
maximum-memory refusal and independent reclaim accounting. The C/owner proposal
and slot are accepted and integrated after audit 96. [LL06-a qualification](../../../tests/wasm/stage1/temporaries/README.md)
now executes temporary lifetime, evaluation order and actual TAGBODY loops, with
300 legal collections and independent stack/control checks. Its compiler proposal
and slot are accepted and integrated after audits 97/98. Next:
LL12-a callable metadata is accepted and integrated after audit 100; hash-table movement remains LL18-b.

The [closed-transfer proposal](../../../tests/wasm/stage1/closure-transfers/README.md)
now executes closed GO through captured control state, including HANDLER-BIND
handlers and RESTART-CASE clauses, with cleanup, binding restoration, moving
roots and live-target identity. Expired-target refusal is separately scoped as
a target safety guarantee. Eligible ordinary loops now use Wasm branches with
no control-record or exit-exception instructions; a conservative IR proof keeps
operand, nested-loop and pending-extent transfers on the reviewed unwind path.
The proposal is accepted and integrated after audit 99. Closed transfers still
use both catch and exit frames and a catch-search THROW; branch eligibility is
all-or-nothing per TAGBODY. The [LL12-a metadata qualification](../../../tests/wasm/stage1/callable-metadata/README.md)
now fills the existing arity/debug words in an isolated opt-in compiler mode,
with native signatures, actual capture-cell checks, cold installation and fresh-Worker
restoration. It is accepted and integrated after audit 100; default-mode output is unchanged.
The [LL11-a aliases and redefinition qualification](../../../tests/wasm/stage1/binding-installation/README.md)
now validates complete package-qualified binding manifests and publishes fresh
code slots transactionally, keeping saved functions and environments callable.
The compiler is unchanged; the owner installer is accepted and integrated after audit 101.
The [LL11-b empty-dispatch qualification](../../../tests/wasm/stage1/generic-dispatch/README.md)
now executes generated method add/remove/replacement and direct/encapsulated
publication, with NO-APPLICABLE-METHOD-EXISTS and CONTINUE through the condition
path. The native stale-method result remains explicit negative evidence. This
initial one-argument primary-method subset is accepted after audit 102; its compiler is integrated. The portable source forms and scenario helpers remain in the reviewed fixture, ready for bootstrap compilation. Native CLOS is unchanged.
LL16-a numeric operations under D6 is accepted at its declared subset and policy scope. The
[integer service](../../../tests/wasm/stage1/integer-core/README.md) now executes
exact D1 add/subtract/multiply, shifts, integer length and quotient/remainder,
with independent Python and native-policy oracles and compiled faults. Audit 103
found no service defect. Its [follow-up](../../../tests/wasm/stage1/integer-core/review-followup/README.md)
adds the missing quotient-only allocation mutant, large multiply/divide cases
and precise alignment/width diagnostic claims, keeping the binary unchanged.
Both packets are accepted after audits 103/104 and the exact integer service is
integrated. The [generated-call proposal](../../../tests/wasm/stage1/integer-calls/README.md)
now executes inline fixnums and rooted integer fallback through the accepted
service and collector owner: 1,221 native-derived comparisons, 429 collector
copies, one growth and nine rejected faults, with default output unchanged and
native R6/R6a passing. It is accepted and integrated after audit 105, with no slot credit.
The [integer-condition R2 proposal](../../../tests/wasm/stage1/integer-condition-review/README.md)
supersedes unaccepted R1 after audit 106: quote admission is numeric-only,
TRUNCATE matches CCL's NIL-divisor default, ASH checks the count first, and the
native condition oracle defers invalid dividends to native type checking.
The 1,693 comparisons and seventeen controls retain policy-dependent +/* error
priority and wrong-class reader differences explicitly. R2 is accepted and integrated after audit 107, with no slot credit. The [numeric-owner composition](../../../tests/wasm/stage1/integer-owner/README.md)
now executes those existing compiler modes together, with eager/cold equality
and forced movement in all three raw constructors. Its trusted capability
bundle and loader profile are accepted and integrated after audit 108. The compiler
is unchanged and its accepted R6/R6a is reused by exact hash. The isolated
[mixed floating-point primitive service](../../../tests/wasm/stage1/float-core/README.md)
now executes arithmetic, exact integer/float comparisons and coercions against
a rational oracle, with scalar-SSE flag checks. R2 corrects the audit-109
signed-zero oracle defect and adds directed and random coercion coverage; the
service is accepted and integrated after audit 110. Native
CCL differs on explicit integer-coercion overflow despite masked hardware flags
and on huge-integer/infinity ordering; both populations are retained, not claimed
as compatibility. The [collecting owner capability](../../../tests/wasm/stage1/float-owner/README.md)
now executes rooted staging, private arithmetic, assurance and publication under
the live TCR mode, including movement and growth. It is accepted and integrated
after audit 111.
The [generated floating-call proposal](../../../tests/wasm/stage1/float-calls/README.md)
now composes mixed calls, Lisp conditions and a frozen three-capability loader
profile, with 1,900 comparisons per eager/cold run and eleven rejected faults.
It preserves native explicit coercion overflow, infinity comparison and same-format
FLOAT identity. Audit 112 identified native-silent bignum conversion in the
rounding band. Under the [user decision](integer-float-coercion.md), the
[R2 follow-up](../../../tests/wasm/stage1/float-calls/review-followup/README.md)
preserves that behavior while keeping small-integer hardware inexact and later
arithmetic flags. Its 4,379 native cases run in eager/cold and moving modes;
the original mathematical entry still passes its full accepted corpus. The
compiler is unchanged. One exact-tiny native trap difference still follows
the adopted D6 policy. R2 is accepted after audit 113 and its reviewed compiler,
primitive, owner, adapter and loader are integrated byte-for-byte.
[LL16-a qualification](../../../tests/wasm/stage1/numeric-qualification/README.md)
now joins the accepted integer and floating subset through the unchanged
integrated runtime: independent integer policies, mixed floating/condition
cases, eager/cold moving execution, fallback inspection, semantic and omission
controls, and fresh generated checking-cost measurements. Claude audit 114 found
no correctness defect; the slot is now accepted after the performance corrections below. The absolute cost (~80 µs
per floating operation) was not surfaced adequately. The user's performance-fix
instruction takes priority. The [owner fast-path proposal](../../../tests/wasm/stage1/numeric-fastpath/README.md)
removes repeated image enumeration; the [direct Wasm scalar proposal](../../../tests/wasm/stage1/scalar-floats/README.md)
then binds the existing numeric import to Wasm for eligible scalar operations,
eliminating the JavaScript round trip and private-memory staging without a
compiler change. Both proposals were reviewed with no defect in Claude audit 115 and are now
accepted and integrated byte-for-byte, including the digest-bound scalar binary.
Owners select the reviewed fast binding by supplying that binary and its pinned
digest; omitting it preserves the slow service.
Qualification preserves the complete generated corpus, forces allocation
shortages to exercise movement, and measures absolute native/generated cost.
Bignums, nonfinite values, demanding checked FP modes and shortages retain the
existing service. Further cost includes live ownership checks, boxing, temporary
frames and result delivery; the separate persistent-frame timing is not a proof
of stack cost alone. LL16-a is accepted; native policies map to the two generated checking variants,
without admitting source OPTIMIZE declarations or claiming formal performance
qualification.
No broader arithmetic coverage is claimed. [LL18-b hash-table movement](../../../tests/wasm/stage1/hash-tables/README.md)
is accepted and integrated after audit 116: strong EQ backing vectors through
generated callers, actual relocation, cache/rehash controls and native semantics.
The compiler is unchanged. CL hash-surface lowering, weak tables, automatic
table growth and production hash-vector materialization remain outside this slice.
The runtime/scanner integration is complete; proceed to 1E (LL21
materialization and granularity).

LL06's integrated backend already clears `*b-local-tags*` per function. Audit 98
withdraws audit 97's contrary observation. The closure-transfer proposal keeps
that reset; U1's closed-GO lowering uses CATCH/THROW rather than a cross-function
branch map. General DO/DOTIMES/LOOP syntax and broader loop optimization remain
outside this slice. No inventory assertion or acceptance criterion changes.


## What Stage 1 delivers

The outline's Stage 1 exit: coordinated cross-loaded heap and code
artifacts executing through the real Wasm pass 2, vinsns, primitives and
runtime; finalized object, allocation, root and TCR contracts; the selected
B ABI confirmed through generated code; a one-Worker image loader; the
read-only file namespace; a precise single-thread collector; measured and
chosen bootstrap module granularity; and D2's materialization confirmed on
the production path. The adopted inventory has 31 tests, one variant each,
derived from the register's Stage 1 metadata, D7's scheme and the outline's
exit criteria, plus two entries proposed from Stage 0 findings.

## Subgates and order

1. **1A: R6-safe shared-compiler edit.** Backend registration, the wasm32
   arch file generated from [the layout schema](../contracts/wasm32-layout.v1.md),
   module lists, systems registrations and the cross-fasloader registration: x8632 supplies tags/NIL,
   ARM supplies the separate-code precedent, under D6's edit-site plan. S1-LL08-a proves
   R6 and R6a for every existing target after the edit; S1-LL22-b binds
   the build; S1-LL23-a makes generated diagnostics structured from the
   first emitted function. Nothing else starts before S1-LL08-a passes.
2. **1B: representation and B through generated code.** S1-LL04-a and
   S1-LL07-a repeat the Stage 0 layout and conversion fixtures through
   generated access and mutation code; S1-LL05-a and S1-LL05-b repeat the
   B corpus, stubs, adapters and tail chains, binding the accepted B decision
   directly in the generated build; S1-LL10-a fixes constant
   pools. The [engine matrix](../stage0/engine-matrix.md) pins the
   features the emitter may use.
3. **1C: control, bindings, temporaries, closures, code identity and
   numerics.** S1-LL19-a extends the nested-exit fixture to generated
   frames and the condition path; S1-LL17-a the binding subset against
   [the TCR schema](../contracts/tcr.v1.md); S1-LL06-a temporaries under
   legal collection; S1-LL12-a closures and callable metadata; S1-LL11-a
   aliases and redefinition; S1-LL11-b the empty-registry condition that
   corrects the U1 stale-dcode defect; S1-LL16-a the numeric subset under
   the approved floating-point policy over
   [the detection rules](../contracts/floating-point.v1.md).
4. **1D: collector.** S1-LL18-a proves the precise single-thread collector
   on a small heap with complete root coverage; S1-LL18-b proves EQ hash
   tables under real movement, the plan's item 3.
5. **1E: materialization, cross-dump, loader, namespace and
   initialization.** S1-LL21-a confirms D2 on the production emitter
   against the engine pins; S1-LL21-b measures and chooses module
   granularity; S1-LL09-a, S1-LL13-a and S1-LL15-a cover symbols, generated
   installation and the census closure's initializers under the
   [initializer-binding](../stage0/initializer-binding.md) discipline;
   S1-LL14-a loads the coordinated heap and code set into a fresh instance;
   S1-NAMESPACE-a supplies the read-only namespace; S1-LOADER-a boots to
   ready.
6. **1F: gates, controls and contracts.** S1-LL01-a, S1-LL02-a, S1-LL03-a,
   S1-LL22-a and S1-LL24-a repeat the Stage 0 rejection tests through the
   real build path; S1-CONTRACTS-a finalizes the contracts against the
   generated fixtures that executed them.

## Stage 0 outputs each subgate consumes

| Stage 0 output | Consumed by |
| --- | --- |
| [Engine matrix](../stage0/engine-matrix.md) feature and JSPI pins | 1B emitter, 1E materialization; a pin change reruns dependents |
| [Layout schema and ledger](../contracts/wasm32-layout.v1.md) | 1A arch file, 1B probes, 1F contracts |
| [TCR schema](../contracts/tcr.v1.md) | 1A runtime record, 1C bindings, 1D roots |
| [Runtime-contract join](../contracts/runtime-contracts.v1.json) and the frame contract | 1C frames and EH, 1F contracts |
| [Materialization](../stage0/materialization.md) and the D2 materializer | 1E production path |
| [Nested exits](../stage0/nested-eh.md) and the boundary fixture | 1C generated EH |
| [Initializer binding](../stage0/initializer-binding.md) | 1E closure initializers and loader |
| [Kernel-import census](../contracts/kernel-imports.v1.md) | 1A runtime import inventory, 1E namespace and host services |
| [Floating-point detection and policy](../contracts/floating-point.v1.md), specified and executed over its corpus with native x86 agreement; policy decided 16 September (the ARM model) | 1C numerics; policy selected, implementation and cost measurement owed |
| Retained startup worklist and on-demand census queries (LL15-b/c under the v0.2 contract) with seeds, ranks, trap and store dispositions; unknown callees kept separate from proven bounds | 1E closure, bundle composition and module granularity; implementation questions answered by focused native scenarios, not by an exhaustive closure |
| Stale-dcode finding | 1C S1-LL11-b |

## Entry decisions, all made on 16 September

- Author: Codex, for the functional shared-compiler changes as well as the
  fixtures, under the amended standing rule; Claude reviews.
- Inventory: adopted as drafted, the two proposed entries included.
- Floating-point condition policy: the ARM model, recorded in
  [the specification](../contracts/floating-point.v1.md); Stage 1 owes the
  cost measurement of the emitted checks.
- Profile: the single-thread JSPI profile is deferred to the profiles stage.
  Stage 1 runs on the full profile with one Worker.

## Obligations carried from Stage 0 by name

The [Stage 0 exit-criteria review](../stage0/exit-criteria-review.md)
carries four census enumerations into this stage under census contract
v0.2: the kernel-import join (65 imports, dispositions decided), the trap
class join (vocabulary decided, 143 native sites inventoried), the direct
foreign-call inventory (eight startup surfaces named) and the classification
of barrier-sensitive stores. Imports and foreign calls fall due in 1A and
1E, traps in 1C, and store classification before the Stage 2 multi-Worker
collector; the single-thread collector of 1D needs no barrier.

The [ARM lessons](arm-lessons.md) add six more by name: the kernel
globals block (1A), thread-local binding growth and the interrupt-level
binding (1C), stack overflow as a condition (1C), the continuable trap
classes for the lowering inventory (1C), and callback slot installation
(Stage 2). The same document revises one precedent: derive the
cross-fasloader's function handling from `xarmfasload.lisp`, not only from
x8632.

The [runtime obligations](runtime-obligations.md) carry the ARM survey into
1A ownership and addressing, binding-vector growth, interrupt masking,
recoverable stack exhaustion, trap lowering and Stage 2 callback installation.
They are implementation work, not additional claims about accepted Stage 0 evidence.

## Rules carried forward

Small commits with one deliverable each; every packet reproduced by its
verifier; adversarial review from a different model before acceptance;
R6 and R7 unweakened; hand-built Stage 0 evidence never discharging a
Stage 1 ID; no comparative timing beyond the benchmark policy.

User direction, 2026-09-20: LL18-b is accepted and integrated. Pause before LL21; next deliverable removes Node-only digest and Buffer dependencies with synchronous shared SHA-256 and browser execution checks.

Portable digest proposal reviewed with no defect in Claude audit 117 (`fa8ccc0e`): [packet](../../../tests/wasm/stage1/portable-digests/README.md). Shared factories remain synchronous; user acceptance and byte-exact integration are recorded in [integration-portable-digests.json](integration-portable-digests.json). The [review](../stage0/claude-review.md) resolves the same-Worker refusal as a Maglev fault in Chromium 145.0.7632.6; Chrome 153 and Node pass. The pinned README’s statement that diagnostic text made the run pass is unsupported by its retained logs and is superseded by audit 117. Keep this engine/build limitation in browser qualification; neither Firefox nor WebKit is qualified by this packet.

User direction after portable digest integration, 20 September: “proceed”. Resume 1E. [LL21-a materialization](../../../tests/wasm/stage1/materialization/README.md) now executes the canonical-template switch and portable D2 installer against production compiler output, with shared/unshared code results and exact Stage 0 engine pins. Accepted and integrated after Claude audit 118 on the user’s “accept, integrate and proceed”. Next is LL21-b measured module granularity; no performance or complete unshared-runtime claim is imported from this qualification.

LL21-b selects one generated function per module after user acceptance of audit 119, under benchmark policy v3, with complete code-ID/entry maps, measured load costs and retained-code growth. The [qualification](../../../tests/wasm/stage1/granularity/README.md) preserves three old/new generations and closures in late Workers. The exact reviewed owner/build module is integrated; no merged ranking or complete bootstrap latency is claimed. Next is S1-LL09-a generated symbol/package work, followed by initialization and final bootstrap membership before LL14.
