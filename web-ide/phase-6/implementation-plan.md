# Phase 6 Detailed Plan: Customization and Beginner Mode

## Document Control
- Status: Complete
- Last Updated: February 8, 2026
- Parent Plan: `web-ide/implementation-plan.md`
- Doctrine Sources:
  - `web-ide/ide-doctrine.md`
  - `web-ui/ui-doctrine.md`
  - `web-ide/phase-0/*.md`
  - `web-ide/phase-1/implementation-plan.md`
  - `web-ide/phase-2/implementation-plan.md`
  - `web-ide/phase-3/implementation-plan.md`
  - `web-ide/phase-4/implementation-plan.md`
  - `web-ide/phase-5/implementation-plan.md`

## Phase 6 Outcome
Deliver a configurable IDE that stays as one coherent product: users can customize theme and keybindings and enable Beginner Mode without forking command semantics or fragmenting the interface model.

## Scope
### In Scope
- Settings model for user, project, and session customization.
- Theme presets and token overrides with deterministic precedence.
- Per-pane keymap profiles and conflict diagnostics.
- Beginner Mode policy layer that reduces visible surface while preserving the same command system.
- Inline explanations and guidance text for beginner-facing actions.
- Import and export for customization profiles.
- Automated acceptance coverage for customization flows.

### Out of Scope
- New runtime protocol families and backend transport work (Phase 5 and beyond).
- Major performance optimization and benchmark program (Phase 7).
- Full accessibility program and audit tooling expansion (Phase 7).
- Multi-user shared preferences or cloud profile sync.

## Baseline
- Phase 0 through Phase 5 architecture and core behavior are complete.
- Typed command model and command history are stable and replayable.
- Theme token model and renderer parity exist across DOM and canvas/WebGL.
- Workspace snapshots and sessions are available for restore.

## Progress Snapshot
- M1 `CZ1`: Complete.
- M2 `CZ2`: Complete.
- M3 `CZ3`: Complete.
- M4 `CZ4`: Complete.
- M5 `CZ5`: Complete.
- M6 `CZ6`: Complete.
- M7 `CZ7`: Complete.

## Phase 6 Success Criteria
- Users can switch theme presets and apply scoped token overrides without visual breakage.
- Users can switch keymap profiles per pane and resolve conflicts deterministically.
- Beginner Mode hides advanced verbs by policy, not by creating a separate command stack.
- Explanations are available inline for beginner-facing actions and condition recovery.
- Customization profiles can be exported and imported with schema validation.
- Customization state survives save and restore cycles across sessions.

## Workstreams

## CZ1: Customization Schema and Precedence
### Goal
Define the customization data model, precedence rules, and migration strategy.

### Tasks
1. Define a versioned customization schema envelope with sections for:
   - `theme`
   - `keymaps`
   - `beginnerMode`
   - `safetyPolicies`
2. Define precedence layers:
   - built-in defaults
   - user profile
   - project profile
   - session overrides
3. Define merge semantics for each section (replace, deep-merge, deny-list).
4. Add migration hooks for schema evolution.

### Deliverables
- Schema updates in `web-ui/src/persistence/schema.mjs`.
- Serialization and migration updates in:
  - `web-ui/src/persistence/serialize.mjs`
  - `web-ui/src/persistence/migrate.mjs`
- Validation helpers for customization payloads.

### Exit Criteria
- Customization data validates and round-trips deterministically.
- Layered precedence is testable and deterministic.

## CZ2: Theme Presets and Token Overrides
### Goal
Provide opinionated themes with controlled overrides that preserve doctrine cohesion.

### Tasks
1. Define built-in theme presets with names, descriptions, and token sets.
2. Add token override support with allow-list constraints.
3. Add runtime theme switching for DOM and canvas/WebGL parity.
4. Add reset and fallback behavior for invalid token overrides.
5. Add preview support for applying theme changes before commit.

