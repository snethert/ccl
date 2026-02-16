# UI Component Visual Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: `web-ui` visual component behavior across DOM/Canvas/WebGL  
Depends on: `web-ui/spec/ui-visual-tokens-v1.json`

## 1. Purpose

This contract defines the minimum normative visual behavior for first-party UI components.
Implementations MUST conform to this document to claim visual parity.

## 2. Conformance

A renderer/backend pair is conformant only if all rules below hold:

1. All component states (`rest`, `hover`, `focus`, `active`, `disabled`, `error`) are implemented where applicable.
2. Numeric geometry is within tolerance:
- Dimensions/padding/border radius: +/- 1 px.
- Shadow blur/offset: +/- 1 px.
3. Color output is within tolerance:
- Target color delta <= 2/255 per channel for RGB, <= 0.02 for alpha.
4. Focus indicator contract is met exactly:
- Ring width MUST be `2px`.
- Ring color MUST map to `focus` token in active mode.
5. Responsive and touch ergonomics contract is met:
- Required viewport lanes: `desktop-lg`, `tablet`, `mobile`.
- In coarse-pointer lanes, effective interactive hit targets MUST be `>=44x44px`.
- If visual control geometry is below `44px`, hit-slop expansion MUST supply the missing interactive area without changing layout geometry.

## 3. Token Mapping Rules

All components MUST use semantic token paths from `ui-visual-tokens-v1.json`.
Hard-coded visual constants are prohibited except where explicitly stated.

Required mappings:

- Surfaces: `modes.{mode}.color.surface*`
- Boundary subtle: `modes.{mode}.color.boundarySubtle`
- Boundary standard: `modes.{mode}.color.boundaryStandard`
- Boundary strong: `modes.{mode}.color.boundaryStrong`
- Boundary focus: `modes.{mode}.color.boundaryFocus`
- Compatibility alias: `modes.{mode}.color.border` MUST resolve to the same value as `boundaryStandard`.
- Primary text: `modes.{mode}.color.textPrimary`
- Focus ring: `modes.{mode}.color.focus` + `focus.ringWidthPx`
- Selection row fill: `modes.{mode}.color.selection`
- Selection row text: `modes.{mode}.color.selectionText`
- Spacing/padding: `space.*`
- Radius: `radius.*`
- Elevation: `elevation.level*`

## 4. Component Contracts

### 4.1 Window

Required geometry:

- Border width: `1px`.
- Radius: `radius.md`.
- Padding: `space.md`.
- Min internal gap: `space.sm`.

Required visuals:

- Background: `surface`.
- Border (rest): `boundaryStandard`.
- Shadow: `elevation.level2`.

State behavior:

- `rest`: baseline values above.
- `focus`: MUST show visibly stronger edge contrast using one of:
- Focus ring outside border using `boundaryFocus` or `focus`.
- Border emphasis with `boundaryStrong` and >= 3:1 non-text contrast against adjacent surface.
- `disabled`: not applicable.
- `error`: window title or header accent MAY use `error`.

### 4.2 Button (Primary Neutral Button)

Required geometry:

- Min height (fine pointer lanes): `32px`.
- Effective hit target (coarse pointer lanes): `>=44px`.
- Horizontal padding: `space.sm`.
- Vertical padding: `>= 3px`.
- Radius: `radius.sm`.
- Border width: `1px`.

State behavior:

- `rest`: background `surfaceRaised`, border `boundaryStandard`, text `textPrimary`.
- `hover`: background MUST increase contrast relative to `rest`; boundary SHOULD step to `boundaryStrong`.
- `focus`: ring MUST be visible and conform to section 2; any border emphasis MUST use `boundaryFocus` or `boundaryStrong`.
- `active`: pressed state MUST be visually distinct from `hover`; boundary MUST be at least `boundaryStrong`.
- `disabled`: opacity MAY be reduced, but text MUST remain legible and boundary SHOULD use `boundarySubtle`.
- `error`: destructive actions MUST expose an `error` affordance (boundary, fill, or label accent) and MUST include a redundant non-color cue (text and/or icon).

### 4.3 Text Input

Required geometry:

