# Runtime Bridge Envelope v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Canonical runtime message envelope between WASM runtime, microkernel, and `web-ui` runtime consumers  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/glossary-v1.md`, `web-ui/src/runtime-bridge.mjs`, `web-ui/bridge/runtime.mjs`, `scripts/wasm/lib/microkernel.mjs`, `doc/wasm/kernel-request-abi.md`  
Compatibility: `v1.x` preserves envelope field names, required lanes, and strict-kind behavior; incompatible envelope or validation changes require `v2`.

## 1. Purpose

This contract defines the runtime bridge message envelope used for host-runtime and UI-runtime integration.
It is normative for envelope shape, normalization, validation, and failure behavior.

## 2. Canonical Envelope Shape

All runtime bridge messages <a id="REQ-RUNTIME-BRIDGE-ENVELOPE-V1-51EAFB0D36"></a>MUST normalize to this object shape:

| Field | Type | Required | Rules |
|---|---|---|---|
| `version` | integer | Yes | <a id="REQ-RUNTIME-BRIDGE-ENVELOPE-V1-2E4C72B408"></a>MUST be `1` for `v1`. |
| `kind` | string | Yes | Non-empty. See Section 3. |
| `jobId` | string or `null` | Yes | Empty string normalizes to `null`. |
| `streamId` | string or `null` | Yes | Empty string normalizes to `null`. |
| `requestId` | string or `null` | Yes | Empty string normalizes to `null`. |
| `seq` | integer | Yes | Non-negative integer. |
| `ts` | number | Yes | Finite non-negative number (milliseconds lane). |
| `payload` | any JSON value or `null` | Yes | If absent, normalizes to `null`. |
| `error` | object or `null` | Yes | Normalized per Section 2.1. |

## 2.1 Error Lane Normalization

`error` normalization <a id="REQ-RUNTIME-BRIDGE-ENVELOPE-V1-394DF4EEDC"></a>MUST follow these rules:

1. `null`/missing error input normalizes to `null`.
2. String error input normalizes to `{ code: null, message: <string>, details: null }`.
3. Object error input normalizes to:
- `code`: non-empty string or `null`.
- `message`: non-empty string or fallback `"Unknown error"`.
- `details`: plain object copy or `null`.
4. Non-string/non-object error input normalizes to `{ code: null, message: "Unknown error", details: null }`.

## 3. Runtime Kind Registry (`v1`)

When strict kind validation is enabled, `kind` <a id="REQ-RUNTIME-BRIDGE-ENVELOPE-V1-5D2B9E2BDE"></a>MUST be one of:

1. `runtime.output`
2. `command.invoke`
3. `command.result`
4. `command.error`
5. `debugger.snapshot`
6. `debugger.restart`
7. `inspector.update`
8. `job.update`
9. `runtime.log`

Non-strict mode MAY accept unknown non-empty `kind` values for extension lanes.

## 4. Validation and Strictness

Envelope validation <a id="REQ-RUNTIME-BRIDGE-ENVELOPE-V1-D3AC637505"></a>MUST enforce:

1. Input is an object.
2. `version` equals `1`.
3. `kind` is present and non-empty.
4. `seq` is a non-negative integer.
5. `ts` is a finite non-negative number.

Strict-kind behavior:

1. `strictKinds=false` (default): unknown `kind` values are accepted.
2. `strictKinds=true`: unknown `kind` values <a id="REQ-RUNTIME-BRIDGE-ENVELOPE-V1-F02012D666"></a>MUST fail validation.

## 5. Transport Binding

Runtime envelope bytes on wire are UTF-8 JSON encoded envelope objects.

Bindings:

1. `KERNEL_OP_RUNTIME_EVENT` payload accepts runtime envelope JSON bytes.
2. Runtime event egress over `sab_ring_v1` uses one JSON envelope frame per ring frame.
3. Stream writes (`KERNEL_OP_STREAM_WRITE`, stdout/stderr lanes) <a id="REQ-RUNTIME-BRIDGE-ENVELOPE-V1-F2A38C5AA9"></a>MUST synthesize `runtime.output` envelopes for recording integration.

Implementation note (`v1`):

