# Front-End Bridge Plan (Lisp<->JS UI)

This plan moves authoritative UI state into the WASM/Lisp runner while reusing the existing JS backends for rendering and input. It is sequential and executable end-to-end.

## Phase 0: Lock the Bridge Contract (Spec + ABI)
1. Add `doc/wasm/ui-bridge-protocol.md` defining wire formats for UI render trees and input event batches.
2. Extend `doc/wasm/kernel-opcode-registry.md` with UI opcodes.
3. Extend `doc/wasm/kernel-request-abi.md` with payload/response layouts for UI opcodes.
4. Update `doc/wasm/browser-ui-spec.md` to reference the UI bridge protocol and state JS is the rendering backend.

Exit criteria:
- Versioned wire format and opcode list exists with unambiguous layouts.

## Phase 1: Define the Concrete UI Opcodes
1. Add opcodes:
   - `KERNEL_OP_UI_POLL` (input event batches)
   - `KERNEL_OP_UI_RENDER` (submit VDOM tree/patch)
   - `KERNEL_OP_UI_MEASURE_TEXT` (text metrics)
2. Define request/response layouts:
   - `UI_POLL` request: `maxEvents`, `maxBytes`, `flags`.
   - `UI_POLL` response: encoded event batch.
   - `UI_RENDER` request: encoded tree payload; response `0` on success.
   - `UI_MEASURE_TEXT` request: font + text; response metrics.

Exit criteria:
- ABI layouts are stable and fully documented.

## Phase 2: JS Microkernel Support
1. Extend `doc/wasm/js/microkernel.mjs` to recognize UI opcodes.
2. Add a UI service interface inside the microkernel:
   - `enqueueEvent(event)`
   - `pollEvents(maxEvents, maxBytes, flags)`
   - `renderTree(payloadBytes)`
   - `measureText(payloadBytes)`
3. Implement `UI_POLL` with `PENDING` when queue is empty and blocking is requested.

Exit criteria:
- Microkernel handles UI requests and returns `-ENOSYS` if UI service is not installed.

## Phase 3: JS Bridge Module (Renderer + Event Capture)
1. Implement a bridge in `web-ui/bridge/` that:
   - Creates DOM backend and root renderer.
   - Captures DOM input and queues events.
2. Capture: pointer, keyboard, focus/blur, IME composition.
3. Provide `createUiBridge({ container, document })` returning the UI service object.

Exit criteria:
- Bridge can render VDOM and queue events without mutating app state.

## Phase 4: Wire Format Implementation (JS)
1. Implement encode/decode modules in `web-ui/bridge/`:
   - `encodeEvents(events) -> Uint8Array`
   - `decodeTree(payload) -> VDOM`
2. Use deterministic binary encoding (string table + flat node list).
3. Add JS unit tests for round-trip determinism.

Exit criteria:
- JS can decode a VDOM payload into the existing renderer and encode event batches.

## Phase 5: Lisp/WASM UI Core (MVP)
1. Implement minimal Lisp UI core:
   - tasks/windows/widgets
   - command registry
   - UI turn queue
2. Build VDOM in Lisp for minimal widgets.
3. Encode VDOM to the wire format; decode `UI_POLL` events.

Exit criteria:
- Lisp UI loop emits VDOM and consumes event batches.

Status note:
- Non-immediate constants still fail unless the constant pool is enabled. `external-call`/FFI now compiles under `:wasm32`, and real UI modules build with const-pool enabled. The browser harness now includes a WASM-UI-TURN round trip when wasm assets are available.

Compiler/runtime unblock plan (detailed, sequential):
1. Capture two failing repros: a function referencing a symbol/string constant and a function calling `external-call` under `:wasm32` compilation.
2. Document the constant pool v1 format and supported object kinds in `doc/wasm/decisions.md` or a new `doc/wasm/const-pool.md`.
3. Add a constant-pool table to WASM2 compilation state in `compiler/WASM/wasm2.lisp`.
4. Implement deduped pooling of non-immediate constants and return pool indices from the constant emission path in `compiler/WASM/wasm2.lisp`.
5. Add IR ops for pool references, e.g. `:const-object` and `:const-pool-ref`, and thread them through the WASM2 emitter.
6. Emit constant pool metadata into the compiled module bundle written by `scripts/wasm/compile-*.lisp`.
7. Extend the module install path to materialize pool objects in `lisp-kernel/wasm-host.c` and record GC roots.
8. Add pool object retention hooks to the image/module loader in `xdump/xwasmfasload.lisp` (or the WASM loader path used by compiled module install).
9. Implement symbol interning during pool materialization so symbol identity is stable across module reloads.
10. Implement function identity resolution for pooled function references (e.g., resolve by symbol fdefinition or exported entry index).
11. Specify the minimal WASM FFI ABI for `external-call` in `doc/wasm/kernel-request-abi.md` or `doc/wasm/decisions.md`.
12. Implement `external-call` lowering in `compiler/WASM/wasm2.lisp` with imports or kernel_request shims per the ABI.
13. Add spill/restore and GC-safety constraints for FFI calls in `compiler/WASM/wasm-backend.lisp`.
14. Add host-side shims to execute the FFI calls in `lisp-kernel/wasm-host.c` and `doc/wasm/js/microkernel.mjs` if JS dispatch is needed.
15. Add smoke compilation tests for a symbol constant and an `external-call` in `scripts/wasm/compile-smoke-modules.lisp`. (done)
16. Add JS harness smoke coverage to load and execute the new compiled entries in `doc/wasm/js/compiler-smoke.mjs`. (done)
17. Validate that compiled module reload keeps entry indices and pool object identity stable across refresh. (done)
18. Remove the UI module stub fallback in `scripts/wasm/compile-ui-modules.lisp` once constant pools compile successfully. (done)
19. Rebuild `doc/wasm/wasm-ui-modules.json` with real Lisp UI functions and update any loader references if needed. (done)
20. Add a browser harness assertion that invokes `WASM-UI-TURN` from the compiled bundle and verifies a render round trip. (done)
21. Update this plan and status notes once the above smoke tests pass. (updated; `compiler-smoke`/`all-smoke` green as of 2026-02-08)

