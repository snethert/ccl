# Persistence Purpose and User Contract v1

Status: Draft  
Version: 1.1.0  
Last updated: 2026-02-16  
Scope: User-facing storage contract and rationale for browser-hosted CCL web UI/workspace persistence  
Depends on: `web-ui/DEV-PLAN.md`, `web-ui/FRONT-END-DEV-PLAN.md`, `web-ui/PRODUCTION-SPEC-GAP-REGISTER.md`, `web-ui/spec/offline-and-service-worker-contract-v1.md`
Compatibility: `v1.x` preserves normative requirements and failure semantics; incompatible changes require `v2`.

## 1. Purpose

This specification defines why the persistence system exists and what user contract it <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-5607F51897"></a>MUST preserve.

The persistence system for browser-hosted CCL <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-18028F490B"></a>MUST:

1. Preserve normal programming workflow based on files, directories, and stable paths.
2. Provide crash-safe, deterministic durability and recovery.
3. Support long-lived interactive sessions (REPL, debugger, inspector, editor integration).
4. Operate local-first with optional asynchronous sync.
5. Enable Lisp-aware tooling without replacing or mutating user-authored files behind the user's back.

## 2. User Contract (Normative)

The user-facing mental model is a filesystem.

From the user's perspective:

1. Files and directories are real.
2. Paths are stable and meaningful.
3. Open, edit, save, rename, copy, and delete operations behave predictably.
4. Tooling that expects POSIX-like file workflows (within documented constraints) continues to work.
5. CCL launch procedures that rely on filesystem access remain supported.

The system <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-C292173F0B"></a>MUST NOT require users to adopt an object-centric workflow for ordinary development.

## 3. Non-Goals

This persistence system explicitly does not aim to be:

1. A full Git implementation.
2. A replacement for user file/path workflow with storage-native abstractions.
3. A per-keystroke collaborative consensus system.
4. A system that rewrites authored files to satisfy indexing or semantic storage internals.

## 4. Why This Design

The primary product outcome is trust.

Users forgive missing features; they do not forgive storage betrayal. The persistence system <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-C4FF70F346"></a>MUST prioritize:

1. No silent data loss.
2. No surprising rewrites.
3. No hidden relocation/renaming.
4. No destructive sync behavior.

The design is successful only if the surface model stays boring and predictable while internals provide strong safety.

## 5. Filesystem Semantics

### 5.1 Path Model

Path semantics <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-EE0CFF87DF"></a>MUST be portable POSIX-like:

1. Path separator is `/`.
2. Workspace root is `/`.
3. Paths are case-sensitive.
4. NUL and `/` inside path components are forbidden.
5. `.` and `..` are normalized; they are not stored as literal components.
6. UTF-8 is used at API boundaries.

### 5.2 Unicode and Length

1. Path components <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-3487C2FCD7"></a>MUST be normalized to NFC on ingest.
2. Normalization handling (canonicalize or reject) <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-0479E05907"></a>MUST be deterministic.
3. Component-length and full-path-length limits <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-0CA0DAFA34"></a>MUST be explicit and enforced.

### 5.3 Permissions and Executability

1. Full POSIX mode-bit emulation is out of scope.
2. Executable metadata MAY exist for interoperability/export.
3. Runtime semantics <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-4A34D2E3A5"></a>MUST treat executability as metadata, not authority.

## 6. Internal Storage Model

The filesystem is a projection over immutable versioned content.

Core model:

1. Immutable content-addressed objects.
2. Append-only persistence.
3. Snapshot-based history.
4. Mutable references to snapshots.

Objects <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-636FD7EF38"></a>MUST NOT be mutated in place. References MAY advance atomically.

### 6.1 Object Classes

1. `Blob`: immutable bytes for authored or binary content.
2. `Tree`: path component mapping to entries.
3. `Snapshot`: root tree plus metadata.
4. `Reference`: mutable pointer to a snapshot.

### 6.2 Identity

1. User-facing identity is path.
2. Internal stable identity MAY be represented by node id.
3. Rename/move SHOULD preserve stable identity when possible.

## 7. File Primacy Rule

A file is a first-class authored unit, not a storage illusion.

The storage layer <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-32D0701880"></a>MUST treat file blobs as authoritative user-authored content:

1. A source file is edited, saved, and versioned as a whole file.
2. Ordering, spacing, comments, and narrative structure are preserved exactly unless the user changes them.
3. Semantic data is derived from files, not a replacement for files.
4. Tooling MAY index or analyze files, but <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-6DD45E7EA5"></a>MUST NOT require file fragmentation into storage-native semantic nodes.

### 7.1 Profile Boundary

Default behavior is `file-primacy-v1`.

Any semantic-canonical mode <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-C316647AFC"></a>MUST be explicit, policy-bound, and auditable:

1. No silent transition from file-primacy default.
2. No implicit replacement of file/path user contract.
3. Mixed-profile compatibility <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-FEBAB2C533"></a>MUST be checked before protected ref advancement.

## 8. Snapshot and Reference Policy

### 8.1 Snapshot Classes

1. User-save snapshots are authoritative and created on explicit save/save-all.
2. Autosave snapshots are safety-only and created at stable points (idle, time-coalesced, boundary-triggered).
3. Autosaves <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-DE8017AFA5"></a>MUST NOT overwrite user-save history.
4. Crash checkpoints <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-7F36A358E4"></a>MUST preserve atomic ref movement guarantees.

