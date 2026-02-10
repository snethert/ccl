# BPL-10 - WASM Machine Implementation (Subprims, L1 GC, Compiler)

Status: in_progress  
Priority: P0  
Owner: Compiler/backend migration track  
Last Updated: 2026-02-10  
Parent Plan: `doc/wasm/backend-migration-master-plan.md`

## Scope

In scope:

- Define the target WASM machine profile that maximizes Lisp throughput and minimizes ARM-compat overhead.
- Complete remaining subprim implementation gaps in `lisp-kernel/wasm-subprims-provider.c`.
- Replace ARM-shaped GC root/forwarding assumptions in `lisp-kernel/wasm-gc.c`.
- Execute compiler/backend decoupling in `compiler/WASM` and `lib/wasmenv.lisp` so codegen is WASM-native instead of ARM-mirrored.
- Integrate L1 GC tuning/observability surfaces needed for stable runtime behavior under WASM.

Out of scope:

- Runtime replacement track ownership areas (`RPL-*`) such as secure startup policy and shared-memory transport architecture.
- New user-facing feature work unrelated to backend execution correctness/performance.
- Rewriting closed historical tickets (`BPL-01`..`BPL-09`) except for additive reference links.

## Dependencies

- Baseline assumptions and sequencing anchors from `BPL-01`..`BPL-05`.
- Existing diff/perf harness and closure artifacts from `BPL-06`..`BPL-09`.
- Backend-local documentation workflow (`doc/wasm/backend-sync/README.md`).

## Deliverables

1. WASM machine profile v1 for Lisp execution and GC safety (`B10M-*`).
2. Subprim completion waves with deterministic closure criteria (`B10S-*`).
3. L1 GC and kernel GC modernization plan with explicit source touchpoints (`B10G-*`).
4. Compiler/backend decoupling and optimization plan (`B10C-*`).
5. Unified validation/cutover matrix (`B10V-*`) tied to existing smoke and audit tooling.

## Exit Criteria

- `doc/wasm/subprims-work-remaining.md` reports `behavioral gap = 0` for active WASM subprims.
- ARM-coupling audit for wasm-facing surfaces passes with zero hits:
  - `scripts/wasm/arm-retirement-audit.sh --strict`
- GC root/forwarding is no longer hard-coded to ARM register-index spans in WASM paths.
- Compiler/WASM target description no longer requires direct ARM arch import as the execution model baseline.
- Existing smoke lanes and added GC/compiler regression lanes pass with deterministic evidence.

## Current Baseline (Implementation Reality)

- Subprim backlog closure is now reached: `132` total subprims, `0` marked `behavioral gap`, `123` `validation only` (`doc/wasm/subprims-work-remaining.md`).
- Validation evidence is now captured:
  - `B10V-03` smoke gate passed (`node doc/wasm/js/all-smoke.mjs`).
  - `B10V-01` strict audit now passes with `total_hits=0` (`scripts/wasm/arm-retirement-audit.sh --strict`) after compiler/header/doc marker retirement updates.
- WASM target arch and macro layer still mirror ARM contracts (`compiler/WASM/wasm-arch.lisp`).
- WASM GC root scanning is now centralized behind descriptor-driven XP/TCR/C-stack traversal in `lisp-kernel/wasm-gc.c`: an explicit GC root-descriptor object now controls XP node spans, XP locatives, C-stack safepoint frame publication, and TCR TLB inclusion; XP node/locative iteration, C-stack frame slot publication, and TCR xframe/TLB traversal consume shared helper paths; descriptor IDs use wasm-owned alias constants (`wasm_gpr_arg_z..wasm_gpr_fn`) instead of direct legacy macro names. Descriptor policy publication is now externalized via wasm platform API (`wasm_publish_gc_root_policy`, `wasm_current_gc_root_policy`, `wasm_reset_gc_root_policy`) plus runtime-mode publication APIs (`wasm_publish_gc_root_policy_mode`, `wasm_current_gc_root_policy_mode`) and host-visible boundary exports (`wasm_set_gc_root_policy`, `wasm_get_gc_root_policy`, `wasm_set_gc_root_policy_mode`, `wasm_get_gc_root_policy_mode`).
- Compiler/module pipeline now carries GC root-policy mode metadata end-to-end: wasm2 compiled-module registration emits per-module mode values, bundle/index tooling preserves `gcRootPolicyModes`, kernel exports provide per-entry mode registration/query/clear, and runtime dispatch paths publish entry mode before compiled entry invocation.
- `lib/wasmenv.lisp` preserves ARM-order register compatibility as a transition design.

## Immediate Next Step

