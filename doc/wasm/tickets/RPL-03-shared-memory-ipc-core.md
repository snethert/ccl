# RPL-03 - Shared-Memory IPC Core

Status: done  
Priority: P0  
Owner: Runtime/WASM replacement track  
Last Updated: 2026-02-09  
Parent Plan: `doc/wasm/runtime-replacement-master-plan.md`

## Scope

In scope:

- Define the shared-memory IPC protocol v1 contract for runtime hot paths.
- Freeze deterministic channel ownership rules mapped to `WTOP-*` roles.
- Specify ring/mailbox layout, Atomics signaling, backpressure, and failure semantics.
- Define startup/lifecycle integration hooks and machine-actionable telemetry artifacts.

Out of scope:

- Runtime/UI message-class migration sequencing (RPL-04).
- Storage V2 object/ref semantics (RPL-05/RPL-06).
- Module/environment sharing work (RPL-07).
- CL thread semantics implementation details (still deferred).

## Dependencies

- RPL-00 governance loop and same-cycle sync discipline.
- RPL-01 startup gating/diagnostics contracts (`SRG-*`, `RPL01-E*`) and contradiction inventory (`C-*`).
- RPL-02 frozen topology/lifecycle contracts (`WTOP-*`, `WSEQ-*`, `WLCS-*`, `WLCT-*`, `WLCR-*`).

## Deliverables

1. Shared-memory IPC protocol v1 contract with frozen `IPCP-*` IDs.
2. Deterministic ownership/layout/signaling/backpressure/failure tables for queue and mailbox primitives.
3. Startup/lifecycle integration mapping to `WSEQ-*` and `WLCT-*` enforcement points.
4. Telemetry artifact schemas required for test-lane assertions and `X-03` progress tracking.

## Exit Criteria

- Hot-path transport is specified as shared-memory-only with explicit no-fallback semantics.
- Channel ownership and queue semantics are deterministic and role-bound.
- Timeout/failure behavior is canonical (stable codes, message templates, remediation).
- Step 2 conformance matrix is frozen with deterministic lane commands/assertions (`IPCV-*`).
- Step 3 committed conformance evidence bundle is published and sufficient to clear hard-gate row `X-03`.

## Current Notes

- Step 1 protocol v1 contract is now published with frozen `IPCP-01`..`IPCP-49` identifiers.
- Step 2 conformance output v1 is now published with frozen validation IDs (`IPCV-01`..`IPCV-12`) and lane registry (`IPCL-01`..`IPCL-05`).
- Conformance summary schema `ipc_conformance_summary_v1` is now defined for machine-gated `X-03` evidence aggregation.
- Step 3 rerun cycle is now complete over all required `IPCV-*` lanes with committed evidence under `doc/wasm/tickets/evidence/rpl-03-step3-rerun-2026-02-09/`.
- Step 3 terminal summary now reports `status=pass` and `x03_clear_ready=true`; blocker gaps `IPCGAP-01`..`IPCGAP-04` are closed.
- Contract explicitly preserves secure-only startup posture and strict no-silent-fallback semantics for hot paths.
- Contradiction follow-through from RPL-01 is now actively absorbed for `C-01`, `C-03`, `C-04`, and `C-08` through explicit protocol clauses.
- Dependency row `X-03` is now `done` based on committed rerun evidence and deterministic assertion closure.

## Immediate Next Step

- Action: maintain frozen `IPCP-*`/`IPCL-*`/`IPCV-*` contracts and hand off the closed IPC baseline to RPL-04 and backend integration consumers.
- Why now: RPL-03 exit criteria are satisfied and `X-03` is closed, so downstream work should consume this baseline without renaming/reopening IDs.
- Success evidence: downstream tickets reference `doc/wasm/tickets/evidence/rpl-03-step3-rerun-2026-02-09/` and keep additive-only ID evolution.

## Step 1 Output - Shared-Memory IPC Protocol v1 Contract (Normative)

### Protocol Guardrails and Compatibility Envelope

| protocol_id | contract field | required value | deterministic requirement |
| --- | --- | --- | --- |
| IPCP-01 | `protocol_id` | `ipc_shared_ring_v1` | All hot-path runtime/kernel/storage/UI channels MUST advertise this protocol ID. |
| IPCP-02 | `allow_hotpath_fallback` | `false` | Any attempt to route hot-path traffic to copy/message fallback MUST fail with `RPL03-E008` and escalate through `WLCT-10`. |

### Channel/Queue Roles and Ownership Boundaries (Mapped to `WTOP-*`)

