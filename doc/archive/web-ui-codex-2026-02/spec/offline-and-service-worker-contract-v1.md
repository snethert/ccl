# Offline and Service Worker Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Offline bootstrap, service-worker cache policy, and asset loading guarantees for `web-ui`  
Depends on: `web-ui/spec/persistence-purpose-and-user-contract-v1.md`, `web-ui/spec/release-compatibility-and-rollout-v1.md`, `web-ui/spec/security-and-capability-model-v1.md`  
Compatibility: `v1.x` preserves offline scope, cache manifest semantics, and fallback behavior; incompatible bootstrap model changes require `v2`.

## 1. Purpose

This contract defines how `web-ui` remains usable when network connectivity is unavailable.

## 2. Offline Scope

`v1` offline guarantees are split:

1. post-bootstrap editing, save, restore, and history operations <a id="REQ-OFFLINE-AND-SERVICE-WORKER-CONTRACT-V1-DF5FA51C48"></a>MUST work offline,
2. initial bootstrap offline support requires service-worker-managed cached shell assets,
3. first-ever visit without prior cache MAY fail with explicit offline error.

## 3. Service Worker Requirements

When service workers are enabled for deployment profile:

1. Service worker registration <a id="REQ-OFFLINE-AND-SERVICE-WORKER-CONTRACT-V1-F68EE010FB"></a>MUST occur before declaring offline-ready status.
2. Asset cache manifest <a id="REQ-OFFLINE-AND-SERVICE-WORKER-CONTRACT-V1-6A981E59A7"></a>MUST include app shell, spec/runtime critical bundles, and versioned static resources.
3. Cache versioning <a id="REQ-OFFLINE-AND-SERVICE-WORKER-CONTRACT-V1-81EA9D1F66"></a>MUST be deterministic and tied to release artifact identity.
4. Cache update strategy <a id="REQ-OFFLINE-AND-SERVICE-WORKER-CONTRACT-V1-E417DD8E2F"></a>MUST avoid serving mixed-version critical bundles.

## 4. Runtime Asset Loading

1. Runtime loader <a id="REQ-OFFLINE-AND-SERVICE-WORKER-CONTRACT-V1-708095A365"></a>MUST fail closed when required local cached assets are missing.
2. Offline startup failures <a id="REQ-OFFLINE-AND-SERVICE-WORKER-CONTRACT-V1-A9DCA5DA96"></a>MUST emit actionable diagnostics with missing asset identifiers.
3. Once bootstrap succeeds, persistence features <a id="REQ-OFFLINE-AND-SERVICE-WORKER-CONTRACT-V1-12DB55C51B"></a>MUST remain network-independent.

## 5. Security and Integrity

1. Cached assets <a id="REQ-OFFLINE-AND-SERVICE-WORKER-CONTRACT-V1-5A2FA9023F"></a>MUST be integrity-checked via version/hash metadata.
2. Service-worker update activation <a id="REQ-OFFLINE-AND-SERVICE-WORKER-CONTRACT-V1-9431BC4444"></a>MUST preserve rollback path for prior known-good bundle.

## 6. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `offline.shell-missing` | Offline bootstrap requested but shell assets are absent. | Conditional | Go online once to prime cache and retry. |
| `offline.cache-version-mismatch` | Mixed-version cached assets detected. | Conditional | Purge/refresh cache and reload. |
| `offline.service-worker-unavailable` | Required service worker lane unavailable. | Conditional | Enable supported environment or run online-only profile. |
| `offline.integrity-failed` | Cached asset failed integrity verification. | No | Remove invalid cache and reacquire trusted assets. |

## 7. Conformance

An implementation is conformant only if Sections 2-6 are satisfied.
