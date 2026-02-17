# Persistence Remote Wire Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Exact remote API contract for persistence object/ref/lease synchronization  
Depends on: `web-ui/spec/persistence-envelope-schema-v1.json`, `web-ui/spec/persistence-ref-update-protocol-v1.md`, `web-ui/spec/persistence-lease-protocol-v1.md`, `web-ui/spec/persistence-sync-and-conflict-protocol-v1.md`
Compatibility: `v1.x` preserves normative requirements and failure semantics; incompatible changes require `v2`.

## 1. Purpose

This contract defines the concrete wire surface for persistence remotes so independent implementations can interoperate without ambiguity.

The wire contract <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-5A82661BE3"></a>MUST guarantee:

1. Deterministic request/response formats.
2. Stable error codes and retry semantics.
3. Idempotent immutable object upload.
4. CAS semantics for mutable refs.
5. Explicit compatibility negotiation.

## 2. Transport and Versioning

Required transport profile:

1. Base path <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-951193896F"></a>MUST be `/api/persistence/v1`.
2. Networked deployments <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-A8A75BA72B"></a>MUST use HTTPS.
3. Request and response bodies <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-B7C251A592"></a>MUST use UTF-8 JSON.
4. Protocol version is `1.0.0`.
5. Clients <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-5554AF3608"></a>MUST send `protocol_version` in every request body.
6. Server <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-CF7B2AA77D"></a>MUST reject unknown major versions with `ERR_PROTOCOL_VERSION_UNSUPPORTED`.

## 3. Common Envelope

Every request body <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-6249C5DD25"></a>MUST include:

1. `protocol_version` (string, required, value `1.0.0`)
2. `request_id` (string, required, stable per attempt)

Every response body <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-A745F23370"></a>MUST include:

1. `protocol_version` (string, required)
2. `request_id` (string, required, echoed from request when available)
3. `ok` (boolean, required)
4. `result` (object, required when `ok=true`)
5. `error` (object, required when `ok=false`)

Error object fields:

1. `code` (string, stable error code)
2. `message` (string, human-readable summary)
3. `retryable` (boolean)
4. `details` (object, optional, machine-readable)

## 4. Capabilities Endpoint

Endpoint:

1. `GET /api/persistence/v1/capabilities`

Success response `result` fields:

1. `wire_version` (`1.0.0`)
2. `envelope_versions` (array, includes `1.0.0`)
3. `profiles` (array, for example `file-primacy-v1`, `semantic-canonical-v1`)
4. `capabilities` (object booleans)
5. `limits` (object with numeric caps)

`capabilities` keys:

1. `lease_api`
2. `commit_walk_api`
3. `batch_has_object`

`limits` keys:

1. `max_batch_has_object`
2. `max_commit_walk_depth`
3. `max_object_bytes`

## 5. Object API

### 5.1 Batch Presence Check

Endpoint:

1. `POST /api/persistence/v1/objects/has`

Request payload fields:

1. `object_ids` (array of `object_id`, required, unique)

Success `result` fields:

1. `present` (map `object_id -> boolean`)

### 5.2 Put Object

Endpoint:

1. `PUT /api/persistence/v1/objects/{object_id}`

Request fields:

1. Common envelope fields.
2. `object` (required immutable object envelope conforming to `persistence-envelope-schema-v1.json`)

Rules:

1. Path `object_id` <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-AA035E3764"></a>MUST equal `object.object_id`.
2. Server <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-1B1608A173"></a>MUST validate envelope and content-address consistency.
3. Operation <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-E33453EC69"></a>MUST be idempotent.

Success `result` fields:

1. `object_id`
2. `stored` (boolean; `false` when already present and valid)

### 5.3 Get Object

Endpoint:

1. `GET /api/persistence/v1/objects/{object_id}`

Success `result` fields:

1. `object` (immutable object envelope)

Rules:

1. Returned object <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-DE5438D66F"></a>MUST hash-validate to requested `object_id`.

## 6. Ref API

### 6.1 Read Ref

Endpoint:

1. `POST /api/persistence/v1/refs/read`

Request fields:

1. `ref_name` (required)

Success `result` fields:

1. `ref_name`
2. `exists` (boolean)
3. `commit_id` (nullable)
4. `refgen` (u64)
5. `updated_at` (epoch ms, optional when `exists=false`)
6. `protected_ref` (boolean)

### 6.2 CAS Advance Ref

Endpoint:

1. `POST /api/persistence/v1/refs/cas`

Request fields:

1. `advance` (required `ref_advance_request` envelope conforming to `persistence-envelope-schema-v1.json`)

Rules:

1. CAS semantics <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-05E4E9AA25"></a>MUST compare `advance.expected_refgen` against remote state.
2. On mismatch, server <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-EE85CBD260"></a>MUST return `ERR_REF_CAS_MISMATCH`.
3. For protected refs, server <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-9C2682D4C1"></a>MUST enforce protected-ref guard requirements from envelope schema.
4. Server <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-6863B0FA3F"></a>MUST reject unresolved-conflict/finalization violations for protected refs.

Success `result` fields:

1. `ref_name`
2. `commit_id`
3. `refgen`
4. `previous_commit_id` (nullable)
5. `updated_at`

