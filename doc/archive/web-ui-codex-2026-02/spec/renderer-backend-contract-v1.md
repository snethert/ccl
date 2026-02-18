# Renderer Backend Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Common renderer/backend lifecycle, invalidation, hit-test, event capture, measurement, and determinism rules for `web-ui` backends  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/ui-state-schema-v1.json`, `web-ui/src/renderer.mjs`  
Compatibility: `v1.x` preserves lifecycle ordering, key reconciliation rules, and backend profile requirements; incompatible lifecycle changes require `v2`.

## 1. Purpose

This contract defines the shared backend semantics required by `web-ui` renderer integrations.
It is normative for backend lifecycle operations and deterministic render behavior.

## 2. Backend Profiles

Implementations <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-B9B3FD6BF4"></a>MUST conform to one of these profiles:

1. `vdom-node-backend-v1`: Node-oriented backend consumed by `createRoot` (`DOM` profile in this release).
2. `scene-backend-v1`: Scene-oriented backend consumed directly by view widgets (`Canvas` and `WebGL` profiles in this release).

A backend MAY implement both profiles.

## 3. Shared Lifecycle Requirements

All profiles <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-3F777D188F"></a>MUST satisfy these requirements:

1. Render operations <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-23C3025D62"></a>MUST be deterministic for fixed `(input tree/scene, backend state, options)`.
2. Backends <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-978E3D8A78"></a>MUST expose stable teardown behavior for any allocated listeners/resources.
3. `measureText`, `hitTest`, `captureEvents`, and `invalidate` semantics <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-01EE16300E"></a>MUST remain stable across runs.
4. Invalidation callbacks <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-99CC044CE2"></a>MUST be cancellable.

## 4. `vdom-node-backend-v1` Interface

A conformant implementation <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-BE75BCA5C3"></a>MUST provide:

1. `createElement(tag)`
2. `createText(text)`
3. `appendChild(parent, child)`
4. `insertBefore(parent, child, anchor)`
5. `removeChild(parent, child)`
6. `setText(node, text)`
7. `setProp(node, name, value, prev?)`
8. `removeProp(node, name, prev?)`

Optional:

1. `replaceChild(parent, next, prev)`
2. `destroy(node)`

### 4.1 Reconciliation Rules

For `createRoot`-driven reconcilers:

1. Child keys <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-1932FC554D"></a>MUST be unique per sibling set.
2. Duplicate keys <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-7FEC032329"></a>MUST fail reconciliation deterministically.
3. Keyed children with same type <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-4CD0BAFBC8"></a>MUST be patched in place.
4. Keyed children with type change <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-528D579D9E"></a>MUST be replaced.
5. Missing keyed children in next tree <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-41A3BB9D87"></a>MUST be removed and unmounted.
6. Child order after reconcile <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-FFC019E4C4"></a>MUST match next tree order exactly.

### 4.2 Scheduling Rules

1. Without scheduler, render <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-B0C0A1FA43"></a>MUST apply immediately.
2. With scheduler, only one flush callback MAY be outstanding.
3. Multiple queued renders before flush <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-7F982F3BFC"></a>MUST coalesce to latest tree.
4. Explicit `flush()` <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-FD4F0A80A5"></a>MUST apply pending render synchronously.

## 5. `scene-backend-v1` Interface

A conformant implementation <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-BE75BCA5C3-D02"></a>MUST provide:

1. `render(scene, options?)`
2. `hitTest(point)`
3. `measureText(text, options?)`
4. `captureEvents(target, handlers, options?)`
5. `invalidate(callback)`

Optional:

1. `setTheme(theme)`
2. `getScene()`

### 5.1 Scene Semantics

1. `render` with explicit `scene` <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-2DE252EB68"></a>MUST replace active scene for subsequent `hitTest` and `getScene`.
2. `render` with `scene` omitted MAY reuse prior scene.
3. Dirty-region options (`dirty`, `dirtyRects`, `dirtyNodes`, `dirtyIds`) <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-02F461ABEB"></a>MUST restrict redraw scope when provided.
4. If no dirty region is supplied, backend <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-ECFA9FE749"></a>MUST perform full redraw.

## 6. Measurement Semantics

1. `measureText` <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-59600C96AD"></a>MUST return `width`, `height`, `ascent`, and `descent`.
2. Missing/unsupported measurement context <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-62EE466197"></a>MUST degrade deterministically to zeroed metrics.
3. Font choice <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-3A0C524043"></a>MUST be deterministic from explicit options, then backend default theme, then profile fallback.

## 7. Hit-Test Semantics

1. Hit-test input coordinates <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-4DF0834B5C"></a>MUST be interpreted in target-local coordinates.
2. Hit-test tie-breaks <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-0AC96428B3"></a>MUST be deterministic; topmost visual item <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-F32B395FCF"></a>MUST win when overlaps exist.
3. Misses <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-55FAD936D8"></a>MUST return `null`.

## 8. Event Capture and Invalidation

1. `captureEvents` <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-78F17B8AC3"></a>MUST return an unsubscribe function that removes all listeners installed by that capture call.
2. `invalidate` <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-22844A127A"></a>MUST schedule callback on animation frame when available; timeout fallback is allowed.
3. Invalidation cancellation <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-060CADBBA1"></a>MUST be idempotent.

## 9. Observability Contract

When a `qualityCollector.recordRender` hook exists, implementations SHOULD emit:

1. `surface`
2. `backend`
3. `operation`
4. `fullRedraw`
5. `dirtyHintCount`
6. `dirtyRectCount`
7. `drawnNodeCount`
8. `totalNodeCount`
9. `durationMs`

Field names <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-352571B482"></a>MUST be stable across `v1.x`.

## 10. Determinism and Tie-Break Rules

1. Key fallback order for unkeyed children <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-C515074BCC"></a>MUST be stable by index.
2. Reconcile traversal order <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-E6C334893E"></a>MUST be left-to-right in next-tree order.
3. Dirty-rect coalescing order <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-DD9441226B"></a>MUST be stable for equivalent input sets.
4. Hit-test overlap resolution <a id="REQ-RENDERER-BACKEND-CONTRACT-V1-893C2B2881"></a>MUST be stable by visual stacking order.

## 11. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `renderer-backend.profile-invalid` | Backend does not satisfy required profile API. | No | Implement missing profile methods. |
| `renderer-backend.duplicate-key` | Reconcile encountered duplicate sibling key. | No | Provide unique keys per sibling set. |
| `renderer-backend.type-mismatch` | Patch attempted across incompatible node types. | Conditional | Replace node or correct emitted tree kind/tag. |
| `renderer-backend.context-missing` | Required rendering context is unavailable. | Conditional | Provision backend context or degrade surface. |
| `renderer-backend.measure-unsupported` | Text metrics context unavailable. | Yes | Accept zeroed metrics or install measurement lane. |
| `renderer-backend.hit-test-invalid-point` | Hit-test input is invalid. | Conditional | Normalize point payload and retry. |

## 12. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/renderer.test.mjs`
2. `web-ui/tests/phase-3-dom-snapshots.test.mjs`
3. `web-ui/tests/phase-3-renderer-parity.test.mjs`

Pass criteria:

1. Keyed mount/patch/replace/remove behavior is deterministic.
2. Scheduled render coalescing semantics are deterministic.
3. Backend parity fixtures pass across required profiles.

## 13. Conformance

An implementation is conformant only if:

1. It satisfies at least one profile in Section 2.
2. Shared lifecycle rules in Sections 3 and 8 hold.
3. Determinism and failure semantics in Sections 10 and 11 hold.
