# Runtime Bridge Protocol (Phase 5)

## Purpose
Define the runtime to UI message envelope used for CL integration. Transport is JSON messages over `postMessage` or websocket. Payloads are structured JSON that reference the existing output recording, presentation taxonomy, and typed command models.

## Envelope
All runtime messages use the same envelope.

Fields:
- `version` integer, protocol version. Current value: 1.
- `kind` string, namespaced event type.
- `jobId` string or null, identifies the evaluation job.
- `streamId` string or null, identifies output stream or logical channel.
- `requestId` string or null, correlates command requests with responses.
- `seq` integer, monotonically increasing per stream.
- `ts` number, timestamp in milliseconds since epoch.
- `payload` JSON value, event specific payload.
- `error` object or null, structured error metadata.

## Kinds
The base kinds used in Phase 5:
- `runtime.output` for output recording entries and anchors.
- `command.invoke` for typed command invocations sent to runtime.
- `command.result` for typed command results.
- `command.error` for typed command failures.
- `debugger.snapshot` for full debugger condition and restart snapshots.
- `debugger.restart` for targeted restart updates (`set` and `invoked`).
- `inspector.update` for inspector data and place edit results.
- `job.update` for background job lifecycle events.
- `runtime.log` for low level runtime diagnostics.

## Error Object
`error` is an object with:
- `code` string or null.
- `message` string.
- `details` object or null.

## Example: Output Recording Entry
```json
{
  "version": 1,
  "kind": "runtime.output",
  "jobId": "job-17",
  "streamId": "repl",
  "requestId": null,
  "seq": 112,
  "ts": 1738992000000,
  "payload": {
    "recording": { "id": "rec-17", "jobId": "job-17", "status": "ok", "streamId": "repl" },
    "entry": { "id": "ent-440", "recordingId": "rec-17", "kind": "text", "text": "=> 42" },
    "anchor": { "id": "anc-1", "entryId": "ent-440", "range": { "start": 3, "end": 5 }, "path": [] }
  },
  "error": null
}
```

## Example: Typed Command Result
```json
{
  "version": 1,
  "kind": "command.result",
  "jobId": "job-18",
  "streamId": "repl",
  "requestId": "cmd-222",
  "seq": 200,
  "ts": 1738992001000,
  "payload": {
    "invocationId": "inv-222",
    "result": { "presentationId": "pres-9", "valueSummary": "(list 1 2 3)" }
  },
  "error": null
}
```

## Example: Typed Command Invoke
```json
{
  "version": 1,
  "kind": "command.invoke",
  "jobId": "job-18",
  "streamId": "commands",
  "requestId": "req-inv-222",
  "seq": 199,
  "ts": 1738992000950,
  "payload": {
    "invocation": {
      "id": "inv-222",
      "commandId": "runtime.eval.form",
      "args": { "form": "(+ 1 2)" },
      "defaults": {},
      "source": "palette",
      "ts": 1738992000900
    },
    "context": {
      "package": "CL-USER"
    }
  },
  "error": null
}
```

## Example: Debugger Snapshot
```json
{
  "version": 1,
  "kind": "debugger.snapshot",
  "jobId": "job-19",
  "streamId": "debugger",
  "requestId": null,
  "seq": 12,
  "ts": 1738992002000,
  "payload": {
    "errorId": "err-77",
    "condition": {
      "id": "err-77",
      "kind": "error",
      "message": "Division by zero",
      "summary": "Attempted (/ 1 0)",
      "sections": [
        { "id": "sec-what", "title": "What happened", "text": "Cannot divide by zero." }
      ]
    },
    "frames": [
      {
        "frameId": "frm-1",
        "label": "FOO",
        "function": "FOO",
        "location": { "file": "src/foo.lisp", "line": 42, "column": 7 },
        "locals": [{ "bindingId": "bind-1", "name": "X", "valueSummary": "0", "presentationId": "pres-bind-1" }]
      }
    ],
    "restarts": [
      {
        "id": "rst-1",
        "title": "Use value",
        "description": "Provide a replacement denominator.",
        "safety": "safe",
        "argSchema": [{ "name": "value", "type": "number", "required": true }],
        "preview": { "text": "Will retry with provided denominator." },
        "recommended": true,
        "recommendedReason": "Most likely successful recovery path."
      }
    ],
    "selectedFrameId": "frm-1"
  },
  "error": null
}
```

## Example: Restart List Update
```json
{
  "version": 1,
  "kind": "debugger.restart",
  "jobId": "job-19",
  "streamId": "debugger",
  "requestId": null,
  "seq": 12,
  "ts": 1738992002000,
  "payload": {
    "type": "set",
    "errorId": "err-77",
    "restarts": [
      { "id": "rst-1", "title": "Retry", "description": "Retry compilation", "safety": "safe", "argSchema": [] },
      { "id": "rst-2", "title": "Abort", "description": "Return to REPL", "safety": "safe", "argSchema": [] }
    ]
  },
  "error": null
}
```

## Example: Inspector Update
```json
{
  "version": 1,
  "kind": "inspector.update",
  "jobId": "job-19",
  "streamId": "inspector",
  "requestId": "insp-3",
  "seq": 4,
  "ts": 1738992002500,
  "payload": {
    "targetId": "pres-9",
    "view": { "type": "clos-object", "slots": [{ "name": "x", "value": 3 }] }
  },
  "error": null
}
```

## Example: Job Update
```json
{
  "version": 1,
  "kind": "job.update",
  "jobId": "job-20",
  "streamId": "jobs",
  "requestId": null,
  "seq": 1,
  "ts": 1738992003000,
  "payload": {
    "status": "started",
    "label": "Compile project",
    "progress": { "current": 5, "total": 100 }
  },
  "error": null
}
```

## Notes
- `seq` is monotonically increasing per `streamId`.
- `ts` is generated by the runtime at emission time.
- Payloads are validated on receipt and rejected if the envelope is invalid.
- Canonical transport is JSON.
- WASM command ingestion may use a binary command frame adapter (`KERNEL_OP_RUNTIME_COMMAND_POLL`) while preserving canonical JSON envelope semantics at UI boundaries.
- `command.invoke`, `command.result`, and `command.error` must carry `requestId` for correlation.
- `debugger.snapshot` requires `errorId`; each restart entry requires `id`, `title`, `safety`, and `argSchema` (empty array allowed).
- `debugger.restart` requires `payload.type` (`set` or `invoked`) and `errorId`.

## Kernel Integration
For WASM runners, structured runtime messages are sent via `KERNEL_OP_RUNTIME_EVENT`
as UTF-8 JSON bytes. See `doc/wasm/kernel-request-abi.md` for payload details.
