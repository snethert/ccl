# CCL→WASM High‑Level Roadmap

**Purpose:** Track the big‑picture phases and current status of the port. This is
separate from the detailed checklists in `porting-status.md`.

**Status key:** ✅ done · ⚠️ partial · ❌ not started · ⏸ deferred

**Last updated:** 2026‑02‑10

## Current snapshot (one‑screen summary)

- **Kernel bring‑up:** ✅ core WASM build + ABI surface in place.
- **JS microkernel MVP:** ✅ kernel_request MVP + runner scaffolding.
- **Subprims provider:** ✅ Tier‑0 semantics + ABI defined and exercised by compiled modules.
- **Lisp runtime (Level‑1):** ✅ capability errors + yield path + WASM stream classes + virtual FS policy.
- **Compiler/backend (WASM):** ⚠️ MVP emission for constants, fixnum ops, calls, multi‑value (2–4 + `values` >4 via VSP push), and local control flow (`if`, `block/return-from`, `tagbody/go`) with compiled-module registry install; `catch`/`throw` routed through subprims; cooperative `unwind-protect` cleanup + closure capture in place with spill/restore validation gates.
- **Image + real toplevel:** ⚠️ boot image via cross‑xload works; runtime module bundles ship as v2 manifest+bin+idx; root image has hash-manifest + builder sanity gating; strict root bootstrap contract is now passing. Root-lane compiled-Lisp UI persistence preflight trap is closed and UI save/restore now runs through memory-snapshot-aligned file persistence (`/ui/wasm-ui-state.bin`) with dirty-flush regression checks. Remaining work is core dispatch cleanup.
- **Replacement runtime prerequisites:** ⚠️ secure-only startup gating and shared-memory-first transport are required for replacement lanes; CL thread semantics remain explicitly deferred.

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
- Finalize compiled-Lisp UI path parity and harden root-lane core symbol/function
  dispatch while keeping legacy unattended memory-snapshot behavior isolated from
  replacement-lane Storage V2 target posture.

### Phase 6 — Image + real toplevel
**Goal:** Boot a real Lisp image and enter `toplevel-loop`.
**Status:** ⚠️
**Remaining:**
- WASM‑compatible image policy (root image + cloning semantics)
- Promotion of strict root-image validation from targeted gate to normal release gate

### Phase 7 — Secure Runtime Gating and Worker/Shared-Memory Architecture
**Goal:** Make secure startup capabilities and shared-memory worker topology
prerequisites for replacement-lane execution.
**Status:** ⚠️
**Notes:** Replacement lanes require strict startup gates, shared-memory IPC, and
no-silent-fallback policy; single-runner fallback is not a replacement target.
CL thread semantics remain deferred by explicit policy boundary.

## Near‑term focus (next 1–2 phases)

1. Permanently resolve root-lane core symbol/function dispatch instability and retire temporary diagnostics.
2. Keep LMDB/IndexedDB as explicit integration lanes while enforcing replacement-lane no-fallback startup policy.
3. Continue enforcing persistence regression gates with explicit lane split: legacy memory-snapshot compatibility lanes vs replacement Storage V2 lanes.

## Interrupt TODOs (Tracking)

- Wire WASM interrupt delivery path (poll → trap → `raise_thread_interrupt`).
- Define/implement host `requestInterrupt` hook in the microkernel.
- Add interrupt smoke test and connect it to the runtime poll path.
- Clarify safepoint frequency policy and add diagnostics for latency.