1. Runtime event ingress may decode specific diagnostic binary payloads and convert them into envelopes (`wasm.fasload.trace.v1`, `wasm.fasload.trace.v2`, `wasm.toplfunc.write.v1`) before emit.

## 6. Determinism Rules

1. For microkernel-generated messages, `seq` <a id="REQ-RUNTIME-BRIDGE-ENVELOPE-V1-AA53F7761A"></a>MUST increase monotonically per `streamId`.
2. Given identical envelope input and strictness option, normalization result <a id="REQ-RUNTIME-BRIDGE-ENVELOPE-V1-0AC30C2AD7"></a>MUST be identical.
3. Envelope validation outcome <a id="REQ-RUNTIME-BRIDGE-ENVELOPE-V1-EA5DF8F11C"></a>MUST not depend on host locale or wall-clock formatting.
4. Unknown non-strict kinds <a id="REQ-RUNTIME-BRIDGE-ENVELOPE-V1-B1FCA71855"></a>MUST preserve original `kind` string exactly.

## 7. Security and Capability Requirements

1. Envelope inputs from runtime or transport <a id="REQ-RUNTIME-BRIDGE-ENVELOPE-V1-496E5E3A82"></a>MUST be treated as untrusted.
2. Callers <a id="REQ-RUNTIME-BRIDGE-ENVELOPE-V1-8AAAC1E976"></a>MUST validate envelope shape before reducer/state application.
3. Consumers <a id="REQ-RUNTIME-BRIDGE-ENVELOPE-V1-F5AB1D6F53"></a>MUST gate command/restart/eval actions via existing capability checks in command execution lanes.
4. Implementations <a id="REQ-RUNTIME-BRIDGE-ENVELOPE-V1-D4C3CDDBB6"></a>MUST NOT execute arbitrary code during envelope decode/normalize.

## 8. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `runtime-envelope.invalid-json` | Envelope payload was not valid JSON text. | No | Emit valid JSON envelope bytes. |
| `runtime-envelope.message-not-object` | Decoded payload is not an object. | No | Send object payload. |
| `runtime-envelope.version-unsupported` | `version` is absent/unsupported for this major. | No | Downgrade/upgrade producer to supported major. |
| `runtime-envelope.kind-required` | `kind` is missing or empty. | No | Provide non-empty kind. |
| `runtime-envelope.kind-unsupported` | Kind rejected by strict mode. | Conditional | Use supported kind or disable strict mode for extension lanes. |
| `runtime-envelope.seq-invalid` | `seq` is missing, negative, or non-integer. | No | Emit non-negative integer sequence. |
| `runtime-envelope.ts-invalid` | `ts` is missing, negative, non-finite, or non-number. | No | Emit finite non-negative timestamp. |
| `runtime-envelope.emit-unavailable` | No runtime emit transport/callback was configured. | No | Configure runtime bridge emit lane before dispatch. |
| `runtime-envelope.emit-backpressure` | SAB runtime-event transport rejected enqueue (ring full). | Yes | Back off and retry dispatch. |
| `runtime-envelope.emit-failed` | Emit callback failed at runtime. | Conditional | Correct callback error or fall back to a supported transport. |

## 9. Observability Requirements

Implementations SHOULD emit structured telemetry per envelope apply/emit with:

1. `kind`
2. `jobId`
3. `streamId`
4. `requestId`
5. `seq`
6. `ts`
7. `transport`
8. `result` (`accepted|rejected|dropped`)
9. `error_code` (when rejected/dropped)

Field names <a id="REQ-RUNTIME-BRIDGE-ENVELOPE-V1-3CE0078D6A"></a>MUST remain stable across `v1.x`.

## 10. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/phase-5-runtime-bridge.test.mjs`
2. `web-ui/tests/phase-5-runtime-output.test.mjs`
3. `web-ui/tests/phase-5-runtime-command-dispatch.test.mjs`
4. `web-ui/tests/phase-5-runtime-command-roundtrip.test.mjs`

Pass criteria:

1. Envelope normalization and strict-kind validation behave as specified.
2. JSON encode/decode round-trip preserves normalized envelope semantics.
3. Runtime output synthesis and runtime event ingestion produce valid envelopes.

## 11. Conformance

An implementation is conformant only if Sections 2-10 are satisfied.
