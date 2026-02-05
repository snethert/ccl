# CCL→WASM High‑Level Roadmap

**Purpose:** Track the big‑picture phases and current status of the port. This is
separate from the detailed checklists in `porting-status.md`.

**Status key:** ✅ done · ⚠️ partial · ❌ not started · ⏸ deferred

**Last updated:** 2026‑02‑05

## Current snapshot (one‑screen summary)

- **Kernel bring‑up:** ✅ core WASM build + ABI surface in place.
- **JS microkernel MVP:** ✅ kernel_request MVP + runner scaffolding.
- **Subprims provider:** ✅ Tier‑0 semantics + ABI defined (awaiting codegen use).
- **Lisp runtime (Level‑1):** ⚠️ capability errors + yield path done; streams/FS policy pending.
- **Compiler/backend (WASM):** ⚠️ calling convention implemented + smoke test; no real codegen yet.
- **Image + real toplevel:** ⚠️ minimal boot image loads + stub toplevel hook returns; no real Lisp toplevel.
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
**Status:** ⚠️
**Remaining:**
- WASM‑specific stream classes
- Virtual filesystem/pathname policy

### Phase 5 — Compiler/backend (WASM codegen)
**Goal:** Emit real WASM code compatible with the subprims ABI.
**Status:** ⚠️
**Remaining:**
- WASM codegen + integration with table‑index entrypoints (calling convention smoke test passes)
- Cooperative unwind checks for `wasm_pending_throw`

### Phase 6 — Image + real toplevel
**Goal:** Boot a real Lisp image and enter `toplevel-loop`.
**Status:** ⚠️
**Remaining:**
- WASM‑compatible image policy (root image + cloning semantics)
- Real Lisp toplevel image + `start_lisp` wiring once codegen exists

### Phase 7 — Concurrency model
**Goal:** Runner‑based parallelism where available.
**Status:** ⏸
**Notes:** Deferred until single‑runner baseline is stable.

## Near‑term focus (next 1–2 phases)

1) Implement WASM codegen emission that honors the calling convention.  
2) Wire `start_lisp` to real toplevel + loader once codegen exists.
