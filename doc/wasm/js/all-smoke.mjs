/*
 * Run all WASM JS smoke tests in a single Node invocation.
 */

const skipUi = process.argv.includes("--no-ui");
const includeWasmUiPersist = process.argv.includes("--with-wasm-ui-persist");
const tests = [
  "./smoke-test.mjs",
  "./kernel-request-smoke.mjs",
  "./compiled-modules-refresh-smoke.mjs",
  "./stream-open-smoke.mjs",
  "./stream-seek-truncate-smoke.mjs",
  "./stream-seek-truncate-wasm-smoke.mjs",
  "./pending-stdin-smoke.mjs",
  "./ccl-step-smoke.mjs",
  "./start-lisp-smoke.mjs",
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

console.log("PASS: all wasm smoke tests");