| protocol_id | channel_id | lane_class | writer owner | reader owner | queue primitive | deterministic ownership rule | linked contradictions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| IPCP-03 | `ipc.kernel.req.ring.v1` | `headless_runtime`, `ui_runtime` | `WTOP-02` | `WTOP-03` | SPSC ring | Only runtime worker enqueues kernel requests; ownership violation is fatal. | C-01, C-03, C-04, C-08 |
| IPCP-04 | `ipc.kernel.resp.ring.v1` | `headless_runtime`, `ui_runtime` | `WTOP-03` | `WTOP-02` | SPSC ring | Only kernel worker enqueues kernel responses; no shared writer access is permitted. | C-01, C-03, C-04, C-08 |
| IPCP-05 | `ipc.storage.req.ring.v1` | `headless_runtime`, `ui_runtime` | `WTOP-02` | `WTOP-04` | SPSC ring | Runtime-to-storage requests are shared-memory-only for hot paths; no copy fallback. | C-04, C-08 |
| IPCP-06 | `ipc.storage.resp.ring.v1` | `headless_runtime`, `ui_runtime` | `WTOP-04` | `WTOP-02` | SPSC ring | Storage responses are emitted only by storage worker role boundary. | C-04, C-08 |
| IPCP-07 | `ipc.ui.req.ring.v1` | `ui_runtime` only | `WTOP-05` | `WTOP-02` | SPSC ring | UI ingress hot-path classes must enter runtime via bridge worker ring only. | C-01, C-03, C-04 |
| IPCP-08 | `ipc.ui.resp.ring.v1` | `ui_runtime` only | `WTOP-02` | `WTOP-05` | SPSC ring | Runtime egress hot-path classes must return via shared ring, not message transport. | C-01, C-03, C-04 |
| IPCP-09 | `ipc.bootstrap.cmd.<role>.mb.v1` | role-dependent | `WTOP-01` | one of `WTOP-02/03/04/05` | mailbox | Startup command mailbox instances are one-per-role and single-writer/single-reader. | C-04, C-08 |
| IPCP-10 | `ipc.bootstrap.ack.<role>.mb.v1` | role-dependent | one of `WTOP-02/03/04/05` | `WTOP-01` | mailbox | Startup ack mailbox instances are one-per-role and single-writer/single-reader. | C-04, C-08 |

### Ring/Mailbox Memory Layout Contract

| protocol_id | structure | bytes | alignment | version field | deterministic rule |
| --- | --- | --- | --- | --- | --- |
| IPCP-11 | `ipc_ring_header_v1` | 128 | 64-byte | `major=1`, `minor=0` | Header fields and offsets are fixed for protocol v1. |
| IPCP-12 | `ipc_ring_slot_v1` | 32-byte header + payload | slot stride multiple of 64 | inherits ring header version | Slot metadata layout is fixed; payload area begins at byte 32. |
| IPCP-13 | `ipc_mailbox_v1` | 64 | 64-byte | `major=1`, `minor=0` | Mailbox state/notify fields are fixed and atomically updated. |
| IPCP-14 | ring capacity profile | `slot_count` power-of-two, minimum 64 | n/a | n/a | `slot_count` and `slot_stride` are immutable after startup commit (`WSEQ-06`). |

#### `ipc_ring_header_v1` Field Layout (Bytes 0-127)

| offset | size | field | type | atomic | required value/constraint |
| --- | --- | --- | --- | --- | --- |
| 0 | 4 | `magic_u32` | u32 | no | `0x49504331` (`IPC1`) |
| 4 | 2 | `major_u16` | u16 | no | `1` |
| 6 | 2 | `minor_u16` | u16 | no | `0` |
| 8 | 2 | `header_bytes_u16` | u16 | no | `128` |
| 10 | 2 | `slot_header_bytes_u16` | u16 | no | `32` |
| 12 | 2 | `slot_stride_u16` | u16 | no | `>=256` and `mod 64 == 0` |
| 14 | 2 | `slot_count_u16` | u16 | no | power-of-two and `>=64` |
| 16 | 4 | `channel_numeric_id_u32` | u32 | no | stable per `channel_id` |
| 20 | 4 | `lane_mask_u32` | u32 | no | bit0=`headless_runtime`, bit1=`ui_runtime` |
| 24 | 4 | `head_index_i32` | i32 | yes | monotonic modulo `slot_count` |
| 28 | 4 | `tail_index_i32` | i32 | yes | monotonic modulo `slot_count` |
| 32 | 4 | `notify_seq_i32` | i32 | yes | increments on publish/consume wakeups |
| 36 | 4 | `state_flags_u32` | u32 | yes | bitfield; unknown bits MUST be zero |
| 40 | 4 | `max_payload_bytes_u32` | u32 | no | `<= slot_stride_u16 - 32` |
| 44 | 4 | `writer_role_id_u32` | u32 | no | one `WTOP-*` role per channel |
| 48 | 4 | `reader_role_id_u32` | u32 | no | one `WTOP-*` role per channel |
| 52 | 4 | `reserved_u32` | u32 | no | `0` |
| 56 | 72 | `reserved_pad` | bytes | no | all bytes `0` in v1 |

#### `ipc_ring_slot_v1` Field Layout (Per Slot)

| offset | size | field | type | required value/constraint |
| --- | --- | --- | --- | --- |
| 0 | 4 | `slot_seq_u32` | u32 | expected sequence for producer/consumer phase handoff |
| 4 | 2 | `op_class_u16` | u16 | operation class identifier |
| 6 | 2 | `slot_flags_u16` | u16 | bit0=`request`, bit1=`response`, bit2=`error` |
| 8 | 4 | `payload_bytes_u32` | u32 | `<= max_payload_bytes_u32` |
| 12 | 4 | `correlation_id_u32` | u32 | non-zero for request/response pairs |
| 16 | 4 | `status_code_u32` | u32 | `0` on success, otherwise canonical code |
| 20 | 8 | `produced_ns_u64` | u64 | monotonic timestamp |
| 28 | 4 | `reserved_u32` | u32 | `0` |

#### `ipc_mailbox_v1` Field Layout (Bytes 0-63)

