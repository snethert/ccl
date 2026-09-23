# Stage 1 work plan — adopted 16 September 2026

Status: ADOPTED. The [inventory](inventory.json) of 33 tests is the
criterion of the [Stage 1 ledger](../evidence/current-stage1-gate-result.json)
by the user's decision of 16 September; Codex is the authorized author of
the shared-compiler changes with Claude as reviewer; the single-thread JSPI
profile is deferred. The entry condition is met: all 48 Stage 0 variants are
accepted. The [1A packet](1a.md) has three accepted records after Claude’s review and the user’s
[acceptance](acceptance-1a.json); the current ledger has 21 accepted records, 12 missing and
zero unreviewed records, including the two BT-0 coverage requirements accepted on 21 September. [LL04 generated representation](representation.md)
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

S1-LL09-a is executed as a [generated symbol/package qualification](../../../tests/wasm/stage1/symbols/README.md), accepted and integrated after Claude audits 120/121. The unchanged compiler calls runtime leaves for intern/find/name/package operations; existing EQ and binding emitters consume the real D1 symbols. Hash-version admission and pointer-aware image relocation are executable. Fixed-capacity pinned packages and sealed topology are explicit scope limits, not production package membership or a moving package scanner. Next is S1-LL13-a initialization/installation, then final bootstrap census membership and LL14.

S1-LL13-a is accepted and integrated as [generated initialization](../../../tests/wasm/stage1/initialization/README.md), following audits 122/123. The trusted owner validates region/write metadata and raw TCR ownership before initializing process or Worker state, and refuses implicit Wasm initializers. Two late Workers preserve the mutated image and registry; the original Worker calls its published code again. This bounded synchronous owner has terminal failure semantics, not rollback or a production scheduler. Final bootstrap membership under LL15 and image construction under LL14 remain next.

Audit-122 follow-up: [initialization admission](../../../tests/wasm/stage1/initialization-review/README.md) checks actual Worker-local tables before a claim and rejects dirty fresh/reserved control storage without writes. This sibling fixture preserves R1 replay pins and freezes its own source list. Busy bootstrap/Worker claims still refuse; waiting and retry belong to the scheduler. Accepted after audit 123 and integrated as initialization-owner.mjs, with actual tables supplied to admission. The owner still permits aliased table roles; callers must supply distinct tables because the loader refuses aliases after a claim. Stage 1 now has 21 accepted slots.

LL15 execution prerequisite: the [generated initializer schedule](../../../tests/wasm/stage1/bootstrap-schedule/README.md) validates module identities and prerequisite order before installation, checks generated physical completion and effects, and rejects omitted loads and forged completion. It is accepted after Claude audit 124 and integrated as bootstrap-schedule.mjs, with no LL15 slot credit. Production startup must bind the actual installed digest to the plan and preserve the owner write boundaries; the accepted trusted-callback protocol does not enforce those itself. Its protocol marker functions are not native initializer implementations. Next, bind the actual selected startup entries, required effects and concrete census witnesses to their implementation/replacement records, then execute that selection through this path before claiming LL15 or proceeding to LL14.

The [native reset effects](../../../tests/wasm/stage1/startup-resets/README.md) now execute thirteen selected literal-reset callbacks from the retained startup inventory through generated global-cell writes, with actual pristine-U1 callbacks as oracle. All 35 snapshot rows remain explicit; 22 stay open, and this is not the whole emitted-initializer population. The accompanying private-catalog adapter binds the actual installed digest to the schedule. Accepted after Claude audit 125; the private-catalog adapter is integrated byte-exactly as bootstrap-install.mjs. Generated reset effects remain retained evidence pending production symbol materialization. Auxiliary, no LL15 credit. Next remains the selected host-service/nonliteral callback and definition effects, ordinary-condition activation, and their concrete startup dependency/implementation joins before LL15 closure.

The [browser configuration effects](../../../tests/wasm/stage1/startup-config/README.md) add five nonliteral callback adaptations: page size, tick units, tick period, listener defaults and spin settings. A real Worker supplies its reported concurrency and a Wasm page; the owner explicitly chooses millisecond clock units and Lisp stack sizes. Native source computations execute with the external reads substituted by each case input, independently of the port owner. Node and Chromium reproduce the same generated effects and return identities, including the timeout symbol returned by SPIN-COUNT. R1 is superseded by accepted R2; the portable configuration modules are integrated, without LL15 credit. Seventeen snapshot callbacks remain open alongside the wider definition/loading and condition-activation work; the next implementation must address those concrete services and dependencies rather than treating this snapshot as complete membership.

