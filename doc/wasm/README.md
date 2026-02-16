# CCL WASM Port

**Status:** Active
**Scope:** Project entry point, current status, and documentation navigation
**Last Updated:** 2026-02-15
**Doc Version:** 1.0.0

---

## Current Reality

This is an **active, experimental port** of Clozure Common Lisp to WebAssembly. The build pipeline is functional end-to-end, but the runtime cannot yet load FASL files due to a module installation issue.

**Strategic Direction:** Two-mode, two-phase approach (see [roadmap.md](roadmap.md)):
1. **MVP-1:** Library/Embedded Mode (single-runner, postMessage, works anywhere)
2. **MVP-2:** Full Runtime Mode (multi-runner, SAB, secure context, full IDE)

### Critical Blocker: FASL Loading

**Status:** ❌ BLOCKING MVP-1

The build pipeline completes successfully and all 7557 compiled modules install, but FASL loading returns -7. The kernel's `wasm_fasload_path` cannot load `l1-fasls/l1-cl-package.lafsl` because the FASL loading functions (`%FASLOAD`, `%FASL-OPEN`, `%SIMPLE-FASL-OPEN`) are not yet bound — they are defined in the level-1 Lisp code that FASL loading is trying to load (chicken-and-egg).

- RESTORE-LISP-POINTERS is called correctly (deferred for boot image, called post-fasload)
- Package hash tables are rebuilt after image load
- Compiled modules are compiled and bundled (7557 modules, 437MB binary)
- All 7557 compiled modules install successfully (B2 resolved)
- `wasm_fasload_path` returns -7 on first FASL

**Impact:** Cannot load level-1 FASLs. Root image build fails. MVP-1 blocked.

**See:** [TODO.md](../../TODO.md) blocker B3 for investigation status.

### What Works Today

- ✅ WASM kernel compiles (~1MB binary)
- ✅ Build pipeline end-to-end (kernel → boot image → runtime modules → root image attempt)
- ✅ Boot image auto-build (triggered when missing during root image build)
- ✅ Image loading into memory (sections map correctly, symbols exist)
- ✅ RESTORE-LISP-POINTERS called after image load (package hash tables rebuilt)
- ✅ Basic Lisp compilation: constants, fixnum arithmetic, simple control flow
- ✅ Minimal subprims: `_SPfuncall`, `_SPmkcatch1v`, `_SPnthrow1value`
- ✅ Exception handling: catch/throw, unwind-protect
- ✅ stdio via `kernel_request` (stdin/stdout/stderr)
- ✅ Basic closures and multi-value support
- ✅ Compiled module registry (7557 modules compiled from level-0/level-1)

### What's Broken or Missing

- ✅ **Compiled module installation**: 7557/7557 modules install (B2 resolved)
- ❌ **FASL loading**: Returns -7 (`%FASLOAD` not yet bound — chicken-and-egg, B3)
- ❌ **Real Lisp toplevel**: Cannot reach toplevel without working FASL loading
- ❌ **Minimal compiler**: No arrays, hash tables, structures, classes, optimization passes
- ❌ **No real I/O**: Filesystem is virtual-only stub, no networking
- ❌ **No FFI**: All foreign function calls signal `CAPABILITY-UNAVAILABLE`
- ❌ **No threads**: Single-runner only (intentionally deferred to MVP-2)

---

## Two Deployment Modes

This port targets **two distinct use cases** with different architectures:

### Library/Embedded Mode (MVP-1 - Current Focus)

**Goal:** CCL WASM as an embeddable library for web applications

- Single WASM runner (no threading)
- postMessage interface for external communication
- Works in any browser context (no special requirements)
- Limited capabilities (stdio only, no persistence, no FFI)
- Small footprint, fast startup

**Example use:**
```html
<script src="ccl-wasm.js"></script>
<script>
  CCL.eval("(+ 1 2)").then(result => console.log(result));
</script>
```