| offset | size | field | type | atomic | required value/constraint |
| --- | --- | --- | --- | --- | --- |
| 0 | 4 | `magic_u32` | u32 | no | `0x4d425831` (`MBX1`) |
| 4 | 2 | `major_u16` | u16 | no | `1` |
| 6 | 2 | `minor_u16` | u16 | no | `0` |
| 8 | 4 | `state_i32` | i32 | yes | `0=empty`, `1=cmd_ready`, `2=ack_ready`, `3=failed` |
| 12 | 4 | `notify_seq_i32` | i32 | yes | increments on each state change |
| 16 | 4 | `command_code_u32` | u32 | no | startup command identifier |
| 20 | 4 | `failure_code_u32` | u32 | no | `0` on success, else canonical failure code |
| 24 | 4 | `correlation_id_u32` | u32 | no | non-zero startup handshake correlation ID |
| 28 | 4 | `payload_words_u32` | u32 | no | `0..8` |
| 32 | 32 | `payload_u32[8]` | u32 array | no | role-specific metadata words |

#### Versioning Contract (Strict v1)

| protocol_id | comparison rule | required outcome |
| --- | --- | --- |
| IPCP-15 | `major_u16 != 1` | Fail startup with `RPL03-E001`; do not continue bootstrap. |
| IPCP-16 | `minor_u16 != 0` | Fail startup with `RPL03-E001`; mixed-minor operation is not allowed in MVP. |
| IPCP-17 | any non-zero reserved bytes in v1 headers | Fail startup with `RPL03-E001`; reserved-space mutation is treated as incompatible contract drift. |

### Atomics Signaling Semantics (Wait/Notify and Ordering)

| protocol_id | flow | normative rule | ordering guarantee | wait/notify behavior |
| --- | --- | --- | --- | --- |
| IPCP-18 | producer publish | Producer MUST reserve `tail_index` slot, write payload, then publish slot availability with release semantics before incrementing `tail_index`. | `payload writes` happens-before consumer acquire read of published slot. | Producer increments `notify_seq_i32` and calls `Atomics.notify(notify_seq, 1+)`. |
| IPCP-19 | consumer consume | Consumer MUST acquire-read `tail_index`, read payload only after slot publication, then advance `head_index` with release semantics. | Producer and consumer observe a single ring order by modulo index progression. | Consumer increments `notify_seq_i32` and `Atomics.notify` after freeing slot when writers are blocked. |
| IPCP-20 | empty-ring wait | Consumers MAY block only in worker contexts (`WTOP-02/03/04/05`) using `Atomics.wait` on `notify_seq_i32`. | Wakeups are advisory; predicate (`head != tail`) must be rechecked after every wakeup. | Main/orchestrator thread (`WTOP-01`) MUST NOT block with `Atomics.wait`; it uses bounded poll only. |
| IPCP-21 | full-ring wait | Producers MAY block on consumer progress only within channel timeout budgets; indefinite waits are forbidden. | Waiting producer must re-read `head_index`/`tail_index` with acquire semantics after wakeup. | Timeout expiration yields deterministic failure (`RPL03-E003`) rather than drop/fallback. |
| IPCP-22 | notify discipline | Any state transition that can satisfy a waiter MUST perform `Atomics.notify` after update commit. | `notify_seq` monotonicity gives deterministic event ordering for telemetry assertions. | Implementations MUST NOT skip notify calls when queue/mailbox state changed. |
| IPCP-23 | mailbox state handoff | Mailbox writer updates payload fields, then stores `state_i32` with release semantics. Reader acquires `state_i32` before reading payload. | Command/ack payload visibility is guaranteed by release/acquire pair. | Mailbox waiters use `notify_seq_i32` with same recheck-loop requirement as rings. |

### Backpressure and Flow-Control Rules (Deterministic Outcomes)

| protocol_id | condition | required behavior | prohibited behavior | deterministic outcome |
| --- | --- | --- | --- | --- |
| IPCP-24 | ring occupancy reaches full (`next_tail == head`) | Producer enters bounded wait up to channel timeout budget. | Silent drop of slot payload. | Timeout emits `RPL03-E003` and fail artifact. |
| IPCP-25 | mailbox not empty when writer attempts send | Writer waits for `state=empty` within timeout budget. | Overwriting mailbox payload while `state != empty`. | Timeout emits `RPL03-E009` and startup/runtime failure path. |
| IPCP-26 | payload size exceeds `max_payload_bytes_u32` | Reject write immediately and emit canonical failure. | Truncating payload or spilling to copy/message lane. | Emit `RPL03-E006`; request is not enqueued. |
| IPCP-27 | repeated ring-full timeouts exceed role policy budget | Escalate through lifecycle policy (`WLCT-04` -> `WLCT-05/06`). | Unbounded retry loop without lifecycle signal. | Deterministic degraded/restart/fatal path per `WLCR-*`. |
| IPCP-28 | consumer observes sequence/index corruption | Trigger immediate fatal escalation. | Auto-repair by mutating index/sequence without failure artifact. | Emit `RPL03-E005`; transition through `WLCT-09` or `WLCT-10` as applicable. |
| IPCP-29 | any hot-path send attempts fallback transport | Treat as policy violation. | Redirecting hot-path message to JSON/copy ABI lane. | Emit `RPL03-E008`; immediate terminal path via `WLCT-10`. |

### Timeout and Failure Contract