### 8.2 Atomicity and Recovery

1. Object persistence is append-only.
2. Ref updates <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-E7D4D5EEF8"></a>MUST be crash-safe and journaled or equivalently atomic.
3. Recovery <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-0D839C0819"></a>MUST always resolve each ref to one complete snapshot state.

## 9. Reference Names and Roles

Common refs SHOULD include:

1. `workspace/main`
2. `autosave/latest`
3. `session/<id>`
4. Optional named checkpoints

Background automation <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-854E8777D8"></a>MUST NOT advance user-visible working refs unless an explicit policy allows it.

## 10. Sync and Concurrency

### 10.1 Local-First

1. Edit/save/history operations <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-7AA1FEFFF2"></a>MUST work offline after successful workspace bootstrap.
2. Sync is asynchronous and secondary to local interaction latency.
3. Initial application bootstrap/offline asset behavior is defined by `web-ui/spec/offline-and-service-worker-contract-v1.md`.

### 10.2 Sync Behavior

1. Sync moves objects and refs, not file-level surprise rewrites.
2. Divergence <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-CF2121E6FA"></a>MUST be represented as explicit ref state, not ad hoc conflict filename litter.
3. Merge/finalization requires deterministic policy and/or explicit user acceptance.

### 10.3 Multi-Tab/Team Coordination

1. Protected refs SHOULD use single-writer lease semantics.
2. Secondary writers <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-E0AB710C1E"></a>MUST default to explicit branch/session refs or read-only.
3. Protected ref advancement <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-004808A9CA"></a>MUST be gated in storage semantics, not UI alone.

## 11. Derived Data and Tooling

### 11.1 Lisp-Aware Indexing

1. Indexes are derived and rebuildable.
2. Indexes <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-EFF25C863F"></a>MUST key by snapshot/file/blob identities.
3. Identical blobs SHOULD reuse parse/index results.

### 11.2 Parser Strategy

1. Use Lisp reader where possible.
2. Tolerant mode MAY support incomplete dirty buffers.
3. Dirty-buffer indexing <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-C457D96066"></a>MUST remain separate from authoritative snapshot indexing.

### 11.3 Artifacts

1. Authored and derived artifacts <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-F3768C060F"></a>MUST be separable.
2. Derived artifacts <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-F59068000B"></a>MUST be discardable and reproducible.

## 12. Failure and Storage Pressure Policy

On storage pressure, implementations <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-30F1192F34"></a>MUST prioritize:

1. Stop autosaves first.
2. Evict derived artifacts second.
3. Refuse user saves only as last resort, with export or explicit recovery path.

Authored work <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-5A171F0B78"></a>MUST NOT be silently destroyed.

## 13. Security and Privacy

1. Content integrity <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-2812BBA576"></a>MUST be verifiable.
2. Optional encryption MAY be supported, with explicit key management and recovery policy.
3. Security controls <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-527B1EB947"></a>MUST NOT break deterministic durability semantics.

## 14. Interoperability

1. A filesystem API surface <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-1E9D167E86"></a>MUST remain explicit.
2. Interop with Git or external VCS is interchange, not canonical storage truth.
3. Storage internals <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-CA3C48418D"></a>MUST remain hidden unless explicitly requested for diagnostics/export.

## 15. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `persistence-user-contract.save-blocked` | User save refused due to storage pressure or integrity risk. | Conditional | Provide non-destructive export path and surface recovery options. |
| `persistence-user-contract.ref-inconsistent` | Ref does not resolve to a complete snapshot after crash recovery. | No | Run integrity scan and enter degraded mode until resolved. |
| `persistence-user-contract.path-invalid` | Path contains forbidden characters or exceeds length limits. | No | Reject operation and report invalid path component to caller. |
| `persistence-user-contract.silent-mutation-detected` | Background process attempted implicit mutation of user-visible ref. | No | Block mutation and emit audit diagnostic for investigation. |

## 16. Conformance

An implementation is conformant only if all conditions hold:

1. Users interact through stable file/path workflow semantics.
2. Save and restore are atomic and deterministic under crash testing.
3. Background sync never rewrites user-visible files implicitly.
4. Semantic tooling layers on top of files without replacing file primacy.
5. Conflict states are explicit and inspectable.
6. Storage pressure policy preserves authored work and degrades predictably.

## 17. UX Doctrine (Normative Summary)

### 16.1 Positive invariants

The system <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-9F8D51FC59"></a>MUST maximize:

1. Predictability.
2. Clear ownership of changes.
3. Atomic save behavior.
4. Local-first responsiveness.
5. Low-ceremony historical recovery.

### 16.2 Negative invariants

The system <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-35CB88A25A"></a>MUST avoid:

1. Ambiguous sync state.
2. Surprise conflict filenames.
3. Hidden special-file behavior.
4. Workflow-breaking abstraction indirection.
5. Implicit background mutation of authored files.

### 16.3 Guiding principle

Trust is the primary storage product property. Feature work <a id="REQ-PERSISTENCE-PURPOSE-AND-USER-CONTRACT-V1-BD41526F25"></a>MUST NOT compromise trust invariants.
