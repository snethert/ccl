/*
 * Run all WASM JS smoke tests in a single Node invocation.
 */

import { emitSyntheticIpcArtifacts } from "./ipc-conformance.mjs";
import { emitSyntheticStorageV2Artifacts } from "./storage-v2-conformance.mjs";

const skipUi = process.argv.includes("--no-ui");
const includeWasmUiPersist = process.argv.includes("--with-wasm-ui-persist");
const ipcConformanceId = process.env.CCL_IPC_CONFORMANCE_ID ?? null;
const ipcLaneId = process.env.CCL_IPC_LANE_ID ?? null;
const bridgeInjectedFailureCode = /^RPL03-E\d{3}$/.test(String(process.env.CCL_UI_BRIDGE_TEST_INJECT_FAILURE ?? ""))
  ? String(process.env.CCL_UI_BRIDGE_TEST_INJECT_FAILURE)
  : null;
const ipcInjectedFailureCode = /^RPL03-E\d{3}$/.test(String(process.env.CCL_IPC_TEST_INJECT_FAILURE ?? ""))
  ? String(process.env.CCL_IPC_TEST_INJECT_FAILURE)
  : null;
const forcedBridgeFallback = String(process.env.CCL_UI_BRIDGE_TEST_FORCE_FALLBACK ?? "") === "1";
const injectedFailureCode = bridgeInjectedFailureCode ?? ipcInjectedFailureCode;
const defaultLaneClass = skipUi ? "headless_runtime" : "ui_runtime";

if (injectedFailureCode || forcedBridgeFallback) {
  emitSyntheticIpcArtifacts({
    defaultLaneClass,
    laneId: ipcLaneId,
    conformanceId: ipcConformanceId,
    source: "doc/wasm/js/all-smoke.mjs",
    failureCode: injectedFailureCode ?? "RPL03-E008",
    failureMessage: forcedBridgeFallback
      ? "forced bridge fallback blocked by no-silent-fallback policy"
      : null,
  });
  process.exit(1);
}

const tests = [
  "./smoke-test.mjs",
  "./gc-forwarding-smoke.mjs",
  "./cstack-frame-coherence-smoke.mjs",
  "./kernel-request-smoke.mjs",
  "./runtime-modules-manifest-smoke.mjs",
  "./root-image-manifest-smoke.mjs",
  "./compiled-modules-refresh-smoke.mjs",
  "./stream-open-smoke.mjs",
  "./stream-seek-truncate-smoke.mjs",
  "./stream-seek-truncate-wasm-smoke.mjs",
  "./pending-stdin-smoke.mjs",
  "./ccl-step-smoke.mjs",
  "./start-lisp-smoke.mjs",
  "./start-lisp-noninteractive-smoke.mjs",
  "./start-boot-smoke.mjs",
  "./toplevel-slot-smoke.mjs",
  "./world-kernel-start-smoke.mjs",
  "./step-demo.mjs",
  "./funcall-smoke.mjs",
  "./const-funcall-smoke.mjs",
  "./const-module-smoke.mjs",
  "./if-smoke.mjs",
  "./if-arg-smoke.mjs",
  "./identity-smoke.mjs",
  "./identity-y-smoke.mjs",
  "./fixnum-add-smoke.mjs",
  "./fixnum-sub-smoke.mjs",
  "./fixnum-ops-smoke.mjs",
  "./fixnum-overflow-smoke.mjs",
  "./compiler-smoke.mjs",
  "./float-smoke.mjs",
  "./web-ui-list-smoke.mjs",
  "./web-ui-virtual-smoke.mjs",
  "./web-ui-canvas-smoke.mjs",
  "./web-ui-webgl-smoke.mjs",
  "./web-ui-command-ui-smoke.mjs",
  "./runtime-command-smoke.mjs",
  "./runtime-debugger-smoke.mjs",
  "./runtime-inspector-smoke.mjs",
  "./runtime-jobs-smoke.mjs",
  "./web-ui-persist-smoke.mjs",
  "./web-ui-layout-focus-smoke.mjs",
  "./web-ui-inspector-smoke.mjs",
  "./web-ui-debugger-smoke.mjs",
  "./closure-unwind-mv-smoke.mjs",
  "./mv-helpers-smoke.mjs",
  "./mvcall-smoke.mjs"
];

if (includeWasmUiPersist) {
  tests.splice(tests.indexOf("./web-ui-layout-focus-smoke.mjs"), 0, "./wasm-ui-persist-smoke.mjs");
}

const filteredTests = skipUi
  ? tests.filter((test) => !test.startsWith("./web-ui-"))
  : tests;

for (const test of filteredTests) {
  await import(new URL(test, import.meta.url));
}

emitSyntheticStorageV2Artifacts({
  source: "doc/wasm/js/all-smoke.mjs",
});

emitSyntheticIpcArtifacts({
  defaultLaneClass,
  laneId: ipcLaneId,
  conformanceId: ipcConformanceId,
  source: "doc/wasm/js/all-smoke.mjs",
});

console.log("PASS: all wasm smoke tests");
