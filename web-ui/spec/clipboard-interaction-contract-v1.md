# Clipboard Interaction Contract v1

Status: Draft  
Version: 1.1.0  
Last updated: 2026-02-17  
Scope: Clipboard copy/cut/paste behavior, sanitization, and backend parity for `web-ui`  
Depends on: `web-ui/spec/command-schema-v1.json`, `web-ui/spec/text-editing-contract-v1.md`, `web-ui/spec/security-and-capability-model-v1.md`  
Compatibility: `v1.x` preserves clipboard command IDs, sanitization defaults, fallback semantics, and clipboard-history ring behavior; incompatible behavior changes require `v2`.

## 1. Purpose

This contract defines canonical clipboard behavior for editor and non-editor surfaces.

## 2. Command Surface

Required command IDs:

1. `ui.clipboard.copy`
2. `ui.clipboard.cut`
3. `ui.clipboard.paste`
4. `ui.clipboard.paste.plain`
5. `ui.clipboard.history.open`
6. `ui.clipboard.history.paste`

These commands <a id="REQ-CLIPBOARD-INTERACTION-CONTRACT-V1-A9CBACC6D4"></a>MUST route through typed command execution and capability/security checks.

## 3. Clipboard Data Model

Paste/read priority order:

1. `text/plain` (required)
2. `text/html` (optional, sanitized)
3. custom app MIME lanes (optional)

Rules:

1. `text/plain` <a id="REQ-CLIPBOARD-INTERACTION-CONTRACT-V1-D3939445C8"></a>MUST always be supported.
2. Rich payload ingestion <a id="REQ-CLIPBOARD-INTERACTION-CONTRACT-V1-4793766D43"></a>MUST pass sanitization policy before insertion.
3. Unknown MIME types <a id="REQ-CLIPBOARD-INTERACTION-CONTRACT-V1-3E6997F683"></a>MUST NOT be executed or interpreted as scriptable content.

## 4. Sanitization Policy

Default policy:

1. Remove scripts and event-handler attributes from rich HTML payloads.
2. Normalize line endings to `\n`.
3. Apply max payload size limits with stable truncation/reject rules.

Sanitization outcome <a id="REQ-CLIPBOARD-INTERACTION-CONTRACT-V1-75F9465FF3"></a>MUST be deterministic for fixed input bytes and policy version.

## 5. Clipboard History Model

Multi-item clipboard history is first-class in `v1.1+`.

State shape:

1. `history[]` entries with `historyId`, `capturedAtSeq`, `mimeSummary`, and normalized payload lanes.
2. `historyLimit` default `24` entries.
3. `historyEnabled` default `true` for editor-capable surfaces.

Rules:

1. Successful `copy` and `cut` operations <a id="REQ-CLIPBOARD-INTERACTION-CONTRACT-V1-765112F04D"></a>MUST append a normalized history entry.
2. History append <a id="REQ-CLIPBOARD-INTERACTION-CONTRACT-V1-7FC06E0FC1"></a>MUST deduplicate adjacent equivalent payloads by content hash.
3. History overflow <a id="REQ-CLIPBOARD-INTERACTION-CONTRACT-V1-202E415B06"></a>MUST evict oldest entries first.
4. `ui.clipboard.history.paste` <a id="REQ-CLIPBOARD-INTERACTION-CONTRACT-V1-7B3FCA3FDE"></a>MUST paste a selected history entry without mutating the selected payload.
5. History persistence is policy-bound; default behavior SHOULD keep history in memory-only session scope unless explicit persistence policy is enabled.

## 6. Backend Parity

DOM, Canvas, and WebGL lanes <a id="REQ-CLIPBOARD-INTERACTION-CONTRACT-V1-47D572DAF7"></a>MUST provide equivalent command-level behavior and user-visible failure messaging.

## 7. Permission and Async Behavior

1. Clipboard read/write may require asynchronous browser permissions.
2. Permission denial <a id="REQ-CLIPBOARD-INTERACTION-CONTRACT-V1-3D3796C594"></a>MUST produce typed command error and non-crashing UX state.
3. Failed async clipboard access MAY fall back to selection-buffer copy when available.

## 8. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `clipboard.permission-denied` | Browser denied clipboard access. | Conditional | Request permission or use fallback lane. |
| `clipboard.payload-unsupported` | Clipboard content type unsupported by target. | No | Use supported paste mode. |
| `clipboard.payload-rejected` | Payload rejected by sanitization or size policy. | Conditional | Use plain paste or reduce payload size. |
| `clipboard.target-readonly` | Cut/paste requested for readonly target. | No | Disable command for readonly scopes. |
| `clipboard.history-empty` | Clipboard history requested but no entries exist. | No | Disable history paste affordance until entries are captured. |
| `clipboard.history-entry-missing` | Requested clipboard history entry does not exist. | Conditional | Refresh history UI and retry with valid entry. |
| `clipboard.history-disabled` | Clipboard history command used while history policy is disabled. | No | Enable history policy or use direct paste commands. |

## 9. Conformance

An implementation is conformant only if Sections 2-8 are satisfied.
