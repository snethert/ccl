# Subprims Execution Prompt (Guiding Document)

Use this document as the single source of truth while iterating through WASM subprims. It is designed to let the agent work without human intervention while maintaining attention, tracking progress, and keeping the work-remaining report current.

## Goal

Implement missing or incomplete WASM subprims in `lisp-kernel/wasm-subprims-provider.c` until the subprims table is functionally complete for the current WASM bring-up. After each subprim (or tight batch), update status docs and this prompt's working memory.

## Files

- Status report: `doc/wasm/subprims-work-remaining.md`
- Generator: `scripts/wasm/update_subprims_work_remaining.py`
- Provider source: `lisp-kernel/wasm-subprims-provider.c`
- Kernel stubs: `lisp-kernel/wasm-kernel-stubs.c`
- Subprims list: `doc/wasm/subprims-map.json`
- Tier guidance: `doc/wasm/subprims-provider-plan.md`
- Semantics reference: `lisp-kernel/arm-spentry.s`, `lisp-kernel/x86-subprims64.s`

## Hard Rules

- Single focus: only one subprim at a time. Do not hop to another until this one is either done or explicitly blocked.
- After each subprim, update:
  1) `doc/wasm/subprims-work-remaining.md` via the generator script.
  2) This document's **Working Memory** section.
- Maintain attention: keep a running checklist for the active subprim and complete it before moving on.

## Prioritization

Work order is deterministic:

1. Tier 0 and Tier 1 subprims with `Work Remaining = behavioral gap`.
2. Non-tier subprims with `behavioral gap`.
3. `validation only` (only if needed for tests or integration).
4. `stub` or `missing` (should be rare given current provider).

## Definition of Done (per subprim)

- All behavioral gaps removed or justified as correct validation traps.
- Traps remaining are input validation only (type/bounds/null/alloc) or explicitly required by ABI.
- Relevant smoke tests pass or have been added.
- Status doc updated and shows the new classification.

## Standard Loop (per subprim)

1. **Select subprim**
   - Read `doc/wasm/subprims-work-remaining.md` and pick the top priority based on the rule above.

2. **Analyze current implementation**
   - Open the subprim body in `lisp-kernel/wasm-subprims-provider.c`.
   - Identify every `wasm_subprims_trap()` and the condition that triggers it.
   - Decide which traps are validation (keep) vs behavioral gaps (must fix).

3. **Find reference semantics**
   - Search `lisp-kernel/arm-spentry.s` and `lisp-kernel/x86-subprims64.s` for the subprim name and related helper labels.
   - Document any required invariants (register use, vsp/tsp effects, GC visibility, unwind protocol).

4. **Implement**
   - Implement missing logic in provider.
   - Keep validation traps, but reduce or eliminate behavioral gap traps.
   - Add helper functions if repeated logic is needed. Keep them local and named `wasm_*`.

5. **Add or update tests**
   - Prefer existing WASM smoke tests in `doc/wasm/js/`.
   - If missing, add a new small smoke test focusing on the subprim behavior.

6. **Update docs**
   - Run `python3 scripts/wasm/update_subprims_work_remaining.py`.
   - Update Working Memory (below).

7. **Next selection**
   - Choose the next subprim based on priorities and update Working Memory.

## Working Memory (update after each subprim)

- Last completed subprim: `_SPdefault_optional_args`
- Changes made: reviewed `_SPdefault_optional_args`; no code changes needed (nil-filling for missing optionals matches ARM behavior).
- Tests run: none
- Remaining traps (if any) and why: `_SPdefault_optional_args` still traps on invalid runtime state (null TCR/VSP).
- Next subprim (single): `_SPdebind`
- Backlog (top 5): `_SPdebind`, `_SPgets32`, `_SPgetu32`, `_SPconslist`, `_SPkeyword_bind`
- Blockers/questions: Interrupt-level subprims still lack real pending-interrupt handling on wasm; no host hook yet.

## Current State

- Last completed subprim: `_SPdefault_optional_args`
- Changes made: reviewed `_SPdefault_optional_args`; no code changes needed (nil-filling for missing optionals matches ARM behavior).
- Tests run: none
- Remaining traps (if any) and why: `_SPdefault_optional_args` still traps on invalid runtime state (null TCR/VSP).
- Next subprim (single): `_SPdebind`
- Backlog (top 5): `_SPdebind`, `_SPgets32`, `_SPgetu32`, `_SPconslist`, `_SPkeyword_bind`
- Blockers/questions: interrupt-level subprims need pending-interrupt handling on wasm; no host hook yet.

## Command Snippets

- Update report:
  - `python3 scripts/wasm/update_subprims_work_remaining.py`

## Quality Guardrails

- Avoid changing semantics in unrelated code paths.
- Keep defensive traps when they enforce runtime invariants.
- If a change affects the ABI or register discipline, document it inline in the provider.
- Prefer small, isolated commits of behavior; do not batch unrelated subprims.

## Notes

This prompt is meant to be used repeatedly without manual intervention. If a subprim is blocked by missing compiler support or runtime state, record it in Working Memory and move to the next priority item.