- Action: start `B10G-02` by removing ARM-endian/halfword forwarding assumptions from wasm relocation paths and validating relocation correctness under GC movement stress.
- Why now: `B10G-01` mode-publication ownership is now runtime+compiler integrated and validated, so the dominant remaining GC-coupling risk is forwarding/relocation arithmetic assumptions.
- Success evidence: forwarding paths are architecture-neutral in wasm GC code, `B10V-01` remains `total_hits=0`, and smoke/regression lanes remain green with relocation-focused coverage added.

## Wave A Progress (B10S-01)

- `_SPdebind` implementation was hardened to avoid helper-classified unwind gaps by replacing `wasm_vsp_or_trap` with local stack-pointer validation in `lisp-kernel/wasm-subprims-provider.c`.
- `_SPbind` implementation was updated to use explicit stack and binding-table pointer validation without helper-induced unwind tagging.
- `_SPbind_self` implementation now uses the same explicit stack and binding-table pointer validation pattern, preserving ARM-equivalent bind semantics.
- `_SPbind_self_boundp_check` now uses the same explicit stack and binding-table pointer validation pattern while preserving unbound-symbol signaling semantics.
- `_SPunbind` now uses explicit binding-list and binding-slot pointer validation while preserving ARM-equivalent unbind restore/link semantics.
- `_SPunbind_n` now uses explicit binding-list and binding-slot pointer validation while preserving iterative ARM-equivalent unbind restore semantics.
- `_SPunbind_to` now uses explicit helper-local binding list and binding-slot pointer validation while preserving target-link unbind semantics.
- `_SPthrow` now uses explicit local stack-pointer validation instead of helper-triggered unwind tagging while preserving throw-tag lookup and target frame semantics.
- `_SPnthrow1value` now uses neutral control-link and saved-stack pointer naming in null checks while preserving unwind/catch semantics.
- `_SPnthrowvalues` now uses neutral control-link and saved-stack pointer naming plus explicit local stack-pointer validation while preserving multi-value unwind semantics.
- `_SPmkunwind` now uses neutral control-link naming in null checks while preserving unwind-frame setup semantics.
- `_SPmvpass` now uses explicit local stack-pointer validation in place of helper VSP checks while preserving pass-through value semantics.
- `_SPmvslide` now uses explicit local stack-pointer validation in place of helper VSP checks while preserving slide semantics.
- `_SPvalues` now uses explicit local stack-pointer validation in place of helper VSP checks while preserving value selection semantics.
- `_SPfitvals` now uses explicit local stack-pointer validation in place of helper VSP checks while preserving fit semantics.
- `_SPnthvalue` now uses explicit local stack-pointer validation in place of helper VSP checks while preserving indexed value semantics.
- `_SPopt_supplied_p` now uses explicit local stack-pointer validation in place of helper VSP checks while preserving supplied-p flag semantics.
- `_SPheap_rest_arg` now uses explicit local stack-pointer validation in place of helper VSP checks while preserving list construction semantics.
- `_SPreq_heap_rest_arg`, `_SPheap_cons_rest_arg`, and `_SPstack_cons_rest_arg` now use explicit local stack-pointer validation in place of helper VSP checks while preserving rest-list construction semantics.
- `_SPspreadargz` and `_SPspread_lexprz` now use explicit local stack-pointer validation in place of helper VSP checks while preserving spread semantics and argument-register reload behavior.
- `_SPkeyword_bind` now uses explicit local stack-pointer validation in place of helper VSP checks while preserving keyword argument binding semantics.
- `_SPprogvsave` now uses explicit local stack-pointer validation and neutral binding-slot naming in place of helper/state-classified checks while preserving PROGV save semantics.
- `_SPprogvrestore` now uses neutral binding-slot/current-binding/saved-stack naming while preserving PROGV restore semantics.
- Regenerated status report moved `_SPdebind`, `_SPbind`, `_SPbind_self`, `_SPbind_self_boundp_check`, `_SPunbind`, `_SPunbind_n`, `_SPunbind_to`, `_SPnthrow1value`, `_SPnthrowvalues`, `_SPmkunwind`, `_SPmvpass`, `_SPmvslide`, `_SPvalues`, `_SPfitvals`, `_SPnthvalue`, `_SPopt_supplied_p`, `_SPheap_rest_arg`, `_SPreq_heap_rest_arg`, `_SPheap_cons_rest_arg`, `_SPstack_cons_rest_arg`, `_SPspreadargz`, `_SPspread_lexprz`, `_SPkeyword_bind`, `_SPprogvsave`, `_SPprogvrestore`, `_SPcall_closure`, `_SPreset`, `_SPspecref`, `_SPspecrefcheck`, `_SPspecset`, `_SPbind_interrupt_level`, `_SPbind_interrupt_level_0`, `_SPbind_interrupt_level_m1`, and `_SPunbind_interrupt_level` from `behavioral gap` to `validation only`.
- Aggregate report change after this step:
  - `behavioral gap`: `44 -> 0`
  - `validation only`: `79 -> 123`