**Status:** Blocked by FASL loading (B3). Modules install, FASL functions not yet bound.

### Full Runtime Mode (MVP-2 - Future)

**Goal:** Complete browser-based development environment

- Multi-runner with Web Workers
- SharedArrayBuffer + Atomics for coordination
- Requires secure context (COOP + COEP headers)
- Full storage backend (IndexedDB)
- Complete IDE capabilities (web-ui/ide integration)

**Requirements:**
```http
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

**Status:** Deferred until MVP-1 is stable and shipped.

**Why two modes?** Different users, different needs. Library users want simplicity and embeddability. Full runtime users want power and don't mind secure context requirements. Both are first-class targets, not fallback strategies.

See [roadmap.md](roadmap.md) for detailed two-phase strategy.

---

## Documentation Navigation

### Start Here

1. **[This file (README.md)](README.md)** - Current status and navigation (you are here)
2. **[project-overview.md](project-overview.md)** - Architectural vision and design goals
3. **[porting-status.md](porting-status.md)** - Detailed feature implementation status
4. **[roadmap.md](roadmap.md)** - Development roadmap and priorities

### Understanding the Architecture

- **[ABI.md](ABI.md)** - WASM calling conventions, subprims ABI, GC root discipline
- **[js-microkernel-spec.md](js-microkernel-spec.md)** - Host-side JavaScript microkernel specification
- **[decisions.md](decisions.md)** - Key architectural decisions

### Building and Running

- **[build.md](build.md)** - Build instructions and dependencies
- **[macos-setup.md](macos-setup.md)** / **[linux-setup.md](linux-setup.md)** - Platform-specific setup
- **Canonical rebuild**: `scripts/wasm/rebuild-everything.sh`

### Runtime Components

- **[kernel-request-abi.md](kernel-request-abi.md)** - Kernel request interface for I/O
- **[kernel-opcode-registry.md](kernel-opcode-registry.md)** - Opcode registry
- **[streams-spec.md](streams-spec.md)** - Stream implementation
- **[image-loader-spec.md](image-loader-spec.md)** - Image loading and boot sequence
- **[const-pool.md](const-pool.md)** - Constant pool management

### Testing

- **[testing.md](testing.md)** - Test strategy and infrastructure
- **Test location**: `scripts/wasm/tests/` (smoke tests and conformance tests)

### Development Context

- **[AI-ASSIST.md](AI-ASSIST.md)** - Operational guide for AI assistants
- **[persistence-dev-environment.md](persistence-dev-environment.md)** - Persistence test environment
- **[archive/](archive/)** - Retired ticket process and evidence (Feb 10, 2026)

### Relocated Documentation (MVP-2)

22 files covering MVP-2 features, obsolete processes, and superseded plans have been relocated to `~/Documents/ccl-proj-history/` per [ADR-0007](decisions.md). These will be reviewed and brought back when MVP-2 work begins.

---

## Quick Start

**Prerequisites**: See [macos-setup.md](macos-setup.md) or [linux-setup.md](linux-setup.md)

### Build Everything

```bash
cd /path/to/ccl
source scripts/wasm/env.sh
scripts/wasm/rebuild-everything.sh
```

This rebuilds in dependency order:
1. WASM kernel (`build/wasm32/kernel/wasmcl.wasm`)
2. Boot image (`build/wasm32/wasm-boot.image`)
3. Runtime modules (`build/wasm32/modules/wasm-runtime-modules.json`)
4. Root image (`build/wasm32/images/root.image`, allowed to fail)

### Run Tests

```bash
# All smoke tests
node scripts/wasm/tests/all-smoke.mjs

