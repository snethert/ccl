# Protocol Version Negotiation v1

Status: Draft  
Version: 1.1.0  
Last updated: 2026-02-17  
Scope: Version and capability negotiation policy for runtime bridge envelope, UI wire formats, and kernel bridge opcodes  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/runtime-bridge-envelope-v1.md`, `web-ui/spec/ui-wire-format-tree-v1.md`, `web-ui/spec/ui-wire-format-events-v1.md`, `scripts/wasm/lib/microkernel.mjs`, `scripts/wasm/lib/sab-ring.mjs`, `doc/wasm/kernel-request-abi.md`, `doc/wasm/kernel-opcode-registry.md`  
Compatibility: `v1.x` preserves negotiation sequence, capability bit assignments, and strict-major policy; `v1.1+` adds UI-tree composite/delta capability bits without changing baseline `v1` negotiation flow.

## 1. Purpose

This contract defines how bridge participants negotiate protocol versions and optional capabilities.
It is normative for startup handshake, mixed-version behavior, extension rules, and deprecation policy.

## 2. Versioned Surfaces in Scope

| Surface | Probe / Field | `v1` value |
|---|---|---|
| Kernel request ABI | `KERNEL_OP_CAPS.response.abi_version` | `1` |
| Pending capability | `KERNEL_OP_CAPS.response.capability_bits bit0` | `0|1` |
| UI tree composite values | `KERNEL_OP_CAPS.response.capability_bits bit1` | `0|1` |
| UI tree delta patches | `KERNEL_OP_CAPS.response.capability_bits bit2` | `0|1` |
| Runtime envelope | `message.version` | `1` |
| UI tree payload | `magic/version` | `0x55494231` / `1` |
| UI event payload | `magic/version` | `0x55494531` / `1` |
| Runtime command frame | `frame_version` at offset `0x00` | `1` |
| SAB transport ID | `transport` string | `sab_ring_v1` |

## 3. Required Handshake Sequence

Consumers <a id="REQ-PROTOCOL-VERSION-NEGOTIATION-V1-639C43C221"></a>MUST run this sequence before enabling bridge features:

1. Call `KERNEL_OP_CAPS` and read `abi_version`, `capability_bits`, `max_response_bytes`.
2. Require `abi_version == 1` for `v1` flows.
3. Read `capability_bits bit0`:
- if set, `UI_POLL` and `RUNTIME_COMMAND_POLL` MAY use `allow_pending_if_empty` flag.
- if clear, callers SHOULD set pending flags to `0` and expect non-pending completion.
4. Read `capability_bits bit1`:
- if set, producer/consumer MAY exchange composite property values (`value_type=4|5`) in `ui-wire-format-tree-v1.md`.
- if clear, producer <a id="REQ-PROTOCOL-VERSION-NEGOTIATION-V1-593CE63620"></a>MUST emit scalar-only property values (`0..3`).
5. Read `capability_bits bit2`:
- if set, producer/consumer MAY exchange `ui-wire-format-tree-delta-v1` payloads.
- if clear, producer <a id="REQ-PROTOCOL-VERSION-NEGOTIATION-V1-B167398859"></a>MUST use full-tree payloads only.
6. Configure runtime bridge transports:
- runtime command ingress: supported transport ID is `sab_ring_v1` when enabled.
- runtime event egress: supported transport ID is `sab_ring_v1` when enabled.
- unsupported transport identifiers <a id="REQ-PROTOCOL-VERSION-NEGOTIATION-V1-671D11C945"></a>MUST fail fast during setup.

## 4. Consumer Compatibility Rules

`v1` consumers <a id="REQ-PROTOCOL-VERSION-NEGOTIATION-V1-C0C69EDCE2"></a>MUST:

1. Reject unsupported major versions for all scoped surfaces.
2. Reject UI tree payloads with unsupported magic/version.
3. Reject runtime envelope `version != 1`.
4. Reject runtime command frame versions other than `1`.
5. Treat unknown request flag bits as reserved and ignore them unless explicitly assigned.
6. Reject composite tree values when capability bit1 is not negotiated.
7. Reject delta tree payloads when capability bit2 is not negotiated.

Runtime kind handling:

1. Non-strict kind mode MAY accept unknown kinds.
2. Strict kind mode <a id="REQ-PROTOCOL-VERSION-NEGOTIATION-V1-C2E9B9CE28"></a>MUST reject unknown kinds.
3. Consumers using strict mode in production <a id="REQ-PROTOCOL-VERSION-NEGOTIATION-V1-C9DC02CDC4"></a>MUST publish extension rollout plans before enabling new kinds.

## 5. Producer Compatibility Rules

`v1` producers <a id="REQ-PROTOCOL-VERSION-NEGOTIATION-V1-E13AC234FD"></a>MUST:

1. Emit only `version=1` artifacts for `v1` consumers.
2. Keep existing field semantics stable across `v1.x`.
3. Avoid reusing or changing meanings of existing kind/type IDs.

`v1.x` additive changes MAY include:

1. New runtime `kind` values (non-strict consumers remain compatible).
2. New event `type_id` values if old consumers can safely ignore/degrade them.
3. New reserved flag bits with documented ignore-safe behavior for old consumers.

Major version (`v2`) is required for:

1. Header layout changes.
2. Reinterpreting existing field semantics.
3. Changing strictness defaults in a way that breaks existing producers.

## 6. Pending and Backpressure Negotiation

Pending semantics are capability-gated:

1. Bit0 set means some requests MAY return `PENDING`.
2. Bit0 clear means callers <a id="REQ-PROTOCOL-VERSION-NEGOTIATION-V1-C4B07A294B"></a>MUST tolerate immediate `DONE` with empty payload when no work is available.

Backpressure semantics:

1. `UI_POLL` overflow maps to `-E2BIG`.
2. Runtime command frame larger than `max_bytes` maps to `-E2BIG`.
3. Runtime event SAB enqueue failures map to transient backpressure (`EWOULDBLOCK` lane).

## 7. Deprecation Policy

For `v1.x`:

1. Deprecations <a id="REQ-PROTOCOL-VERSION-NEGOTIATION-V1-C0EBB202C1"></a>MUST be announced in spec updates before enforcement.
2. Removed behavior <a id="REQ-PROTOCOL-VERSION-NEGOTIATION-V1-19B66926CD"></a>MUST have one documented transitional release where both old and new behavior are accepted, unless a security issue requires immediate removal.
3. Any removed surface <a id="REQ-PROTOCOL-VERSION-NEGOTIATION-V1-F64188A9FF"></a>MUST include explicit migration notes and conformance fixture updates.

## 8. Rollout and Mixed-Version Policy

1. Deployments SHOULD upgrade consumers before enabling new producer features.
2. Mixed-version tests <a id="REQ-PROTOCOL-VERSION-NEGOTIATION-V1-B02655298A"></a>MUST include:
- old producer -> new consumer,
- new producer -> old consumer (expected degrade/failure behavior documented).
3. Producers <a id="REQ-PROTOCOL-VERSION-NEGOTIATION-V1-6C231376FE"></a>MUST gate feature enablement on successful startup handshake and transport setup.
4. On negotiation failure, bridge startup <a id="REQ-PROTOCOL-VERSION-NEGOTIATION-V1-BCFBC44652"></a>MUST fail closed with explicit diagnostics.

## 9. Security and Capability Requirements

1. Capability bits <a id="REQ-PROTOCOL-VERSION-NEGOTIATION-V1-BA5A64133C"></a>MUST be treated as authoritative host contract, not hints.
2. Unsupported transport identifiers <a id="REQ-PROTOCOL-VERSION-NEGOTIATION-V1-5CBB698B8E"></a>MUST be rejected before runtime traffic begins.
3. Version mismatch handling <a id="REQ-PROTOCOL-VERSION-NEGOTIATION-V1-9E87000710"></a>MUST avoid silent fallback to ambiguous semantics.
4. Implementations <a id="REQ-PROTOCOL-VERSION-NEGOTIATION-V1-AFBEBBA252"></a>MUST keep negotiation decisions immutable for a process lifetime unless a full restart occurs.

## 10. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `protocol-negotiation.abi-unsupported` | `KERNEL_OP_CAPS` reports unknown ABI major. | No | Use compatible kernel/runtime pair. |
| `protocol-negotiation.pending-unsupported` | Pending flags requested when capability bit0 is unavailable. | Conditional | Disable pending flags and retry poll path. |
| `protocol-negotiation.transport-unsupported` | Unsupported transport ID configured. | No | Configure supported transport (`sab_ring_v1`) or disable lane. |
| `protocol-negotiation.envelope-version-unsupported` | Runtime envelope version mismatch. | No | Send supported envelope major. |
| `protocol-negotiation.ui-tree-version-unsupported` | UI tree magic/version mismatch. | No | Send supported tree format. |
| `protocol-negotiation.ui-tree-composite-unsupported` | Composite values used without capability bit1. | No | Negotiate capability bit1 or emit scalar-only properties. |
| `protocol-negotiation.ui-tree-delta-unsupported` | Delta payload used without capability bit2. | No | Negotiate capability bit2 or emit full-tree payloads. |
| `protocol-negotiation.ui-events-version-unsupported` | UI event magic/version mismatch. | No | Send supported event format. |
| `protocol-negotiation.command-frame-version-unsupported` | Runtime command frame version mismatch. | No | Send supported frame version. |
| `protocol-negotiation.kind-unsupported-strict` | Unknown runtime kind in strict mode. | Conditional | Use supported kind or non-strict extension lane. |

## 11. Observability Requirements

Implementations SHOULD emit startup negotiation telemetry with:

1. `abi_version`
2. `capability_bits`
3. `runtime_envelope_version`
4. `ui_tree_version`
5. `ui_events_version`
6. `command_frame_version`
7. `command_transport`
8. `event_transport`
9. `result`
10. `error_code` (when failed)

Field names <a id="REQ-PROTOCOL-VERSION-NEGOTIATION-V1-2574133877"></a>MUST remain stable across `v1.x`.

## 12. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/phase-5-runtime-bridge.test.mjs`
2. `web-ui/tests/bridge-codec.test.mjs`
3. `web-ui/tests/bridge-microkernel.test.mjs`
4. `web-ui/tests/phase-5-runtime-command-roundtrip.test.mjs`
5. `scripts/wasm/tests/runtime-command-smoke.mjs`

Pass criteria:

1. Handshake-derived behavior (pending flags, version checks) is deterministic.
2. Unsupported versions/transports fail with explicit stable outcomes.
3. Mixed strict/non-strict runtime kind handling matches this contract.

## 13. Conformance

An implementation is conformant only if Sections 2-12 are satisfied.