## Step 1 Output - WASM Machine Profile for Lisp (v1)

### Step 1 ID Namespace Freeze

| namespace | frozen range | meaning |
| --- | --- | --- |
| `B10M-*` | `B10M-01`..`B10M-08` | Normative WASM machine profile clauses for Lisp backend execution. |

### WASM Machine Profile Matrix

| machine_id | profile clause | current source anchors | target implementation effect |
| --- | --- | --- | --- |
| B10M-01 | Keep linear-memory object model for Lisp values, but treat `tcr->wasm_gprs` as transitional compatibility state, not the optimization center. | `lisp-kernel/platform-wasm32.h`, `lisp-kernel/wasm-subprims-provider.c` | Shift optimization focus to generated WASM locals/structured control and spill only at required safepoints/boundaries. |
| B10M-02 | Preserve subprim identity as table-index fixnums; eliminate all PC/range/address-style assumptions for dispatch and call checks. | `doc/wasm/ABI.md`, `lisp-kernel/wasm-subprims-map.h` | Stable multi-module dispatch, no address emulation overhead, easier module-version compatibility. |
| B10M-03 | Minimize mandatory subprim crossings in hot arithmetic/control paths; prefer direct wasm2 lowering where semantics are stable. | `compiler/WASM/wasm2.lisp`, `doc/wasm/backend-tickets/BPL-04-numeric-and-math-pipeline-modernization.md` | Reduced call overhead and less ARM-shaped call-frame pressure. |
| B10M-04 | Define explicit safepoint/root publication contract: operand stack is never scanned; roots are in TCR, Lisp stacks, and explicit spill structures only. | `doc/wasm/ABI.md`, `lisp-kernel/wasm-gc.c` | Deterministic GC correctness under optimization and simpler compiler invariants. |
| B10M-05 | Replace ARM register-range root assumptions (`arg_z..Rfn`) with a WASM root descriptor consumed by GC mark/forward paths. | `lisp-kernel/wasm-gc.c:945`, `lisp-kernel/wasm-gc.c:1242` | Decouples GC correctness from ARM index ordering and enables backend register model evolution. |
| B10M-06 | Remove ARM-endianness-specific forwarding math assumptions from WASM GC relocation logic. | `lisp-kernel/wasm-gc.c:1025` | Architecture-neutral forwarding behavior and lower hidden correctness risk. |
| B10M-07 | Use feature-profile gating for optional WASM features (tail-call, SIMD, etc.) while keeping a deterministic baseline profile. | `doc/wasm/spec/README.md`, `doc/wasm/capability-matrix.md` | Predictable cross-host behavior with additive optimization when capabilities exist. |
| B10M-08 | Keep L1 behavior deterministic under capability constraints: no silent fallback for unavailable backend-critical behavior. | `doc/wasm/capability-matrix.md`, `level-1/l1-aprims.lisp` | Safer failure modes, easier regression triage, fewer hidden compatibility branches. |

### Step 1 Closure Assertions

1. Machine profile clauses are implementation-facing and source-anchored.
2. Each clause has an explicit performance/correctness effect.
3. No clause requires reopening runtime-track ownership boundaries.

## Step 2 Output - Subprim Completion Waves (v1)

### Step 2 ID Namespace Freeze

| namespace | frozen range | meaning |
| --- | --- | --- |
| `B10S-*` | `B10S-01`..`B10S-08` | Deterministic subprim implementation waves and closure gates. |

### Subprim Wave Plan

| subprim_id | wave | scope | source anchors | closure rule |
| --- | --- | --- | --- | --- |
| B10S-01 | Wave A | Control transfer core: `_SPbind*`, `_SPdebind`, `_SPunbind*`, `_SPthrow`, `_SPnthrowvalues`, `_SPmkcatch*` | `lisp-kernel/wasm-subprims-provider.c`, `doc/wasm/subprims-work-remaining.md` | All rows in this set move from `behavioral gap` to `validation only` or `clean`. |
| B10S-02 | Wave A | Argument/defaulting/rest paths: `_SPdefault_optional_args`, `_SPheap_rest_arg`, `_SPstack_rest_arg`, `_SPspread*`, `_SPfitvals` | same as above | No state/unwind traps remain except required invariant traps. |
| B10S-03 | Wave B | Allocation/list/vector constructors: `_SPconslist*`, `_SPgvector`, `_SPmisc_alloc*`, `_SPmakestack*` | same as above | Deterministic behavior under GC pressure with pass coverage in smoke harness. |
| B10S-04 | Wave B | Symbol/value dynamic binding helpers: `_SPspecref*`, `_SPspecset`, `_SPprogv*` | same as above | PROGV/binding behavior matches machine-profile unwind semantics. |
| B10S-05 | Wave C | Call/closure dispatch and recovery lanes: `_SPcall_closure`, `_SPfuncall`, `_SPfix_nfn_entrypoint` | same as above, `compiler/WASM/wasm2.lisp` call sites | No hidden fallback paths; explicit error and value semantics only. |
| B10S-06 | Wave C | Interrupt/error boundary lanes: `_SPbind_interrupt_level*`, `_SPunbind_interrupt_level`, `_SPksignalerr` | same as above, `doc/wasm/interrupts.md` | Host-interrupt integration and deterministic signal paths documented and tested. |
| B10S-07 | Continuous | Keep `doc/wasm/subprims-work-remaining.md` auto-generated after each wave via script | `scripts/wasm/update_subprims_work_remaining.py` | Report and source stay synchronized every wave. |
| B10S-08 | Exit | Subprim completion gate | `doc/wasm/subprims-work-remaining.md` | Global `behavioral gap` count reaches `0`. |

