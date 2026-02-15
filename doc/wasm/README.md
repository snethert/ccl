# CCL WASM Port

**Status: Early Development / Experimental**
**Branch: `wasm-port`**
**Last Updated: 2026-02-15**

---

## ⚠️ Current Reality

This is an **active, experimental port** of Clozure Common Lisp to WebAssembly. The project demonstrates core concepts but has significant functionality gaps and stability issues.

**Strategic Direction:** Two-mode, two-phase approach (see [roadmap.md](roadmap.md)):
1. **MVP-1:** Library/Embedded Mode (single-runner, postMessage, works anywhere)
2. **MVP-2:** Full Runtime Mode (multi-runner, SAB, secure context, full IDE)

### 🚨 Critical Regression

**FASL loading is broken** - the system **used to load fasls without trouble**, now:
- `level-1.lafsl` returns -7 (load failure)
- `minimal.image` fails strict bootstrap
- `root.image` has symbol resolution failures

**This regression blocks MVP-1 and must be fixed before new features.**

### What Actually Works Today

- ✅ WASM kernel compiles (~1MB binary)
- ✅ Basic Lisp compilation: constants, fixnum arithmetic, simple control flow
- ✅ Minimal subprims: `_SPfuncall`, `_SPmkcatch1v`, `_SPnthrow1value`
- ✅ Exception handling: catch/throw, unwind-protect
- ✅ stdio via `kernel_request` (stdin/stdout/stderr)
- ✅ Basic closures and multi-value support

### What's Broken or Missing

- ❌ **Image loading REGRESSION**: Used to work, now broken (blocks MVP-1)
- ❌ **Real Lisp toplevel**: Boots but has documented stability failures
- ❌ **Most subprims are stubs**: 152 of ~160 subprims call `Bug()` if invoked
- ❌ **Minimal compiler**: No arrays, hash tables, structures, classes, optimization passes
- ❌ **No real I/O**: Filesystem is virtual-only stub, no networking
- ❌ **No FFI**: All foreign function calls signal `CAPABILITY-UNAVAILABLE`
- ❌ **No threads**: Single-runner only (intentionally deferred to MVP-2)
- ❌ **No test suite**: Found tests only validate symbol resolution, not runtime functionality

### Known Critical Blockers

1. **FASL loading regression** - `level-1.lafsl` returns -7 (highest priority)
2. **Image bootstrap failures** in minimal/root image paths
3. **Core symbol/function dispatch instability** during persistence operations ([tracked here](wasm-ui-persistence-problem-tracker.md))
4. **Code cleanup needed**: Obsolete code from previous attempts littered throughout codebase

---

## 🎯 Two Deployment Modes

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

**Status:** Blocked by fasl loading regression. Once fixed, can ship.

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

## 📚 Documentation Navigation

### Start Here

1. **[This file (README.md)](README.md)** - Current status and navigation (you are here)
2. **[project-overview.md](project-overview.md)** - Architectural vision and design goals
3. **[porting-status.md](porting-status.md)** - Detailed feature implementation status
4. **[roadmap.md](roadmap.md)** - Development roadmap and priorities

### Understanding the Architecture

- **[ABI.md](ABI.md)** - WASM calling conventions, subprims ABI, GC root discipline
- **[js-microkernel-spec.md](js-microkernel-spec.md)** - Host-side JavaScript microkernel specification
- **[capability-matrix.md](capability-matrix.md)** - Feature capability model and browser constraints
- **[threads-protocol.md](threads-protocol.md)** / **[threads.md](threads.md)** - Concurrency model (deferred)

### Building and Running

- **[build.md](build.md)** - Build instructions and dependencies
- **[macos-setup.md](macos-setup.md)** / **[linux-setup.md](linux-setup.md)** - Platform-specific setup
- **Canonical rebuild**: `scripts/wasm/rebuild-everything.sh`

### Runtime Components

- **[kernel-request-abi.md](kernel-request-abi.md)** - Kernel request interface for I/O
- **[streams-spec.md](streams-spec.md)** - Stream implementation
- **[image-loader-spec.md](image-loader-spec.md)** - Image loading (currently unstable)
- **[persistence-service-spec.md](persistence-service-spec.md)** - Persistence backend

### Compiler and Code Generation

