# DOM Backend Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: DOM backend API and behavior for `web-ui` VDOM reconciliation, DOM event wiring, hit-testing, measurement, and invalidation  
Depends on: `web-ui/spec/renderer-backend-contract-v1.md`, `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/backends/dom/renderer.mjs`  
Compatibility: `v1.x` preserves DOM property/event semantics, measurement fallback behavior, and hit-test boundaries; incompatible mapping changes require `v2`.

## 1. Purpose

This contract defines the normative DOM backend behavior used by `createRoot` and DOM snapshot fixtures.

## 2. Construction

`createDomBackend({ document, container })` <a id="REQ-DOM-BACKEND-CONTRACT-V1-F03354F4C1"></a>MUST resolve a document in this order:

1. Explicit `document` argument.
2. `container.ownerDocument`.
3. Global `document`.

If no document can be resolved, construction <a id="REQ-DOM-BACKEND-CONTRACT-V1-7846900FB2"></a>MUST fail.

## 3. Required Operations

The backend <a id="REQ-DOM-BACKEND-CONTRACT-V1-81F9E4469E"></a>MUST expose all `vdom-node-backend-v1` methods from `renderer-backend-contract-v1.md` plus:

1. `measureText(text, options?)`
2. `hitTest(point, options?)`
3. `captureEvents(target, handlers, options?)`
4. `invalidate(callback)`

## 4. Property and Event Semantics

## 4.1 Event Props

1. Props named `on*` (for example `onClick`) <a id="REQ-DOM-BACKEND-CONTRACT-V1-CC150F7C77"></a>MUST map to DOM events by lowercasing suffix (`click`).
2. Setting an event prop <a id="REQ-DOM-BACKEND-CONTRACT-V1-6E541AF167"></a>MUST replace any prior listener for the same event on the same node.
3. Removing an event prop <a id="REQ-DOM-BACKEND-CONTRACT-V1-8D7468CB35"></a>MUST remove the listener.
4. `destroy(node)` <a id="REQ-DOM-BACKEND-CONTRACT-V1-9D7201BAC9"></a>MUST remove all listeners installed through backend event props.

## 4.2 Style and Class

1. `class` and `className` <a id="REQ-DOM-BACKEND-CONTRACT-V1-70DFB837C5"></a>MUST both set `node.className`.
2. `style` string <a id="REQ-DOM-BACKEND-CONTRACT-V1-8D268A63AF"></a>MUST map to `node.style.cssText`.
3. `style` object <a id="REQ-DOM-BACKEND-CONTRACT-V1-D13B7619C6"></a>MUST clear prior cssText and then assign style keys.
4. Removing style <a id="REQ-DOM-BACKEND-CONTRACT-V1-AB99F1380D"></a>MUST clear style attribute and cssText.

## 4.3 Boolean and Attribute Semantics

1. `false`, `null`, and `undefined` prop values <a id="REQ-DOM-BACKEND-CONTRACT-V1-BA8A34A3D9"></a>MUST remove attributes.
2. For boolean DOM properties, removal <a id="REQ-DOM-BACKEND-CONTRACT-V1-B13A344D50"></a>MUST also set property to `false`.
3. If a prop name exists on node instance, backend <a id="REQ-DOM-BACKEND-CONTRACT-V1-313BCD5A45"></a>MUST assign property directly.
4. Otherwise backend <a id="REQ-DOM-BACKEND-CONTRACT-V1-0D8935033D"></a>MUST set string attribute.

## 4.4 Internal Hook Props

Props prefixed with `__` are reserved internal hooks.

1. Backend <a id="REQ-DOM-BACKEND-CONTRACT-V1-19C3AE58D7"></a>MUST assign the hook value directly to node.
2. `__canvasRender` and `__webglRender` hooks, when functions, <a id="REQ-DOM-BACKEND-CONTRACT-V1-3EDA325C72"></a>MUST be invoked immediately after assignment.
3. Removing `__*` prop <a id="REQ-DOM-BACKEND-CONTRACT-V1-DC4AF6A543"></a>MUST delete or clear node field deterministically.

## 5. Text Measurement

1. Measurement <a id="REQ-DOM-BACKEND-CONTRACT-V1-292D0CF363"></a>MUST use an internal 2D canvas context when available.
2. If context is unavailable, `measureText` <a id="REQ-DOM-BACKEND-CONTRACT-V1-00B7270EBA"></a>MUST return zeros for all metrics.
3. Default font <a id="REQ-DOM-BACKEND-CONTRACT-V1-0EAFAF4F23"></a>MUST be `12px monospace` unless options provide explicit `font`.
4. `height` <a id="REQ-DOM-BACKEND-CONTRACT-V1-B916197624"></a>MUST equal `ascent + descent`.
5. Ascent/descent fallback <a id="REQ-DOM-BACKEND-CONTRACT-V1-E09A524DA0"></a>MUST derive from parsed px font size when DOM metrics omit bounding boxes.

