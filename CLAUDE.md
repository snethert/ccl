# CCL WASM — Development Instructions

## Project Context

This is a port of Clozure Common Lisp to WebAssembly. Two deployment modes:
- **MVP-1: Library Mode** (current focus) — single-runner, blocked by FASL loading
- **MVP-2: Full Runtime Mode** (future) — multi-runner, web-ui, deferred

Current task status: see [TODO.md](TODO.md).

## Spec-Driven Development

All implementation work is driven by specs in `spec/`.

### Before implementing anything:

1. Read `spec/ARCHITECTURE.md` for system context
2. Read the relevant subsystem `OVERVIEW.md` for component map and implementation order
3. Read the specific contract for the component you're modifying

### After modifying any source file:

1. Run the corresponding conformance check:
   ```bash
   node spec/web-ui/checks/<contract>.test.mjs
   ```
2. If it fails, **STOP and report** — do not silently fix

### Human escalation (STOP and ask):

- Conformance check fails and the fix requires changing the spec
- Task needs functionality not covered by any contract
- Two contracts appear to contradict each other
- Need to add a dependency not listed in the contract
- Need to change a contract's Interface section

### Spec locations:

| Spec | Location |
|------|----------|
| System architecture | `spec/ARCHITECTURE.md` |
| Web-UI subsystem | `spec/web-ui/OVERVIEW.md` |
| Web-UI contracts | `spec/web-ui/contracts/*.md` |
| Web-UI checks | `spec/web-ui/checks/*.test.mjs` |
| Web-UI doctrine | `spec/web-ui/doctrine.md` |
| Kernel docs | `doc/wasm/` (being migrated to `spec/kernel/`) |

### Archived reference material:

The original CODEX-generated web-ui specifications are preserved at
`doc/archive/web-ui-codex-2026-02/`. This is read-only reference — never modified.

## Build Commands

```bash
# Full rebuild (kernel, subprims, boot image, modules, root image)
scripts/wasm/rebuild-everything.sh

# Check if build artifacts are stale
scripts/wasm/check-freshness.sh

# Syntax-check Lisp files before rebuild
scripts/wasm/check-lisp-syntax.sh --modified

# Run kernel smoke tests
node scripts/wasm/tests/all-smoke.mjs

# Run web-ui conformance checks
node spec/web-ui/checks/run-all.mjs
```

## Standing Rules

### Code Quality
- After editing `.lisp` files, run: `scripts/wasm/check-lisp-syntax.sh <file>`
- Before debugging runtime bugs, run: `scripts/wasm/check-freshness.sh`
- Artifact alignment: kernel, subprims, boot image, modules must be from the same build

### Architecture
- ARM32 is the reference architecture — check `compiler/ARM/` first for compiler/runtime bugs
- Two-module WASM: kernel (`wasmcl.wasm`) and subprims (`subprims.wasm`) are separate, linked at runtime
- UTF-8 at every CL↔JS boundary, no exceptions
- Capabilities fail explicitly (`CAPABILITY-UNAVAILABLE`), never silent fallback

### Terminology
- Use: "Library Mode" / "MVP-1" and "Full Runtime Mode" / "MVP-2"
- Do NOT use: "replacement", "deprecation", "legacy", "ASCII-first"
- Status markers: ✅ Working | ⚠️ Partial | ❌ Not working | ⏸️ Deferred

### Build
- Always pass `--boot-modules` when running `make-real-image.mjs` directly
- Module build takes ~6 minutes — don't skip or assume cached artifacts are fresh
- 8-minute rule: if a build runs 8+ min with no output, kill and restart with tracing