| contract_id | failure code | condition | message template | remediation guidance | escalation binding |
| --- | --- | --- | --- | --- | --- |
| IPCP-30 | `RPL03-E001` | protocol/header/version incompatibility | `[{code}] IPC contract mismatch on {channel_id}: observed_major={major} observed_minor={minor}.` | Rebuild channel headers to exact `ipc_shared_ring_v1` layout (`major=1`,`minor=0`) and restart. | startup hard-fail (`WLCT-03`) |
| IPCP-31 | `RPL03-E002` | ownership boundary violation | `[{code}] Ownership violation on {channel_id}: writer={writer_role} reader={reader_role} observed_actor={actor_role}.` | Restore single-writer/single-reader role wiring per `IPCP-03`..`IPCP-10`. | fatal (`WLCT-09`) |
| IPCP-32 | `RPL03-E003` | ring full timeout | `[{code}] Ring full timeout on {channel_id} after {timeout_ms}ms (op={op_class}, corr={correlation_id}).` | Increase consumer throughput or slot capacity within contract; do not add fallback lane. | degraded/fatal by `WLCR-*` budget |
| IPCP-33 | `RPL03-E004` | wait timeout on empty/busy channel | `[{code}] Wait timeout on {channel_id} while awaiting {wait_state} after {timeout_ms}ms.` | Verify role liveness and startup/readiness ordering before retry. | startup fail (`WLCT-03`) or runtime degraded |
| IPCP-34 | `RPL03-E005` | sequence/index corruption | `[{code}] Queue integrity failure on {channel_id}: expected_seq={expected_seq} observed_seq={observed_seq}.` | Treat as memory-order/contract defect; restart lane and collect telemetry artifact set. | fatal (`WLCT-09`) |
| IPCP-35 | `RPL03-E006` | payload contract violation | `[{code}] Payload contract violation on {channel_id}: bytes={payload_bytes} max={max_payload_bytes}.` | Fix caller payload framing and slot sizing assumptions. | request fail + telemetry assertion |
| IPCP-36 | `RPL03-E007` | lifecycle/startup gate violation | `[{code}] Lifecycle gate violation on {channel_id}: required_checkpoint={required_checkpoint} observed={observed_checkpoint}.` | Enforce `WSEQ-*` ordering and role readiness before channel use. | startup/runtime fail via `WLCT-03`/`WLCT-11` |
| IPCP-37 | `RPL03-E008` | fallback policy violation | `[{code}] Hot-path fallback forbidden for {channel_id}; attempted_lane={attempted_lane}.` | Remove fallback branch; preserve `allow_hotpath_fallback=false`. | terminal (`WLCT-10`) |
| IPCP-38 | `RPL03-E009` | mailbox handshake timeout | `[{code}] Startup mailbox timeout for role={role_id} phase={phase} after {timeout_ms}ms.` | Check role launch/readiness and mailbox notify wiring. | startup fail (`WLCT-03`) |
| IPCP-39 | `RPL03-E010` | lane-role mismatch (`ui_runtime`/`headless_runtime`) | `[{code}] Lane-role mismatch on {channel_id}: lane_class={lane_class} role={role_id}.` | Correct lane selection and required role/channel set before bootstrap. | fatal (`WLCT-11`) |

### Lifecycle/Startup Integration Points (`WSEQ-*`, `WLCT-*`)

| protocol_id | runtime hook | required IPC behavior | failure path |
| --- | --- | --- | --- |
| IPCP-40 | `WSEQ-01` strict preflight | Validate all ring/mailbox headers (`IPCP-11`..`IPCP-17`) before any runtime hot-path enqueue/dequeue. | `RPL03-E001` / `RPL03-E007` -> `WLCT-03` |
| IPCP-41 | `WSEQ-02` storage bring-up | Storage mailbox/rings (`IPCP-05`, `IPCP-06`, `IPCP-09`, `IPCP-10`) MUST pass readiness handshake before sequence advance. | `RPL03-E004` / `RPL03-E009` -> `WLCT-03` |
| IPCP-42 | `WSEQ-03` kernel bring-up | Kernel mailbox/rings (`IPCP-03`, `IPCP-04`, `IPCP-09`, `IPCP-10`) MUST pass readiness handshake before runtime activation. | `RPL03-E004` / `RPL03-E009` -> `WLCT-03` |
| IPCP-43 | `WSEQ-04` runtime bring-up | Runtime worker binds required channels and confirms publish/consume loopback for bound lane class. | `RPL03-E002` / `RPL03-E007` -> `WLCT-03` |
| IPCP-44 | `WSEQ-05` lane-conditional bridge bring-up | `ui_runtime` MUST initialize `IPCP-07`/`IPCP-08`; `headless_runtime` MUST reject those channels. | `RPL03-E010` -> `WLCT-11` |
| IPCP-45 | `WSEQ-06` topology commit | Emit terminal readiness artifact `ipc_protocol_ready_v1` before bootstrap continuation. | Missing/invalid artifact -> `RPL03-E007` fail |
| IPCP-46 | `WLCT-09` ownership breach transition | Any channel owner mismatch MUST escalate as immediate fatal. | `RPL03-E002` |
| IPCP-47 | `WLCT-10` fallback violation transition | Any hot-path fallback attempt MUST escalate as policy-fail terminal transition. | `RPL03-E008` |
| IPCP-48 | `WLCT-11` lane-role mismatch transition | Lane-specific channel misuse MUST terminate session. | `RPL03-E010` |
| IPCP-49 | `WLCT-04`/`WLCT-05`/`WLCT-06` degraded/restart policy | IPC pressure/timeouts follow deterministic restart budgets from `WLCR-03` and `WLCR-05`; non-restartable roles remain fatal-only. | `RPL03-E003` / `RPL03-E004` |

### Contradiction Linkage (RPL-01 Follow-Through)