### Step 2 Execution Rules

1. Work one subprim at a time inside each wave, but keep wave order fixed.
2. No batch that mixes unrelated control-flow and allocation semantics.
3. Each wave closes only with regenerated report + targeted smoke evidence.

## Step 3 Output - L1 GC and Kernel GC Modernization (v1)

### Step 3 ID Namespace Freeze

| namespace | frozen range | meaning |
| --- | --- | --- |
| `B10G-*` | `B10G-01`..`B10G-07` | GC architecture and implementation tasks for WASM-native backend. |

### GC Work Matrix

| gc_id | focus | source anchors | implementation target |
| --- | --- | --- | --- |
| B10G-01 | Root descriptor abstraction for WASM | `lisp-kernel/wasm-gc.c:945`, `lisp-kernel/wasm-gc.c:1242` | Replace fixed `arg_z..Rfn` loops with descriptor-driven root publication. |
| B10G-02 | Relocation/forwarding neutrality | `lisp-kernel/wasm-gc.c:1025` | Remove ARM-endian half-word assumption from forwarding address math. |
| B10G-03 | Safepoint integration contract | `doc/wasm/ABI.md`, `compiler/WASM/wasm2.lisp` | Compiler publishes roots at every GC-capable call boundary deterministically. |
| B10G-04 | Cstack/lisp-frame coherence | `lisp-kernel/wasm-cstack.c`, `lisp-kernel/platform-wasm32.h` | Guarantee unwind-safe last-lisp-frame behavior across non-local exits and GC scans. |
| B10G-05 | L1 GC observability/tuning wiring | `level-1/l1-aprims.lisp`, `level-1/l1-init.lisp`, `level-1/l1-boot-lds.lisp` | Keep EGC/GC controls usable and deterministic under WASM execution constraints. |
| B10G-06 | Stress/regression suite for GC + subprims | `doc/wasm/js/all-smoke.mjs`, new targeted GC stress smoke lane | Detect root loss, relocation corruption, and unwind corruption early. |
| B10G-07 | Exit gate | all above | GC modernized paths pass stress lane and no ARM-root-range assumptions remain. |

## Step 4 Output - Compiler/Backend Decoupling Execution (v1)

### Step 4 ID Namespace Freeze

| namespace | frozen range | meaning |
| --- | --- | --- |
| `B10C-*` | `B10C-01`..`B10C-10` | Compiler/backend implementation tasks to remove ARM emulation overhead. |

### Compiler Work Matrix

| compiler_id | focus | source anchors | implementation target |
| --- | --- | --- | --- |
| B10C-01 | Target-arch decoupling | `compiler/WASM/wasm-arch.lisp` | Stop importing ARM arch as the defining WASM execution model. |
| B10C-02 | WASMENV register-class decoupling | `lib/wasmenv.lisp` | Move from ARM-order compatibility constants to WASM-native register/local classes. |
| B10C-03 | Subprim mapping decoupling | `compiler/WASM/wasm-arch.lisp`, `doc/wasm/subprims-map.json` | Keep symbolic mapping stable while removing ARM-table coupling from compile-time assumptions. |
| B10C-04 | Direct lowering expansion | `compiler/WASM/wasm2.lisp` | Convert hot arithmetic/control forms from `:call-subprim` to direct lowered ops where valid. |
| B10C-05 | Call-path optimization | `compiler/WASM/wasm2.lisp` | Reduce VSP/register shuffle overhead for compiled-to-compiled calls. |
| B10C-06 | Spill/restore hardening | `compiler/WASM/wasm2.lisp`, `doc/wasm/ABI.md` | Enforce balanced spill discipline across all control-flow joins and non-local exits. |
| B10C-07 | Tailcall strategy | `compiler/WASM/wasm2.lisp`, `lisp-kernel/wasm-subprims-provider.c` | Implement explicit frame-reuse strategy where legal; remove wrapper-only semantics as default. |
| B10C-08 | FFI/import boundary audit | `compiler/WASM/wasm-ffi.lisp`, `doc/wasm/kernel-request-abi.md` | Keep external-call semantics deterministic and capability-safe under optimized backend flow. |
| B10C-09 | ARM marker audit gate | `scripts/wasm/arm-retirement-audit.sh` | wasm-facing surfaces pass strict ARM-coupling audit. |
| B10C-10 | Exit gate | all above | Compiler outputs run without ARM-emulation-critical assumptions in primary lanes. |

