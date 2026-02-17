# Persistence Failure-Mode Matrix v1

Status: Draft  
Version: 1.1.0  
Last updated: 2026-02-17  
Scope: Normative crash/race/partition failure matrix for persistence conformance and fault-injection coverage  
Depends on: `web-ui/spec/persistence-ref-update-protocol-v1.md`, `web-ui/spec/persistence-lease-protocol-v1.md`, `web-ui/spec/persistence-sync-and-conflict-protocol-v1.md`, `web-ui/spec/persistence-conformance-fixtures-v1.json`, `web-ui/tests/persistence-fault-harness.mjs`
Compatibility: `v1.x` preserves normative requirements and failure semantics; incompatible changes require `v2`.

## 1. Purpose

This matrix defines exactly which failure points <a id="REQ-PERSISTENCE-FAILURE-MODE-MATRIX-V1-83F563D2BB"></a>MUST be tested, what state outcomes are required, and which fixture IDs provide evidence.

The matrix <a id="REQ-PERSISTENCE-FAILURE-MODE-MATRIX-V1-C7FEEF12E3"></a>MUST be used as:

1. Go/no-go gate for persistence release readiness.
2. Input for deterministic fault-injection fixtures.
3. Coverage map from requirement to automated test.

## 2. Severity and Release Policy

Priority classes:

1. `P0`: Required before production use.
2. `P1`: Required before broad-team default enablement.
3. `P2`: Required before scale/HA hardening milestones.

Release rule:

1. All `P0` rows <a id="REQ-PERSISTENCE-FAILURE-MODE-MATRIX-V1-7C2C321895"></a>MUST have automated fixture coverage with deterministic replay.
2. Any uncovered `P0` row blocks production-spec completion.
3. `P1` gaps require explicit waiver and target date.

## 3. Crash-Point Matrix

| Matrix ID | Priority | Injection Point | Expected Outcome | Primary Error | Fixture ID | Coverage |
|---|---|---|---|---|---|---|
| `CRASH-REF-001` | P0 | crash before protected ref metadata commit | ref unchanged, no half-state, commit closure still valid | `ERR_HARNESS_CRASH` | `crash.before_ref_commit.v1` | covered |
| `CRASH-REF-002` | P0 | crash immediately after protected ref metadata commit | ref advanced exactly once to complete commit | `ERR_HARNESS_CRASH` | `crash.after_ref_commit.v1` | covered |
| `CRASH-OBJ-001` | P1 | crash during split immutable write before chunk manifest/closure completion | ref not advanced, incomplete closure unreadable | `ERR_OBJECT_TXN_FAILED` | `crash.object_split_before_manifest.v1` | covered |
| `CRASH-RTX-001` | P1 | crash after `reftxn` prepared marker before metadata CAS apply | no ref moved or deterministic repair on startup | `ERR_METADATA_TXN_FAILED` | `crash.reftxn_prepared.v1` | covered |
| `CRASH-REC-001` | P1 | crash during startup recovery scanner | scanner restart is idempotent; no guessed ref rewrites | `ERR_RECOVERY_MANUAL_ACTION_REQUIRED` | `crash.recovery_scanner_restart.v1` | covered |

## 4. Lease-Race Matrix

| Matrix ID | Priority | Injection Point | Expected Outcome | Primary Error | Fixture ID | Coverage |
|---|---|---|---|---|---|---|
| `LEASE-RACE-001` | P0 | two contenders acquire same lease concurrently | exactly one writer lease succeeds | `ERR_LEASE_HELD` | `lease.race.single_writer.v1` | covered |
| `LEASE-RACE-002` | P0 | stale writer attempts protected ref advance after takeover | write rejected, ref unchanged | `ERR_LEASE_REQUIRED` | `lease.stale_writer_blocked.v1` | covered |
| `LEASE-RACE-003` | P1 | lease heartbeat lost immediately before ref advance | in-flight write rejected by epoch/token check | `ERR_LEASE_LOST` | `lease.heartbeat_loss_before_write.v1` | covered |
| `LEASE-RACE-004` | P1 | simultaneous takeover attempts after expiry | metadata commit order tie-break is deterministic | `ERR_LEASE_HELD` | `lease.double_takeover_tiebreak.v1` | covered |

