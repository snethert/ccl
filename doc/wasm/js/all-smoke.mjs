/*
 * Run all WASM JS smoke tests in a single Node invocation.
 */

const tests = [
  "./smoke-test.mjs",
  "./kernel-request-smoke.mjs",
  "./stream-open-smoke.mjs",
  "./pending-stdin-smoke.mjs",
  "./ccl-step-smoke.mjs",
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
  "./mv-helpers-smoke.mjs"
];

for (const test of tests) {
  await import(new URL(test, import.meta.url));
}

console.log("PASS: all wasm smoke tests");