# Individual smoke tests
node scripts/wasm/tests/kernel-request-smoke.mjs
node scripts/wasm/tests/compiler-smoke.mjs
node scripts/wasm/tests/smoke-test.mjs
```

---

## Project Vision

From [project-overview.md](project-overview.md):

> A **Common Lisp system derived from CCL's architecture** that targets **WebAssembly as the primary execution substrate**, with a **JavaScript microkernel** acting as the host environment.

**Key Goals:**
- ✅ Keep root Lisp minimal for cheap cloning (spawn-from-image)
- ⚠️ Dynamic loading of functions into running WASM environment (blocked by B2)
- ✅ Safepoints in generated code (interrupts, cancellation)
- ✅ UTF-8 wire format for strings (UTF-32 internal, UTF-8 boundary, UTF-16 JS)
- ⏸️ MVP-2 Full Runtime Mode threading (architecture defined, not implemented)
- ⏸️ Quicklisp compatibility (post-MVP)

**Architecture:**
- **JS Microkernel**: Runner lifecycle, module management, I/O mediation, coordination
- **Lisp Backend**: Real CL environment (Lisp-2, macros, reader/printer, dynamic loading)
- **Per-runner heaps**: No shared Lisp heap, explicit inter-runner communication
- **Capability model**: Explicit host feature matrix, fail-fast on missing capabilities

---

## Implementation Maturity Matrix

| Component | Designed | Stubbed | Partial | Working | Tested |
|-----------|----------|---------|---------|---------|--------|
| WASM Kernel | ✅ | - | - | ✅ | ⚠️ |
| Build Pipeline | ✅ | - | - | ✅ | ✅ |
| Subprims (Tier-0) | ✅ | - | - | ✅ | ⚠️ |
| Subprims (Tier-1+) | ✅ | ✅ | ⚠️ | ⚠️ | ❌ |
| Compiler Backend | ✅ | ⚠️ | ✅ | ⚠️ | ❌ |
| Image Loading | ✅ | - | - | ✅ | ⚠️ |
| Module Installation | ✅ | - | - | ✅ | ⚠️ |
| Toplevel/REPL | ✅ | - | ✅ | ❌ | ❌ |
| Stdio Streams | ✅ | - | - | ✅ | ⚠️ |
| Filesystem | ✅ | ✅ | - | - | - |
| Networking | ✅ | ✅ | - | - | - |
| FFI | ✅ | ✅ | - | - | - |
| Threading | ✅ | ✅ | - | - | - |

**Legend:**
- ✅ Complete for this phase
- ⚠️ Partial/problematic
- ❌ Not working
- Blank: Not applicable

---

## Development Workflow

### Current Focus

Per [TODO.md](../../TODO.md):

1. **Fix FASL loading** (B3 — returns -7, `%FASLOAD` not bound)
2. **Stabilize bootstrap** for minimal/root images
3. **Validate end-to-end** (boot → FASL load → toplevel)

### Key Directories

```
ccl/
├── build/wasm32/               # Build outputs (gitignored)
│   ├── kernel/wasmcl.wasm      # WASM kernel binary
│   ├── images/*.image          # Heap images
│   ├── modules/*.json          # Compiled modules
│   └── subprims/subprims.wasm  # Subprims provider
├── lisp-kernel/wasm32/         # C kernel source
├── compiler/WASM/              # WASM backend (~8,900 lines)
├── scripts/wasm/               # Build scripts and infrastructure
│   ├── lib/                    # JS runtime libraries
│   └── tests/                  # Smoke tests
└── doc/wasm/                   # This documentation
```

---

## Documentation Standards

See [STYLE-GUIDE.md](STYLE-GUIDE.md) for full standards.

- **Be honest about status**: Use ✅/⚠️/❌/⏸️ accurately
- **Link with descriptions**: `[doc](./file.md) – Brief description`
- **Date your work**: Include `Last Updated` and `Doc Version`
- **Separate vision from reality**: Use "Future Work" for planned features

---

## License

Same as Clozure Common Lisp (Apache 2.0)

---

**Remember**: This is experimental software. Verify claims against actual code and test results. See [TODO.md](../../TODO.md) for current task status and blockers.