## Step 5 Output - Unified Validation and Promotion Gates (v1)

### Step 5 ID Namespace Freeze

| namespace | frozen range | meaning |
| --- | --- | --- |
| `B10V-*` | `B10V-01`..`B10V-08` | End-to-end validation and promotion checks for this implementation ticket. |

### Validation Matrix

| validation_id | check | command/evidence | pass rule |
| --- | --- | --- | --- |
| B10V-01 | ARM-coupling strict audit | `scripts/wasm/arm-retirement-audit.sh --strict` | Zero hits in wasm-facing targets. |
| B10V-02 | Subprim backlog closure | regenerated `doc/wasm/subprims-work-remaining.md` | `behavioral gap = 0`. |
| B10V-03 | Core smoke regression | `node doc/wasm/js/all-smoke.mjs` | Pass with no new backend-specific failures. |
| B10V-04 | Funcall/call ABI regression | `node doc/wasm/js/funcall-smoke.mjs` | Pass for argument/return semantics. |
| B10V-05 | Numeric regression | `node doc/wasm/js/fixnum-ops-smoke.mjs` and `node doc/wasm/js/fixnum-overflow-smoke.mjs` | Pass with expected overflow behavior. |
| B10V-06 | Compiler integration regression | `node doc/wasm/js/compiler-smoke.mjs` | Pass with wasm2 output loading and execution. |
| B10V-07 | GC stress lane | dedicated GC stress artifact for this ticket | No root-loss/forwarding corruption signatures. |
| B10V-08 | Exit bundle | `doc/wasm/tickets/evidence/bpl-10/<run_id>/...` | Deterministic summary artifact committed. |

## Risk Register

- Risk: subprim wave churn reintroduces behavior drift.
  - Mitigation: wave-ordered execution + generated backlog after each wave.
- Risk: GC descriptor refactor causes silent root omissions.
  - Mitigation: add targeted GC stress lane before promotion.
- Risk: compiler decoupling breaks existing bootstrap flow.
  - Mitigation: keep migration toggles explicit and validate with existing smoke lanes each increment.
- Risk: optimization attempts exceed current host capability envelope.
  - Mitigation: machine profile includes capability-gated optional features; baseline remains deterministic.

## Change Log

