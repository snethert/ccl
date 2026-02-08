# Phase 0 Spec: Theme and Motion Contract (v0)

## Purpose
Define a backend-agnostic theme and motion contract so DOM and canvas/WebGL renderers share a single visual language.

## Goals
- Unified visual system across all renderers.
- Dark mode as a primary design target.
- Motion that explains state changes and can be suppressed.

## Non-Goals
- Full design system documentation.
- Complete color palettes for every widget type.

## Theme Tokens
All renderers must consume the same token set.

### Core Tokens
- `color.bg`, `color.surface`, `color.text.primary`, `color.text.secondary`
- `color.accent`, `color.accent.muted`, `color.warning`, `color.error`
- `elevation.level1..level4`
- `radius.sm`, `radius.md`
- `space.xs..xl`
- `font.body`, `font.mono`, `font.size.sm..xl`

### Example Token Payload
```json
{
  "mode": "dark",
  "color": {
    "bg": "#121212",
    "surface": "#1b1b1b",
    "text": {"primary": "#e8e8e8", "secondary": "#b8b8b8"},
    "accent": "#6fb0ff"
  },
  "elevation": {"level1": "0 1px 4px rgba(0,0,0,0.25)"},
  "font": {"body": "Inter", "mono": "Iosevka"}
}
```

## Typography Rules
- Text conveys primary meaning before icons.
- Font sizes and weights define hierarchy, not decoration.
- Monospace is reserved for code and structured data.

## Motion Contract
- Every state transition should animate (120–250 ms).
- Motion is non-linear (ease-out or spring).
- Motion can be globally suppressed.

### Motion Tokens
- `motion.fast`, `motion.normal`, `motion.slow`
- `motion.easing.primary`
- `motion.reduced` (boolean)

## Renderer Requirements
- DOM and canvas/WebGL must pull from the same token source.
- Tokens must be resolved at render time, not hardcoded.
- Dark and light themes are independent (no inversion).

## Invariants
- No OS-native widget styling.
- No decorative motion.
- Typography-first hierarchy is enforced.

## Phase 0 Decisions
- Theme tokens are runtime-editable behind an advanced toggle and persisted per workspace profile.
- Typography tokens in v0 remain axis-agnostic; optical sizing axes are deferred until typography telemetry justifies added complexity.