### Deliverables
- Theme preset registry in `web-ui/src/theme.mjs`.
- Theme customization commands and effects in:
  - `web-ui/src/state.mjs`
  - `web-ui/src/customization.mjs`
- Updated style/token application for DOM and renderers.

### Exit Criteria
- Theme preset switches are immediate and reversible.
- Invalid overrides degrade safely to known-good values.

## CZ3: Keymap Profiles and Conflict Resolution
### Goal
Allow pane-specific keymap customization while keeping command dispatch deterministic.

### Tasks
1. Define keymap profiles:
   - Editor profile (Emacs-like baseline)
   - REPL profile (readline-like baseline)
   - Debugger profile (single-key baseline)
2. Add per-pane keymap assignment in workspace state.
3. Implement conflict detection with deterministic resolution order.
4. Expose conflict diagnostics in keybinding viewer and command palette.
5. Add import/export format for keymap bindings.

### Deliverables
- Keymap profile model in:
  - `web-ui/src/commands.mjs`
  - `web-ui/src/state.mjs`
- Resolver tracing and conflict diagnostics in keybinding surfaces.
- Tests for conflict resolution and profile switching.

### Exit Criteria
- Keybinding collisions are visible and resolved deterministically.
- Pane-specific profiles work without cross-pane command regressions.

## CZ4: Beginner Mode Policy Layer
### Goal
Implement a reversible training-wheels layer over the same command system.

### Tasks
1. Define Beginner Mode policy flags for command visibility and confirmation.
2. Mark advanced commands with policy metadata instead of creating separate implementations.
3. Add Beginner Mode toggle and workspace/session persistence.
4. Gate destructive or advanced operations behind explicit confirmation when Beginner Mode is on.
5. Keep command ids and history format unchanged across modes.

### Deliverables
- Beginner policy metadata updates in typed command registry.
- Mode toggle commands and persistence wiring.
- Command-palette filtering and context-menu filtering by mode policy.

### Exit Criteria
- Beginner Mode changes exposure, not behavior semantics.
- Switching modes does not invalidate saved command history.

## CZ5: Explanations and Guided Surfaces
### Goal
Add contextual explanations so beginner users can build accurate mental models.

### Tasks
1. Add explanation strings for core beginner-visible commands and actions.
2. Add inline "why am I seeing this?" links for problems and condition flows.
3. Add light-weight guidance in inspector/debugger action bars.
4. Ensure explanations are concise and avoid blocking primary workflows.
5. Persist "dismissed guidance" flags per session.

### Deliverables
- Guidance content model and wiring in state and widgets.
- Condition/problem explanation hooks in:
  - `web-ui/src/state.mjs`
  - `web-ui/src/widgets.mjs`
- Tests for explanation visibility and persistence.

### Exit Criteria
- Beginner users can discover action intent without external docs.
- Experts can suppress guidance without disabling core functionality.

## CZ6: Profile Portability and Management
### Goal
Make customizations portable and auditable.

### Tasks
1. Define export format for theme, keymap, and beginner policy sections.
2. Add import flow with schema validation and conflict reporting.
3. Add profile management commands:
   - create profile
   - apply profile
   - rename profile
   - delete profile
4. Add safe rollback to previous profile after failed import.

### Deliverables
- Profile import/export helpers in persistence modules.
- Profile management command wiring and UI surface.
- Tests for import validation and rollback behavior.

### Exit Criteria
- Profiles can be moved between workspaces without manual edits.
- Invalid profiles never corrupt existing customization state.

## CZ7: Phase 6 Acceptance and Quality Gates
### Goal
Codify customization and beginner-mode reliability as automated gates.

### Tasks
1. Add Phase 6 test suites for:
   - customization schema precedence
   - theme preset/override application
   - keymap profile switching and conflict resolution
   - beginner mode command filtering and confirmations
   - profile import/export round trip
