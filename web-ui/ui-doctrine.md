This document is a **UI Doctrine** suitable for a windowing / UI toolkit specification.
It is written as a normative, future-facing design doctrine rather than a style guide, so it remains valid as implementation details evolve.

---

# UI Doctrine

**Presentation Principles for a Durable, Modern Windowing System**

---

## 0. Purpose

This document defines the **presentation doctrine** for the UI system.
It governs visual form, spatial behavior, and perceptual cues, independent of widget inventory, programming model, or rendering backend.
It intentionally does not define interaction arbitration semantics (`z-order`, modal stacking, resize rules, focus handoff); those rules are normative in `web-ui/spec/ui-interaction-window-management-contract-v1.md`.

The goal is not trendiness, but **durability**: a UI that looks modern now and defensible years later.

### Relationship to the IDE Doctrine
This UI Doctrine governs *presentation*. Product interaction semantics, tool behavior, and system capabilities are defined in `web-ide/ide-doctrine.md`.
System-level interaction/window-management semantics are defined in `web-ui/spec/ui-interaction-window-management-contract-v1.md`.
If a conflict appears:
- UI Doctrine controls visual form, motion, and spatial presentation.
- Interaction/Window Management Contract controls z-order, modal stacking, resize governance, and focus handoff.
- IDE Doctrine controls product/tool interaction semantics and behavior.

### Backend-Agnostic Application
This doctrine applies equally to DOM, canvas, and WebGL renderers.
The system uses a hybrid model where text-heavy surfaces may be DOM-backed for input fidelity.
DOM usage does not permit OS-native widget styling or browser-default chrome.
All backends must consume shared theme tokens so the UI reads as one instrument.

### Production Contracts
For production implementation and conformance, this doctrine is complemented by:
- `web-ui/spec/ui-visual-tokens-v1.json`
- `web-ui/spec/ui-component-visual-contract-v1.md`
- `web-ui/spec/ui-interaction-window-management-contract-v1.md`
- `web-ui/spec/ui-motion-contract-v1.md`
- `web-ui/spec/ui-accessibility-visual-map-v1.md`
- `web-ui/spec/ui-conformance-fixtures-v1.json`
- `web-ui/spec/ui-conformance-fixture-catalog-v1.md`
- `web-ui/spec/ui-conformance-runner-contract-v1.md`
- `web-ui/spec/ui-conformance-matrix-v1.md`
- `web-ui/spec/ui-conformance-report-schema-v1.json`
- `web-ui/spec/ui-accessibility-baseline-audit-v1.md`

If any nontrivial ambiguity exists between this doctrine and those contracts, the contracts take precedence for implementation behavior.

### Normative Strata and Claim Rules
This doctrine distinguishes three layers:
- **Doctrine layer**: design intent and long-term presentation principles.
- **Contract layer**: machine-testable requirements and tolerances.
- **Evidence layer**: executable fixtures, reports, and diagnostics.

Conformance claim rules:
- No clause may be treated as a release gate unless it maps to contract language and at least one executable fixture.
- Text-only checks (`document includes phrase X`) are not sufficient evidence for visual conformance.
- Structural snapshots are useful for regression detection, but they do not substitute for computed-style, geometry, contrast, and parity assertions.

---

## 1. Foundational Axiom

> **The interface must read as a serious instrument, not a decorative surface.**

Visual elements exist to communicate structure, state, and causality.
Decoration without informational value is disallowed.

---

## 2. Spatial Model: Shallow Physicality

### Doctrine

* The UI exists on a small number of visual planes.
* Planes imply depth through shadow and occlusion, not perspective or texture.
* Depth is informational, not ornamental.

### Requirements

* Elevation levels MUST be few (typically 2-4).
* Shadows MUST be soft, low-contrast, and directional.
* Boundaries MUST use semantic roles (`subtle`, `standard`, `strong`, `focus`) rather than ad hoc styling.
* Boundaries MAY separate controls, states, and regions when they improve legibility, affordance, or accessibility contrast.

### Prohibitions

* No skeuomorphism.
* No hard outlines as default separators for every element.
* No excessive z-stacking.

---

## 3. Motion as Semantic Explanation

### Doctrine

Motion exists to explain **what changed and why**.

### Requirements

* State transitions SHOULD animate when motion clarifies causality or spatial continuity.
* The following classes MUST NOT animate and MUST snap to final state: `critical-alert`, `rapid-command-feedback`, `high-frequency-update`.
* Motion duration SHOULD be brief (approximately 120-250 ms).
* Easing MUST be non-linear (spring or ease-out).
* Motion class names MUST map to runtime-observable transition categories used by conformance and reliability telemetry.

### Prohibitions

