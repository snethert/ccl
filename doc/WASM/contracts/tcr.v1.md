# Production TCR schema v1

Status: the versioned TCR schema D5 lists among its artifacts, authored by
Claude on 15 September 2026 as the Stage 1 build target, reviewed by Codex
without defect, and extended on 16 September with the `fp_control` word
under the decided D6 floating-point policy; no inventory slot and no gate
credit. The machine-readable schema is
[tcr.v1.json](tcr.v1.json). Regenerate it with
`python3 tests/wasm/stage0/tcr-schema/run.py --generate`; the producer
refuses when the committed file differs from the regeneration.

## Layout

One 256-byte, 16-byte-aligned record per Lisp thread in linear memory, with
the last 52 bytes reserved and zero. Every field has an explicit offset,
width, alignment, classification and owner, and every field is assigned
exactly once. The nine groups are D5's field groups in D5's order:

| Group | Fields |
| --- | --- |
| Identity and lifetime | tcr_index, worker_id, lifetime_generation, registry_next, registry_prev, tcr_address |
| Atomic state and pending | state, pending, stop_generation |
| Allocation area | alloc_pointer, alloc_limit, alloc_base, allocation_quantum_log2 |
| Explicit stacks | vsp, vsp_base, vsp_limit, tsp, tsp_base, tsp_limit, csp, csp_base, csp_limit, stack_reserve_bytes |
| Dynamic bindings | tlb_pointer, tlb_limit, db_link |
| Multiple values | mv_count (complete ordered sequence, value0 included), mv_base, mv_owner_top |
| Roots and frames | root_head, frame_head, frame_generation, handler_checkpoint, foreign_descriptor, unwind_state |
| Mailbox | active_request, request_block_base, request_count, mailbox_id |
| Runtime private | c_stack_pointer, tls_base, tls_size, scratch0, scratch1, next_method_context, error_service_mode, debug_policy, fp_control (logical floating-point enable mask, the ARM model; default invalid, division by zero, overflow) |

Classifications are tagged root, raw address, bounded index or count,
atomic state, code identifier and raw scalar. The only tagged root is
`next_method_context`; the collector updates it and nothing else in the
record. The three atomic-state fields (`state`, `pending`,
`active_request`) are accessed only with sequentially consistent atomics
and preserve unrelated bits. Owners are the thread while admitted, the
registry under admission, and the collector while the thread is stopped or
admitted; the host owns nothing here and writes only inside the owned
request descriptors that `request_block_base` names. `tcr_index` and a
symbol's binding index remain different namespaces.

## Joins

Every native TCR cell that the [layout schema](wasm32-layout.v1.md) marks
replaced maps to one or more production fields, and both deferred cells (the
allocation statistics) are recorded as deferred; the 18 unsupported cells,
which are native registers, FP control words and signal contexts, map to
nothing. Fourteen production fields have no native origin because they make
explicit what the native kernel kept implicit: the registry index, the
allocation limit, the multiple-value descriptor, the logical frame head and
generation, the published foreign-call descriptor, the request count, the
TLS region, the two bootstrap policy words and the floating-point control
word, which takes the role of ARM's `lisp_fpscr` and x86's `lisp_mxcsr`
while their register-format images stay unsupported in the layout.

Every TCR field the accepted fixtures use, all 56 names from the
[runtime-contract join](runtime-contracts.v1.json), maps to a production
field or is declared fixture-private with its reason: 25 map and 31 are
fixture instrumentation such as counters, observations and supervisor
handshakes. The five extension offsets the fixtures aliased under different
names are resolved here once. Twenty-two production fields therefore carry
at least one executed witness.

## What this does not claim

The schema is a build target, not executed proof: the fixtures executed
their own TCRs, and Stage 1 executes this one through generated code and a
fresh cross-dump. Request descriptors keep their own contract, including the
aligned 64-bit wake/generation pair, in the integrated-runtime schema and
D5's protocol v1.1.