## 5. Sync Partition and Retry Matrix

| Matrix ID | Priority | Injection Point | Expected Outcome | Primary Error | Fixture ID | Coverage |
|---|---|---|---|---|---|---|
| `SYNC-NET-001` | P0 | push partition after object upload and before remote ref CAS | retry converges; remote ref advanced once | `ERR_SYNC_NETWORK` | `sync.push.partition_retry.v1` | covered |
| `SYNC-NET-002` | P0 | pull partition during closure fetch | retry converges; local ref state deterministic | `ERR_SYNC_NETWORK` | `sync.pull.partition_mid_fetch_retry.v1` | covered |
| `SYNC-NET-003` | P0 | protected pull without semantic guard | fast-forward rejected; guarded retry required | `ERR_SYNC_PROTECTED_REF_GUARD_REQUIRED` | `sync.pull.protected_guard_required.v1` | covered |
| `SYNC-NET-004` | P0 | pull divergence (non-ancestor) | incoming ref created; `workspace/main` unchanged | `ERR_SYNC_DIVERGENCE` or no-op conflict path | `sync.pull.divergence_incoming.v1` | covered |
| `SYNC-NET-005` | P1 | remote ref CAS mismatch during push | no force-update; divergence path recorded | `ERR_SYNC_REF_CAS_MISMATCH` | `sync.push.cas_mismatch_divergence.v1` | covered |
| `SYNC-NET-006` | P1 | remote object hash mismatch on pull | object rejected; ref unchanged | `ERR_SYNC_OBJECT_HASH_MISMATCH` | `sync.pull.hash_mismatch_reject.v1` | covered |
| `SYNC-NET-007` | P1 | duplicate push retry after client timeout | idempotent object uploads, no duplicate side effects | `ERR_SYNC_NETWORK` | `sync.push.retry_idempotent_timeout.v1` | covered |

## 6. Required Invariant Checks per Fixture

Every fixture in this matrix <a id="REQ-PERSISTENCE-FAILURE-MODE-MATRIX-V1-CA29DAB4CA"></a>MUST assert at minimum:

1. `no_half_state_refs`
2. `protected_refs_resolve_complete_closure` for protected ref paths
3. `single_writer_per_lease` for lease race paths

Additional fixture-specific checks SHOULD include:

1. exact `refgen` transitions,
2. expected error-code presence/absence,
3. deterministic replay for fixed seed.

## 7. Deterministic Replay Requirements

Fault harness requirements:

1. deterministic RNG from explicit fixture seed,
2. virtual monotonic clock,
3. deterministic fault trigger by `op_id + phase`,
4. deterministic result ordering for multi-op scripts.

A fixture run <a id="REQ-PERSISTENCE-FAILURE-MODE-MATRIX-V1-5FE31412F4"></a>MUST be replayable byte-for-byte in serialized result output for identical seed and fixture version.

## 8. Evidence and Traceability

Each matrix row <a id="REQ-PERSISTENCE-FAILURE-MODE-MATRIX-V1-24ACCEF90E"></a>MUST map to:

1. matrix id,
2. fixture id,
3. automated test file,
4. latest pass timestamp,
5. harness version.

Recommended evidence file:

1. `web-ui/spec/persistence-conformance-report-v1.json` (future artifact).

## 9. Current Gap Summary

Current state based on `persistence-conformance-fixtures-v1.json`:

1. All listed `P0` and `P1` rows in sections 3-5 are covered.
2. Coverage is strong for crash/lease/sync behavior across first-pass and promoted P1 scenarios.
3. Remaining depth risk is long-haul/soak behavior beyond fixture-level deterministic fault replay.

## 10. Conformance

Persistence fault coverage is conformant to this matrix only if:

1. every `P0` and `P1` row is covered by automated fixtures,
2. fixtures pass deterministically on repeated runs,
3. fixture assertions include required invariant checks,
4. any uncovered row is explicitly marked pending with target fixture IDs.
