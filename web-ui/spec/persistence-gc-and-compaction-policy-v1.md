# Persistence GC and Compaction Policy v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Reachability-based garbage collection and compaction for append-only persistence storage  
Depends on: `web-ui/spec/persistence-ref-update-protocol-v1.md`, `web-ui/spec/persistence-sync-and-conflict-protocol-v1.md`, `web-ui/spec/persistence-storage-backend-matrix-v1.md`  
Compatibility: `v1.x` preserves root-set definitions, safe-delete rules, and quota-pressure behavior; incompatible retention policy changes require `v2`.

## 1. Purpose

This contract defines bounded-storage behavior for append-only persistence.

## 2. Root Set Definition

Live-object roots <a id="REQ-PERSISTENCE-GC-AND-COMPACTION-POLICY-V1-32C694E57A"></a>MUST include:

1. all protected refs (`workspace/*`),
2. autosave refs retained by policy,
3. pending merge candidates,
4. incoming divergence refs not yet merged/finalized,
5. in-flight sync transfer references.

Objects reachable from this root set are live.

## 3. GC Eligibility and Safety

An object is deletable only when all conditions hold:

1. object is unreachable from root set,
2. object age exceeds retention grace period (`retentionGraceMs`),
3. remote sync policy confirms no required replication dependencies remain.

Protected refs and unresolved merge candidates <a id="REQ-PERSISTENCE-GC-AND-COMPACTION-POLICY-V1-0F5EDCAF7F"></a>MUST NOT be collected.

## 4. Compaction Triggers

Required trigger classes:

1. periodic maintenance interval,
2. explicit operator/user command,
3. storage quota pressure threshold crossing,
4. startup recovery compaction pass when prior compaction interrupted.

Compaction <a id="REQ-PERSISTENCE-GC-AND-COMPACTION-POLICY-V1-5344625734"></a>MUST be crash-safe and restart-resumable.

## 5. Sync Interaction

1. Objects pending remote fetch acknowledgment <a id="REQ-PERSISTENCE-GC-AND-COMPACTION-POLICY-V1-41D184E042"></a>MUST remain pinned.
2. GC policy <a id="REQ-PERSISTENCE-GC-AND-COMPACTION-POLICY-V1-78123ECFC7"></a>MUST preserve objects referenced by unresolved incoming refs.
3. Remote-aware compaction metadata <a id="REQ-PERSISTENCE-GC-AND-COMPACTION-POLICY-V1-2A6873E80F"></a>MUST be auditable.

## 6. Quota Pressure Response

On quota pressure, system <a id="REQ-PERSISTENCE-GC-AND-COMPACTION-POLICY-V1-CB7F152F1F"></a>MUST degrade in this order:

1. prune old telemetry/derived artifacts,
2. compact unreachable objects,
3. suspend non-critical autosave lanes,
4. block new writes only as last resort with explicit recovery/export path.

## 7. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `persistence-gc.scan-failed` | Reachability scan failed. | Conditional | Repair metadata and retry scan. |
| `persistence-gc.delete-blocked` | Candidate object cannot be safely deleted yet. | No | Keep object pinned until preconditions are met. |
| `persistence-gc.compaction-interrupted` | Compaction interrupted before commit. | Conditional | Resume compaction from checkpoint. |
| `persistence-gc.quota-critical` | Quota pressure exceeded safe-write threshold. | Conditional | Execute pressure policy and retry writes. |

## 8. Conformance

An implementation is conformant only if Sections 2-7 are enforced.
