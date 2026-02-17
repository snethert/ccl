# Web UI

**Status:** Design stage (MVP-2)
**Priority:** Deferred until MVP-1 (Library/Embedded Mode) ships
**Spec count:** 62 artifacts across 10 domains

## What This Is

This directory contains the complete specification suite for the CCL web-based windowing and UI toolkit. These are **design documents** — normative contracts written ahead of implementation to guide future development.

Nothing here is running yet. The runtime it depends on (MVP-1) is still blocked on FASL loading. These specs exist so that when implementation begins, the target is unambiguous and a separate team could build it without ad hoc interpretation.

## Relationship to the WASM Port

The CCL WASM port follows a two-mode, two-phase strategy:

1. **MVP-1: Library/Embedded Mode** — Single-runner, postMessage interface, works anywhere. Current focus. See `doc/wasm/roadmap.md`.
2. **MVP-2: Full Runtime Mode** — Multi-runner, SharedArrayBuffer, secure context required. This is where `web-ui` lives.

`web-ui` is entirely MVP-2 infrastructure. It requires a working kernel, compiled Lisp modules, and a stable runtime bridge — none of which exist yet.

## Directory Structure

```
web-ui/
  DEV-PLAN.md                 # Phased development roadmap (Phases 0-10)
  FRONT-END-DEV-PLAN.md       # Lisp<->JS bridge integration plan
  PRODUCTION-SPEC-GAP-REGISTER.md  # Gap analysis and production gate status
  ui-doctrine.md              # Visual presentation principles
  spec/                       # Normative specification artifacts
  bridge/                     # JS bridge modules (runtime<->UI)
  src/                        # UI core implementation modules
  tests/                      # Test suites and conformance fixtures
  scripts/                    # Build and gate automation
```

## Spec Organization

| Domain | Specs | Purpose |
|---|---|---|
| Governance | 5 | Spec index, normative language, glossary, ratification, conformance gates |
| Visual/UI | 10 | Tokens, component states, motion, accessibility, conformance runner |
| Core Model | 8 | Event log, snapshots, state graph, commands, focus/selection |
| Rendering | 4 | Backend lifecycle, DOM, Canvas, WebGL contracts |
| Persistence | 13 | Storage model, sync, conflict, leases, corruption recovery |
| Performance | 3 | SLOs, telemetry sampling, scale testing |
| Commands/Debug | 5 | Keybindings, IME, location provider, stepper, breakpoints |
| Runtime Bridge | 4 | Wire formats, envelope, protocol negotiation |
| Security/Ops | 4 | Capability model, observability, rollout, incident runbook |
| Evidence | 5 | Conformance matrix, requirements index, readiness review |

Entry point: [spec/spec-index-v1.md](spec/spec-index-v1.md)

## Reading Order

For understanding the design:

1. `ui-doctrine.md` — Visual philosophy
2. `DEV-PLAN.md` — Phase structure and kernel dependencies
3. `FRONT-END-DEV-PLAN.md` — How Lisp and JS interact
4. `spec/glossary-v1.md` — Terminology
5. Domain specs as needed (start with `command-routing-algorithm-v1.md` and `renderer-backend-contract-v1.md`)

## Current Gate Status

See `PRODUCTION-SPEC-GAP-REGISTER.md` for auto-generated gate results.

- `kernel-free-v1` (JS-only, no WASM runtime): **PASS**
- `kernel-full-v1` (with WASM runtime): **BLOCKED** (missing kernel artifacts)