Audit-126 correction: [configuration R2](../../../tests/wasm/stage1/startup-config-review/README.md) supersedes the unaccepted R1 proposal. CPU-COUNT is not a pure external read: the native OR/cache/SETQ is now preserved, the generated callback conditionally publishes the owner count, and the cache is a ninth observed global. Both reset and configuration harnesses compare complete TCR preservation apart from separately verified result count, including actual TSP/CSP and FP control. Original pointer escapes and corrected refusals are retained. R2 is accepted after audit 127; config.mjs and browser-config.mjs are integrated byte-exactly. Future work uses its corrected effects and both full-TCR harnesses. Seventeen callbacks and the wider startup obligations remain open.

The [joined startup callbacks](../../../tests/wasm/stage1/startup-joined/README.md) unit is executed and awaits review. Eighteen selected reset/configuration effects execute in one schedule over 21 live globals; the CPU reset and cache publication share a cell. Thirteen reset completion constants recompiled through unchanged compiler; native resets rerun, R2 configuration bytes and native answers reused. Node and Chromium at both placements: 5184 callback comparisons, 5996 invocations, 180 refusals. Full-TCR and foreign-region checks; no LL15 credit.

The [startup EQ table reset](../../../tests/wasm/stage1/startup-winners/README.md) unit is executed and awaits review. RESET-WINNERS native registered callback and six generated calling forms over the strong EQ backing vector. Clear preserves identity/capacity and retires buckets, cache, tombstones and moved state; collection reclaims prior keys/values. Proposed hash service extension, unchanged compiler and adapter, inherited hash corpus replayed. No LL15 credit or production hash wrapper claim.

The [startup publication review](../../../tests/wasm/stage1/startup-winners-review/README.md) unit is executed and awaits review. Audit-128 F1: direct CLR success checks all four publication words. Three faults reproduce their complete R1 escape and reject under the corrected harness; nine prior faults still reject and the positive execution record is identical. Unchanged compiler, service, adapter and native oracle. Registry-order execution of all eighteen callbacks matches grouped R1 semantics in Node and Chromium. Auxiliary, not integrated, no LL15 credit.

The [startup clear publication completion](../../../tests/wasm/stage1/startup-winners-publication/README.md) unit is executed and awaits review. Audit-129 F1a: poison all four result words before direct CLR success. Six omitted/stale-store faults reject, including five that escape the prior guard; twelve older faults remain rejected. Positive execution is byte-identical. Compiler, service and adapter unchanged; audit-129 registry-order evidence reused. Auxiliary, not integrated, no LL15 credit.

The [database-handle startup reset](../../../tests/wasm/stage1/startup-db/README.md) unit is executed and awaits review. RESET-DB-FILES now clears all seven cached handles per interface directory through an owner-admitted pinned D1 DLL service and unchanged generated calling forms. The untouched native callback supplies six cases; 96 placement/order/calling scenarios, 30 preserving refusals and four compiled faults pass. Complete DLL validation precedes mutation; all four publication words are poisoned and observed. Reuses compiler R6/R6a by hash. Auxiliary proposal, not integrated or joined; production FTD materialization and moving structures remain open, no LL15 credit.

The [database reset admission follow-up](../../../tests/wasm/stage1/startup-db-review/README.md) unit is executed and awaits review. Audit-130 F1: consistent forged and shortened DLLs isolate membership and exact-visit admission. A third case isolates shared descriptor refusal. Six directed refusals preserve the arena, outside object, publication and full TCR. All three remove-one-check mutants escape R1 and reject here; four prior faults reject. Positive record byte-identical, compiler and service unchanged. Auxiliary, not integrated, no LL15 credit.

The [GC counter startup storage](../../../tests/wasm/stage1/startup-counters/README.md) unit is executed and awaits review. Two more startup effects: fresh owner-reserved pinned buffers for TOTAL-GC-MICROSECONDS and TOTAL-BYTES-FREED, zeroed by a checked C/Wasm service and published by generated SET. Untouched native callbacks verify zero bytes, pointer/global identity and fresh repeated allocations. Four generated modules pass 32 scenarios at 4 MiB and 2 GiB, 38 refusals and six faults. Compiler and adapter unchanged; R6/R6a reused. Production allocation/disposal, moving macptrs and statistics consumers remain open. Auxiliary proposal, not integrated or joined, no LL15 credit.