- **[const-pool.md](const-pool.md)** - Constant pool management
- **[interrupts.md](interrupts.md)** / **[INTERRUPT-WORK.md](INTERRUPT-WORK.md)** - Interrupt mechanism
- **[yield-resume.md](yield-resume.md)** - Cooperative scheduling

### Browser UI (Post-MVP)

- **[browser-ui-spec.md](browser-ui-spec.md)** - UI toolkit specification
- **[ui-bridge-protocol.md](ui-bridge-protocol.md)** - Lisp↔JS bridge
- **[runtime-bridge.md](runtime-bridge.md)** - Runtime integration
- **Note**: UI components are marked post-MVP per project constraints

### Implementation Details

- **[subprims-provider-plan.md](subprims-provider-plan.md)** - Subprims module architecture
- **[subprims-work-remaining.md](subprims-work-remaining.md)** - Subprim implementation status
- **[startup-symbol-pipeline-implementation-plan.md](startup-symbol-pipeline-implementation-plan.md)** - Bootstrap symbol resolution
- **[wasm-startup-autoresolution-report-2026-02-14.md](wasm-startup-autoresolution-report-2026-02-14.md)** - Recent startup work

### Execution Plans and Reports

- **[mvp-unattended-execution-plan.md](mvp-unattended-execution-plan.md)** - MVP execution strategy
- **[mvp-unattended-execution-report.md](mvp-unattended-execution-report.md)** - Execution results
- **[wasm-ui-persistence-problem-tracker.md](wasm-ui-persistence-problem-tracker.md)** - Active problem tracking

### Testing

- **[testing.md](testing.md)** - Test strategy and infrastructure
- **Test location**: `doc/wasm/js/tests/` (limited coverage)

### Future Work

- **[quicklisp.md](quicklisp.md)** - Quicklisp compatibility (post-MVP)
- **[capability-negotiation.md](capability-negotiation.md)** - Advanced capability negotiation

### Historical Context

- **[TICKET-PROCESS-RETIRED.md](TICKET-PROCESS-RETIRED.md)** - Archived ticket-driven development process
- **[decisions.md](decisions.md)** - Key architectural decisions
- **[archive/](archive/)** - Retired ticket process and evidence (Feb 10, 2026)

---

## 🚀 Quick Start

**Prerequisites**: See [macos-setup.md](macos-setup.md) or [linux-setup.md](linux-setup.md)

### Build Everything

```bash
cd /Users/buildsomething/Source/ccl
scripts/wasm/rebuild-everything.sh
```

This rebuilds:
1. WASM kernel (`doc/wasm/js/wasmcl.wasm`)
2. Boot image (`wasm-boot.image`)
3. Runtime modules (`doc/wasm/wasm-runtime-modules.json`)
4. Versioned artifacts (contract + symbol scope)
5. Root image (with manifest, if successful)

### Run Tests (Current State Unknown)

```bash
# Symbol resolution tests
npm --prefix web-ui test

# Smoke tests (status unclear based on code scan)
node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive
node doc/wasm/js/all-smoke.mjs

# Persistence smoke test
CCL_PERSIST_BACKEND=memory-snapshot \
  CCL_PERSIST_SNAPSHOT_FILE=.tmp/persist-smoke.snapshot.json \
  node doc/wasm/js/wasm-ui-persist-smoke.mjs
```

**Warning**: Based on code analysis, test results may not reflect claimed "passing" status.

---

## 🎯 Project Vision

From [project-overview.md](project-overview.md):

> A **Common Lisp system derived from CCL's architecture** that targets **WebAssembly as the primary execution substrate**, with a **JavaScript microkernel** acting as the host environment.

**Key Goals:**
- ✅ Keep root Lisp minimal for cheap cloning (spawn-from-image)
- ✅ Dynamic loading of functions into running WASM environment
- ✅ Safepoints in generated code (interrupts, cancellation)
- ✅ ASCII-first strings with path to UTF-8
- ⏸ Replacement-lane threading (architecture defined, not implemented)
- ⏸ Quicklisp compatibility (post-MVP)

**Architecture:**
- **JS Microkernel**: Runner lifecycle, module management, I/O mediation, coordination
- **Lisp Backend**: Real CL environment (Lisp-2, macros, reader/printer, dynamic loading)
- **Per-runner heaps**: No shared Lisp heap, explicit inter-runner communication
- **Capability model**: Explicit host feature matrix, fail-fast on missing capabilities

---