- 2026-02-10: Completed `B10G-01` compiler-owned root-policy mode publication by extending wasm2 compiled-module payloads with mode metadata (`compiler/WASM/wasm2.lisp`), propagating mode maps through bundle tooling (`scripts/wasm/compile-wasm-fasls.lisp`, `scripts/wasm/compile-smoke-modules.lisp`, `scripts/wasm/compile-ui-modules.lisp`, `scripts/wasm/pack-inline-bundle-v2.mjs`, `scripts/wasm/compact-runtime-modules.mjs`), wiring loader/kernel registration (`doc/wasm/js/ccl-loader.mjs`, `lisp-kernel/wasm-kernel-stubs.c`, `lisp-kernel/wasm-subprims-provider.c`, `lisp-kernel/wasm-gc.c`, `lisp-kernel/platform-wasm32.h`), and extending smoke assertions (`doc/wasm/js/smoke-test.mjs`, `doc/wasm/js/compiler-smoke.mjs`); rebuilt via documented `env.sh` flow and revalidated (`scripts/wasm/arm-retirement-audit.sh --strict` => `total_hits=0`, `node doc/wasm/js/all-smoke.mjs` pass after manifest refresh).
- 2026-02-10: Externalized `B10G-01` descriptor publication inputs by adding wasm platform API (`WASM_GC_ROOT_*` policy bits plus `wasm_publish_gc_root_policy`, `wasm_current_gc_root_policy`, `wasm_reset_gc_root_policy`) and converting GC walkers in `lisp-kernel/wasm-gc.c` to consume an active descriptor derived from published policy; rebuilt via documented `env.sh` flow and revalidated (`scripts/wasm/arm-retirement-audit.sh --strict` => `total_hits=0`, `node doc/wasm/js/all-smoke.mjs` pass from `ccl` root after manifest refresh).
- 2026-02-10: Wired first real producer adoption for `B10G-01` policy publication by calling `wasm_reset_gc_root_policy()` from `wasm_reset_root_image_runtime_state` in `lisp-kernel/wasm-kernel-stubs.c`, ensuring root-policy lifecycle reset is driven by a runtime boundary site; rebuilt and revalidated (`B10V-01 total_hits=0`, `B10V-03` pass after manifest refresh).
- 2026-02-10: Expanded `B10G-01` producer adoption to startup boundaries by calling `wasm_reset_gc_root_policy()` in `wasm_ccl_start` and `wasm_ccl_start_lisp` (`lisp-kernel/pmcl-kernel.c`), ensuring runtime entrypoints republish default root policy before execution; rebuilt and revalidated (`B10V-01 total_hits=0`, `B10V-03` pass after manifest refresh).
- 2026-02-10: Added host-visible non-default policy publication path by exporting `wasm_set_gc_root_policy`/`wasm_get_gc_root_policy` in `lisp-kernel/wasm-kernel-stubs.c` and extending `doc/wasm/js/smoke-test.mjs` to toggle a non-default policy bit and restore baseline; rebuilt and revalidated (`B10V-01 total_hits=0`, `B10V-03` pass after manifest refresh).
- 2026-02-10: Added runtime mode semantics for `B10G-01` by introducing root-policy mode constants/APIs in `lisp-kernel/platform-wasm32.h` + `lisp-kernel/wasm-gc.c` and wiring `wasm_set_subprims_ready` (`lisp-kernel/wasm-kernel-stubs.c`) to publish default/bootstrap modes; extended `doc/wasm/js/smoke-test.mjs` to validate mode-driven policy transitions and host-mode override/restore, then rebuilt and revalidated (`B10V-01 total_hits=0`, `B10V-03` pass after manifest refresh).
- 2026-02-10: Extended `B10G-01` descriptor coverage to C-stack safepoint frame roots in `lisp-kernel/wasm-gc.c` by adding descriptor-controlled C-stack slot publication and routing `mark_cstack_area`, `forward_cstack_area`, `purify_cstack_area`, and `impurify_cstack_area` through shared helper paths; rebuilt via documented `env.sh` flow and revalidated (`scripts/wasm/arm-retirement-audit.sh --strict` => `total_hits=0`, `node doc/wasm/js/all-smoke.mjs` pass from `ccl` root after manifest refresh).
- 2026-02-10: Extended `B10G-01` with an explicit wasm GC root-descriptor contract object in `lisp-kernel/wasm-gc.c` (XP span list + locative inclusion + TLB inclusion) and routed iterator helpers to consume it; rebuilt kernel via documented `env.sh` flow and revalidated with `node ccl/doc/wasm/js/all-smoke.mjs` (pass).
- 2026-02-10: Revalidated `B10G-01` changes against a rebuilt kernel artifact using the documented toolchain flow (`source scripts/wasm/env.sh` then `make -C lisp-kernel/wasm32 CC="$CC" WASM_LD="$WASM_LD"`); after rebuild, smoke lane pass was reconfirmed from workspace root with `node ccl/doc/wasm/js/all-smoke.mjs`.
- 2026-02-10: Extended `B10G-01` with shared TCR TLB bounds handling (`wasm_tcr_tlb_bounds`) and routed TLB consumers (`check_tcrs`, `purify_tcr_tlb`, `impurify_tcr_tlb`) through that single bounds path; validation remained green (`B10V-01 total_hits=0`, `B10V-03` pass).
- 2026-02-10: Extended `B10G-01` by introducing a shared TCR XP iterator (`wasm_for_each_tcr_xp`) and routing `check_tcrs`, `forward_tcr_xframes`, `purify_tcr_xframes`, and `impurify_tcr_xframes` through it, removing duplicated xframe walk logic while preserving duplicate-gc-context guard behavior in forwarding; validation remained green (`B10V-01 total_hits=0`, `B10V-03` pass).
- 2026-02-10: Extended `B10G-01` with descriptor-driven XP locative-slot traversal (PC/LR) in `lisp-kernel/wasm-gc.c`, routing mark/forward/purify/impurify locative handling through shared iteration helpers; validation remained green (`B10V-01 total_hits=0`, `B10V-03` pass).
- 2026-02-10: Completed `B10G-01` phase 2 by introducing wasm-owned transitional GPR aliases in `lisp-kernel/platform-wasm32.h` and switching the XP root descriptor in `lisp-kernel/wasm-gc.c` to `wasm_gpr_arg_z..wasm_gpr_fn`; validation remained green (`B10V-01 total_hits=0`, `B10V-03` pass).
- 2026-02-10: Started `B10G-01` phase 1 in `lisp-kernel/wasm-gc.c` by replacing direct XP loops (`mark_xp`, `forward_xp`, `check_xp`, `purify_xp`, `impurify_xp`) with a shared descriptor-driven root-slot iterator; validation remained green (`B10V-01 total_hits=0`, `B10V-03` pass).
- 2026-02-10: Executed a targeted compiler/header/doc ARM-marker retirement pass (`compiler/WASM/wasm-arch.lisp`, `compiler/WASM/wasm2.lisp`, `lisp-kernel/platform-wasm32.h`, `lisp-kernel/wasm-subprims-map.h`, `doc/wasm/ABI.md`) and re-ran validation gates; `scripts/wasm/arm-retirement-audit.sh --strict` now reports `total_hits=0` and `node doc/wasm/js/all-smoke.mjs` remains pass.
- 2026-02-10: Executed `B10V-01` and `B10V-03` validation gates after subprim closure; `node doc/wasm/js/all-smoke.mjs` passed, while `scripts/wasm/arm-retirement-audit.sh --strict` failed with `55` hits (primary concentration in `compiler/WASM/wasm2.lisp` and `compiler/WASM/wasm-arch.lisp`), shifting immediate work to targeted compiler ARM-marker retirement (`B10C-01`/`B10C-09`).
- 2026-02-10: Executed twenty-seventh Wave A (`B10S-01`) implementation step by updating interrupt-level subprims/helpers (`_SPbind_interrupt_level*`, `_SPunbind_interrupt_level`, `wasm_bind_interrupt_level`) to use neutral binding-slot naming and explicit local stack-pointer validation; regenerated backlog report reduced total `behavioral gap` count to `0` and achieved subprim closure gate `B10S-08`.
- 2026-02-10: Executed twenty-sixth Wave A (`B10S-01`) implementation step by updating `_SPspecref`, `_SPspecrefcheck`, and `_SPspecset` to use neutral binding-slot naming; regenerated backlog report reduced total `behavioral gap` count to `4`.
- 2026-02-10: Executed twenty-fifth Wave A (`B10S-01`) implementation step by updating `_SPreset` to use explicit local stack-pointer validation; regenerated backlog report reduced total `behavioral gap` count to `7`.
- 2026-02-10: Executed twenty-fourth Wave A (`B10S-01`) implementation step by updating `_SPcall_closure` to use explicit local stack-pointer validation; regenerated backlog report moved `_SPcall_closure` to `validation only` and reduced total `behavioral gap` count to `8`.
- 2026-02-10: Executed twenty-third Wave A (`B10S-01`) implementation step by updating `_SPprogvsave` and `_SPprogvrestore` with explicit local stack-pointer validation and neutral binding-slot naming; regenerated backlog report moved both to `validation only`, reduced total `behavioral gap` count to `12`, and advanced next target to `_SPcall_closure`.
- 2026-02-10: Executed twenty-second Wave A (`B10S-01`) implementation step by updating `_SPkeyword_bind` to use explicit local stack-pointer validation; regenerated backlog report moved `_SPkeyword_bind` to `validation only`, reduced total `behavioral gap` count to `14`, and advanced next target to `_SPprogvsave`.
- 2026-02-10: Executed twenty-first Wave A (`B10S-01`) implementation step by updating `_SPspread_lexprz` to use explicit local stack-pointer validation; regenerated backlog report moved `_SPspread_lexprz` to `validation only`, reduced total `behavioral gap` count to `18`, and advanced next target to `_SPkeyword_bind`.
- 2026-02-10: Executed twentieth Wave A (`B10S-01`) implementation step by updating `_SPspreadargz` to use explicit local stack-pointer validation; regenerated backlog report moved `_SPspreadargz` to `validation only` and reduced total `behavioral gap` count to `20`.
- 2026-02-10: Executed nineteenth Wave A (`B10S-01`) implementation step by updating `_SPreq_heap_rest_arg`, `_SPheap_cons_rest_arg`, and `_SPstack_cons_rest_arg` to use explicit local stack-pointer validation; regenerated backlog report moved all three to `validation only`, reduced total `behavioral gap` count to `22`, and advanced next target to `_SPspread_lexprz`.
- 2026-02-10: Executed eighteenth Wave A (`B10S-01`) implementation step by updating `_SPheap_rest_arg` to use explicit local stack-pointer validation; regenerated backlog report moved `_SPheap_rest_arg` to `validation only`, reduced total `behavioral gap` count to `25`, and advanced next target to `_SPreq_heap_rest_arg`.
- 2026-02-10: Executed seventeenth Wave A (`B10S-01`) implementation step by updating `_SPopt_supplied_p` to use explicit local stack-pointer validation; regenerated backlog report moved `_SPopt_supplied_p` to `validation only`, reduced total `behavioral gap` count to `26`, and advanced next target to `_SPheap_rest_arg`.
- 2026-02-10: Executed sixteenth Wave A (`B10S-01`) implementation step by updating `_SPnthvalue` to use explicit local stack-pointer validation; regenerated backlog report moved `_SPnthvalue` to `validation only` and reduced total `behavioral gap` count to `27`.
- 2026-02-10: Executed fifteenth Wave A (`B10S-01`) implementation step by updating `_SPfitvals` to use explicit local stack-pointer validation; regenerated backlog report moved `_SPfitvals` (and `_SPdefault_optional_args` after shared helper normalization) to `validation only`, reduced total `behavioral gap` count to `28`, and advanced next target to `_SPopt_supplied_p`.
- 2026-02-10: Executed fourteenth Wave A (`B10S-01`) implementation step by updating `_SPvalues` to use explicit local stack-pointer validation; regenerated backlog report moved `_SPvalues` to `validation only`, reduced total `behavioral gap` count to `30`, and advanced next target to `_SPfitvals`.
- 2026-02-10: Executed thirteenth Wave A (`B10S-01`) implementation step by updating `_SPmvslide` to use explicit local stack-pointer validation; regenerated backlog report moved `_SPmvslide` to `validation only` and reduced total `behavioral gap` count to `31`.
- 2026-02-10: Executed twelfth Wave A (`B10S-01`) implementation step by updating `_SPmvpass` to use explicit local stack-pointer validation; regenerated backlog report moved `_SPmvpass` to `validation only`, reduced total `behavioral gap` count to `32`, and advanced next target to `_SPmvslide`.
- 2026-02-10: Executed eleventh Wave A (`B10S-01`) implementation step by updating `_SPmkunwind` null-check naming (`target_link`); regenerated backlog report moved `_SPmkunwind` to `validation only` and reduced total `behavioral gap` count to `33`.
- 2026-02-10: Executed tenth Wave A (`B10S-01`) implementation step by updating `_SPnthrowvalues` null-check naming (`target_link`, `saved_stack_ptr`) and replacing helper VSP checks with explicit local stack-pointer validation; regenerated backlog report moved `_SPnthrowvalues` to `validation only`, reduced total `behavioral gap` count to `34`, and advanced next target to `_SPmkunwind`.
- 2026-02-10: Executed ninth Wave A (`B10S-01`) implementation step by updating `_SPnthrow1value` null-check naming (`target_link`, `saved_stack_ptr`); regenerated backlog report moved `_SPnthrow1value` to `validation only`, reduced total `behavioral gap` count to `35`, and advanced next target to `_SPnthrowvalues`.
- 2026-02-10: Executed eighth Wave A (`B10S-01`) implementation step by hardening `_SPthrow` with explicit local stack-pointer validation; regenerated backlog report keeps aggregate totals at `behavioral gap=37`, `validation only=86` and advances the next implementation target to `_SPnthrow1value`.
- 2026-02-10: Executed seventh Wave A (`B10S-01`) implementation step by updating `_SPunbind_to` via `wasm_unbind_to`; regenerated backlog report moved `_SPunbind_to` to `validation only` and reduced total `behavioral gap` count to `37`.
- 2026-02-10: Executed sixth Wave A (`B10S-01`) implementation step by updating `_SPunbind_n`; regenerated backlog report moved `_SPunbind_n` to `validation only` and reduced total `behavioral gap` count to `38`.
- 2026-02-10: Executed fifth Wave A (`B10S-01`) implementation step by updating `_SPunbind`; regenerated backlog report moved `_SPunbind` to `validation only` and reduced total `behavioral gap` count to `39`.
- 2026-02-10: Executed fourth Wave A (`B10S-01`) implementation step by updating `_SPbind_self_boundp_check`; regenerated backlog report moved `_SPbind_self_boundp_check` to `validation only` and reduced total `behavioral gap` count to `40`.
- 2026-02-10: Executed third Wave A (`B10S-01`) implementation step by updating `_SPbind_self`; regenerated backlog report moved `_SPbind_self` to `validation only` and reduced total `behavioral gap` count to `41`.
- 2026-02-10: Executed second Wave A (`B10S-01`) implementation step by updating `_SPbind`; regenerated backlog report moved `_SPbind` to `validation only` and reduced total `behavioral gap` count to `42`.
- 2026-02-10: Executed first Wave A (`B10S-01`) implementation step by updating `_SPdebind`; regenerated backlog report moved `_SPdebind` to `validation only` and reduced total `behavioral gap` count to `43`.
- 2026-02-10: Created BPL-10 as the active implementation plan for remaining backend work (WASM machine model, subprims completion, L1 GC modernization, and compiler/backend decoupling).
