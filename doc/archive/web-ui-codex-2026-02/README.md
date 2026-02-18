# Web UI

**Status:** Design stage (MVP-2)  
**Deployment policy:** `full-runtime-v1` only (SAB + worker atomics + shared-memory thread path)

## What This Is

This directory contains the specification suite and implementation scaffolding for the CCL browser UI runtime.
The specs are normative design artifacts intended to be implementation-ready for a separate team.

## Relationship to the WASM Port

The CCL WASM effort is split into two runtime tracks:

1. **MVP-1 Library/Embedded runtime**: broad portability and bring-up.
2. **MVP-2 Full runtime UI track (`web-ui`)**: full shared-memory runtime requirements.

`web-ui` is explicitly scoped to MVP-2 full-runtime deployment and does not support non-SAB fallback lanes.

## Directory Structure

```text
web-ui/
  DEV-PLAN.md
  FRONT-END-DEV-PLAN.md
  PRODUCTION-SPEC-GAP-REGISTER.md
  ui-doctrine.md
  spec/
  bridge/
  src/
  tests/
  scripts/
```

## Canonical Sources

1. `spec/spec-index-v1.md` for authoritative artifact/profile registry.
2. `spec/normative-language-and-conformance-v1.md` for requirement/evidence rules.
3. `PRODUCTION-SPEC-GAP-REGISTER.md` for design-stage gate status.

## Current Gate Posture

Conformance claim scope is `full-runtime-v1`.
Current blocker status is determined by `PRODUCTION-SPEC-GAP-REGISTER.md` auto-generated gate output.

## Historical Context

Older docs and reviews may mention prior dual-scope claim labels.
Those labels are superseded; current policy is single-scope `full-runtime-v1`.