- Min height (fine pointer lanes): `32px`.
- Effective hit target (coarse pointer lanes): `>=44px`.
- Radius: `radius.sm`.
- Border width: `1px`.
- Horizontal padding: `space.sm`.

State behavior:

- `rest`: background `surface`, border `boundaryStandard`, text `textPrimary`.
- `hover`: optional; MUST NOT reduce readability; if present, boundary SHOULD step to `boundaryStrong`.
- `focus`: ring MUST be visible and conform to section 2; focus boundary MUST use `boundaryFocus` or `focus`.
- `active`: same as focused editing state.
- `disabled`: readability MUST remain >= WCAG AA for text/background; boundary SHOULD use `boundarySubtle`.
- `error`: boundary or assistive marker MUST use `error` and be non-color redundant.

### 4.4 List Row / Tree Row

Required geometry:

- Row min height (fine pointer lanes): `32px`.
- Effective row hit target (coarse pointer lanes): `>=44px`.
- Row horizontal padding: `space.sm`.
- Radius: `radius.sm`.

State behavior:

- `rest`: transparent fill, inherited text.
- `hover`: subtle surface-raised fill or boundary emphasis using `boundarySubtle`.
- `focus`: row or contained control MUST expose focus indicator using `boundaryFocus` and/or focus ring.
- `active`: may match selected semantics if activation implies selection.
- `disabled`: row MAY dim; text MUST stay readable.
- `error`: row with error metadata MAY tint text with `error`.
- `selected`: fill MUST use `selection`; text MUST use `selectionText`; boundary SHOULD use `boundaryStrong`.

### 4.5 Tab (Dock/Tabbed Regions)

Required geometry:

- Tab min height (fine pointer lanes): `32px`.
- Effective tab hit target (coarse pointer lanes): `>=44px`.
- Horizontal padding: `space.sm`.
- Border radius: `radius.sm` for active tab corners.

State behavior:

- `rest`: reduced emphasis with `boundarySubtle` or no boundary.
- `hover`: contrast increase and boundary SHOULD step to `boundaryStandard`.
- `focus`: focus ring or equivalent visible indicator with `boundaryFocus`/`focus`.
- `active`: clear active-background distinction, text emphasis, and boundary SHOULD step to `boundaryStrong`.
- `disabled`: present but non-interactive and legible.
- `error`: tabs representing error-bearing surfaces MUST expose a persistent `error` affordance (badge, icon, or boundary accent) and MUST remain distinguishable without color alone.

## 5. Backend Parity Rules

### 5.1 DOM vs Canvas

- Layout and spacing MUST match within tolerance (section 2).
- Focus indicator placement MUST match target bounds within +/- 1 px.
- Text baseline drift MUST be <= 1 px for default font settings.

### 5.2 DOM vs WebGL

- Color mapping and opacity MUST satisfy section 2 tolerance.
- Selection and focus visuals MUST be semantically equivalent.
- Shadow/elevation MAY approximate blur kernel, but perceived depth ordering MUST be identical.

### 5.3 Canvas vs WebGL

- Hit-target bounds for interactive components MUST match within +/- 1 px.
- State transitions MUST preserve semantic differences (`hover` vs `active` vs `selected`).

## 6. Failure Semantics

If a backend cannot meet an effect:

1. It MUST degrade to the nearest compliant non-ornamental representation.
2. It MUST preserve state distinguishability (especially focus and selected).
3. It MUST emit a structured diagnostic event for conformance telemetry.

## 7. Test Vectors (Required)

The following fixtures MUST exist for conformance:

1. Single-window baseline snapshot in dark, light, high-contrast, and forced-colors lanes.
2. Component state matrix snapshots for button, input, list row, tab.
3. Focus-ring geometry fixture across all backends.
4. Selection contrast fixture across all backends.
5. Disabled/error legibility fixture across all backends.
6. Responsive/touch target fixture across desktop/tablet/mobile viewport lanes.

Canonical fixture IDs and assertion definitions are in:
- `web-ui/spec/ui-conformance-fixtures-v1.json`
- `web-ui/spec/ui-conformance-fixture-catalog-v1.md`
- `web-ui/spec/ui-conformance-matrix-v1.md`