User direction, 20 September: “Get rid of the db thing” and make substantial
progress toward LL15. The database reset and follow-up are withdrawn from
implementation, with immutable evidence retained. The native-buffer counter
proposal is also withdrawn in favour of collector-owned statistics and a
five-value GCTIME consumer. New work first binds all 35 callback classifications
to the unchanged selection; deferred/excluded dependencies remain open until
the selected bootstrap demonstrates exclusion or a replacement.

The [portable startup runtime](../../../tests/wasm/stage1/startup-runtime/README.md)
implements collector-owned session counters and a generated five-value GCTIME
reader, including named calls through real function cells. It replaces the
withdrawn native buffer proposal and binds a new 35-row callback classification
to the untouched historical selection. Seven modules execute at both placements
with collection, large counters and complete value preservation; auxiliary and
awaiting review. Next: host namespace/image/argument/home effects, thread and
stream dependency disposition, then the concrete 167-unit initializer/definition
and ordinary-condition activation join. Classification alone closes none of
those dependencies; no native database leaf should return to that worklist.


2026-09-20: the [portable runtime follow-up](../../../tests/wasm/stage1/startup-runtime-review/README.md)
answers audit 131 without changing the original fixture: signed counter decoding,
isolated admission controls, generated timing conditions and corrected provider
classification. It is executed and awaits review.

The user chose “Use the Stage 1 strong substitute” for bootstrap weak tables.
The [bootstrap table proposal](../../../tests/wasm/stage1/bootstrap-tables/README.md)
implements explicit owner admission and strong EQ backing-vector construction
for 18 source sites, with native adaptation checks over all 21 candidate sites.
It retains both keys and values across collection. EQL/EQUAL tests are preserved
and target construction refuses until those services exist; fixed capacity and
missing HASH-TABLE wrapper materialization remain explicit. Stage 2 owes weak
semantics. This is not a new closure claim or slot credit, and the proposal is
not integrated. The next startup joins must use these declared differences,
not native weak flags or EQ substitutions for other tests.


2026-09-20, audit 132: the [table/population follow-up](../../../tests/wasm/stage1/bootstrap-tables-review/README.md)
uses pinned-image population measurements (1,281, 1,281, 1,049) rather than
constructor size hints alone. Each needs 2,048 slots with headroom. Requests
beyond the fixed service ceiling refuse, and post-install FULL preserves state.
The earlier name-based probe reported eight EQUAL `*combined-methods*` entries (the later heap snapshot records seven): its missing service
and wrapper are a bootstrap blocker, not an optional refinement. Other selected
image populations must be measured before construction too.

The user extended the policy with “Use strong retention for populations too.”
All four constructor paths are explicitly assigned strong retention for Stage 1,
with weak semantics owed in Stage 2. A portable ordinary-vector/cons proposal
now copies list/alist structure and preserves member identities across movement.
It does not install native population accessors or qualify scanners for arbitrary
lock/thread/GF instances. Those joins and the EQUAL service remain required
before claiming a collectable bootstrap image. Follow-up executed, not reviewed
or integrated; no LL15 credit.


2026-09-20, audit 133: [the complete weak-object instance census](../../../tests/wasm/stage1/bootstrap-heap-census/README.md)
replaces the three-global probe. Nineteen tables hold 6,550 entries; every
instance is attributed by owner identity to a source constructor. All seven
oversized tables get measured plans, with no one-entry fallback for hidden
state. Both the 97-entry EQL specializer table and the seven-entry EQUAL
combined-methods table block bootstrap until their equality services exist.
Two constructor sites have no observed table; that does not prove exclusion.

Twenty-two population objects hold 739 members. Eighteen empty ordinary lists
come from `%cons-mci`, beyond the previous four-path inventory. A separate
terminatable alist belongs to `*termination-population*`; no finalization service
is claimed and it remains blocking even though empty. Ordinary strong storage
is tested at actual instance counts; accessor/member-scanner integration and
future growth remain open. The census packet is executed, not reviewed or
integrated, and earns no LL15 credit.