## 📊 Implementation Maturity Matrix

| Component | Designed | Stubbed | Partial | Working | Tested |
|-----------|----------|---------|---------|---------|--------|
| WASM Kernel | ✅ | - | - | ✅ | ⚠️ |
| Subprims (Tier-0) | ✅ | - | - | ✅ | ⚠️ |
| Subprims (Tier-1+) | ✅ | ✅ | ⚠️ | ⚠️ | ❌ |
| Compiler Backend | ✅ | ⚠️ | ✅ | ⚠️ | ❌ |
| Image Loading | ✅ | - | ✅ | ❌ | ❌ |
| Toplevel/REPL | ✅ | - | ✅ | ❌ | ❌ |
| Stdio Streams | ✅ | - | - | ✅ | ⚠️ |
| Filesystem | ✅ | ✅ | - | - | - |
| Networking | ✅ | ✅ | - | - | - |
| FFI | ✅ | ✅ | - | - | - |
| Threading | ✅ | ✅ | - | - | - |
| Persistence | ✅ | - | ✅ | ⚠️ | ⚠️ |
| Browser UI | ✅ | - | ✅ | ⚠️ | ⚠️ |

**Legend:**
- ✅ Complete for this phase
- ⚠️ Partial/problematic
- ❌ Not working
- Blank: Not applicable

---

## 🔧 Development Workflow

### Current Focus Areas

Per [wasm-ui-persistence-problem-tracker.md](wasm-ui-persistence-problem-tracker.md):

1. **Stabilize symbol/function dispatch** during persistence operations
2. **Fix image bootstrap** for minimal/root images
3. **Harden regression gates** for UI persistence
4. **Document vs implement gap**: Align documentation with actual implementation status

### Next Execution Gate

Before claiming "MVP complete", these must pass:
```bash
npm --prefix web-ui test
node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive
CCL_PERSIST_BACKEND=memory-snapshot node doc/wasm/js/wasm-ui-persist-smoke.mjs
node doc/wasm/js/all-smoke.mjs
```

Current status: Unknown (tests exist but functional coverage unclear)

---

## 🤝 Contributing / Working on This Port

### Before Starting Work

1. Read [project-overview.md](project-overview.md) - understand the vision
2. Read [porting-status.md](porting-status.md) - know what's claimed as done
3. Read **this file** - understand what's actually working
4. Check [wasm-ui-persistence-problem-tracker.md](wasm-ui-persistence-problem-tracker.md) - active blockers
5. Review [roadmap.md](roadmap.md) - planned work

### Development Cycle

1. Make changes
2. Run `scripts/wasm/rebuild-everything.sh`
3. Run tests (see Quick Start)
4. Update documentation to match reality
5. Check that new artifacts are committed

### Key Directories

```
ccl/
├── lisp-kernel/wasm32/      # C kernel implementation
├── compiler/WASM/           # WASM backend (~8,900 lines)
├── lib/                     # Runtime libraries (wasmenv.lisp, wasm-ui.lisp)
├── doc/wasm/                # This documentation (39+ files)
│   ├── js/                  # JavaScript runtime and tests
│   └── repro/               # Reproduction logs and evidence
├── scripts/wasm/            # Build scripts
└── web-ui/                  # Browser UI toolkit (post-MVP)
```

---

## 📝 Documentation Standards

### When Writing New Docs

- **Be honest about status**: Use ✅/⚠️/❌ accurately
- **Link liberally**: Reference related docs
- **Date your work**: Include "Last Updated" dates
- **Separate vision from reality**: Don't describe plans as if they're working

### When Updating Implementation

- **Update porting-status.md** when features change state
- **Update this README** if maturity matrix changes
- **Log blockers** in problem tracker if you hit issues
- **Don't claim "done"** unless tests pass

---

## 🆘 Getting Help

- **Documentation issues**: Check this navigation guide first
- **Build failures**: See [build.md](build.md) and platform-specific setup
- **Runtime errors**: Check [wasm-ui-persistence-problem-tracker.md](wasm-ui-persistence-problem-tracker.md)
- **Architecture questions**: Read [project-overview.md](project-overview.md) and [ABI.md](ABI.md)

---

## 📜 License

Same as Clozure Common Lisp (Apache 2.0)

---

**Remember**: This is experimental software. Many documented features are aspirational or partially implemented. Always verify claims against the actual code and test results.