## 7. Lease API (Optional Capability)

If `capabilities.lease_api=true`, server <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-71D0E582F4"></a>MUST expose:

1. `POST /api/persistence/v1/leases/acquire`
2. `POST /api/persistence/v1/leases/renew`
3. `POST /api/persistence/v1/leases/release`

Acquire request fields:

1. `lease_name`
2. `owner_instance_id`
3. `writer_token`
4. `mode` (`normal | takeover`)
5. `workspace_id` (optional)

Acquire success `result` fields:

1. `lease_id`
2. `epoch`
3. `expires_at`
4. `writer_token`

Renew request fields:

1. `lease_name`
2. `writer_token`
3. `epoch`

Renew success `result` fields:

1. `lease_name`
2. `epoch`
3. `expires_at`
4. `last_heartbeat_at`

Release request fields:

1. `lease_name`
2. `writer_token`
3. `epoch`

Release success `result` fields:

1. `released` (boolean)

## 8. Commit Walk API (Optional Capability)

If `capabilities.commit_walk_api=true`, server <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-63F918F684"></a>MUST expose:

1. `POST /api/persistence/v1/commits/walk`

Request fields:

1. `start_commit_id`
2. `max_depth` (u32, required, bounded by `limits.max_commit_walk_depth`)

Success `result` fields:

1. `nodes` (array of `{commit_id, parents[]}`)
2. `truncated` (boolean)

Use:

1. Enables bounded ancestor checks when remote head ancestry is unknown locally.

## 9. HTTP Status Mapping

Servers <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-2E14F86EAE"></a>MUST map errors consistently:

1. `200` success.
2. `201` created object where preferred.
3. `400` malformed request payload.
4. `401` authentication required.
5. `403` permission denied.
6. `404` missing object/ref/lease.
7. `409` CAS mismatch or lease held conflicts.
8. `412` semantic precondition/guard failure.
9. `422` schema or validation failure.
10. `429` rate limited.
11. `500` internal non-retryable error.
12. `503` temporary service unavailable.

## 10. Stable Error Codes

Servers <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-AAFA68EB9E"></a>MUST emit the following wire-visible codes where applicable:

1. `ERR_PROTOCOL_VERSION_UNSUPPORTED`
2. `ERR_REQUEST_INVALID`
3. `ERR_AUTH_REQUIRED`
4. `ERR_PERMISSION_DENIED`
5. `ERR_OBJECT_NOT_FOUND`
6. `ERR_OBJECT_HASH_MISMATCH`
7. `ERR_OBJECT_ENVELOPE_INVALID`
8. `ERR_OBJECT_TOO_LARGE`
9. `ERR_REF_NOT_FOUND`
10. `ERR_REF_CAS_MISMATCH`
11. `ERR_REF_PROTECTED_GUARD_REQUIRED`
12. `ERR_REF_GUARD_FAILED`
13. `ERR_REF_TARGET_UNREADABLE`
14. `ERR_REF_TARGET_UNFINALIZED`
15. `ERR_REF_TARGET_CONFLICTED`
16. `ERR_LEASE_HELD`
17. `ERR_LEASE_LOST`
18. `ERR_LEASE_REQUIRED`
19. `ERR_LEASE_TAKEOVER_BLOCKED`
20. `ERR_RATE_LIMITED`
21. `ERR_REMOTE_UNAVAILABLE`
22. `ERR_INTERNAL`

## 11. Retry and Idempotency Rules

Client obligations:

1. `PUT /objects/{object_id}` retries are always safe.
2. `POST /refs/cas` retries are safe only with unchanged `expected_refgen`.
3. `POST /leases/renew` retries are safe for same token+epoch pair.
4. Clients SHOULD back off on `429` and `503`.

Server obligations:

1. Object PUT <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-7C60D05A35"></a>MUST be idempotent by content id.
2. CAS failure <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-C2799A591A"></a>MUST never partially apply ref updates.
3. Lease mutations <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-73425949D7"></a>MUST be atomic per lease record.

## 12. Security Requirements

1. Server <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-CCE05497CE"></a>MUST authenticate callers before mutable operations.
2. Server <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-C18257E0C8"></a>MUST authorize ref namespaces independently.
3. Protected refs <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-5CF7816C20"></a>MUST require elevated policy checks.
4. Logs <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-1CC02E3D13"></a>MUST avoid storing raw secrets in clear text.

## 13. Observability Requirements

Each operation <a id="REQ-PERSISTENCE-REMOTE-WIRE-CONTRACT-V1-16D1BAF890"></a>MUST emit structured telemetry with:

1. `request_id`
2. `operation`
3. `ref_name` or `object_id` when applicable
4. `remote_id`
5. `duration_ms`
6. `result`
7. `error_code` (when failed)

## 14. Conformance

A remote implementation is conformant only if:

1. All required endpoints in sections 4-6 are implemented exactly.
2. Payloads and guards validate against `persistence-envelope-schema-v1.json`.
3. Error code/status mapping in sections 9-10 is stable.
4. Idempotency and CAS semantics in section 11 hold under retry and partition tests.
5. Optional endpoints are advertised accurately via capabilities.