| contradiction_id | absorbed by protocol IDs | Step 1 resolution stance | status after Step 1 |
| --- | --- | --- | --- |
| C-01 | `IPCP-01`, `IPCP-03`, `IPCP-04`, `IPCP-29` | Hot-path runtime/kernel transport is normative shared-memory ring, not copy baseline. | in_progress (contract published; upstream doc rewrites pending) |
| C-03 | `IPCP-01`, `IPCP-03`, `IPCP-04`, `IPCP-30` | ABI transport baseline for hot paths is now `ipc_shared_ring_v1` with strict incompatibility failure. | in_progress (contract published; ABI doc alignment pending) |
| C-04 | `IPCP-02`, `IPCP-20`, `IPCP-29`, `IPCP-47` | No-silent-fallback policy is explicit in signaling and failure escalation. | in_progress (contract published; microkernel text alignment pending) |
| C-08 | `IPCP-03`, `IPCP-18`, `IPCP-22`, `IPCP-41` | Interrupt/IPC posture now assumes secure shared-memory runtime with deterministic signaling. | in_progress (contract published; interrupt spec alignment pending) |

### Required Telemetry Artifact Schemas (Test-Lane Assertions)

#### Startup Readiness Artifact (`ipc_protocol_ready_v1`)

| field | type | required | constraints / meaning |
| --- | --- | --- | --- |
| `schema_version` | string | yes | Must equal `ipc_protocol_ready_v1`. |
| `run_id` | string | yes | Must match startup run ID used by `startup_gate_summary_v1`. |
| `lane_class` | string | yes | `headless_runtime` or `ui_runtime`. |
| `protocol_id` | string | yes | Must equal `ipc_shared_ring_v1`. |
| `protocol_major` | integer | yes | Must equal `1`. |
| `protocol_minor` | integer | yes | Must equal `0`. |
| `channel_bindings` | array<object> | yes | One entry per required channel; includes `channel_id`, `writer_role_id`, `reader_role_id`, `slot_count`, `slot_stride`. |
| `startup_sequence_refs` | array<string> | yes | Must include consumed `WSEQ-*` IDs in observed order. |
| `allow_hotpath_fallback` | boolean | yes | Must be `false`. |
| `status` | string | yes | `pass` or `fail`. |
| `failure_code` | string/null | yes | `RPL03-E*` when `status=fail`; else `null`. |
| `message` | string | yes | Deterministic summary text. |

#### Channel Event Artifact (`ipc_channel_event_v1`)

| field | type | required | constraints / meaning |
| --- | --- | --- | --- |
| `schema_version` | string | yes | Must equal `ipc_channel_event_v1`. |
| `run_id` | string | yes | Startup/runtime attempt ID. |
| `channel_id` | string | yes | One of `IPCP-03`..`IPCP-10` channel IDs. |
| `lane_class` | string | yes | `headless_runtime` or `ui_runtime`. |
| `role_id` | string | yes | Emitting role (`WTOP-*`). |
| `event_type` | string | yes | `enqueue`, `dequeue`, `wait`, `notify`, `fail`. |
| `sequence_no` | integer | yes | Monotonic per channel event stream. |
| `head_index` | integer | yes | Snapshot after event. |
| `tail_index` | integer | yes | Snapshot after event. |
| `occupancy` | integer | yes | Derived queue occupancy at event point. |
| `correlation_id` | integer | yes | Correlates request/response pair; `0` allowed only for control probes. |
| `op_class` | integer | yes | Operation class ID. |
| `wait_ms` | integer | yes | Wait duration (`0` for non-wait events). |
| `status` | string | yes | `ok` or `fail`. |
| `failure_code` | string/null | yes | Canonical `RPL03-E*` when `status=fail`. |
| `transition_id` | string/null | yes | `WLCT-*` when event triggers lifecycle transition; else `null`. |
| `allow_hotpath_fallback` | boolean | yes | Must be `false` for all events. |

#### Channel Summary Artifact (`ipc_channel_summary_v1`)

| field | type | required | constraints / meaning |
| --- | --- | --- | --- |
| `schema_version` | string | yes | Must equal `ipc_channel_summary_v1`. |
| `run_id` | string | yes | Matches per-event artifacts. |
| `channel_id` | string | yes | One channel summary per required channel. |
| `protocol_id` | string | yes | Must equal `ipc_shared_ring_v1`. |
| `events_emitted` | integer | yes | Count of `ipc_channel_event_v1` records for this channel. |
| `max_occupancy` | integer | yes | Highest observed occupancy during run. |
| `wait_timeout_count` | integer | yes | Count of timeout-class wait failures. |
| `first_failure_code` | string/null | yes | First `RPL03-E*` failure if any; else `null`. |
| `status` | string | yes | `pass` or `fail`. |
| `allow_hotpath_fallback` | boolean | yes | Must be `false`. |
| `results_digest` | string | yes | Deterministic digest over per-channel event stream. |

### Minimum Test-Lane Assertions (Step 1 Contract Consumers)

1. Parse and schema-validate `ipc_protocol_ready_v1`, `ipc_channel_event_v1`, and `ipc_channel_summary_v1` artifacts.
2. Assert ownership invariants: event `role_id` must match configured writer/reader role for each `channel_id`.
3. Assert no-fallback invariant: every artifact record has `allow_hotpath_fallback=false`.
4. Assert queue-order invariants: `sequence_no` monotonic and occupancy bounds `0 <= occupancy <= slot_count`.
5. Assert failure determinism: first failure code in summary matches first per-event failure record.

## Step 2 Output - Conformance Matrix and Queue-Correctness Assertions (v1)

### Conformance Execution Contract

1. Step 2 identifiers are frozen: `IPCL-01`..`IPCL-05` and `IPCV-01`..`IPCV-12`.
2. Every conformance run MUST emit:
   - `ipc_protocol_ready_v1`,
   - required `ipc_channel_event_v1` streams,
   - required `ipc_channel_summary_v1` records,
   - one terminal `ipc_conformance_summary_v1`.