Current status:
- Repros: `scripts/wasm/repro-compiler-blocks.lisp` shows symbol/string constants still fail unless const-pool is enabled; `external-call` now compiles.
- Smoke: `scripts/wasm/compile-smoke-modules.lisp` emits modules including constant-pool entries and the FFI smoke entry; `doc/wasm/js/compiler-smoke.mjs` and `doc/wasm/js/all-smoke.mjs` are green.
- Constant-pool runtime install/ref + symbol interning + function resolution are implemented in `lisp-kernel/wasm-kernel-stubs.c` and wired through `doc/wasm/js/ccl-loader.mjs`.
- Added wasm `funcall` support for 3–6 args to unblock UI keyword calls.
- `scripts/wasm/compile-ui-modules.lisp` now completes and rebuilds `doc/wasm/wasm-ui-modules.json`.
- Browser harness invokes `WASM-UI-TURN` via the compiled bundle in `web-ui/tests/browser/harness.mjs` (not exercised by `doc/wasm/js/all-smoke.mjs --no-ui`).
- UI poll now yields on `-EWOULDBLOCK` when `allow-pending` is set, and `ccl::*wasm-yield-on-eagain*` defaults to `T` on wasm builds to enable `wasm_ccl_step` integration.

## Phase 6: Lisp<->JS Integration (Kernel ABI Helpers)
1. Add UI opcode helpers in `lisp-kernel/wasm-host.c`.
2. Lisp wrappers for UI poll/render/measure.
3. Integrate with `wasm_ccl_step` (yield on PENDING).

Exit criteria:
- Lisp runner renders and handles events via microkernel without blocking.

Status: Complete

## Phase 7: End-to-End Bridge Smoke Test
1. Add a smoke test that:
   - Starts runner and microkernel in browser harness.
   - Renders button + label.
   - Click updates label.
2. Run via `web-ui/tests/browser.test.mjs`.

Exit criteria:
- Bridge passes in headless browser with deterministic output.

Status note:
- Browser harness now runs the WASM UI demo turn via the kernel export (`wasm_ui_demo_turn`) when using the minimal image; a full Lisp/UI image is still required to exercise the compiled Lisp UI path.
- Headless harness now falls back to an in-process route server when localhost binds are blocked, but Playwright still requires browser launch permissions (some environments skip with EPERM/Mach port errors).

Status: Complete (WASM)

## Phase 8: Canvas/WebGL Views
1. Allow Lisp to emit canvas/webgl views with stable IDs.
2. JS bridge installs canvas/webgl render hooks and hit-testing.
3. Validate with smoke tests.

Exit criteria:
- Canvas/WebGL views participate in input + command routing.

Execution plan:
- Extend the UI bridge to detect `canvas` nodes with `data-canvas-scene` or `data-webgl-scene` props and render them via the canvas/WebGL backends.
- Encode canvas/webgl hit targets as stable IDs (e.g., `${viewId}:${hitId}`) during pointer/wheel event capture.
- Add headless browser harness coverage to render a canvas/webgl scene via UI bridge and assert hit-test routing.

Status note:
- Kernel demo payload includes canvas/webgl widgets with scene payloads; browser harness validates hit-testing and command routing for canvas/webgl targets. Lisp emission remains pending a real image.

Status: Complete (WASM)

## Phase 9: Persistence + Inspector/Debugger Integration
1. Persist Lisp UI snapshots via kernel_request storage.
2. Wire inspector/debugger windows.
3. Add restore tests.

Exit criteria:
- Persistent sessions restore deterministically with debugger/inspector windows.

Execution plan:
- Define snapshot payloads for Lisp UI state and route them through kernel_request persistence.
- Add Lisp-side serializer/deserializer and JS microkernel persistence bindings.
- Wire inspector/debugger window descriptors to persisted task/window state and add restore tests.

Status note:
- Implemented Lisp UI snapshot serialization + file persistence via kernel_request streams.
- Added minimal inspector/debugger window helpers (titles + IDs) suitable for persistence restore.
- Added WASM UI persistence smoke test (`doc/wasm/js/wasm-ui-persist-smoke.mjs`) with strict-mode execution (`--strict`) for the full runtime path.
- The default non-strict path intentionally skips to keep sandbox/default smoke deterministic while minimal-image runtime stabilization continues.

Status: Partial (Lisp MVP scaffolding complete; full compiled-Lisp image path pending)

## Phase 10: Parity + Cleanup
1. Verify Lisp semantics match JS reference model where applicable.
2. Update status docs.
3. Remove temporary shims.

Exit criteria:
- Lisp runner is authoritative, JS is backend-only, and bridge is stable.

Execution plan:
- Create a parity checklist comparing Lisp UI behavior to the JS reference model.
- Update all status docs and remove transitional shims once Lisp becomes authoritative.

Status note:
- Deferred until Phases 5-9 unblock Lisp-side execution.