2026-09-20, audit 134: the heap census and strong-substitute chain have no
remaining review defect at their declared scope. They await user acceptance;
no integration or LL15 credit is recorded. [Count clarification](../../../tests/wasm/stage1/bootstrap-heap-census/README-errata.md):
the actual heap snapshot has seven combined-methods entries, not the earlier
probe's eight. Keep the original packet bytes. Re-census the port's own
cross-dumped heap before image qualification; the native counts cannot stand
in for port image population or capacity evidence. The user chose [Stage 1 termination exclusion](termination-decision.md): refuse
registration, reject images with outstanding termination state, and defer
finalization to Stage 2. Policy is decided; admission and generated refusal
enforcement remain to be implemented and qualified.


2026-09-20, [termination exclusion implementation](../../../tests/wasm/stage1/termination-exclusion/README.md):
five generated replacement entries now implement the approved refusal and
inactive automatic hook; a read-only owner guard rejects registered objects,
pending callbacks, live callback registrations and enabled scheduling. Seventeen
modules, 52 native comparisons, 26 collections, 64 admission checks and ten
controls pass; fresh replay reproduces 207 deterministic files at 106 pins.
Compiler and runtime are unchanged. This is a reviewable auxiliary proposal,
not integration or LL15 credit. Join the actual image slots, real CCL function
bindings and READY schedule after review. Native automatic termination is T,
so disabling it is an explicit image edit, not an assumption from empty queues.

The next equality slice must implement EQL numeric behavior and table lookup,
not merely relabel an EQ vector. The captured 97-key specializer table contains
94 symbols and integers 1, 2 and 30; retain that exact bootstrap trace, then add
nonidentical numeric keys, signed zeros, widths and relocation cases when
qualifying the service. EQUAL, population accessors/scanners, root installation
and growth remain open. No old packet or accepted scope was altered.


2026-09-20, audit 135 follow-up: [termination empty-state compatibility](../../../tests/wasm/stage1/termination-exclusion-review/README.md)
corrects cancellation, lookup and draining to native one-NIL answers. R1's
blanket exclusion would break fd-stream close and must not be installed. The
reference now uses untouched native consumers rather than substituted bodies.
Generated cancellation/flush/close and cleanup paths, native empty-state cases,
and actual file closes execute. Registration exclusion and admission remain;
no compiler/runtime changes or LL15 credit. Integrate only the corrected
entries after independent review and acceptance.


2026-09-20, audit 136: the corrected termination exclusion is reviewed with no
defect; audit-135 F1 is closed. Import e153515d and bind its review-file hash in
the index. Both this exclusion and the strong-table/ordinary-population chain
(audits 132–134) await acceptance. Use the corrected exclusion packet for later
integration. Actual CCL symbol installation, cross-dumped slot discovery,
scheduling disablement and the READY join remain required; no LL15 credit.


2026-09-20, user: “accept integrate and finish ::15”. Both reviewed policies are
accepted and integrated under integration-bootstrap-policies.json. Ten new files
are exact reviewed bytes: strong table/population builders and the corrected
termination entry data, mapping, guard and five modules. Production-import
checks reproduce four retained records. Remaining work is functional LL15
closure: equality services, population consumers/roots, selected initializer
implementation/dependency joins and READY. Acceptance is not slot credit.

2026-09-20: [EQL/EQUAL services](../../../tests/wasm/stage1/equality-tables/README.md)
now execute through unchanged generated callers and the integrated collector.
The captured 97/0 EQL and seven-key EQUAL tables resolve copied key graphs after
movement. Method objects remain identity placeholders; native NaN hashing's FP
trap behavior is explicitly outside this leaf. This closes comparison-service
implementation, subject to review; real wrappers, population consumers and the
initializer/READY closure still remain. No LL15 credit or shared runtime edit.

2026-09-20: [strong-population access](../../../tests/wasm/stage1/population-access/README.md)
implements checked data read/write and raw type codes through the generated B
call paths. Native constructors copy their spines; setters preserve supplied
identity for NIL, proper, dotted and cyclic lists. Population-only member roots
survive moving collection. This is the access primitive, not native macro
lowering or public keyword type conversion. Binding those consumers and real
lock/thread/GF member representations remains required for the selected image.

2026-09-20: [Startup image name and arguments](../../../tests/wasm/stage1/startup-host-inputs/README.md)
add two generated global publications and a readback to the registry-ordered
schedule, taking the callback snapshot to twenty of thirty-five. Native U1
pointer acquisitions alone are substituted; native string decoding, adjacent
composition, argv ordering and global-write semantics supply the answers.
Published graphs move under the integrated collector and survive poisoned old
storage in Node and Chromium below and above 2 GiB. The owner accepts explicit
application inputs; it does not infer browser arguments from the URL. This
proposal does not change the worklist's membership or grant LL15 credit.
Next implementation joins still include home/logical pathname effects, thread
and scheduler state, static-cons disposition, the reviewed runtime services,
and production image bindings. Definition/loading initializers and the census
query/build-path proof remain separate required parts of LL15.

