# CCL→WASM High‑Level Roadmap

**Purpose:** Track the big‑picture phases and current status of the port. This is
separate from the detailed checklists in `porting-status.md`.

**Status key:** ✅ done · ⚠️ partial · ❌ not started · ⏸ deferred

**Last updated:** 2026‑02‑05

## Current snapshot (one‑screen summary)

- **Kernel bring‑up:** ✅ core WASM build + ABI surface in place.
- **JS microkernel MVP:** ✅ kernel_request MVP + runner scaffolding.
- **Subprims provider:** ✅ Tier‑0 semantics + ABI defined and exercised by compiled modules.
- **Lisp runtime (Level‑1):** ✅ capability errors + yield path + WASM stream classes + virtual FS policy.
- **Compiler/backend (WASM):** ⚠️ MVP emission for constants, fixnum ops, calls, multi‑value (2–4 + `values` >4 via VSP push), and local control flow (`if`, `block/return-from`, `tagbody/go`) with compiled-module registry install; `catch`/`throw` routed through subprims; cooperative `unwind-protect` cleanup + closure capture now in place with multi‑value preservation.
- **Image + real toplevel:** ⚠️ minimal boot image loads + post‑load `start_lisp` entry wired; no real Lisp toplevel.
- **Concurrency model:** ⏸ deferred (single‑threaded baseline first).

## Roadmap phases

### Phase 1 — Kernel bring‑up (WASM32, freestanding)
**Goal:** Kernel links and exposes the minimum host ABI for a JS microkernel.
**Status:** ✅
**Delivered:**
- Freestanding kernel build (`wasmcl.wasm`)
- KERNEL_IMPORTS + `kernel_request` wrappers
- Manual cstack + step/yield entrypoints

### Phase 2 — JS microkernel MVP
**Goal:** Minimal host that can drive the kernel via `kernel_request`.
**Status:** ✅
**Delivered:**
- `kernel_request` MVP (CAPS/LOG/STREAM/TIME)
- Named byte sources + runner scaffolding

### Phase 3 — Subprims provider (Tier‑0)
**Goal:** Reach Lisp toplevel path and return cleanly to host.
**Status:** ✅
**Notes:** Cooperative unwind + table‑index entry ABI in place; requires codegen.

### Phase 4 — Lisp runtime integration (Level‑1)
**Goal:** Usable runtime surface under WASM constraints.
**Status:** ✅
**Delivered:**
- WASM‑specific stream classes + `open` defaulting to `wasm-stream`
- Virtual filesystem/pathname policy with capability‑unavailable errors for mutating ops

### Phase 5 — Compiler/backend (WASM codegen)
**Goal:** Emit real WASM code compatible with the subprims ABI.
**Status:** ⚠️
**Remaining:**
- Spill/restore discipline around all subprim calls (closure allocation paths still partial)

### Phase 6 — Image + real toplevel
**Goal:** Boot a real Lisp image and enter `toplevel-loop`.
**Status:** ⚠️
**Remaining:**
- WASM‑compatible image policy (root image + cloning semantics)
- Real Lisp toplevel image; current `start_lisp` entry uses a stub toplevel

### Phase 7 — Concurrency model
**Goal:** Runner‑based parallelism where available.
**Status:** ⏸
**Notes:** Deferred until single‑runner baseline is stable.

## Near‑term focus (next 1–2 phases)

1) Tighten spill/restore discipline around all subprim calls (closure allocation paths still partial).  
2) Wire a real toplevel image to the loader/runner in the browser.

## Interrupt TODOs (Tracking)

- Wire WASM interrupt delivery path (poll → trap → `raise_thread_interrupt`).
- Define/implement host `requestInterrupt` hook in the microkernel.
- Add interrupt smoke test and connect it to the runtime poll path.
- Clarify safepoint frequency policy and add diagnostics for latency.