2. Add at least one integration flow:
   - apply profile -> switch mode -> run commands -> save session -> restore -> verify parity.
3. Wire Phase 6 suites into `web-ui/package.json` `test:sandbox`.

### Deliverables
- `web-ui/tests/phase-6-customization.test.mjs`
- `web-ui/tests/phase-6-theme-profiles.test.mjs`
- `web-ui/tests/phase-6-keymaps.test.mjs`
- `web-ui/tests/phase-6-beginner-mode.test.mjs`
- `web-ui/tests/phase-6-integration.test.mjs`

### Exit Criteria
- Phase 6 acceptance suites pass.
- Existing suites remain green.

## Completion
- Landed schema migration `4 -> 5` for layered customization persistence.
- Landed theme presets/overrides, keymap profile assignment, and conflict diagnostics.
- Landed Beginner Mode command policy filtering, confirmation gates, and guidance dismissal persistence.
- Landed customization profile export/import with validation and rollback payload.
- Landed and wired Phase 6 acceptance suites in `web-ui/package.json`.
- Validation command: `cd web-ui && npm test` (passing).

## Milestone Sequence
1. M1: CZ1 complete (schema, precedence, migrations).
2. M2: CZ2 complete (theme presets and token overrides).
3. M3: CZ3 complete (keymap profiles and conflict diagnostics).
4. M4: CZ4 complete (Beginner Mode policy layer).
5. M5: CZ5 complete (explanations and guided surfaces).
6. M6: CZ6 complete (profile import/export and management).
7. M7: CZ7 complete (acceptance gates and signoff).

## Implementation Strategy
1. Land schema and precedence first to avoid rework in every surface.
2. Implement theme and keymap customization before Beginner Mode to keep policy work orthogonal.
3. Add Beginner Mode as command metadata filtering, never as duplicate command implementations.
4. Add profile portability only after local customization semantics are stable.
5. Run full `web-ui` test suite at every milestone gate.

## Code Focus Areas
- `web-ui/src/persistence/schema.mjs`
- `web-ui/src/persistence/serialize.mjs`
- `web-ui/src/persistence/migrate.mjs`
- `web-ui/src/theme.mjs`
- `web-ui/src/commands.mjs`
- `web-ui/src/typed-commands.mjs`
- `web-ui/src/state.mjs`
- `web-ui/src/widgets.mjs`
- `web-ui/tests/*`

## Risks and Mitigations
- Risk: customization options fragment UX into inconsistent variants.
  - Mitigation: enforce token and command policy constraints with validation.
- Risk: keymap conflicts create non-deterministic command dispatch.
  - Mitigation: single resolver precedence plus conflict diagnostics.
- Risk: Beginner Mode diverges behavior from Expert Mode.
  - Mitigation: same command ids and handlers, visibility/confirmation policy only.
- Risk: profile import introduces invalid state.
  - Mitigation: strict schema validation and transactional rollback.
- Risk: excessive settings complexity harms discoverability.
  - Mitigation: opinionated defaults and a minimal first-run surface.

## Decision Gates (Expected)
1. Settings precedence policy:
   - Option A (recommended): defaults < user < project < session override.
   - Option B: defaults < project < user < session override.
2. Keymap conflict policy:
   - Option A (recommended): deterministic resolver order + explicit diagnostics, no silent overrides.
   - Option B: last-write wins with warning logs only.
3. Beginner Mode default:
   - Option A (recommended): enabled for first-time workspace only, reversible anytime.
   - Option B: disabled by default, opt-in only.
4. Profile exchange format:
   - Option A (recommended): JSON with schema version and strict validation.
   - Option B: permissive JSON with best-effort normalization.

## Phase 6 Signoff Conditions
- M1 through M7 complete.
- `cd web-ui && npm test` passes.
- Phase 6 acceptance suites pass.
- Theme and keymap profiles persist across session restore.
- Beginner Mode remains behaviorally equivalent to Expert Mode at command-handler level.