## 6. Hit Testing

1. Hit-testing <a id="REQ-DOM-BACKEND-CONTRACT-V1-6FD13A0E4B"></a>MUST use `document.elementFromPoint(x, y)` when available.
2. Missing `elementFromPoint` support <a id="REQ-DOM-BACKEND-CONTRACT-V1-7EC0892D3A"></a>MUST return `null`.
3. If `options.container` is supplied, hits outside that container <a id="REQ-DOM-BACKEND-CONTRACT-V1-520C95C646"></a>MUST be rejected.
4. Hit-test miss <a id="REQ-DOM-BACKEND-CONTRACT-V1-3B15E69203"></a>MUST return `null`.

## 7. Event Capture

1. `captureEvents` <a id="REQ-DOM-BACKEND-CONTRACT-V1-FFAFE5C3A6"></a>MUST register supplied handlers on target with defaults:
- `capture=true`
- `passive=false`
2. Returned unsubscribe <a id="REQ-DOM-BACKEND-CONTRACT-V1-D84B1CD507"></a>MUST remove exactly those listeners.

## 8. Invalidation

1. If `requestAnimationFrame` exists, `invalidate` <a id="REQ-DOM-BACKEND-CONTRACT-V1-2E6E85E0CF"></a>MUST schedule callback on the next animation frame.
2. If unavailable, invalidate <a id="REQ-DOM-BACKEND-CONTRACT-V1-D7BC3733F8"></a>MUST schedule zero-delay timeout fallback.
3. Returned cancel function <a id="REQ-DOM-BACKEND-CONTRACT-V1-A989A0425C"></a>MUST cancel scheduled callback when still pending.

## 9. Root Wrapper

`createDomRoot(container, options)` <a id="REQ-DOM-BACKEND-CONTRACT-V1-82E797A33C"></a>MUST:

1. Construct DOM backend via `createDomBackend`.
2. Construct root reconciler via `createRoot`.
3. Forward optional scheduler into `createRoot`.

## 10. Determinism and Tie-Break Rules

1. Event listener replacement order <a id="REQ-DOM-BACKEND-CONTRACT-V1-441EF95B68"></a>MUST be last-write-wins for the same node/event.
2. Hit-test container filtering <a id="REQ-DOM-BACKEND-CONTRACT-V1-556F300038"></a>MUST be deterministic for identical DOM and point.
3. Style object application order <a id="REQ-DOM-BACKEND-CONTRACT-V1-F6E3F444E4"></a>MUST follow property enumeration order.

## 11. Security and Isolation Requirements

1. Backend <a id="REQ-DOM-BACKEND-CONTRACT-V1-EC59452070"></a>MUST treat all prop values as untrusted and <a id="REQ-DOM-BACKEND-CONTRACT-V1-DC9D0B997C"></a>MUST NOT eval string values.
2. Internal `__*` hooks <a id="REQ-DOM-BACKEND-CONTRACT-V1-4790DA09A4"></a>MUST remain private to backend/widget infrastructure and <a id="REQ-DOM-BACKEND-CONTRACT-V1-8E651705C3"></a>MUST NOT be interpreted as end-user attributes.
3. Event capture handlers <a id="REQ-DOM-BACKEND-CONTRACT-V1-F408E22558"></a>MUST execute only through explicit registration and teardown paths.

## 12. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `dom-backend.document-missing` | No usable DOM document reference. | No | Provide `document` or valid container with ownerDocument. |
| `dom-backend.measure-context-missing` | 2D measure context unavailable. | Yes | Accept zero metrics or provide DOM/canvas context support. |
| `dom-backend.hit-test-unsupported` | `elementFromPoint` unavailable in host. | Conditional | Use fallback hit-testing strategy or different host. |
| `dom-backend.target-invalid` | Event capture/hit-test target invalid or absent. | Conditional | Provide valid target/container node. |

## 13. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/renderer.test.mjs`
2. `web-ui/tests/phase-3-dom-snapshots.test.mjs`
3. `web-ui/tests/phase-3-renderer-parity.test.mjs`

Pass criteria:

1. DOM snapshots are stable across repeated runs for identical state trees.
2. Property/event mapping behavior is deterministic.
3. Measurement/hit-test fallbacks remain deterministic under missing capabilities.

## 14. Conformance

A DOM backend implementation is conformant only if Sections 2-13 are satisfied.
