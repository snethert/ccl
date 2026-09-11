# Logical debugger frames v0.1

Status: initial implementation contract; not executed, accepted or ABI-frozen. This specifies the information the Wasm compiler/runtime must preserve before D3 freezes. S0-LL23-b proves a hand-built slice; Stage 1 repeats with generated frames under LL23, and Stage 3 exercises the real debugger under R2/LL19/LL20.

## Representation

Each Lisp activation has a logical frame in that Worker's owned, bounds-checked, nonmoving explicit-stack region. A frame address is a raw wasm32 offset, never a tagged object or saved engine-stack pointer. Its generation prevents debugger handles from referring to reused storage. Tagged payload slots are declared roots and are updated by moving GC. Unboxed slots and headers have explicit types and are never conservatively treated as roots.

The initial 64-byte, 8-byte-aligned header below is a proof layout, version 1. Payload slots follow it; `frame_bytes` includes their aligned extent. D3 may revise concrete offsets before freeze with a version bump and repeated independent fixtures, while retaining the information and restoration obligations.

| Byte offset | Field | Encoding and ownership |
| --- | --- | --- |
| 0 | layout_version | u32, fixed at construction |
| 4 | frame_bytes | bounded u32, includes header and payload |
| 8 | previous_frame | raw offset, zero terminates chain |
| 12 | frame_generation | u32 lifetime token, exhaustion checked before reuse |
| 16 | logical_code_id | D5 tagged nonnegative fixnum; not a table slot |
| 20 | code_version | bounded u32 descriptor version |
| 24 | source_site_id | bounded u32 key into immutable debug metadata |
| 28 | policy_flags | u32 identifying debug/optimization policy and tail status |
| 32 | binding_checkpoint | raw offset into owned dynamic-binding stack |
| 36 | handler_checkpoint | raw offset into owned handler stack |
| 40 | root_descriptor | bounded u32 key into the frame's slot map |
| 44 | self_slot | frame-relative byte offset of tagged closure/function slot |
| 48 | argument_count | bounded u32 count, encoding distinct from tagged Lisp count |
| 52 | value_count | bounded u32; complete MV descriptor remains governed by D3 |
| 56 | mv_descriptor | raw offset of owned result descriptor, zero if absent |
| 60 | reserved | zero; no undocumented use |

Every actual self/argument/local payload location is specified by a build-bound descriptor. Its entries contain lexical binding identity, display name, package identity if applicable, source scope, storage kind, byte offset/width, live range, and availability state. A variable name alone is not identity. Root maps and debug maps may share storage descriptions but have different purposes; debug availability never silently controls GC liveness.

## Compiler and runtime protocol

Before any legal poll, allocating transition, host suspension, indirect lazy stub or callback, publish a complete frame chain, the current source-site ID and all live tagged references. A caller records its call site before entering its callee. No observation/poll is permitted during partial frame construction or an indivisible allocation/store sequence.

The inspecting Lisp thread admits through D5 and uses either its own stable frame chain or a target thread stopped under the same rendezvous protocol. It never walks a concurrently mutating chain. The host receives serialized inspection replies through stable request storage; it does not inspect the moving Lisp heap directly.

After collection, reload every live tagged local from the updated slots and rederive interior addresses before execution or debugger access. On return, EH transfer, restart or C-boundary escape, restore the frame head, explicit-stack bounds, binding/handler checkpoints and complete multiple-value ownership together. A cleanup that transfers again follows the same restoration contract. Nested debugger/callback activations get distinct frames and owned request descriptors.

Tail transfer may replace the physical logical-frame record only after satisfying D3's argument/root/cleanup ownership. Retained active bindings/handlers have explicit records for their remaining extent. An eliminated caller is labeled as such and must not be presented as an inspectable live frame. Long tail chains must meet bounded explicit-stack/root use at the benchmark's fixed policy.

## Inspection policy and acceptance

At debug 3, all lexically in-scope arguments and locals promised by the published CCL compatibility profile are materialized at supported inspection points. At lower policies, each unavailable value is reported with a reason (`optimized-out`, `out-of-scope`, or `unavailable-at-site`); the debugger must not substitute NIL, global values or a stale slot. Initially inspection occurs only at declared safepoints and suspended call sites, not arbitrary Wasm instruction offsets.

S0-LL23-b constructs unequal arguments, shadowed same-name locals, an escaping captured cell and zero/many values in nested hand-built frames. It moves the referenced objects, suspends/resumes, enters a nested debugger frame, performs a nonlocal exit and verifies frame order, lexical identities, values, source-site mapping and restored frame head. Mutants using a stale root slot, reused generation, wrong code-version metadata or a fabricated unavailable value must fail.

Code/debug metadata for live and superseded functions remains paired through redefinition. Saved quiescent application images retain code/debug descriptors and declared reconstruction data; they do not serialize these live activation records or engine stacks. Stack/metadata bytes and publication cost are charged to each D3 candidate at the same compiler policy.
