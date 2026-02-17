# Persistence Semantic Profile Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Profile model for file-primary vs semantic-canonical persistence behavior  
Depends on: `web-ui/spec/persistence-purpose-and-user-contract-v1.md`, `web-ui/spec/persistence-ref-update-protocol-v1.md`, `web-ui/spec/persistence-sync-and-conflict-protocol-v1.md`
Compatibility: `v1.x` preserves normative requirements and failure semantics; incompatible changes require `v2`.

## 1. Purpose

This contract defines explicit persistence profiles so file-primacy and semantic-canonical workflows do not conflict implicitly.

### 1.1 In Scope

1. Local-first, team-capable persistence for browser-hosted Common Lisp workflows.
2. Deterministic ref/lease safety and explicit conflict workflows.
3. Controlled-reader profile requirements that forbid or normalize non-deterministic reader behavior:
   `#.` read-time evaluation is forbidden by default, and package/readtable behavior is deterministic by policy.

## 2. Profile Model

An implementation <a id="REQ-PERSISTENCE-SEMANTIC-PROFILE-V1-B06B0E6117"></a>MUST expose a profile identifier in workspace metadata.

Primary invariants:

1. After crash recovery, every ref resolves to one complete commit state.
2. Canonical semantic state MAY be represented as `FormGraph`, but projection-to-FormGraph round-tripping <a id="REQ-PERSISTENCE-SEMANTIC-PROFILE-V1-C3F44A2C56"></a>MUST preserve user intent under configured reader/projection policy.
3. Merge candidates <a id="REQ-PERSISTENCE-SEMANTIC-PROFILE-V1-EF1EB29192"></a>MUST be intrinsically marked unfinalized in commit metadata; ref naming alone is insufficient.

Supported profiles:

1. `file-primacy-v1` (default, required)
2. `semantic-canonical-v1` (optional)

## 3. File-Primacy Profile (Default)

In `file-primacy-v1`:

1. Authoritative persisted content is file/blob rooted.
2. Semantic structures are derived/index data.
3. Merge uses file-level baseline with optional semantic assist.
4. User-visible workflow remains path/file primary.

This profile <a id="REQ-PERSISTENCE-SEMANTIC-PROFILE-V1-73C106FAC7"></a>MUST remain the default unless explicitly changed by policy/user action.

## 4. Semantic-Canonical Profile (Optional)

In `semantic-canonical-v1`:

1. Authoritative persisted representation for Lisp docs is semantic graph model.
2. Text files are projection views over semantic representation.
3. Merge semantics are graph-structural first, text fallback second.
4. Non-Lisp docs may remain blob-canonical.

This profile <a id="REQ-PERSISTENCE-SEMANTIC-PROFILE-V1-CC8CCBA15A"></a>MUST be opt-in and explicit.

## 5. Activation and Migration Rules

Profile changes <a id="REQ-PERSISTENCE-SEMANTIC-PROFILE-V1-5F624B5B43"></a>MUST obey:

1. No silent profile transitions.
2. Explicit compatibility check before transition.
3. A migration record linked to transition event.
4. Ability to abort transition without advancing protected refs.

When switching to `semantic-canonical-v1`, implementation SHOULD support reversible export/projection to file-primary interchange.

## 6. Sync and Compatibility

Mixed-profile collaborators <a id="REQ-PERSISTENCE-SEMANTIC-PROFILE-V1-4A53D7D099"></a>MUST be treated as compatibility-sensitive.

Required rules:

1. Profile id <a id="REQ-PERSISTENCE-SEMANTIC-PROFILE-V1-F0EEA0DE12"></a>MUST be included in sync metadata handshake.
2. If remote profile is incompatible, sync <a id="REQ-PERSISTENCE-SEMANTIC-PROFILE-V1-C8081EEB49"></a>MUST fail with explicit compatibility error or negotiate downgraded behavior.
3. `workspace/main` <a id="REQ-PERSISTENCE-SEMANTIC-PROFILE-V1-3EC1D2C9A0"></a>MUST NOT auto-advance across incompatible profile boundaries.

## 7. Guardrails

Regardless of profile:

1. Ref/lease safety rules remain mandatory.
2. Background workers <a id="REQ-PERSISTENCE-SEMANTIC-PROFILE-V1-C43494C6BD"></a>MUST NOT silently advance `workspace/main`.
3. Conflict states <a id="REQ-PERSISTENCE-SEMANTIC-PROFILE-V1-E786228C73"></a>MUST remain explicit and auditable.

## 8. Error Codes

Implementations <a id="REQ-PERSISTENCE-SEMANTIC-PROFILE-V1-EF4AD4FCBF"></a>MUST expose:

1. `ERR_PROFILE_UNSUPPORTED`
2. `ERR_PROFILE_INCOMPATIBLE`
3. `ERR_PROFILE_TRANSITION_REQUIRES_EXPLICIT_ACCEPT`
4. `ERR_PROFILE_TRANSITION_ABORTED`

## 9. Observability

Profile operations <a id="REQ-PERSISTENCE-SEMANTIC-PROFILE-V1-1A2932CAE6"></a>MUST emit:

1. `workspace_id`
2. `from_profile`
3. `to_profile`
4. `result`
5. `compatibility_mode`
6. `error_code` (if failed)

## 10. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `persistence-semantic-profile.unsupported` | Requested profile is not supported by the running build. | No | Use a supported profile or upgrade the runtime. |
| `persistence-semantic-profile.incompatible` | Remote or target profile is incompatible with local workspace profile. | No | Negotiate compatible mode or reject sync/migration. |
| `persistence-semantic-profile.transition-aborted` | Profile transition was aborted before protected refs were advanced. | No | Inspect abort reason and retry transition after resolving preconditions. |
| `persistence-semantic-profile.silent-transition-blocked` | Implicit profile transition was detected and blocked by policy. | No | Request explicit user/policy approval before changing profile. |

## 11. Conformance

An implementation is conformant only if:

1. `file-primacy-v1` is supported and default.
2. `semantic-canonical-v1` is never activated implicitly.
3. Profile transitions are explicit, auditable, and non-destructive.
4. Sync safety gates prevent silent incompatible advancement.
