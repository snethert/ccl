# Bridge Envelope

## Status
⏸️ Not started

## Purpose

Message framing for all communication between the Lisp runtime and the
JavaScript UI layer. Every runtime↔UI message is wrapped in a canonical
envelope with version, kind, sequence number, timestamp, payload, and
error lane. Normalization is deterministic and locale-independent.

## Depends On
None.

## Interface

```
Envelope {
  version:   1                          // always 1
  kind:      string                     // non-empty, one of 9 canonical kinds
  jobId:     string | null
  streamId:  string | null
  requestId: string | null
  seq:       non-negative integer       // monotonic per streamId
  ts:        finite non-negative number // milliseconds
  payload:   any JSON value | null
  error:     ErrorObject | null
}

ErrorObject {
  code:    string | null                // non-empty when present
  message: string                       // fallback: "Unknown error"
  details: object | null
}
```

**Canonical kind values:**
`runtime.output`, `command.invoke`, `command.result`, `command.error`,
`debugger.snapshot`, `debugger.restart`, `inspector.update`, `job.update`,
`runtime.log`

**Transport binding:** `KERNEL_OP_RUNTIME_EVENT` payload accepts UTF-8 JSON
envelope bytes. Stream writes synthesize `runtime.output` envelopes.

## Invariants

1. Envelope version field MUST be 1
2. Empty string fields (jobId, streamId, requestId) normalize to null
3. Non-string/non-object error input normalizes to `{code: null, message: "Unknown error", details: null}`
4. Normalization is deterministic: identical input + strictness → identical output
5. Sequence numbers are monotonically increasing per streamId
6. All envelope fields are present after normalization (no missing keys)

## Behavior

1. When `strictKinds=true`, unknown kind values are rejected with an error
2. When `strictKinds=false` (default), unknown kind values are preserved exactly
3. Validation MUST occur before reducer/state application
4. `seq` monotonicity is enforced for microkernel-generated messages
5. Timestamp (`ts`) is finite and non-negative; invalid values are rejected

## Anti-Patterns

1. Never execute arbitrary code during envelope decode/normalize
2. Never skip validation before state application
3. Never allow validation outcome to depend on host locale
4. Never trust envelope inputs from runtime/transport without validation
5. Never silently drop malformed envelopes (must error)

## Out of Scope

- Envelope routing logic (see [command-system](command-system.md))
- Payload interpretation (varies by kind)
- Transport implementation details beyond the kernel_request binding

## Conformance Check
Run: `node spec/web-ui/checks/bridge-envelope.test.mjs`
