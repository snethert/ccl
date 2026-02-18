# CCL WASM — System Architecture

## What This System Is

A Common Lisp system derived from CCL's architecture, compiled to WebAssembly,
hosted by a JavaScript microkernel. WASM instances serve as processes ("runners").
The JS side provides capabilities the runtime cannot provide itself: I/O, spawning,
linking, scheduling. The Lisp side is a real CL environment — Lisp-2, macros,
reader/printer, dynamic loading — honest about the web as a platform.

## Deployment Modes

### MVP-1: Library/Embedded Mode (current focus)

Single WASM runner, postMessage interface, works in any browser context.
No threading, no secure context, no persistence. Embeddable via `<script>` tag.
**Status: Blocked by FASL loading regression.**

### MVP-2: Full Runtime Mode (future)

Multi-runner with Web Workers, SharedArrayBuffer + Atomics, secure context required
(COOP + COEP headers). Full IDE capabilities, storage backend, web-ui integration.
**Status: Deferred until MVP-1 ships.**

Both modes are first-class targets. No silent degradation between them.

## Component Map

```
┌─────────────────────────────────────────────────────┐
│                    Browser / Node.js                 │
│                                                     │
│  ┌──────────────┐    ┌──────────────┐               │
│  │ JS Microkernel│◄──►│  Web UI      │ (MVP-2 only) │
│  │ (host)       │    │  (browser)   │               │
│  └──────┬───────┘    └──────────────┘               │
│         │ kernel_request ABI                        │
│  ┌──────┴───────┐                                   │
│  │ WASM Kernel  │  wasmcl.wasm                      │
│  │ (C, ~1MB)    │                                   │
│  └──────┬───────┘                                   │
│         │ subprims ABI                              │
│  ┌──────┴───────┐                                   │
│  │ Subprims     │  subprims.wasm                    │
│  │ (C)          │                                   │
│  └──────────────┘                                   │
│                                                     │
│  ┌──────────────┐                                   │
│  │ Lisp Image   │  root.image (heap snapshot)       │
│  │ (compiled CL)│  + compiled modules (.lafsl)      │
│  └──────────────┘                                   │
└─────────────────────────────────────────────────────┘
```

| Component | Location | Purpose |
|-----------|----------|---------|
| WASM Kernel | `lisp-kernel/wasm32/` | Tagged objects, GC, image loading, kernel_request |
| Subprims | `lisp-kernel/wasm32/subprims/` | Low-level runtime support (funcall, throw, etc.) |
| Compiler | `compiler/WASM/` | Cross-compiler: CL source to WASM modules |
| JS Microkernel | `scripts/wasm/lib/` | Host: I/O, module loading, runner lifecycle |
| Build Pipeline | `scripts/wasm/` | Kernel, boot image, modules, root image |
| Web UI | `spec/web-ui/` (spec only) | Browser IDE — MVP-2, not yet implemented |

## Data Flow

```
Lisp code
  → compiler emits WASM function (compiled module)
  → module installed into function table
  → Lisp calls function via funcall ABI
  → function uses kernel_request for I/O
  → JS microkernel handles request, returns result
  → (MVP-2) UI tree sent via bridge → renderer → DOM/Canvas
```

## Key Encoding

```
CCL (internal)  →  Wire Protocol  →  JavaScript (internal)
   UTF-32       ↔     UTF-8       ↔      UTF-16
```

Full Unicode from day one. Convert only at boundaries.

## System-Wide Invariants

1. Lisp makes requests, not syscalls — all external interaction via kernel_request
2. Missing capabilities fail explicitly (CAPABILITY-UNAVAILABLE), never silent fallback
3. Each runner has its own heap — no shared Lisp heap across runners
4. Kernel and subprims are separate WASM modules, linked at runtime by JS host
5. Build artifacts must be aligned — kernel, subprims, boot image, modules from same build
6. UTF-8 at every CL↔JS boundary, no exceptions
7. ARM32 is the reference architecture — when in doubt, check `compiler/ARM/`

## System-Wide Anti-Patterns

1. Never silently degrade capabilities (no "try SAB, fall back to postMessage")
2. Never hardcode struct offsets — use `wasm_debug_tcr_offset(field_id)` for TCR fields
3. Never use `%svref`/`%fixnum-ref` in cross-compiled test lambdas (not WASM acode operators)
4. Never assume build artifacts are fresh — run `check-freshness.sh` before debugging
5. Never use `snprintf %s` with width modifiers — use manual string helpers instead
6. Never modify subprims without also rebuilding kernel (linked at runtime)

## Subsystem Index

| Subsystem | Spec | Status | Description |
|-----------|------|--------|-------------|
| Kernel | `doc/wasm/` | ⚠️ MVP-1 in progress | WASM kernel, compiler, build pipeline |
| Web UI | `spec/web-ui/OVERVIEW.md` | ⏸️ Deferred (MVP-2) | Browser IDE, rendering, persistence |

## Build Commands

```bash
# Full rebuild (default: force)
scripts/wasm/rebuild-everything.sh

# Check if artifacts are stale
scripts/wasm/check-freshness.sh

# Syntax-check Lisp files before rebuild
scripts/wasm/check-lisp-syntax.sh --modified

# Run smoke tests
node scripts/wasm/tests/all-smoke.mjs
```

## Spec-Driven Development

All implementation is driven by specs in `spec/`. See the subsystem OVERVIEW
for implementation order. See individual contracts for component-level details.

**Process:**
1. Read ARCHITECTURE.md (this file) for system context
2. Read the subsystem OVERVIEW for component map and implementation order
3. Read the specific contract before implementing a component
4. Run conformance checks after every modification
5. If a check fails and the fix requires changing the spec, STOP and consult a human

**Expanding the spec:** See [CONTRIBUTING.md](CONTRIBUTING.md) for templates and
rules for adding subsystems, contracts, and conformance checks.
