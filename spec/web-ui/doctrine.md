# UI Doctrine

Presentation principles for a durable, modern windowing system.
Governs visual form, spatial behavior, and perceptual cues — independent of
widget inventory, programming model, or rendering backend.

Interaction semantics (z-order, modals, resize, focus handoff) are defined
in [focus-and-selection](contracts/focus-and-selection.md) and
[command-system](contracts/command-system.md), not here.

## Foundational Axiom

> The interface must read as a serious instrument, not a decorative surface.

Visual elements exist to communicate structure, state, and causality.
Decoration without informational value is disallowed.

## Spatial Model: Shallow Physicality

- Few elevation levels (2-4). Depth is informational, not ornamental.
- Soft, low-contrast, directional shadows. No hard outlines as default separators.
- Boundary roles: `subtle`, `standard`, `strong`, `focus` — not ad hoc styling.
- No skeuomorphism. No excessive z-stacking.

## Motion as Semantic Explanation

- Motion exists to explain what changed and why.
- State transitions animate when motion clarifies causality (120-250ms, non-linear easing).
- Three classes MUST NOT animate: `critical-alert`, `rapid-command-feedback`, `high-frequency-update`.
- Motion is globally suppressible without loss of meaning.
- No decorative motion. No linear easing. No animations that block interaction.

## Typography-First Hierarchy

- Text precedes icons in conveying meaning.
- Hierarchy through size, weight, and spacing — not color alone.
- Variable fonts with optical sizing preferred.
- No icon-only controls for primary actions. No decorative typefaces.

## Density and White Space

- Controls within a component: dense. Separation between conceptual regions.
- White space communicates grouping.
- Fine-pointer targets: 32px class minima.
- Coarse-pointer targets: 44x44px effective (including hit-slop).
- No vast empty regions. No floating controls without context.

## Color Modes

- **Dark mode is primary** — designed independently, not inverted.
- Backgrounds: dark gray (not pure black). Text: off-white (not pure white).
- Light, high-contrast, and forced-colors lanes: tokenized and testable.
- No automatic color inversion. No high-saturation accents as defaults.

## OS Neutrality

- Widgets do not mimic native OS controls.
- Visual language is self-consistent across platforms.
- No macOS/Windows cosplay. No system-native widget cloning.

## Directionality and Locale

- Layout uses logical properties where practical.
- RTL lanes preserve affordance order, focus visibility, and selection clarity.
- Directional iconography mirrors when semantics require it.
- No hardcoded left/right for core structure.

## Windows as Instruments

- Window chrome: minimal and functional.
- Focus state: visually unambiguous.
- Window boundaries: clear without heavy framing.
- No overlapping ornamental chrome. No fake 3D effects.

## Backend-Agnostic Application

This doctrine applies equally to DOM, Canvas, and WebGL renderers.
All backends consume shared theme tokens. DOM does not permit OS-native
widget styling or browser-default chrome.

## Prohibited Aesthetics

- Heavy gradients
- Glossy highlights
- Thick borders everywhere
- Beveled controls
- Icon-only toolbars
- Floating translucent glass effects
- 1990s dialog metaphors

These signal toolkit demos, not serious systems.

## Longevity Test

Before adopting any visual feature:
1. Does this explain state or structure?
2. Would this look embarrassing in five years?
3. Does removing it reduce clarity?

If the answer to (3) is "no," it does not belong.

## Closing Principle

> Restraint is not minimalism. Restraint is discipline.