2026-09-21: Audit 137 corrects the preceding host-input proposal: Wasm has no
Darwin filename origin and its reader features do not select precomposition.
The [follow-up](../../../tests/wasm/stage1/startup-review-137/README.md) preserves
owner namespace strings unchanged and uses the target-selected native body as
oracle. It also closes the named equality/population test gaps with directed
cases and compiled faults. All three proposals remain unaccepted pending
Claude review; this does not change LL15's membership or grant slot credit.

2026-09-21: Audit 138 confirms the target-branch correction and NIL/cons semantics,
while exposing another depth site and backed-region test gaps. The
[audit-138 follow-up](../../../tests/wasm/stage1/startup-review-138/README.md)
replays the prior unit with portable dependency keys and covers those guards
without service changes. Review and acceptance still precede integration.
Remaining LL15 implementation and worklist obligations above are unchanged.

2026-09-21: [Population consumers](../../../tests/wasm/stage1/population-consumers/README.md)
now generate the data/setter entries and keyword type answers for the strong
representation, with selected native PUSH/SETF expansion and moving closure,
cleanup and transfer cases. This advances consumer implementation beyond the
raw service. The rewrite is scoped to selected runtime definitions, not general
user-source admission. Real symbol/macro installation, Lisp condition mapping
for bad inputs, real member layouts and production image-root discovery remain
required. The [audit-139 supplement](../../../tests/wasm/stage1/startup-review-139/README.md)
closes the residual refusal observations alongside this work. Neither is accepted
or integrated and neither changes LL15 worklist membership or credit.

2026-09-21: Audit 140 closes the equality/population service test findings. The
consumer rewriter remains fixture scaffolding and must not be integrated. Its
[admission follow-up](../../../tests/wasm/stage1/population-consumer-review/README.md)
now covers both SETF place orders and lexical/macro shadows explicitly. PUSHNEW
at method-combination.lisp:155 and POP remain owed. The
[typed population proposal](../../../tests/wasm/stage1/typed-populations/README.md)
provides a distinguishable strong D1 shape and both moving and pinned-image
scanners, a prerequisite for target accessor indices and native REQUIRE-TYPE.
The two-field strong shape excludes native weak/termination layouts. Migration
from v1 vectors, actual member layouts, real symbols and READY remain open.
No acceptance, integration or LL15 credit is claimed.

2026-09-21: On the user's “pushnew perhaps”, implement the selected population
PUSHNEW default form plus callable :test. The subsequent instruction to call
EQL is implemented by adding an entry to the shared EQL table module, which
calls its existing comparator; the separate comparison-module candidate was
discarded. Generated branch loops avoid local-function closure allocation.
The [packet](../../../tests/wasm/stage1/population-pushnew/README.md) checks
native effect order, duplicates, numeric members, movement and exact allocation.
This supplies generated execution of the method-combination source shape, not
actual GF layout or general macro admission. The source adapter remains
scaffolding; native accessor/REQUIRE-TYPE compilation and real installation
remain the durable next work. POP and :key/:test-not are still owed/out of scope.

## Bootstrap compiler coverage — BT-0 adopted 21 September

The user's “I accept BT-0” adds S1-LL15-c (emitted acode coverage) and S1-LL15-d
(unchanged-source compilation). See [authorization](bootstrap-coverage-decision.json).
Report numerator, denominator, unknowns and native-matched execution separately;
correctness fixes need not increase a count. Coverage is qualified at actual
operator/operand forms, including movement and unwinding for new allocating or
nonlocal operators. Preserve all earlier contracts and accepted scopes.

The accepted [front-end entry](../../../tests/wasm/stage1/bootstrap-frontend/README.md)
compiles original MEMQ, APPEND-2, ADJOIN-EQ and UNION-EQ through CCL's own front
end. Its sample is not the full startup worklist. The user ordered quoted constants, special references, then OR; the
[values lowering](../../../tests/wasm/stage1/bootstrap-values/README.md) is accepted
and integrated. Its historical 639/82 counts included audit-143 F1/F2; eight
original definitions executed. The [core proposal](../../../tests/wasm/stage1/bootstrap-core/README.md)
now compiles l0-pred and l0-utils whole (78 named definitions), implements the
Wasm predicate branches and node operators, and executes 129 original
definitions including MEMEQL/ADJOIN-EQL and all 44 callee-closed definitions in
those two files. Corrected admission is 1,539/2,492, with 193 callee-closed;
this is not initialized bootstrap closure. The proposal is accepted and integrated following audit 145 and Steve’s R6
source-location decision.

