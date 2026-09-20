# Runtime obligations carried into Stage 1

Implementation planning, 16 September 2026, incorporating the user's supplied
[ARM survey](arm-lessons.md). These obligations do not revise Stage 0 acceptance or count as
executed Stage 1 tests.

- **Runtime globals (1A design, 1D/1E implementation).** The Wasm runtime owns
  a process-wide record in linear memory, separate from NIL and from every
  Worker's TCR. The loader supplies its aligned base as an immutable instance
  import; native negative NIL-relative offsets are never accepted. Heap bounds,
  collection thresholds/counters, inhibition state and registry heads belong
  here. Tagged values must be published through explicit root descriptors;
  raw addresses and counters are not Lisp roots. Before a generated global
  access is enabled, the schema must assign its offset, width, owner, access
  protocol and collector treatment. Native return addresses, subprim addresses,
  TLS keys, signal numbers and Objective-C cells get protocol/service
  replacements or unsupported dispositions, not copied storage. The 1A
  generator excludes these native offsets and the initial leaf backend cannot
  emit a kernel-global access. This assigns the ownership/addressing model;
  it does not yet implement the complete record or its services.
- **Binding-vector growth (S1-LL17-a).** Specify the growing thread's ownership,
  the D1 no-thread-local-binding marker, initialization of every new slot,
  roots while copying, publication of pointer and byte limit, allocation
  failure, and retirement of old storage. Exercise collection at each legal
  boundary. ARM's `extend_tcr_tlb` in `lisp-kernel/arm-exceptions.c` and
  `%ensure-tlb-index` in `level-0/ARM/arm-symbol.lisp` are semantic references;
  native `realloc` and the trap are not Wasm implementations.
- **Interrupt masking (S1-LL17-a and S1-LL19-a).** Delivery consults the special
  binding for interrupt level as well as the pending request. Test nested
  `without-interrupts`, unwind restoration and pending delivery on re-enable.
  Masking Lisp interrupts must not disable collector rendezvous. See
  `check_pending_interrupt` in `lisp-kernel/arm-macros.s`; D5's explicit polls
  remain the mechanism.
- **Recoverable stack exhaustion (S1-LL19-a).** Distinguish a soft-limit Lisp
  condition from a damaged-stack fatal diagnostic. Reserve space before
  invoking the condition machinery, unwind safely and re-arm the soft limit
  after recovery. Cover control, value and temporary stacks, recursive handler
  exhaustion, and failure to restore the reserve. A bare engine trap does not
  satisfy this obligation. The accepted LL19 implementation uses one reserve-in-use
  bit for all three soft checks; hard limits remain independent. This is not
  native per-stack guard parity. [TCR v2](../contracts/tcr.v2.md) names this
  persistent state and the debugger depth; neither may be reused as scratch.
- **Trap lowering (1C).** Cross-reference the retained x86 sites with ARM's
  UUO list in `compiler/ARM/arm-asm.lisp`. Record continuable versus fatal
  checks, slot-unbound, missing throw tag, undefined function, unavailable
  foreign entry, array rank/flags/axis checks and integer division by zero.
  Preserve condition/restart semantics where supported; unsupported cases
  require explicit tested conditions. The list is a checklist, not an
  instruction encoding to carry over.
- **Callbacks (Stage 2 host services).** Specify slot allocation, signature,
  per-Worker installation, publication, replacement and retirement, plus
  host glue and stale-handle refusal. Do not copy ARM's four instruction
  words into linear memory. Wasm modules can be compiled and installed
  dynamically; linear-memory writes do not create executable trampolines.

## Architecture precedents

Use x8632 for the accepted D1 tags, distinguished-cons NIL and constant-index
limits. Read `xdump/xarmfasload.lisp` for the separation of function objects
and code, especially `xload-arm-set-entrypoint`; replace its native entry
address with D5's logical identity and typed table lookup. The per-target
registration shape is common to ARM and x8632. Neither native image writer
nor planted instruction sequences are a Wasm implementation.

ARM starts constants after two function words and adjusts `nth-immediate`;
x8632 has a different convention. The production constant-pool origin and
logical-versus-physical indexing must be explicit in S1-LL10-a. The 1A leaf
slice rejects heap constants and does not silently inherit either convention.
The Wasm CPU discriminator uses the unused value four in U1's three-bit CPU
field (32 after shifting), with OS discriminator seven and 32-bit word mode.
Existing values remain unchanged; the registration test checks collisions.

Do not use the unfinished ARM64 kernel, abandoned Darwin ARM build,
empty ARM trap handler, FP debug-trap stubs or absent ARM event-poll vinsn as
working precedents. D6's approved floating-point policy and D5's explicit
polling and allocation protocols remain in force.

## LL05 qualification follow-through

Implicit call errors now allocate private condition vectors and signal before
unwinding. LL19 must replace the private representation with production condition
construction/slots and extend the remaining checked-error paths, restarts and
debugger boundary. The collector must scan the helper’s condition and dynamic
result descriptor, including pending nonlocal transfers. Owner catalog/registry
trust, host re-entry and multi-Worker publication remain loader/runtime obligations.
General result-demand propagation remains an optimization beyond the proven-small
per-callee scratch path; LL05 makes no timing claim.

Claude audit 84 follow-through: LL19 must route APPLY with a non-list or dotted
final argument through Lisp TYPE-ERROR handling. The retained counterexample is
not covered by LL05’s designator/arity condition clause. Private class-mask
vectors and the checked no-handler boundary also remain production condition
and debugger obligations.


19 September execution follow-through (pending review): [LL19](control.md)
replaces the private condition payload with D1 instances/slot vectors under a
sealed owner bootstrap registry, routes improper APPLY into TYPE-ERROR with its
native datum, and executes restart/debugger-hook recovery. The same qualification
covers soft VSP/TSP/CSP exhaustion and explicit interrupt masking/re-enable with
independent collector service. These are executed claims, not accepted or
integrated changes. General class/symbol installation, moving collection and
host re-entry keep their separate obligations.


## Callable materialization (Claude audit 100)

Top-level function objects are materialized by the owner. LL14 must copy pool elements zero and one into the arity/debug words; only closure constructors initialize them in generated code.

Metadata validation is a per-call cost. It checks shape, identity and fixed counts, not all key-vector/debug contents. No timing claim.

Only keyword-symbol key names are admitted. Capture debug records follow environment-slot order, not source order; indices are explicit.


## Binding publication (Claude audit 101)

Manifest module rows match by name; their order does not affect admission.

Completeness is measured against the trusted owner's expected list. An owner omitting an alias from both lists is outside this control's authority.

Failed transactions discard their compiled instances and loader; rolled-back slots can be reused. Retained old module slots are never reused.


## Empty generic dispatch (Claude audit 102)

The empty-registry correction is in the generated dispatch service. Native CCL l1-dcode.lisp still has the retained stale-dcode defect; compiling native CLOS requires a separate source correction.

The guard covers an empty method registry. A raw stale store with a nonempty registry can select an incorrect method until recomputation; owner records remain trusted.

The private condition readers refuse non-instance arguments with checked code 4, not a handleable Lisp error.

Condition-using module bytes change with the bounded registry check. The inherited corpus was re-executed against native expectations, not claimed byte-identical.
