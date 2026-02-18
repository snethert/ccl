# Contributing to Specs

How to add, modify, or expand the specification hierarchy.

## Spec Structure

```
spec/
  ARCHITECTURE.md              Level 0: system-wide (one file)
  CONTRIBUTING.md              This file
  <subsystem>/
    OVERVIEW.md                Level 1: subsystem overview
    doctrine.md                Optional: design principles
    contracts/
      <component>.md           Level 2: one per component (50-80 lines)
    checks/
      <component>.test.mjs     One per contract
      run-all.mjs              Runs all checks for this subsystem
```

## Adding a New Subsystem

1. Create `spec/<name>/OVERVIEW.md` following the template below
2. Create `spec/<name>/contracts/` and `spec/<name>/checks/`
3. Add the subsystem to the table in `spec/ARCHITECTURE.md`
4. Write contracts and checks per the templates below

### OVERVIEW.md Template

```markdown
# <Subsystem Name>

## Status
⏸️ Not started | ⚠️ In progress | ✅ Complete

## What This Subsystem Does
[3-5 sentences]

## Dependencies
- Requires: [what must exist first]
- Provides: [what this enables]

## Component Map
[Diagram showing components and relationships]
[Each component links to its contract]

## Implementation Order
| # | Contract | Depends On | Description |
|---|----------|------------|-------------|
| 1 | [name](contracts/name.md) | — | One-line description |
| 2 | [name](contracts/name.md) | 1 | One-line description |

## Key Design Decisions
[Bullet points: real architectural decisions, not aspirations]

## Conformance
Run all checks: `node spec/<subsystem>/checks/run-all.mjs`
```

## Adding a New Contract

1. Create `spec/<subsystem>/contracts/<component>.md` using the rigid format below
2. Create `spec/<subsystem>/checks/<component>.test.mjs` with numbered stubs
3. Add the contract to the Implementation Order table in OVERVIEW.md
4. Update ARCHITECTURE.md subsystem table if contract count changed

### Contract Template (rigid — every contract follows this exactly)

```markdown
# <Component Name>

## Status
⏸️ Not started | ⚠️ In progress | ✅ Complete

## Purpose
[2-3 sentences: what and why]

## Depends On
- [contract](contract.md) — [why]
(or "None.")

## Interface
[Exact data shapes, function signatures, message formats]
[MOST IMPORTANT SECTION — put near top so it survives context compression]

## Invariants
[Numbered. Things that must ALWAYS be true. Each becomes a test assertion.]
1. ...
2. ...

## Behavior
[Numbered. Input→output rules. Each becomes a test case.]
1. ...
2. ...

## Anti-Patterns
[Numbered. Things this component must NEVER do. Each becomes a negative test.]
1. ...
2. ...

## Out of Scope
[What this contract does NOT cover. Prevents AI scope-creep.]

## Conformance Check
Run: `node spec/<subsystem>/checks/<component>.test.mjs`
```

### Check Stub Template

```javascript
/**
 * Conformance checks for: <component>
 * Contract: spec/<subsystem>/contracts/<component>.md
 *
 * Stub — all checks skip until implementation exists.
 */

const checks = [
  { id: 'invariant.1', desc: '<from contract>' },
  { id: 'behavior.1', desc: '<from contract>' },
  { id: 'anti-pattern.1', desc: '<from contract>' },
  // One entry per numbered item in the contract
];

export async function run() {
  let pass = 0, fail = 0, skip = 0;
  for (const check of checks) {
    // TODO: Replace with real assertions against implementation
    console.log(`SKIP ${check.id} — ${check.desc} (not implemented)`);
    skip++;
  }
  return { pass, fail, skip };
}
```

## Modifying an Existing Contract

**Rules:**
- Changing the **Interface** section requires human approval
- Adding Invariants/Behaviors/Anti-Patterns: add at the end (don't renumber)
- Removing items: mark as `(removed)` rather than deleting (preserves check IDs)
- Always update the corresponding check file to match
- Run `node spec/<subsystem>/checks/run-all.mjs` after any change

## Modifying ARCHITECTURE.md

This file is read first by every AI. Changes affect all downstream work.
**Always require human approval before modifying.**

## Check Output Format

All checks use structured output with IDs matching contract section numbers:
```
PASS invariant.1 — Description
FAIL behavior.3 — Description
  Expected: ...
  Got: ...
SKIP anti-pattern.2 — Description (not implemented)
```

## Human Escalation

An AI MUST stop and consult a human when:
1. A conformance check fails and the fix requires changing the spec
2. The task requires functionality not covered by any contract
3. Two contracts appear to contradict each other
4. Implementation needs a new dependency not in the contract
5. The Interface section of a contract needs to change
6. Adding a contract would change the Implementation Order of existing contracts