The [library proposal](../../../tests/wasm/stage1/bootstrap-library/README.md)
implements ERROR/SIGNAL arguments and character/string primitives, admits all
l0-symbol file records, and admits 31/56 l0-misc records. It executes 137
original definitions, up from 129. It follows the actual 57-file target list,
but 22 reader/environment failures still prevent a complete denominator.
Next close those compile-time and foreign-reader environments and the remaining
l0-misc operators; preserve the explicit unsupported cases. Audit-145 carries
have directed checks except the still-owed source-emitted %I<> witness.
Continue closing the real TYPEP/REQUIRE-TYPE and error callees, then execute
initializers and install definitions at actual image symbols. Continue measuring
startup operator occurrences and source admissions without claiming terminal
BT-0 credit prematurely. Keep Lisp in CCL's style and use no consumer source
rewriters. Rework the pending population shape to native's zero-link/type/data
fields when native accessors can be compiled.

Denominator diagnosis after audit 145: U1's `target-xcompile-directory` visits
all root level-0 files, including l0-bignum64; target reader conditionals remove
that file's definitions. On the pinned kernel with Wasm features, the normal
reader (`*read-eval*` T) reads only `(IN-PACKAGE "CCL")`. The diagnostic census
uses `*read-eval*` NIL, gets a read-time-evaluation error inside the suppressed
form, then its recovery resumes inside that excluded form. Replace this
recovery-based denominator with file-compiler observations in the actual target
file/initialization environment; merely deleting a filename is insufficient.
The historical 1,539/2,492 figures remain diagnostic, not target-worklist
completion. The 129 executed-definition evidence is independent of this tally.

2026-09-21: Audit 146's byte-store defect and false string-copy execution claim
are addressed in the [execution proposal](../../../tests/wasm/stage1/bootstrap-execution/README.md).
Native-matched definitions rise from 137 to 172. Computed-call classification,
arithmetic operator lowering and cheap scalar calls now support real list,
string, EQL and FUNCALL/APPLY consumers. The review candidates remain
unintegrated. Next prioritize executable dependency closure and valid input
recipes, including native TYPEP/REQUIRE-TYPE and initialized object layouts;
continue the target file environment and remaining l0-misc work. Do not count
primitive EQL as a newly compiled Lisp definition, dynamic callbacks as static
closure, or an input recipe as an executed test. Numeric-ctype and stream-ioblock
cases and the read-loop environment remain owed; %IZEROP and %I<> need emitted
source witnesses. LL15 is unfinished.

2026-09-21: Execution R2 repairs audit 147's retained-source mismatch and raises
the original native-matched count to 186 without changing the compiler proposal.
The finalized packet must pass its own unmodified verifier before commit;
retention also rejects stale compiler input copies. Copy-function boundary rows
and float-only division scope are now explicit. Continue implementation with
TYPEP/REQUIRE-TYPE dependencies and initialized layouts, native-error comparison,
ASSQ/LOGAND/LOGIOR/subtraction call closure, and the remaining actual file
compilation environment. Do not rebuild unchanged native qualifications.

2026-09-21: The user's integer-division witness request is implemented in the
[division proposal](../../../tests/wasm/stage1/bootstrap-division/README.md).
Exact integer quotients use the existing integer service; CALL and DIV2 each
have integer witnesses. Nonintegral quotients require ratio arithmetic and still
refuse. Mixed handler clauses exposed the symbol-versus-mask dispatch bug;
bootstrap condition and restart names now share the literal symbol owner.
This remains a review candidate, with 186 original definitions executed and no
change to the admission count or LL15 disposition.

2026-09-21: The [dependency execution packet](../../../tests/wasm/stage1/bootstrap-dependencies/README.md)
raises native-matched original definitions to 252 (+66), with admission
unchanged. ASSQ, fixnum logical calls, subtraction, constant type tests and LDB
fields close real callers; original LENGTH/SEQUENCE-TYPE and %BADARG/type-ID
decoding execute. Continue with initialized object recipes, the complete Lisp
type system and its environment, bignum logical operations, proper native
improper-list conditions, and the remaining file compilation environment.
Representation primitive witnesses and fixture adapters are excluded from
original-definition credit. The packet is unintegrated and LL15 remains open.

