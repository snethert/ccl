# Persistence Storage Backend Matrix v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Backend guarantees, limitations, and fallback policy for persistence storage  
Depends on: `web-ui/spec/persistence-ref-update-protocol-v1.md`, `web-ui/spec/persistence-lease-protocol-v1.md`, `web-ui/spec/persistence-sync-and-conflict-protocol-v1.md`, `web-ui/spec/persistence-purpose-and-user-contract-v1.md`, `web-ui/spec/persistence-envelope-schema-v1.json`

## 1. Purpose

This matrix defines which backends are supported, what guarantees each backend provides, and how fallback is selected.

## 2. Backend Roles

Storage MUST be split into:

1. Object store (immutable content objects).
2. Metadata store (refs, leases, sync markers, optional journals).

Backends MAY co-locate both roles if invariants are preserved.

### 2.1 Canonical Encoding Constraints

Canonical object encoding MUST be deterministic across platforms and map-order independent.

Canonical encoding MUST include deterministic symbol encoding rules:

1. package identity encoding,
2. case/escape normalization,
3. readtable-case policy identifier in graph/document metadata.

Persisted objects/records MUST validate against `web-ui/spec/persistence-envelope-schema-v1.json` before protected refs are advanced.

## 3. Canonical Backend Matrix

| Backend | Role | Durability | Multi-record metadata atomicity | Streaming support | Notes |
|---|---|---|---|---|---|
| `memory-snapshot` | object + metadata (test/dev lane) | process-lifetime only | n/a | no | default unattended lane for sandbox-safe workflows |
| `indexeddb` | object + metadata (browser local) | durable browser local storage | yes (per transaction scope) | chunked blob via app layer | primary browser persistent lane |
| `opfs+idb` (optional) | object in OPFS, metadata in IDB | durable local storage | yes for metadata; object staging policy required | yes | use when large object streaming pressure requires file-backed chunks |
| `kernel_request-file` (integration lane) | host-mediated object/metadata operations | host-defined | host-defined | yes | for runtime/microkernel persistence integration paths |

## 4. Backend Selection and Fallback

Implementations MUST define a deterministic backend policy order.

Recommended order:

1. `indexeddb`
2. `opfs+idb` (when enabled and supported)
3. `memory-snapshot` (degraded mode)

Rules:

1. Fallback transitions MUST be explicit and observable.
2. Degraded fallback MUST NOT claim durable persistence.
3. Existing durable data MUST NOT be silently discarded on fallback.

## 5. IndexedDB Requirements

For IDB-backed persistence:

1. Object writes MUST occur in a single IndexedDB transaction spanning all immutable-write stores (`objects` + `chunks` when used).
   If platform limits require split writes, implementation MUST stage via immutable chunk-manifest object (for example `ChunkList`) and MUST advance refs only after complete closure durability.
2. Ref/lease updates MUST use metadata transaction boundaries.
3. Multi-ref updates MUST execute in one metadata transaction.
4. Large objects SHOULD use chunking strategy with complete-closure validation.
5. Read failures MUST be distinguishable from "not found" at protocol surface.
6. Envelope validation failures MUST be explicit and MUST block protected ref advancement.

## 6. OPFS + IDB Requirements (Optional)

If OPFS is used:

1. Object chunk manifests MUST be immutable and content-addressed.
2. Refs MUST advance only after complete chunk closure is durable.
3. Partial file writes MUST never appear as committed object ids.
4. Metadata authority remains in IDB or equivalent transactional store.

## 7. Memory Backend Requirements

Memory backend MAY be used for:

1. tests
2. sandbox-safe unattended execution
3. explicit degraded mode

Memory backend MUST:

1. be labeled non-durable,
2. avoid claiming crash recovery across process restart,
3. preserve deterministic behavior within process lifetime.

## 8. Error and Pressure Behavior

Backends MUST emit stable error categories:

1. `ERR_BACKEND_UNAVAILABLE`
2. `ERR_BACKEND_DEGRADED`
3. `ERR_OBJECT_WRITE_FAILED`
4. `ERR_METADATA_WRITE_FAILED`
5. `ERR_QUOTA_EXCEEDED`
6. `ERR_READ_INTEGRITY_FAILED`

Pressure policy MUST follow:

1. stop autosave,
2. evict derived artifacts,
3. block user save only as last resort with export/recovery path.

## 9. Security and Capability Notes

1. Backends requiring secure context capabilities MUST fail explicitly when unavailable.
2. Capability loss MUST never be interpreted as successful persistence.
3. Backend switches across capability boundaries MUST be auditable.

## 10. Observability

Backends MUST report:

1. active backend id,
2. durability class (`durable`, `degraded`, `ephemeral`),
3. fallback cause,
4. transaction failure counts,
5. quota pressure signals.

## 11. Conformance

An implementation is conformant only if:

1. Backend guarantees in this matrix match runtime behavior.
2. Ref-update invariants are preserved across all enabled backends.
3. Degraded modes are explicit and non-destructive.
4. Fallback order is deterministic and documented.