3. Hot-path no-fallback semantics remain mandatory in all conformance lanes (`allow_hotpath_fallback=false`).
4. Fail-injection controls for deterministic lanes are normative:
   - `CCL_IPC_TEST_INJECT_FAILURE=<RPL03-E*>`
   - `CCL_IPC_TEST_INJECT_CHANNEL=<channel_id>` (optional but required when ambiguity exists)
   - `CCL_IPC_TEST_INJECT_LANE_CLASS=<headless_runtime|ui_runtime>` (optional)
5. If runtime internals use different knobs, test wrappers MUST expose equivalent behavior for the three controls above.

### Conformance Lane Registry

| lane_id | command | lane_class | required artifact outcomes |
| --- | --- | --- | --- |
| IPCL-01 | `node doc/wasm/js/load-image.mjs --mode start-lisp --manifest doc/wasm/root.image.manifest.json --stdin-text "(quit)\\n" --close-stdin` | `headless_runtime` | terminal `ipc_protocol_ready_v1` pass + per-channel summaries for kernel/storage channels |
| IPCL-02 | `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive` | `headless_runtime` | startup + smoke lane consumes and validates IPC artifacts from `IPCL-01` path |
| IPCL-03 | `node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | `ui_runtime` | terminal protocol-ready pass + required UI channel summary coverage |
| IPCL-04 | `node doc/wasm/js/all-smoke.mjs` | mixed | aggregate suite preserves IPC artifact visibility and fails on IPC conformance breach |
| IPCL-05 | `npm --prefix web-ui run test:sandbox` | `ui_runtime` | browser harness validates IPC conformance fields and no-fallback invariants |

### Conformance Matrix (`IPCV-*`)

| conformance_id | lane_id | objective | command | deterministic assertions | expected failure mapping |
| --- | --- | --- | --- | --- | --- |
| IPCV-01 | IPCL-01 | baseline protocol-ready pass | `node doc/wasm/js/load-image.mjs --mode start-lisp --manifest doc/wasm/root.image.manifest.json --stdin-text "(quit)\\n" --close-stdin` | `ipc_protocol_ready_v1.status=pass`; `protocol_id=ipc_shared_ring_v1`; `allow_hotpath_fallback=false` | n/a |
| IPCV-02 | IPCL-01 | kernel channel queue correctness | same as IPCV-01 | kernel req/resp summaries (`IPCP-03`,`IPCP-04`) show monotonic `sequence_no`, bounded occupancy, and zero integrity failures | n/a |
| IPCV-03 | IPCL-01 | storage channel queue correctness | same as IPCV-01 | storage req/resp summaries (`IPCP-05`,`IPCP-06`) satisfy slot bounds and no fallback flags | n/a |
| IPCV-04 | IPCL-03 | UI lane channel correctness | `node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | UI req/resp summaries (`IPCP-07`,`IPCP-08`) present only for `ui_runtime`; no lane-role mismatch | n/a |
| IPCV-05 | IPCL-01 | deterministic protocol mismatch fail | `CCL_IPC_TEST_INJECT_FAILURE=RPL03-E001 node doc/wasm/js/load-image.mjs --mode start-lisp --manifest doc/wasm/root.image.manifest.json --stdin-text "(quit)\\n" --close-stdin` | terminal summary `status=fail`; first failure code `RPL03-E001`; startup abort before runtime continuation | `WLCT-03` |
| IPCV-06 | IPCL-01 | deterministic ownership violation fail | `CCL_IPC_TEST_INJECT_FAILURE=RPL03-E002 CCL_IPC_TEST_INJECT_CHANNEL=ipc.kernel.req.ring.v1 node doc/wasm/js/load-image.mjs --mode start-lisp --manifest doc/wasm/root.image.manifest.json --stdin-text "(quit)\\n" --close-stdin` | first failure code `RPL03-E002`; channel summary marks ownership breach; terminal path is fatal | `WLCT-09` |
| IPCV-07 | IPCL-01 | deterministic ring-full timeout fail | `CCL_IPC_TEST_INJECT_FAILURE=RPL03-E003 CCL_IPC_TEST_INJECT_CHANNEL=ipc.kernel.req.ring.v1 node doc/wasm/js/load-image.mjs --mode start-lisp --manifest doc/wasm/root.image.manifest.json --stdin-text "(quit)\\n" --close-stdin` | first failure code `RPL03-E003`; timeout counters increment deterministically | `WLCT-04`/`WLCT-05`/`WLCT-06` per role policy |
| IPCV-08 | IPCL-01 | deterministic wait-timeout fail | `CCL_IPC_TEST_INJECT_FAILURE=RPL03-E004 CCL_IPC_TEST_INJECT_CHANNEL=ipc.storage.resp.ring.v1 node doc/wasm/js/load-image.mjs --mode start-lisp --manifest doc/wasm/root.image.manifest.json --stdin-text "(quit)\\n" --close-stdin` | first failure code `RPL03-E004`; wait-state context populated in failure message | `WLCT-03` or degraded path |
| IPCV-09 | IPCL-04 | deterministic queue-integrity fail | `CCL_IPC_TEST_INJECT_FAILURE=RPL03-E005 CCL_IPC_TEST_INJECT_CHANNEL=ipc.kernel.resp.ring.v1 node doc/wasm/js/all-smoke.mjs` | aggregate run fails; first failure code `RPL03-E005`; no post-fatal steady-state events | `WLCT-09` |
| IPCV-10 | IPCL-01 | deterministic payload violation fail | `CCL_IPC_TEST_INJECT_FAILURE=RPL03-E006 CCL_IPC_TEST_INJECT_CHANNEL=ipc.storage.req.ring.v1 node doc/wasm/js/load-image.mjs --mode start-lisp --manifest doc/wasm/root.image.manifest.json --stdin-text "(quit)\\n" --close-stdin` | first failure code `RPL03-E006`; violation fields include observed/max payload bytes | request fail + summary fail |
| IPCV-11 | IPCL-04 | deterministic fallback-policy fail | `CCL_IPC_TEST_INJECT_FAILURE=RPL03-E008 node doc/wasm/js/all-smoke.mjs` | first failure code `RPL03-E008`; `allow_hotpath_fallback=false` remains explicit in terminal record | `WLCT-10` |
| IPCV-12 | IPCL-03 | deterministic lane-role mismatch fail | `CCL_IPC_TEST_INJECT_FAILURE=RPL03-E010 CCL_IPC_TEST_INJECT_LANE_CLASS=headless_runtime node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | first failure code `RPL03-E010`; UI channel contract rejected under wrong lane class | `WLCT-11` |

### Conformance Summary Artifact (`ipc_conformance_summary_v1`)

| field | type | required | constraints / meaning |
| --- | --- | --- | --- |
| `schema_version` | string | yes | Must equal `ipc_conformance_summary_v1`. |
| `run_id` | string | yes | Global ID for one conformance execution set. |
| `protocol_id` | string | yes | Must equal `ipc_shared_ring_v1`. |
| `protocol_major` | integer | yes | Must equal `1`. |
| `protocol_minor` | integer | yes | Must equal `0`. |
| `conformance_ids` | array<string> | yes | List of executed `IPCV-*` IDs. |
| `passed_ids` | array<string> | yes | Subset of executed IDs that passed. |
| `failed_ids` | array<string> | yes | Subset of executed IDs that failed. |
| `first_failure_id` | string/null | yes | First failing `IPCV-*` ID, else `null`. |
| `first_failure_code` | string/null | yes | First failing `RPL03-E*` code, else `null`. |
| `allow_hotpath_fallback` | boolean | yes | Must be `false`. |
| `lane_results_digest` | string | yes | Deterministic digest over all lane summaries/events used in this run. |
| `status` | string | yes | `pass` or `fail`. |
| `x03_clear_ready` | boolean | yes | `true` only when all required pass/fail assertions for `IPCV-*` set are satisfied and evidence is commit-ready. |
| `timestamp_utc` | string | yes | RFC3339 UTC timestamp. |

### `X-03` Hard-Gate Readiness Assertions (Step 2)

1. Required baseline pass set (`IPCV-01`..`IPCV-04`) must pass with terminal `ipc_conformance_summary_v1.status=pass` when fail injection is disabled.
2. Required deterministic fail set (`IPCV-05`..`IPCV-12`) must emit exact first-failure `RPL03-E*` code and mapped `WLCT-*` transition class.
3. All emitted artifacts must preserve `allow_hotpath_fallback=false`.
4. `x03_clear_ready=true` requires complete artifact set and deterministic assertion success for all required `IPCV-*` rows.
5. Hard-gate closure in matrix row `X-03` remains blocked until Step 3 commits evidence artifacts proving these assertions.

## Step 3 Output - Conformance Execution Evidence (run v1 + rerun v2)

### Historical Run v1 (failed; retained for traceability)

Evidence bundle path:

- `doc/wasm/tickets/evidence/rpl-03-step3-2026-02-09/ipcv-results.tsv`
- `doc/wasm/tickets/evidence/rpl-03-step3-2026-02-09/ipc_conformance_summary_v1.json`
- `doc/wasm/tickets/evidence/rpl-03-step3-2026-02-09/assertion-report.md`
- `doc/wasm/tickets/evidence/rpl-03-step3-2026-02-09/logs/IPCV-01.log` .. `doc/wasm/tickets/evidence/rpl-03-step3-2026-02-09/logs/IPCV-12.log`

Run v1 summary (`ipc_conformance_summary_v1`):

| field | observed value |
| --- | --- |
| `run_id` | `rpl03-step3-2026-02-09T22:36:42Z` |
| `status` | `fail` |
| `x03_clear_ready` | `false` |
| `failed_ids` | `IPCV-01`..`IPCV-12` |
| `lane_results_digest` | `be6364f47a6bdeecec8b922c351fe05ead4bc852721139a5c2db4c36e03c31a2` |

### Rerun v2 (closure run)

Evidence bundle path:

- `doc/wasm/tickets/evidence/rpl-03-step3-rerun-2026-02-09/ipcv-results.tsv`
- `doc/wasm/tickets/evidence/rpl-03-step3-rerun-2026-02-09/ipc_conformance_summary_v1.json`
- `doc/wasm/tickets/evidence/rpl-03-step3-rerun-2026-02-09/assertion-report.md`
- `doc/wasm/tickets/evidence/rpl-03-step3-rerun-2026-02-09/logs/IPCV-01.log` .. `doc/wasm/tickets/evidence/rpl-03-step3-rerun-2026-02-09/logs/IPCV-12.log`

Rerun v2 summary (from committed `ipc_conformance_summary_v1`):

| field | observed value |
| --- | --- |
| `run_id` | `rpl03-step3-rerun-2026-02-09T22:53:53.698Z` |
| `status` | `pass` |
| `x03_clear_ready` | `true` |
| `passed_ids` | `IPCV-01`..`IPCV-12` |
| `failed_ids` | none |
| `first_failure_id` | `null` |
| `first_failure_code` | `null` |
| `lane_results_digest` | `9b01aa84b30856276d5b5687792a1f15961759a60781c0abad5442811167553d` |

### Gap Closure Register

| gap_id | closure evidence | closure status |
| --- | --- | --- |
| IPCGAP-01 | Baseline lanes `IPCV-01`..`IPCV-04` now emit required runtime `ipc_protocol_ready_v1`, `ipc_channel_event_v1`, `ipc_channel_summary_v1`, and lane-level terminal summaries. | closed |
| IPCGAP-02 | Deterministic fail lanes `IPCV-05`..`IPCV-12` now fail with expected `RPL03-E*` first-failure codes and non-zero exit behavior. | closed |
| IPCGAP-03 | Runtime emits terminal `ipc_conformance_summary_v1` in every lane log and committed rerun bundle summary reports `status=pass`. | closed |
| IPCGAP-04 | Fail-lane channel events now include expected `WLCT-*` transition mappings (`WLCT-03`, `WLCT-04`, `WLCT-09`, `WLCT-10`, `WLCT-11`) with deterministic code linkage. | closed |

### Step 3 Assertion Outcome (rerun v2)

1. Baseline pass set (`IPCV-01`..`IPCV-04`): pass.
2. Deterministic fail set (`IPCV-05`..`IPCV-12`): pass (expected failure-code/transition mappings observed).
3. Terminal conformance summary requirement: pass.
4. Hard-gate row `X-03` closure readiness: `true` (row transitioned to `done`).

## Detailed Work Breakdown

### Step 1 - Shared-Memory IPC Core Contract (v1)

- Status: done
- Notes:
  - Published protocol v1 contract with frozen `IPCP-01`..`IPCP-49` IDs.
  - Added deterministic channel ownership, memory layout, signaling, flow-control, failure, and lifecycle integration rules.
  - Added required telemetry schemas and machine-actionable assertion rules for test lanes.
- Next:
  - Keep `IPCP-*` IDs frozen; evolve only additively in later steps.

### Step 2 - Conformance and Queue-Correctness Evidence

- Status: done
- Notes:
  - Published Step 2 conformance matrix and queue-correctness assertions with frozen IDs (`IPCV-01`..`IPCV-12`) and lane registry (`IPCL-01`..`IPCL-05`).
  - Defined deterministic fail-injection controls and terminal evidence schema (`ipc_conformance_summary_v1`) for machine-gated hard-gate checks.
- Next:
  - Keep `IPCL-*`/`IPCV-*` identifiers frozen; evolve only additively in follow-on tickets.

### Step 3 - Conformance Execution and Hard-Gate Closure

- Status: done
- Notes:
  - Step 3 run v1 failure evidence is retained for traceability and rerun v2 closure evidence is now committed.
  - Rerun v2 closes `IPCGAP-01`..`IPCGAP-04` and publishes terminal `ipc_conformance_summary_v1` with `status=pass` and `x03_clear_ready=true`.
  - Dependency row `X-03` is now `done`.
- Next:
  - Hand off frozen IPC baseline to RPL-04 and backend integration consumers; no ID renames/reopens.

## Test and Validation Plan

- Unit:
  - Validate ring/mailbox header parsing against fixed offset/size constraints and strict version checks.
  - Validate sequence/occupancy math for enqueue/dequeue transitions and timeout boundaries (`IPCV-02`, `IPCV-03`).
- Integration:
  - Validate startup sequence consumption (`WSEQ-01`..`WSEQ-06`) emits `ipc_protocol_ready_v1` before runtime continuation (`IPCV-01`).
  - Validate hot-path channels emit per-event and summary artifacts with canonical `RPL03-E*` failure mapping (`IPCV-04`..`IPCV-12`).
- Regression:
  - Inject ownership, timeout, and fallback violations and assert deterministic `WLCT-*` escalation paths.
  - Preserve additive-only ID policy for frozen `IPCP-*`, `IPCL-*`, and `IPCV-*` IDs.

## Risks and Mitigations

- Risk: protocol contract drifts from frozen worker topology/lifecycle IDs.
  - Mitigation: require direct `WTOP-*`, `WSEQ-*`, `WLCT-*`, `WLCR-*` linkage in every normative section.
- Risk: implementations introduce hidden fallback under pressure.
  - Mitigation: enforce `IPCP-02`/`IPCP-29`/`IPCP-47` plus artifact-level no-fallback assertions.
- Risk: queue behavior appears specified but not verifiable.
  - Mitigation: retain committed run-v1 and rerun-v2 evidence bundles and require downstream tickets to reference the closed rerun bundle.

## Change Log

- 2026-02-09: Initial RPL-03 subplan created and Step 1 protocol v1 contract published (`IPCP-01`..`IPCP-49`) with telemetry schema requirements and Step 2 conformance handoff.
- 2026-02-09: Executed Step 2 by publishing conformance matrix/assertions (`IPCV-01`..`IPCV-12`), lane registry (`IPCL-01`..`IPCL-05`), and terminal evidence schema (`ipc_conformance_summary_v1`).
- 2026-02-09: Executed Step 3 run v1 across `IPCV-01`..`IPCV-12` and committed evidence bundle (`rpl03-step3-2026-02-09`); recorded blocking gaps `IPCGAP-01`..`IPCGAP-04` after assertion failures.
- 2026-02-09: Remediated `IPCGAP-01`..`IPCGAP-04`, executed Step 3 rerun across `IPCV-01`..`IPCV-12`, and committed closure evidence bundle (`rpl-03-step3-rerun-2026-02-09`) with `status=pass`, `x03_clear_ready=true`, and `X-03` closure.