2026-09-21: Audit 148 is accepted on Steve’s “accept as advised”; execution R2,
division and dependencies are integrated with folded dispatchers and final
R6/R6a. The current executable headline is **252 definitions, 193 with a
non-NIL witness**. Next, supply a member input to each negative-only predicate,
then recipes for the 136 closed definitions without inputs, then repair the 22
stopped target-file environments. Alongside this substantive work, move ASSQ
into idiomatic target Lisp, refuse unsupported literal handler classes at
compile time, and close the %I<>/%IZEROP and condition/array refusal carry items.
Do not count this integration as new throughput or completion of LL15.


### Audit153 integration and the combined math execution packet

Steve accepted the admission proposal and required the next work in the same packet. The reviewed compiler/architecture/source is integrated, with runtime bytes unchanged. The new bootstrap-math proposal combines shift-domain assertions, recipe expansion, all 26 single/double libm entries and the next portable coercion/word-shift operators. It executes 423 original definitions, 394 with non-NIL return witnesses, and leaves 44 of the prior 82 original closed names with explicit state/representation/dependency dispositions. The seven additional fixture names are not original-definition credit.

The libm numerical envelope is proposed only: observed native differences are one ULP, and checked inexact/underflow modes refuse until their flags are qualified. No timing claim, full-domain proof or scalar fast-path claim follows. Integration of this new work requires independent review and user acceptance. LL15 still owes the executable startup closure, remaining target branches/capabilities, image roots and READY join; the counts do not claim completion.


Audit154 repair: use native CCL's default FP mask for every generated case, with an unprefixed condition witness and a control restoring the bad switch. Steve adopted pinned musl with a two-ULP native comparison limit on 21 September; signed zeros, exact results and domain conditions remain exact. This is a tested compatibility criterion, not a full-domain error proof. Reuse unchanged compiler/runtime native qualification by hash. The R2 implementation remains proposed pending review/acceptance. Current closed names without inputs total 77; the 44 previously described were a historical-cohort remainder. Extend the uint32 proof to immediate bignum constants in the next substantive compiler work.


Audit155: math R2 is accepted and integrated on Steve's authorization, including the production musl build and all 40 owner checks. The next closure proposal executes 436 original definitions, 407 with non-NIL witnesses. Immediate uint32 masks and MINUS1 are exercised; 13 new destructive double-float primitives have exact native mutation witnesses. 64 current closed names still lack recipes. Continue with substantive execution and the file-namespace provider boundary; these counts do not complete the startup closure or READY join.


Recipe cohort update: 21 of the prior 64 names and newly closed NEED-USE-EQL now execute, bringing the headline to 458/427. Keep fixture/target primitives (8), paired single-float interfaces (13), excluded native interfaces (9) and substantive remaining work (13) distinct. The latter comprises boxed uint32 stores/random state and bignum LOGBITP (3), target representation oracles (5), dynamic GVECTOR construction (1), cyclic pool graph transport (1), unbound-function cell state (1), a live catch-frame oracle (1), and the known PATH-MEMBER source bug (1). Do not fill these with bypass-only inputs. Continue toward actual startup closure and the file-provider boundary; no READY or LL15 completion follows from the execution count.


Audit156 F1 is addressed by the [file-environment packet](../../../tests/wasm/stage1/bootstrap-file-environments/README.md). Use 1,895/2,231 for the comparable admission cohort, not the previous standalone upper bounds. Report macro-generated and newly reached definitions separately (852/893 additional lower). Numeric files now expand NUMBER-CASE and buffer macros in their real environments; missing target arch macros and primitive callees are explicit. Execution reaches 460 originals with 429 non-NIL witnesses. Next numeric implementation should close those actual target macros/callees, rather than count calls to missing macro names. The file-provider boundary and executable startup/image/READY joins remain open. Closure and recipes are reviewed, not yet accepted; the new recount/execution packet awaits review.

### Condition matching after the fixed registry (O-10)

Replace the exhausted handler mask with `TYPEP` on real condition classes and
class precedence lists. Build on the class/wrapper layout and execute CCL's own
class-based predicate path. This is the next condition-matching architecture;
a second mask, a wider mask or another fixed class-bit registry is not the plan.