* No motion as decoration.
* No linear easing.
* No animations that block interaction.
* No unregistered motion category names in production code.

### Accessibility

* Motion MUST be globally suppressible without loss of meaning.

---

## 4. Typography-First Hierarchy

### Doctrine

Typography is the primary structural element of the UI.

### Requirements

* Text MUST precede icons in conveying meaning.
* Hierarchy MUST be established through size, weight, and spacing.
* Fonts SHOULD support variable axes and optical sizing.
* Fallback stacks MUST preserve readability for supported script coverage.

### Prohibitions

* Icon-only controls for primary actions.
* Excessive font size variation.
* Decorative typefaces.

---

## 5. Density and White Space Discipline

### Doctrine

The UI should feel calm, not empty.

### Requirements

* Controls within a component SHOULD be dense.
* Separation SHOULD occur between conceptual regions, not individual elements.
* White space MUST communicate grouping.
* Fine-pointer control geometry SHOULD target compact instrument density (commonly 32 px class minima).
* Coarse-pointer lanes MUST preserve effective hit targets of at least 44 x 44 px, including hit-slop when visual geometry is smaller.

### Prohibitions

* Vast empty regions.
* Floating controls without context.
* "Gallery-style" layouts for tool interfaces.

---

## 6. Color Modes and Visual Lanes

### Doctrine

Dark mode is primary, but not exclusive.

### Requirements

* Dark mode MUST be designed independently, not inverted.
* Backgrounds SHOULD be dark gray, not pure black.
* Text SHOULD be off-white, not pure white.
* Light, high-contrast, and forced-colors lanes MUST be tokenized and testable.
* Full conformance claims MUST NOT be made unless all required lanes pass their mapped fixtures.

### Prohibitions

* Automatic color inversion.
* High-saturation accents as defaults.
* Loss of depth cues in dark mode.
* "Supported in spec only" claims when runtime lane activation is absent.

---

## 7. OS Neutrality

### Doctrine

The UI must belong to itself, not to an operating system.

### Requirements

* Widgets MUST NOT mimic native OS controls.
* Visual language MUST be self-consistent across platforms.
* Rendering MUST feel browser-native without inheriting browser aesthetics.

### Prohibitions

* macOS / Windows cosplay.
* Title-bar metaphors as visual mimicry.
* System-native widget cloning.

---

## 8. Directionality and Locale Robustness

### Doctrine

Presentation must remain coherent across writing systems and directionality.

### Requirements

* Layout and spacing SHOULD use logical properties where practical.
* RTL lanes MUST preserve affordance order, focus visibility, and selection clarity.
* Directional iconography MUST mirror when semantics require it.

### Prohibitions

* Hardcoded left/right layout semantics for core component structure.
* Locale-specific clipping or fallback that degrades state legibility.

---

## 9. Windows as Instruments, Not Decorations

### Doctrine

Windows are containers for tasks, not visual ornaments.

### Requirements

* Window chrome MUST be minimal and functional.
* Focus state MUST be visually unambiguous.
* Window boundaries MUST be clear without heavy framing.

### Prohibitions

* Overlapping ornamental chrome.
* Draggable regions without semantic meaning.
* Fake 3D window effects.

---

## 10. What This System Must Never Look Like

The following aesthetics are explicitly disallowed:

* Heavy gradients
* Glossy highlights
* Thick borders used everywhere
* Beveled controls
* Icon-only toolbars
* Floating translucent glass effects
* 1990s dialog metaphors

These signal **toolkit demos**, not serious systems.

---

## 11. Evidence Freshness and Audit Integrity

Doctrine quality depends on current evidence.

### Requirements

* Baseline accessibility and conformance audits MUST record source token version/date and measurement method.
* Historical failures MAY be retained for traceability, but current pass/fail status MUST be explicitly separated.
* Draft artifacts MUST NOT be cited as proof of production conformance unless accompanied by passing executable runs.

### Prohibitions

* Mixing historical and current measurements without explicit labeling.
* Treating stale audits as current release evidence.

---

## 12. Visual North Star

The intended visual target can be summarized as:

> *Editorial clarity x developer tooling seriousness x long-term usability*

Or more plainly:

> **A calm, information-dense instrument designed to be trusted.**

---

## 13. Longevity Test

Before adopting any visual feature, ask:

1. Does this explain state or structure?
2. Would this look embarrassing in five years?
3. Does removing it reduce clarity?
4. Can this be measured by an existing contract/fixture path?

If the answer to (3) is "no," it does not belong.
If the answer to (4) is "no," it is not yet release-gate material.

---

## 14. Closing Principle

> **Restraint is not minimalism.
> Restraint is discipline.**

This doctrine prioritizes legibility, durability, and seriousness over novelty.
