# Non-DOM Accessibility Proxy Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Accessibility proxy model for Canvas/WebGL surfaces in `web-ui`  
Depends on: `web-ui/spec/ui-accessibility-visual-map-v1.md`, `web-ui/spec/renderer-backend-contract-v1.md`, `web-ui/spec/focus-and-selection-contract-v1.md`  
Compatibility: `v1.x` preserves proxy tree semantics, focus synchronization rules, and parity obligations; incompatible proxy model changes require `v2`.

## 1. Purpose

This contract defines how non-DOM rendered content exposes equivalent accessibility semantics.

## 2. Proxy Tree Model

Non-DOM surfaces <a id="REQ-NON-DOM-ACCESSIBILITY-PROXY-CONTRACT-V1-20C574204E"></a>MUST provide an accessibility proxy tree with:

1. stable node IDs,
2. role and accessible name,
3. state lanes (`focused`, `selected`, `disabled`, `expanded`, `error` where relevant),
4. bounding boxes in viewport coordinates.

## 3. Synchronization Rules

1. Proxy node lifecycle <a id="REQ-NON-DOM-ACCESSIBILITY-PROXY-CONTRACT-V1-B68610A595"></a>MUST mirror rendered scene lifecycle.
2. Focus movement <a id="REQ-NON-DOM-ACCESSIBILITY-PROXY-CONTRACT-V1-7FCB701C7E"></a>MUST update rendered focus and proxy focus in same logical turn.
3. Proxy bounds <a id="REQ-NON-DOM-ACCESSIBILITY-PROXY-CONTRACT-V1-A0A50DB308"></a>MUST track rendered hit regions within defined tolerance from accessibility map contract.
4. Name/role/state changes <a id="REQ-NON-DOM-ACCESSIBILITY-PROXY-CONTRACT-V1-FF609AA3E8"></a>MUST propagate without requiring full surface reinitialization.

## 4. Interaction Routing

Keyboard and assistive-tech actions targeting proxy nodes <a id="REQ-NON-DOM-ACCESSIBILITY-PROXY-CONTRACT-V1-32C3F788B7"></a>MUST route through the same command execution lanes as pointer interactions.

## 5. Fallback Behavior

If proxy synchronization fails:

1. system <a id="REQ-NON-DOM-ACCESSIBILITY-PROXY-CONTRACT-V1-81D5DD5F37"></a>MUST emit conformance-visible diagnostics,
2. affected non-DOM view SHOULD degrade to safe reduced-interaction mode until synchronization recovers.

## 6. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `a11y-proxy.node-missing` | Rendered target has no proxy node. | Conditional | Rebuild proxy subtree and retry mapping. |
| `a11y-proxy.state-diverged` | Proxy state diverged from rendered state. | Conditional | Resynchronize from canonical state graph. |
| `a11y-proxy.bounds-invalid` | Proxy bounds are malformed/out of tolerance. | Conditional | Recompute geometry and republish proxy frame. |
| `a11y-proxy.route-failed` | Assistive-tech action could not route to command lane. | Conditional | Validate routing metadata and retry action. |

## 7. Conformance

An implementation is conformant only if Sections 2-6 are enforced.