The implementation must join constructed conditions to their real class and
wrapper, trace that identity and the CPL under movement, and make handler search
use the class relation. Qualify inherited and multiple-inheritance handlers,
declining handlers, movement during signalling, and a newly defined condition
class without assigning a bit. Preserve the accepted restart/cleanup behaviour
and slot semantics. Until that works, keep the eight unsupported classes as
explicit refusals; the plan itself earns no execution or admission credit.

The division proposal's behavioural `NO-REM` change is listed as
[WB-1](behavioural-branches.md) for explicit treatment at acceptance. Use the
[canonical condition verifier](../tools/verify-condition-frontier.py) for new
replays; leave the original retained source and records unchanged. It reads
source revision `7212d982200c017930a0e7d9fcc9f02b9fa74374` from Git into a
temporary directory, checks all packet pins there, and uses that source for
both regeneration and fresh execution. It does not depend on current runtime
or compiler bytes. `--source-revision` may select another commit only if all
retained pins match. `--replay` checks an existing qualified run without executing
it again; `--output` performs a fresh run. For example:

```sh
python3 doc/WASM/tools/verify-condition-frontier.py --output /tmp/ccl-condition-canonical-replay --report /tmp/ccl-condition-canonical-verification.json
```


## Audit 161 integration

Steve accepted the reviewed standard GF-dispatch packet with “accept and
integrate”. The [acceptance](acceptance-bootstrap-generic.json) carries O-14–O-18,
and the integration uses the reviewed files byte for byte. Standard method
selection, combinations and lifecycle now execute in the shared tree. The
native-projected class graph is still a fixture: install the real cross-dumped
class table and `%ALL-GFS%` before claiming the image/READY join. Class-wrapper
invalidation precedes dispatch caching; closure metadata and the O-10 real-CPL
condition successor remain explicit work. The separate LAP merge must retain
this EQUAL and backend ILOGCOUNT, dropping the overlapping LAP definition.

The [condition CPL proposal](../../../tests/wasm/stage1/bootstrap-condition-cpl/README.md)
implements the O-10 matching component using unchanged `CLASS-TYPEP` and
initialized real CPLs. It remains default-off pending review and class-cell
installation. Its custom condition instances are native-projected; general
MAKE-CONDITION and generic slot readers must join this path before retiring
the old construction/readers' schemas. Do not treat its 96 protocol
comparisons as completion of the full condition system or the image/READY join.

## Audit 162 integration

The reviewed CPL matching component is accepted and integrated default-off.
See [the record](integration-condition-cpl.json) and O-19–O-21 in
[runtime obligations](runtime-obligations.md). No throughput or slot count
changes. The next condition work must unify actual class-cell lookup,
MAKE-CONDITION/MAKE-INSTANCE, slot initialization/readers and SIGNAL designators.
CCL class cells are structures: the fixture cons-cell catalog is temporary,
not an image representation to preserve. Class finalization and real image
installation remain open.

## Audit 163 integration

Steve accepted the native condition-system proposal default-off. Four source
files equal the reviewed proposal. Continue with SETF GETHASH, real image class
roots and retirement of the implicit allocation registry. See
[integration](integration-condition-system.json) and its explicit obligations.

## Audit 164 integration

Steve accepted the native class-table proposal default-off. Three source
files equal the reviewed proposal. Continue with growth, REMHASH, real image class
roots and retirement of the implicit allocation registry. See
[integration](integration-class-table.json) and its explicit obligations.

### Audit 165 integration — 23 September

Steve's “accept” accepts the prepared class-growth integration. The reviewed
backend and w32-prims are integrated byte-exactly with class mode default-off.
[Identity record](integration-class-growth.json) reuses native qualification and
Claude's from-scratch replay; it claims no new execution. O-27–O-30 remain
recorded in the runtime obligations. P4 tooling at 16584ba0 remains unchanged
under Claude's separate review. Next runtime work is the cross-dumped class
table as a real image root, READY and retirement of legacy mode; production
module granularity remains a separate decision at that join.

### Class-image cold-load unit — 23 September

The [completed proposal](../../../tests/wasm/stage1/class-image/README.md)
adds a portable D1 image writer/loader and saves the class table after generated
Lisp builds and publishes all 612 cells. Fresh consumers do not reconstruct the
graph or rerun that builder. Review this runtime boundary before integration.
It does not remove the default-off condition mode or establish the complete
cold initializer worklist. The next image work is the xfasloader's real class
construction metadata and joining this owner to the process-wide READY contract.
