# Security and Capability Model

## Status
⏸️ Not started

## Purpose

Fail-closed startup gate for Full Runtime Mode (MVP-2) and capability-gated
command execution. Twelve prerequisite checks must pass before the runtime
starts. Commands require explicit capability grants. Safe mode is a global
kill-switch that blocks all capability-gated execution.

## Depends On
- [command-system](command-system.md) — capability gates are part of command enablement

## Interface

```
StartupCheck {
  run_id:           string
  sequence:         integer
  check_id:         string        // SRG-01..SRG-12
  required:         boolean
  status:           "pass" | "fail"
  fail_code:        string | null // E001..E012
  message:          string
  observed:         any
  pass_criteria:    string
  contradiction_ids: string[]
  remediation:      string
}

CapabilityState {
  safeMode:  boolean              // default false
  granted:   string[]             // deduped, lexically sorted
  log:       CapabilityLogEntry[] // append-only
}

CapabilityLogEntry {
  id: string, action: string, capability: string,
  reason: string, taskId: string|null,
  windowId: string|null, commandId: string|null
}

CapabilityPolicy {
  defaultDecision: "ask" | "grant" | "deny"  // default "ask"
  rules: [{id, capability, decision, reason}]
}
```

**Startup checks (SRG-01..SRG-12):**
01: Cross-origin isolation, 02: SharedArrayBuffer, 03: Worker Atomics,
04: WASM shared-memory/threads, 05: Worker READY handshake,
06: OPFS directory access, 07: SyncAccessHandle parity,
08: Hot-path shared-memory transport, 09: UI bridge shared transport,
10: Persistence profile match, 11: Strict no-fallback policy,
12: Runtime thread capability boundary

## Invariants

1. Startup gate mode is always strict: `startup_gate_mode="strict"`, `allow_fallback=false`
2. Check execution stops at first failure — no partial startup
3. `load-image.mjs` terminates on gate failure or malformed summary
4. `granted[]` is always deduplicated and lexically sorted
5. Capability log is append-only — entries are never mutated or removed
6. Safe mode blocks ALL capability-gated commands regardless of grants
7. Policy evaluation is deterministic: same (state, policy, inputs) → same decision
8. Disabling safe mode does NOT auto-grant missing capabilities

## Behavior

1. Startup applies only to `full-runtime-v1` deployment mode
2. All 12 checks execute in sequence SRG-01 through SRG-12; stop at first failure
3. Startup summary records `results_digest` matching the emitted check record set
4. `hasCapability(cap)` returns false when safe mode is enabled
5. Policy rules evaluate first-match: explicit capability → wildcard `*` → defaultDecision
6. Grant/revoke operations log to the capability log with action and reason
7. `setSafeMode(true)` disables all capability-based escapes immediately
8. Pending capability requests process in stable list order under auto-run policy
9. `ui.dom.escape` is always capability-gated (default capability `dom.escape`)

## Anti-Patterns

1. Never silently downgrade transport/privilege on startup failure
2. Never skip or reorder startup gate checks
3. Never allow missing capability to silently degrade execution
4. Never auto-grant capabilities when safe mode is disabled
5. Never mutate the capability log (append-only)
6. Never emit startup summary with mismatched results_digest
7. Never allow non-deterministic policy evaluation

## Out of Scope

- Library Mode (MVP-1) security (no startup gate needed)
- Network security / CSP headers (deployment concern)
- User authentication (not part of the capability model)

## Conformance Check
Run: `node spec/web-ui/checks/security.test.mjs`
