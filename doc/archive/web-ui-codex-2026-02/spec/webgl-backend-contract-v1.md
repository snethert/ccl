# WebGL Backend Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: WebGL scene backend behavior for shader/program lifecycle, draw-list generation, dirty-rect scissoring, scene hit-testing, text measurement, and theme defaults  
Depends on: `web-ui/spec/renderer-backend-contract-v1.md`, `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/backends/webgl/renderer.mjs`, `web-ui/backends/webgl/draw-list.mjs`  
Compatibility: `v1.x` preserves draw-list encoding and clipping semantics, color parsing, and scene hit-test behavior; incompatible pipeline changes require `v2`.

## 1. Purpose

This contract defines normative behavior for the WebGL backend used by `webgl-view` widgets.

## 2. Construction and GL Pipeline

`createWebGLBackend({ canvas, document, onMeasureTextCacheMiss })` <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-FCF84DDDAB"></a>MUST:

1. Require a `canvas` element.
2. Resolve a WebGL context from `webgl` or `experimental-webgl`.
3. Fail construction when context is unavailable.
4. Compile vertex/fragment shaders and link a program at initialization.
5. Fail initialization when shader compile or program link fails.
6. Initialize blending mode with SRC_ALPHA / ONE_MINUS_SRC_ALPHA.

## 3. Scene and Draw-List Model

1. Scene input semantics <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-94AB103FC6"></a>MUST match Canvas contract (`buildScene` normalization for arrays).
2. Active scene <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-A80A34D6AA"></a>MUST be retained for `hitTest` and `getScene`.
3. Draw-list generation <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-23C7FEC034"></a>MUST include only `rect` nodes in `v1`.
4. Each rect <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-71CC8A9C12"></a>MUST emit two triangles (6 vertices).
5. Draw-list output <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-ECA9B2CC8F"></a>MUST include typed arrays for positions and colors plus vertex count.

## 4. Color and Theme Semantics

## 4.1 Color Parsing

`parseWebGLColor` <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-0FCDF83082"></a>MUST support:

1. Array channels (`[r,g,b,a?]`)
2. Hex forms (`#rgb`, `#rrggbb`, `#rrggbbaa`)
3. `rgb(...)` and `rgba(...)` strings

Channels <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-028DFC1860"></a>MUST be normalized into `[0,1]` with clamping.

## 4.2 Theme Defaults

1. Theme application <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-25B5AF25AD"></a>MUST derive default font and default background from normalized tokens.
2. Background color <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-3B9DDBDD1A"></a>MUST map to `gl.clearColor`.
3. Theme update <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-8C96711EA1"></a>MUST be deterministic across repeated equivalent token sets.

## 5. Render Semantics

## 5.1 Full Redraw

When no dirty rects are active:

1. Backend <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-B81A319883"></a>MUST disable scissor test.
2. Backend <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-4E952DDAF6"></a>MUST clear full surface with resolved clear color.
3. Backend <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-47F41F3738"></a>MUST draw full draw-list.

## 5.2 Dirty Redraw

Dirty hints (`dirty`, `dirtyRects`, `dirtyNodes`, `dirtyIds`) <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-D4CF2583B0"></a>MUST normalize/coalesce deterministically.

For each dirty rect:

1. Backend <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-CBBDCA8B08"></a>MUST enable scissor test.
2. Dirty rect <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-AFB8B3D21C"></a>MUST be transformed into WebGL scissor coordinates.
3. Backend <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-960D388CA9"></a>MUST clear only that rect.
4. Backend <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-B1A65811C4"></a>MUST build clipped draw-list and issue draw call.

After dirty pass, backend <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-AACCE5D916"></a>MUST disable scissor test.

## 6. Hit Testing

1. Hit-testing <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-7D9CC181E9"></a>MUST be scene-graph based via shared hit-test algorithm.
2. GPU color-picking is not part of `v1` and <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-E0D0AAC1E3"></a>MUST NOT alter hit-test outcomes.
3. Hit-test topmost tie-break <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-B371196316"></a>MUST match reverse flattened scene order.

## 7. Text Measurement

1. Backend <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-46699F3DD4"></a>MUST maintain measurement cache semantics equivalent to Canvas contract.
2. Measurement lane MAY use offscreen/document 2D context.
3. If measurement context is unavailable, metrics <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-A571E805A7"></a>MUST degrade to zeros deterministically.
4. Cache miss callback <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-5C9E2A7793"></a>MUST be invoked when provided.

## 8. Event Capture and Invalidation

1. `captureEvents` defaults <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-35A034F975"></a>MUST be `capture=true`, `passive=false`.
2. Unsubscribe <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-2EB31C8D9A"></a>MUST remove exactly registered listeners.
3. `invalidate` <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-9E004AB5A7"></a>MUST use animation frame when available, timeout fallback otherwise.
4. Invalidation cancellation <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-E0DFBF0C37"></a>MUST be supported and idempotent.

## 9. Observability

When `qualityCollector.recordRender` exists, backend SHOULD emit stable samples with:

1. `surface="webgl"`
2. `backend="webgl"`
3. `operation="render"`
4. `fullRedraw`
5. `dirtyHintCount`
6. `dirtyRectCount`
7. `drawnNodeCount`
8. `totalNodeCount`
9. `durationMs`

## 10. Determinism and Tie-Break Rules

1. Draw-list vertex order <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-45654FC47B"></a>MUST be stable for fixed scene input.
2. Clipped draw-list inclusion <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-4D59517617"></a>MUST be deterministic for equal clip rectangles.
3. Scissor coordinate conversion <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-865824C8B2"></a>MUST be deterministic and integer-stable.
4. Hit-test tie-break <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-B308CD412A"></a>MUST match Section 6 ordering.

## 11. Security and Safety Requirements

1. Shader sources are fixed internal strings in `v1`; runtime scene data <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-8466EEA68E"></a>MUST NOT inject shader code.
2. Scene props used for draw-list generation <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-E8F23CD750"></a>MUST be treated as data only.
3. Invalid color inputs <a id="REQ-WEBGL-BACKEND-CONTRACT-V1-98E8A5A87F"></a>MUST degrade to deterministic defaults, not host-dependent behavior.

## 12. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `webgl-backend.canvas-missing` | Canvas element not supplied. | No | Provide a valid canvas element. |
| `webgl-backend.context-missing` | WebGL context unavailable. | No | Run on host with WebGL support. |
| `webgl-backend.shader-compile-failed` | Vertex or fragment shader compile failure. | Conditional | Inspect shader/runtime compatibility and retry. |
| `webgl-backend.program-link-failed` | Shader program link failure. | Conditional | Inspect GL capabilities and retry. |
| `webgl-backend.scene-invalid` | Scene payload cannot be normalized/drawn. | Conditional | Correct scene payload shape and retry. |

## 13. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/webgl-draw-list.test.mjs`
2. `web-ui/tests/phase-3-renderer-parity.test.mjs`
3. `web-ui/tests/widgets-dirty-rects.test.mjs`

Pass criteria:

1. Draw-list generation and color parsing fixtures pass deterministically.
2. Dirty-rect render path emits stable redraw coverage.
3. Theme parity with expected clear color/font defaults passes.

## 14. Conformance

A WebGL backend implementation is conformant only if Sections 2-13 are satisfied.
