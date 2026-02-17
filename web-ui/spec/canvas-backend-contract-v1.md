# Canvas Backend Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Canvas scene backend behavior for rendering, dirty-rect invalidation, scene hit-testing, text measurement cache, and theme-driven defaults  
Depends on: `web-ui/spec/renderer-backend-contract-v1.md`, `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/backends/canvas/renderer.mjs`, `web-ui/backends/canvas/scene.mjs`  
Compatibility: `v1.x` preserves scene normalization, dirty-region behavior, measure-cache keys, and hit-test ordering; incompatible scene semantics require `v2`.

## 1. Purpose

This contract defines normative behavior for the Canvas backend used by `canvas-view` widgets.

## 2. Construction

`createCanvasBackend({ canvas, document, onMeasureTextCacheMiss })` <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-70DB179C71"></a>MUST:

1. Require a `canvas` element.
2. Require a usable `2d` rendering context.
3. Fail construction when either is missing.

## 3. Scene Model

1. Scene input MAY be an array of scene nodes or an already normalized scene root.
2. Array input <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-88A91E0C48"></a>MUST be normalized via `buildScene` with deterministic defaults.
3. Active scene <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-EB373B44F8"></a>MUST be stored and reused for `hitTest` and `getScene`.
4. `render(undefined, options)` <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-79C4889587"></a>MUST reuse prior active scene.

## 4. Render Semantics

## 4.1 Theme and Defaults

1. When `options.theme` is provided, backend <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-0C1B116CEA"></a>MUST derive defaults from normalized tokens.
2. Default font <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-1DAD38AD56"></a>MUST resolve from theme monospaced font lane.
3. Default text color and background <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-41DD6830D5"></a>MUST resolve from theme color lanes.

## 4.2 Full Redraw Path

1. If no dirty region is supplied after normalization, backend <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-EC9A8C7BF5"></a>MUST perform full redraw.
2. Full redraw <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-773CB8E4BF"></a>MUST clear surface or fill full-surface background before drawing nodes.

## 4.3 Dirty Redraw Path

Dirty-region hints are accepted from `dirty`, `dirtyRects`, `dirtyNodes`, and `dirtyIds`.

1. Dirty bounds <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-74F402814B"></a>MUST be normalized and coalesced deterministically.
2. Each dirty rect <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-0F177B4EAE"></a>MUST clip drawing to that rectangle.
3. Background clear/fill <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-50AE9EE3B0"></a>MUST apply per dirty rect.
4. Only entries intersecting a dirty rect MAY be drawn for that rect.

## 4.4 Node Draw Rules

1. `group` nodes <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-7F3EC2D2F1"></a>MUST draw children recursively.
2. `rect` nodes MAY fill and/or stroke.
3. `text` nodes <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-A7FDA8CC58"></a>MUST use selected font and fill color.
4. `path` nodes with callable path builder <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-EA438412A4"></a>MUST render within save/restore isolation.

## 5. Hit Testing

1. Hit-testing <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-D1E9A46330"></a>MUST be computed from active scene graph, not pixel readback.
2. Flattened traversal order <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-6F4A745449"></a>MUST resolve topmost node as reverse scene order.
3. `group` nodes <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-D3F37A07CF"></a>MUST not be returned as hits.
4. Misses <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-E9438AA9CE"></a>MUST return `null`.

## 6. Text Measurement Cache

1. Measurement cache key <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-9433D39AB8"></a>MUST be `${font}::${text}`.
2. Cache <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-C787D58BE3"></a>MUST track hit/miss counters.
3. Returned measurement payload <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-1D1D96EB5B"></a>MUST include `cacheHit` boolean.
4. On cache miss, `onMeasureTextCacheMiss` <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-1522E14BA2"></a>MUST be called when supplied.
5. Missing font in options <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-800C39107F"></a>MUST fall back to backend default font.

## 7. Event Capture and Invalidation

1. `captureEvents` <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-1C004DF971"></a>MUST use `capture=true` and `passive=false` defaults.
2. Unsubscribe <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-F4F1FCC559"></a>MUST remove exactly registered listeners.
3. `invalidate` <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-3C9049F268"></a>MUST use animation frame when available, timeout fallback otherwise.
4. Invalidation cancellation <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-CF64D23FC3"></a>MUST be supported and idempotent.

## 8. Observability

When `qualityCollector.recordRender` is supplied, backend SHOULD emit stable samples with:

1. `surface="canvas"`
2. `backend="canvas"`
3. `operation="render"`
4. `fullRedraw`
5. `dirtyHintCount`
6. `dirtyRectCount`
7. `drawnNodeCount`
8. `totalNodeCount`
9. `durationMs`

## 9. Determinism and Tie-Break Rules

1. Scene normalization <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-BB211C234F"></a>MUST coerce non-finite bounds to zero deterministically.
2. Dirty-rect coalescing <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-88141EDD3B"></a>MUST produce stable ordering.
3. Hit-test topmost choice <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-CDB17CC564"></a>MUST be deterministic under overlap.
4. Cache keying <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-ACD8104EC1"></a>MUST treat equal `(font,text)` as identical across runs.

## 10. Accessibility and Command Routing Expectations

For `canvas-view` integration lanes:

1. Backend rendering <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-BE3ABC303F"></a>MUST be compatible with explicit DOM-level accessibility overlays/properties supplied by widget adapters.
2. Hit-test payloads (`id`, `kind`, `props`) <a id="REQ-CANVAS-BACKEND-CONTRACT-V1-0964E1B178"></a>MUST remain stable for command routing hooks.

## 11. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `canvas-backend.canvas-missing` | Canvas element not supplied. | No | Provide a valid canvas element. |
| `canvas-backend.context-missing` | 2D context unavailable. | No | Run on host with Canvas2D support. |
| `canvas-backend.scene-invalid` | Scene payload cannot be normalized. | Conditional | Fix scene node shape/types and retry. |
| `canvas-backend.measure-failed` | Text measurement failed unexpectedly. | Conditional | Validate font/text inputs; allow fallback metrics if configured. |

## 12. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/canvas-scene.test.mjs`
2. `web-ui/tests/canvas-hit-test.test.mjs`
3. `web-ui/tests/canvas-dirty-rects.test.mjs`
4. `web-ui/tests/canvas-measure-cache.test.mjs`
5. `web-ui/tests/phase-3-renderer-parity.test.mjs`
6. `web-ui/tests/widgets-dirty-rects.test.mjs`

Pass criteria:

1. Scene normalization and hit-test assertions are deterministic.
2. Dirty redraw fixtures prove bounded clear/draw behavior.
3. Measure cache hit/miss accounting is stable.
4. Theme parity fixtures pass against expected colors/fonts.

## 13. Conformance

A Canvas backend implementation is conformant only if Sections 2-12 are satisfied.
