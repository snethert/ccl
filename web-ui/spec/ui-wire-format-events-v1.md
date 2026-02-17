# UI Wire Format Events v1

Status: Draft  
Version: 1.1.0  
Last updated: 2026-02-17  
Scope: Binary wire format for UI input event batches returned by `KERNEL_OP_UI_POLL`  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/bridge/codec.mjs`, `web-ui/bridge/ui-bridge.mjs`, `scripts/wasm/lib/microkernel.mjs`, `doc/wasm/kernel-request-abi.md`  
Compatibility: `v1.x` preserves batch header/layout, event type IDs, and selection semantics; `v1.1+` documents planned bounded-input/coalescing extensions without changing binary record layout.

## 1. Purpose

This contract defines the exact binary event batch format used by the UI bridge and microkernel poll path.
It is normative for byte layout, event typing, queue selection, and overflow behavior.

## 2. Binary Profile

1. Endianness: little-endian for all scalar fields.
2. Magic: `0x55494531` (`"UIE1"`).
3. Version: `1`.
4. Batch payload is a single contiguous byte buffer.

## 3. Batch Layout

Header (`16` bytes):

| Offset | Size | Type | Field | Rules |
|---|---:|---|---|---|
| `0x00` | 4 | `u32` | `magic` | <a id="REQ-UI-WIRE-FORMAT-EVENTS-V1-E50592962C"></a>MUST equal `0x55494531`. |
| `0x04` | 4 | `u32` | `version` | <a id="REQ-UI-WIRE-FORMAT-EVENTS-V1-4388786B39"></a>MUST equal `1`. |
| `0x08` | 4 | `u32` | `string_count` | Number of string entries. |
| `0x0c` | 4 | `u32` | `event_count` | Number of event records. |

After header:

1. String table entries (Section 4).
2. `event_count` event records (Section 5), in queue order.

## 4. String Table Layout

Each string entry is:

| Offset | Size | Type | Field |
|---|---:|---|---|
| `+0` | 4 | `u32` | `byte_length` |
| `+4` | `byte_length` | bytes | UTF-8 bytes |

Index conventions:

1. `0xffffffff` means null/missing string.
2. All other indices refer to table position.
3. Writers <a id="REQ-UI-WIRE-FORMAT-EVENTS-V1-B278B9ABF4"></a>MUST insert strings in first-seen order while scanning events.

## 5. Event Record Layout

## 5.1 Common Event Header (`16` bytes)

| Offset | Size | Type | Field |
|---|---:|---|---|
| `+0` | 4 | `u32` | `type_id` |
| `+4` | 4 | `u32` | `flags` |
| `+8` | 4 | `u32` | `target_id_index` |
| `+12` | 4 | `u32` | `window_id_index` |

## 5.2 Event Type IDs (`v1`)

| ID | Type |
|---:|---|
| `1` | pointer |
| `2` | key |
| `3` | composition |
| `4` | text |
| `5` | focus |
| `6` | blur |
| `7` | wheel |

## 5.3 Pointer Event Body (`40` bytes)

| Offset | Size | Type | Field |
|---|---:|---|---|
| `+0` | 8 | `f64` | `x` |
| `+8` | 8 | `f64` | `y` |
| `+16` | 4 | `i32` | `button` |
| `+20` | 4 | `i32` | `buttons` |
| `+24` | 4 | `i32` | `modifiers` |
| `+28` | 4 | `i32` | `pointer_type` (`0=mouse/unknown`, `1=pen`, `2=touch`) |
| `+32` | 4 | `i32` | `click_count` |
| `+36` | 4 | `u32` | `reserved=0` |

Pointer flag bits used by the bridge:

1. `1` down
2. `2` up
3. `4` move
4. `8` enter
5. `16` leave
6. `32` cancel

## 5.4 Key Event Body (`32` bytes)

| Offset | Size | Type | Field |
|---|---:|---|---|
| `+0` | 4 | `u32` | `key_index` |
| `+4` | 4 | `u32` | `code_index` |
| `+8` | 4 | `u32` | `modifiers` |
| `+12` | 4 | `u32` | `repeat` (`0|1`) |
| `+16` | 4 | `u32` | `location` |
| `+20` | 4 | `u32` | `is_composing` (`0|1`) |
| `+24` | 4 | `u32` | `text_index` |
| `+28` | 4 | `u32` | `reserved=0` |

Key flag bits used by the bridge:

1. `1` keydown
2. `2` keyup

## 5.5 Composition Event Body (`16` bytes)

| Offset | Size | Type | Field |
|---|---:|---|---|
| `+0` | 4 | `u32` | `phase` (`0=start`, `1=update`, `2=end`) |
| `+4` | 4 | `u32` | `data_index` |
| `+8` | 4 | `u32` | `reserved=0` |
| `+12` | 4 | `u32` | `reserved=0` |

## 5.6 Text Event Body (`16` bytes)

| Offset | Size | Type | Field |
|---|---:|---|---|
| `+0` | 4 | `u32` | `text_index` |
| `+4` | 4 | `u32` | `reserved=0` |
| `+8` | 4 | `u32` | `reserved=0` |
| `+12` | 4 | `u32` | `reserved=0` |

## 5.7 Focus/Blur Event Body (`16` bytes)

| Offset | Size | Type | Field |
|---|---:|---|---|
| `+0` | 4 | `u32` | `related_id_index` |
| `+4` | 4 | `u32` | `reserved=0` |
| `+8` | 4 | `u32` | `reserved=0` |
| `+12` | 4 | `u32` | `reserved=0` |

## 5.8 Wheel Event Body (`32` bytes)

| Offset | Size | Type | Field |
|---|---:|---|---|
| `+0` | 8 | `f64` | `delta_x` |
| `+8` | 8 | `f64` | `delta_y` |
| `+16` | 4 | `u32` | `delta_mode` |
| `+20` | 4 | `u32` | `modifiers` |
| `+24` | 4 | `u32` | `reserved=0` |
| `+28` | 4 | `u32` | `reserved=0` |

## 5.9 Unknown Type Fallback

For unknown `type_id`, `v1` encoder writes a reserved body of `16` zero bytes.

## 5.10 Planned Coalescing and High-Rate Event Classes (Non-blocking)

Coalescing policy is profile-gated and applies before Section 6 batch selection when the extension profile is enabled.

Event classes:

1. Structural events (expected to be non-coalesced in planned profiles):
- pointer `down`, `up`, `enter`, `leave`, `cancel`
- key `keydown`, `keyup`
- composition `start`, `update`, `end`
- text input
- focus/blur
2. High-rate events (MAY be coalesced):
- pointer `move`
- wheel

Coalescing rules:

1. Pointer move coalescing key is `(pointer_id, target_id, window_id, drag_session_id)`.
2. Wheel coalescing key is `(target_id, window_id, delta_mode, modifiers)`.
3. If coalesced, the representative event should preserve the latest position/value in queue order.
4. If coalesced, dropped-event count metadata should be emitted through observability telemetry.

## 6. Selection and Poll Semantics

The bridge event queue selection <a id="REQ-UI-WIRE-FORMAT-EVENTS-V1-C430C9AF0C"></a>MUST follow this deterministic algorithm:

1. Input order is queue insertion order.
2. `maxEvents`:
- if integer and `>0`, cap count to that value.
- otherwise treat as unlimited.
3. `maxBytes`:
- if `0`, treat as unlimited.
- otherwise enforce `header + string-table growth + event record sizes`.
4. Events are considered one-by-one; selected set is a prefix.
5. If the first event alone exceeds `maxBytes`, selection returns `overflow=true` and zero selected events.
6. If a later event exceeds `maxBytes`, selection stops with current prefix and `overflow=false`.

Planned extension profile notes (non-blocking in baseline `v1`):

1. bounded input queue limits (`inputQueueMaxEvents`, `inputQueueMaxBytes`) are specified in `input-backpressure-and-coalescing-contract-v1.md`.
2. deterministic high-rate coalescing/drop policy is specified in `input-backpressure-and-coalescing-contract-v1.md`.
3. saturation telemetry counters are specified in `observability-contract-v1.md`.

`UI_POLL` behavior:

1. Empty queue with `allowPending=true`: return pending.
2. Empty queue with `allowPending=false`: return zero events and empty payload.
3. Selection `overflow=true`: return `E2BIG` (`kernel_result=-E2BIG`).

## 7. Determinism Rules

1. For identical queue content and limits, selected prefix <a id="REQ-UI-WIRE-FORMAT-EVENTS-V1-F09D37F10E"></a>MUST be identical.
2. Batch `event_count` <a id="REQ-UI-WIRE-FORMAT-EVENTS-V1-DBA99D2AAF"></a>MUST equal encoded event record count.
3. String table index assignment <a id="REQ-UI-WIRE-FORMAT-EVENTS-V1-69D360ECB9"></a>MUST be stable first-seen order.
4. Encoded event order <a id="REQ-UI-WIRE-FORMAT-EVENTS-V1-B98780F705"></a>MUST match selected queue order.
5. Planned extension profile: coalescing representative selection should be deterministic for a fixed queue prefix and profile.

## 8. Security Requirements

1. Event data from DOM/canvas hit-test <a id="REQ-UI-WIRE-FORMAT-EVENTS-V1-028A2239A3"></a>MUST be treated as untrusted until validated by command handlers.
2. Implementations <a id="REQ-UI-WIRE-FORMAT-EVENTS-V1-894B660C57"></a>MUST bound batch size via `maxBytes`.
3. Consumers <a id="REQ-UI-WIRE-FORMAT-EVENTS-V1-701B7DD72C"></a>MUST validate magic/version and buffer bounds before decode.
4. Producers <a id="REQ-UI-WIRE-FORMAT-EVENTS-V1-D415A36068"></a>MUST not encode host-object references, only primitive lanes.

## 9. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `ui-events.batch-overflow` | Selected batch exceeds `maxBytes` at first event (`E2BIG`). | Yes | Increase budget or drain more frequently. |
| `ui-events.poll-pending` | Queue empty and pending mode selected. | Yes | Poll later or wait for wake signal. |
| `ui-events.version-unsupported` | Event batch magic/version mismatch. | No | Use supported wire version. |
| `ui-events.payload-truncated` | Batch bytes do not contain all declared records/strings. | No | Send full payload. |
| `ui-events.service-unavailable` | UI poll service missing (`-ENOSYS`). | No | Install/configure UI service. |
| `ui-events.invalid-request` | Poll request payload malformed (`-EINVAL`). | No | Send valid poll request fields. |

Planned extension failure codes (non-blocking in baseline `v1`):

1. `ui-events.input-overflow`
2. `ui-events.backpressure`

## 10. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/bridge-codec.test.mjs`
2. `web-ui/tests/bridge-microkernel.test.mjs`
3. `web-ui/tests/browser.test.mjs`
4. `web-ui/tests/phase-5-runtime-command-roundtrip.test.mjs`
5. `web-ui/tests/bridge-input-flood.test.mjs`
6. `web-ui/tests/bridge-coalescing-determinism.test.mjs`
7. `web-ui/tests/ui-poll-backpressure.test.mjs`

Pass criteria:

1. Encoded batch header and version fields are stable and correct.
2. Selection honors `maxEvents` and `maxBytes` rules exactly.
3. Overflow and pending behavior map to expected poll result semantics.
4. Event ordering remains stable under repeated fixed-input runs.

## 11. Conformance

An implementation is conformant only if Sections 2-10 are satisfied.
