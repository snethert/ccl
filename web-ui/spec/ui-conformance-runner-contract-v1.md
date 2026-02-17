# UI Conformance Runner Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Execution semantics for `web-ui` conformance fixtures across DOM/Canvas/WebGL  
Depends on: `web-ui/spec/ui-conformance-fixtures-v1.json`, `web-ui/spec/ui-conformance-report-schema-v1.json`

## 1. Purpose

This contract defines how the conformance runner executes fixtures, measures assertions, and emits reports.
It is the normative source for runner behavior; fixture metadata alone is not sufficient.

## 2. Conformance

A runner is conformant only if all rules below hold:

1. It executes all fixtures with `status=required` from `ui-conformance-fixtures-v1.json`.
2. It evaluates each fixture using its declared `requiredHarness` semantics from this contract.
3. It emits a report that validates against `ui-conformance-report-schema-v1.json`.
4. It preserves deterministic results for repeated runs with the same seed and inputs.

## 3. Execution Model

### 3.1 Deterministic Input Space

The runner <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-2AB5E7EF97"></a>MUST execute using the `executionProfile` declared in `ui-conformance-fixtures-v1.json`:

1. Seed (`executionProfile.seed`).
2. Mode lanes (`executionProfile.modes`).
3. Backend lanes (`executionProfile.backends`).
4. Viewport lanes (`executionProfile.viewports`).

### 3.2 Lane Expansion Rules

1. If a fixture declares `modeLanes`, the runner <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-5B9FA88C98"></a>MUST execute only those modes; otherwise all profile modes apply.
2. If a fixture declares `viewportLanes`, the runner <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-CCCADB3D85"></a>MUST execute only those viewports; otherwise profile default viewport applies.
3. If a fixture declares `parityBackendPairs` and uses `requiredHarness=parity`, the runner <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-F1A08C731B"></a>MUST execute only those backend pairs and <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-73B5CC4054"></a>MUST NOT synthesize additional backend pairs.
4. Every backend named in `parityBackendPairs` <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-9F5C689187"></a>MUST be present in the fixture's effective backend lane set; missing or unknown backend members are fixture failures (`runner-lane-missing`).
5. If a fixture declares backend scope indirectly via test binding, the runner <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-C66983E180"></a>MUST still annotate report rows with effective backend.
6. Any missing declared lane is a fixture failure (`runner-lane-missing`).

### 3.3 Clock and Scheduling

1. Timing-based harnesses <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-88A44A63B0"></a>MUST use monotonic time.
2. Animation scheduling assumptions <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-ECB36D8B80"></a>MUST match `executionProfile.timing.animationFrameHz`.
3. Measured drift constraints <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-A2D754878C"></a>MUST use fixture assertion thresholds, not hardcoded defaults.

## 4. Harness Semantics

### 4.1 `snapshot`

1. Capture canonical output for fixture scope (DOM tree snapshot, renderer scene snapshot, or equivalent deterministic serialization).
2. Normalize attribute ordering, numeric precision, and stable IDs before comparison.
3. Compare against expected artifact baseline.
4. Snapshot harness <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-AAE3CF5237"></a>MUST fail on structural mismatch, missing required node/state cues, or non-deterministic serialization.

### 4.2 `geometry`

1. Measure geometry in CSS pixel space after device-scale normalization.
2. Evaluate bounds, offsets, focus ring placement, hit-target extents, and viewport lane requirements.
3. For coarse-pointer lanes, effective interactive target size <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-F445036909"></a>MUST include hit-slop expansion where applicable.

### 4.3 `contrast`

1. Compute contrast using WCAG relative luminance over sRGB values.
2. Evaluate text and non-text assertions against fixture thresholds.
3. Mode-specific contrast checks <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-37E0D5077C"></a>MUST run in all declared mode lanes.

### 4.4 `parity`

1. Compare equivalent fixture scenes across declared backend pairs (`parityBackendPairs` when present, otherwise all pairwise combinations from effective backend lanes).
2. Evaluate geometry delta, color channel delta, alpha delta, and semantic state parity where asserted.
3. Parity failure <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-26A6B87DCE"></a>MUST include both compared backend identities.

### 4.5 `timing`

1. Measure transition duration from observable start/end events.
2. Enforce declared duration thresholds and tolerances.
3. Reduced-motion assertions <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-ADE97F952F"></a>MUST verify semantic parity in addition to timing values.

### 4.6 `replay`

1. Re-run identical traces with identical seed and input order.
2. Compute stable state hash and compare across runs.
3. Replay harness <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-E0EE393783"></a>MUST fail if end state, key diagnostics, or ordering diverges.

### 4.7 `keyboard`

1. Execute deterministic keyboard interaction sequences.
2. Assert focus visibility, traversal correctness, and required focus metadata.
3. Keyboard harness <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-71E03675EE"></a>MUST fail on dead focus, missing indicator, or nondeterministic traversal.

## 5. Assertion Evaluation Rules

1. `==` requires exact equality after harness normalization.
2. `<=` and `>=` are inclusive.
3. If `tolerance` exists, it applies only to numeric metrics and <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-1312689BE9"></a>MUST be explicit in report output.
4. `stable-hash` requires identical hash values across repeated runs.
5. Boolean assertions require strict boolean equality.

## 6. Artifact and Diagnostics Requirements

1. Each fixture result <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-FA6608260C"></a>MUST list emitted artifact IDs/paths from its fixture definition.
2. Missing required artifact is a fixture failure (`runner-artifact-missing`).
3. Runner <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-64BCE9AA45"></a>MUST emit structured diagnostics for lane/setup failures, measurement failures, and unsupported effects.

## 7. Report Emission Contract

1. Report root fields and fixture rows <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-7040F3E7FF"></a>MUST validate against `ui-conformance-report-schema-v1.json`.
2. `env.mode` and `env.backend` MAY be lane-specific values or `mixed` when aggregating multi-lane runs.
3. Assertion rows <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-2827486AA4"></a>MUST include `id`, `metric`, `comparator`, `expected`, and `actual`.
4. Failed assertions <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-ACBFFCA3E1"></a>MUST include enough detail to deterministically reproduce failure (lane tuple + binding).

## 8. Failure Semantics

If a required fixture cannot run or fails:

1. Fixture status <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-E41210DC40"></a>MUST be `failed`.
2. Run summary status <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-9B6AC2DDF0"></a>MUST be `failed`.
3. Runner <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-3B2BA800A7"></a>MUST continue executing remaining required fixtures unless aborted by explicit policy.
4. Final report <a id="REQ-UI-CONFORMANCE-RUNNER-CONTRACT-V1-61CDEA61AB"></a>MUST include all encountered fixture failures.

## 9. Change Policy

1. Harness semantics are contract-level behavior and may not change incompatibly within minor versions.
2. New harness types require contract update and fixture schema update.
3. Deprecating a harness requires migration guidance and at least one full version overlap.
