import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  applyRuntimeOutput,
  applyRuntimeMessage,
  drainRuntimeSabMessages
} from "../src/index.mjs";
import {
  createMicrokernel,
  KERNEL_OP_STREAM_WRITE,
  KERNEL_OP_RUNTIME_EVENT
} from "../../doc/wasm/js/microkernel.mjs";
import { createSabRing, SAB_RING_TRANSPORT } from "../../doc/wasm/js/sab-ring.mjs";

function encodeUtf8(text) {
  return new TextEncoder().encode(String(text));
}

function writeBytes(mem, ptr, bytes) {
  new Uint8Array(mem.buffer, ptr, bytes.length).set(bytes);
}

const WASM_STARTUP_DIAG_MAGIC_V1 = 0x31534457;
const WASM_STARTUP_DIAG_V1_SIZE = 132;
const WASM_STARTUP_DIAG_MAGIC_V2 = 0x32534457;
const WASM_STARTUP_DIAG_V2_SIZE = 196;
const WASM_FASLOAD_TRACE_MAGIC_V1 = 0x31534657;
const WASM_FASLOAD_TRACE_V1_SIZE = 56;
const WASM_FASLOAD_TRACE_MAGIC_V2 = 0x32534657;
const WASM_FASLOAD_TRACE_V2_SIZE = 84;
const WASM_TOPLFUNC_TRACE_MAGIC_V1 = 0x31544657;
const WASM_TOPLFUNC_TRACE_V1_SIZE = 48;

function encodeStartupDiagV1(overrides = {}) {
  const defaults = {
    eventCode: 3,
    rc: -2,
    line: 4301,
    tcrPtr: 0x1000,
    throwBefore: 0,
    throwAfter: 0x2000,
    pendingConditionBefore: 0,
    internSymObj: 0x3000,
    internSymTag: 5,
    internSymSubtag: 1,
    internFcellObj: 0x4000,
    internFcellTag: 5,
    internFcellSubtag: 9,
    pkgObj: 0x5000,
    pkgTag: 5,
    pkgSubtag: 6,
    pkgInScannableArea: 1,
    nameObj: 0x6000,
    nameTag: 5,
    nameSubtag: 31,
    nameLenInput: 6,
    nameLenObj: 6,
    resultObj: 0,
    resultTag: 0,
    resultSubtag: 0xffffffff,
    cspBefore: 0x7000,
    vspBefore: 0x7100,
    tspBefore: 0x7200,
    cspAfter: 0x7000,
    vspAfter: 0x70f0,
    tspAfter: 0x7200,
    ...overrides
  };
  const buf = new ArrayBuffer(WASM_STARTUP_DIAG_V1_SIZE);
  const dv = new DataView(buf);
  let off = 0;
  const setU32 = (value) => {
    dv.setUint32(off, Number(value) >>> 0, true);
    off += 4;
  };
  const setI32 = (value) => {
    dv.setInt32(off, Number(value) | 0, true);
    off += 4;
  };

  setU32(WASM_STARTUP_DIAG_MAGIC_V1);
  setU32(1);
  setU32(defaults.eventCode);
  setI32(defaults.rc);
  setU32(defaults.line);
  setU32(defaults.tcrPtr);
  setU32(defaults.throwBefore);
  setU32(defaults.throwAfter);
  setU32(defaults.pendingConditionBefore);
  setU32(defaults.internSymObj);
  setU32(defaults.internSymTag);
  setU32(defaults.internSymSubtag);
  setU32(defaults.internFcellObj);
  setU32(defaults.internFcellTag);
  setU32(defaults.internFcellSubtag);
  setU32(defaults.pkgObj);
  setU32(defaults.pkgTag);
  setU32(defaults.pkgSubtag);
  setU32(defaults.pkgInScannableArea);
  setU32(defaults.nameObj);
  setU32(defaults.nameTag);
  setU32(defaults.nameSubtag);
  setU32(defaults.nameLenInput);
  setU32(defaults.nameLenObj);
  setU32(defaults.resultObj);
  setU32(defaults.resultTag);
  setU32(defaults.resultSubtag);
  setU32(defaults.cspBefore);
  setU32(defaults.vspBefore);
  setU32(defaults.tspBefore);
  setU32(defaults.cspAfter);
  setU32(defaults.vspAfter);
  setU32(defaults.tspAfter);
  return new Uint8Array(buf);
}

function encodeStartupDiagV2(overrides = {}) {
  const defaults = {
    eventCode: 4,
    rc: -3,
    line: 4490,
    tcrPtr: 0x1000,
    throwBefore: 0,
    throwAfter: 0,
    pendingConditionBefore: 0,
    internSymObj: 0x3000,
    internSymTag: 5,
    internSymSubtag: 1,
    internFcellObj: 0x4000,
    internFcellTag: 5,
    internFcellSubtag: 9,
    pkgObj: 0x5000,
    pkgTag: 5,
    pkgSubtag: 6,
    pkgInScannableArea: 1,
    nameObj: 0x6000,
    nameTag: 5,
    nameSubtag: 31,
    nameLenInput: 6,
    nameLenObj: 6,
    resultObj: 0,
    resultTag: 0,
    resultSubtag: 0xffffffff,
    cspBefore: 0x7000,
    vspBefore: 0x7100,
    tspBefore: 0x7200,
    cspAfter: 0x7000,
    vspAfter: 0x70f0,
    tspAfter: 0x7200,
    callableObj: 0x3000,
    callableTag: 5,
    callableSubtag: 1,
    callableValid: 1,
    internFcellResolved: 0,
    internFcellIsUdf: 1,
    pkgValid: 1,
    nameIsBaseString: 1,
    nameLenMatchesInput: 1,
    nameBytesMatchInput: 1,
    pendingConditionSnapshotBeforeClear: 0,
    abortReasonCode: 3,
    firstFailNameLen: 6,
    firstFailNameHash: 0x89abcdef,
    firstFailNamePrefix: 0x44414f4c,
    abortOnFirstFailure: 1,
    ...overrides
  };
  const buf = new ArrayBuffer(WASM_STARTUP_DIAG_V2_SIZE);
  const dv = new DataView(buf);
  let off = 0;
  const setU32 = (value) => {
    dv.setUint32(off, Number(value) >>> 0, true);
    off += 4;
  };
  const setI32 = (value) => {
    dv.setInt32(off, Number(value) | 0, true);
    off += 4;
  };

  setU32(WASM_STARTUP_DIAG_MAGIC_V2);
  setU32(2);
  setU32(defaults.eventCode);
  setI32(defaults.rc);
  setU32(defaults.line);
  setU32(defaults.tcrPtr);
  setU32(defaults.throwBefore);
  setU32(defaults.throwAfter);
  setU32(defaults.pendingConditionBefore);
  setU32(defaults.internSymObj);
  setU32(defaults.internSymTag);
  setU32(defaults.internSymSubtag);
  setU32(defaults.internFcellObj);
  setU32(defaults.internFcellTag);
  setU32(defaults.internFcellSubtag);
  setU32(defaults.pkgObj);
  setU32(defaults.pkgTag);
  setU32(defaults.pkgSubtag);
  setU32(defaults.pkgInScannableArea);
  setU32(defaults.nameObj);
  setU32(defaults.nameTag);
  setU32(defaults.nameSubtag);
  setU32(defaults.nameLenInput);
  setU32(defaults.nameLenObj);
  setU32(defaults.resultObj);
  setU32(defaults.resultTag);
  setU32(defaults.resultSubtag);
  setU32(defaults.cspBefore);
  setU32(defaults.vspBefore);
  setU32(defaults.tspBefore);
  setU32(defaults.cspAfter);
  setU32(defaults.vspAfter);
  setU32(defaults.tspAfter);
  setU32(defaults.callableObj);
  setU32(defaults.callableTag);
  setU32(defaults.callableSubtag);
  setU32(defaults.callableValid);
  setU32(defaults.internFcellResolved);
  setU32(defaults.internFcellIsUdf);
  setU32(defaults.pkgValid);
  setU32(defaults.nameIsBaseString);
  setU32(defaults.nameLenMatchesInput);
  setU32(defaults.nameBytesMatchInput);
  setU32(defaults.pendingConditionSnapshotBeforeClear);
  setU32(defaults.abortReasonCode);
  setU32(defaults.firstFailNameLen);
  setU32(defaults.firstFailNameHash);
  setU32(defaults.firstFailNamePrefix);
  setU32(defaults.abortOnFirstFailure);
  return new Uint8Array(buf);
}

function encodeFasloadTraceV1(overrides = {}) {
  const defaults = {
    stepCode: 16,
    rc: 0,
    line: 4902,
    throwState: 4,
    pathLen: 13,
    pathPrefix: 0x656c6576,
    symbolObj: 0x01020304,
    symbolTag: 6,
    symbolSubtag: 58,
    callableObj: 0x05060708,
    callableTag: 6,
    callableSubtag: 42,
    ...overrides
  };
  const buf = new ArrayBuffer(WASM_FASLOAD_TRACE_V1_SIZE);
  const dv = new DataView(buf);
  let off = 0;
  const setU32 = (value) => {
    dv.setUint32(off, Number(value) >>> 0, true);
    off += 4;
  };
  const setI32 = (value) => {
    dv.setInt32(off, Number(value) | 0, true);
    off += 4;
  };

  setU32(WASM_FASLOAD_TRACE_MAGIC_V1);
  setU32(1);
  setU32(defaults.stepCode);
  setI32(defaults.rc);
  setU32(defaults.line);
  setU32(defaults.throwState);
  setU32(defaults.pathLen);
  setU32(defaults.pathPrefix);
  setU32(defaults.symbolObj);
  setU32(defaults.symbolTag);
  setU32(defaults.symbolSubtag);
  setU32(defaults.callableObj);
  setU32(defaults.callableTag);
  setU32(defaults.callableSubtag);
  return new Uint8Array(buf);
}

function encodeFasloadTraceV2(overrides = {}) {
  const defaults = {
    stepCode: 17,
    rc: -7,
    line: 4912,
    throwState: 4,
    pathLen: 25,
    pathPrefix: 0x6d697373,
    symbolObj: 0x11111111,
    symbolTag: 6,
    symbolSubtag: 58,
    callableObj: 0x22222222,
    callableTag: 6,
    callableSubtag: 42,
    argZ: 0x4000001,
    argY: 0x34,
    nfn: 0x4000001,
    nargs: 0x2,
    vsp: 0x100100,
    csp: 0x200200,
    tsp: 0x300300,
    ...overrides
  };
  const buf = new ArrayBuffer(WASM_FASLOAD_TRACE_V2_SIZE);
  const dv = new DataView(buf);
  let off = 0;
  const setU32 = (value) => {
    dv.setUint32(off, Number(value) >>> 0, true);
    off += 4;
  };
  const setI32 = (value) => {
    dv.setInt32(off, Number(value) | 0, true);
    off += 4;
  };

  setU32(WASM_FASLOAD_TRACE_MAGIC_V2);
  setU32(2);
  setU32(defaults.stepCode);
  setI32(defaults.rc);
  setU32(defaults.line);
  setU32(defaults.throwState);
  setU32(defaults.pathLen);
  setU32(defaults.pathPrefix);
  setU32(defaults.symbolObj);
  setU32(defaults.symbolTag);
  setU32(defaults.symbolSubtag);
  setU32(defaults.callableObj);
  setU32(defaults.callableTag);
  setU32(defaults.callableSubtag);
  setU32(defaults.argZ);
  setU32(defaults.argY);
  setU32(defaults.nfn);
  setU32(defaults.nargs);
  setU32(defaults.vsp);
  setU32(defaults.csp);
  setU32(defaults.tsp);
  return new Uint8Array(buf);
}

function encodeToplfuncTraceV1(overrides = {}) {
  const defaults = {
    writerCode: 3,
    phaseCode: 2,
    targetCode: 2,
    line: 3410,
    rawValue: 0x4000001,
    entryIndex: -1,
    pendingThrow: 0,
    tcrPtr: 0x01020304,
    nrsToplfuncRaw: 0x4000001,
    tcrSlotRaw: 0x05060708,
    ...overrides
  };
  const buf = new ArrayBuffer(WASM_TOPLFUNC_TRACE_V1_SIZE);
  const dv = new DataView(buf);
  let off = 0;
  const setU32 = (value) => {
    dv.setUint32(off, Number(value) >>> 0, true);
    off += 4;
  };
  const setI32 = (value) => {
    dv.setInt32(off, Number(value) | 0, true);
    off += 4;
  };

  setU32(WASM_TOPLFUNC_TRACE_MAGIC_V1);
  setU32(1);
  setU32(defaults.writerCode);
  setU32(defaults.phaseCode);
  setU32(defaults.targetCode);
  setU32(defaults.line);
  setU32(defaults.rawValue);
  setI32(defaults.entryIndex);
  setU32(defaults.pendingThrow);
  setU32(defaults.tcrPtr);
  setU32(defaults.nrsToplfuncRaw);
  setU32(defaults.tcrSlotRaw);
  return new Uint8Array(buf);
}

test("applyRuntimeOutput ingests recording payloads", () => {
  const state = createState();
  const payload = {
    recording: { id: "rec-1", jobId: "job-1", streamId: "repl" },
    entry: { id: "ent-1", recordingId: "rec-1", kind: "text", text: "=> 42", seq: 1, ts: 10 },
    anchor: { id: "anc-1", entryId: "ent-1", range: { start: 4, end: 6 }, path: [] }
  };
  const result = applyRuntimeOutput(state, payload);
  assert.deepEqual(result.errors, []);
  assert.ok(result.state.recordingStore.recordings["rec-1"]);
  assert.ok(result.state.recordingStore.entries["ent-1"]);
  assert.ok(result.state.recordingStore.anchors["anc-1"]);
});

test("applyRuntimeMessage handles runtime.output", () => {
  const state = createState();
  const message = {
    kind: "runtime.output",
    payload: { recording: { id: "rec-2", jobId: "job-2", streamId: "repl" } }
  };
  const result = applyRuntimeMessage(state, message);
  assert.equal(result.handled, true);
  assert.ok(result.state.recordingStore.recordings["rec-2"]);
});

test("microkernel emits runtime.output on stdout writes", () => {
  const memory = new WebAssembly.Memory({ initial: 1 });
  const messages = [];
  const microkernel = createMicrokernel({
    memory,
    runtimeBridge: {
      jobId: "job-1",
      emit: (msg) => messages.push(msg)
    }
  });

  const payloadPtr = 0;
  const bytes = encodeUtf8("hello\n");
  const dataPtr = 64;
  writeBytes(memory, dataPtr, bytes);
  const dv = new DataView(memory.buffer, payloadPtr, 16);
  dv.setUint32(0, 1, true); // sid stdout
  dv.setUint32(4, 0, true); // flags
  dv.setUint32(8, dataPtr, true);
  dv.setUint32(12, bytes.length, true);

  const id = microkernel.imports.kernel_request(KERNEL_OP_STREAM_WRITE, payloadPtr, 16);
  microkernel.imports.kernel_poll(id);
  microkernel.imports.kernel_drop_request(id);

  assert.equal(messages.length, 1);
  assert.equal(messages[0].kind, "runtime.output");
  assert.equal(messages[0].payload.entry.text, "hello\n");
  assert.equal(messages[0].payload.recording.jobId, "job-1");
});

test("microkernel accepts KERNEL_OP_RUNTIME_EVENT payloads", () => {
  const memory = new WebAssembly.Memory({ initial: 1 });
  const messages = [];
  const microkernel = createMicrokernel({
    memory,
    runtimeBridge: {
      emit: (msg) => messages.push(msg)
    }
  });

  const payload = {
    version: 1,
    kind: "runtime.output",
    jobId: "job-2",
    streamId: "repl",
    requestId: null,
    seq: 1,
    ts: 123,
    payload: { recording: { id: "rec-9" } },
    error: null
  };
  const payloadPtr = 128;
  const bytes = encodeUtf8(JSON.stringify(payload));
  writeBytes(memory, payloadPtr, bytes);

  const id = microkernel.imports.kernel_request(KERNEL_OP_RUNTIME_EVENT, payloadPtr, bytes.length);
  microkernel.imports.kernel_poll(id);
  const result = microkernel.imports.kernel_result(id);
  microkernel.imports.kernel_drop_request(id);

  assert.equal(result, 0);
  assert.equal(messages.length, 1);
  assert.deepEqual(messages[0], payload);
});

test("microkernel decodes binary startup diagnostics runtime events", () => {
  const memory = new WebAssembly.Memory({ initial: 1 });
  const messages = [];
  const microkernel = createMicrokernel({
    memory,
    now: () => 456,
    runtimeBridge: {
      jobId: "job-3",
      emit: (msg) => messages.push(msg)
    }
  });

  const payloadPtr = 256;
  const bytes = encodeStartupDiagV1({
    eventCode: 3,
    throwAfter: 0xdeadbeef,
    nameLenInput: 7
  });
  writeBytes(memory, payloadPtr, bytes);

  const id = microkernel.imports.kernel_request(KERNEL_OP_RUNTIME_EVENT, payloadPtr, bytes.length);
  microkernel.imports.kernel_poll(id);
  const result = microkernel.imports.kernel_result(id);
  microkernel.imports.kernel_drop_request(id);

  assert.equal(result, 0);
  assert.equal(messages.length, 1);
  assert.equal(messages[0].kind, "wasm.startup.diag.v1");
  assert.equal(messages[0].jobId, "job-3");
  assert.equal(messages[0].ts, 456);
  assert.equal(messages[0].payload.magic, WASM_STARTUP_DIAG_MAGIC_V1);
  assert.equal(messages[0].payload.eventCode, 3);
  assert.equal(messages[0].payload.eventName, "intern.call.throw");
  assert.equal(messages[0].payload.throwAfter, 0xdeadbeef >>> 0);
  assert.equal(messages[0].payload.nameLenInput, 7);
});

test("microkernel decodes binary startup diagnostics runtime events v2", () => {
  const memory = new WebAssembly.Memory({ initial: 1 });
  const messages = [];
  const microkernel = createMicrokernel({
    memory,
    now: () => 789,
    runtimeBridge: {
      jobId: "job-4",
      emit: (msg) => messages.push(msg)
    }
  });

  const payloadPtr = 320;
  const bytes = encodeStartupDiagV2({
    eventCode: 4,
    abortReasonCode: 3,
    firstFailNameLen: 4,
    firstFailNameHash: 0x10203040,
    firstFailNamePrefix: 0x44414f4c,
    pendingConditionSnapshotBeforeClear: 0xbeefcafe
  });
  writeBytes(memory, payloadPtr, bytes);

  const id = microkernel.imports.kernel_request(KERNEL_OP_RUNTIME_EVENT, payloadPtr, bytes.length);
  microkernel.imports.kernel_poll(id);
  const result = microkernel.imports.kernel_result(id);
  microkernel.imports.kernel_drop_request(id);

  assert.equal(result, 0);
  assert.equal(messages.length, 1);
  assert.equal(messages[0].kind, "wasm.startup.diag.v2");
  assert.equal(messages[0].jobId, "job-4");
  assert.equal(messages[0].ts, 789);
  assert.equal(messages[0].payload.magic, WASM_STARTUP_DIAG_MAGIC_V2);
  assert.equal(messages[0].payload.version, 2);
  assert.equal(messages[0].payload.eventCode, 4);
  assert.equal(messages[0].payload.eventName, "intern.result.bad_tag");
  assert.equal(messages[0].payload.abortReasonCode, 3);
  assert.equal(messages[0].payload.abortReasonName, "intern.result.bad_tag");
  assert.equal(messages[0].payload.pendingConditionSnapshotBeforeClear, 0xbeefcafe >>> 0);
  assert.equal(messages[0].payload.firstFailNameLen, 4);
  assert.equal(messages[0].payload.firstFailNameHash, 0x10203040 >>> 0);
  assert.equal(messages[0].payload.firstFailNamePrefix, 0x44414f4c >>> 0);
  assert.equal(messages[0].payload.abortOnFirstFailure, 1);
  assert.equal(messages[0].payload.nameBytesMatchInput, 1);
});

test("microkernel decodes binary fasload trace runtime events v1", () => {
  const memory = new WebAssembly.Memory({ initial: 1 });
  const messages = [];
  const microkernel = createMicrokernel({
    memory,
    now: () => 901,
    runtimeBridge: {
      jobId: "job-fasload-v1",
      emit: (msg) => messages.push(msg)
    }
  });

  const payloadPtr = 384;
  const bytes = encodeFasloadTraceV1({
    stepCode: 16,
    rc: 0,
    line: 4902
  });
  writeBytes(memory, payloadPtr, bytes);

  const id = microkernel.imports.kernel_request(KERNEL_OP_RUNTIME_EVENT, payloadPtr, bytes.length);
  microkernel.imports.kernel_poll(id);
  const result = microkernel.imports.kernel_result(id);
  microkernel.imports.kernel_drop_request(id);

  assert.equal(result, 0);
  assert.equal(messages.length, 1);
  assert.equal(messages[0].kind, "wasm.fasload.trace.v1");
  assert.equal(messages[0].jobId, "job-fasload-v1");
  assert.equal(messages[0].ts, 901);
  assert.equal(messages[0].payload.magic, WASM_FASLOAD_TRACE_MAGIC_V1);
  assert.equal(messages[0].payload.version, 1);
  assert.equal(messages[0].payload.stepCode, 16);
  assert.equal(messages[0].payload.stepName, "call.post");
  assert.equal(messages[0].payload.line, 4902);
  assert.equal(messages[0].payload.throwState, 4);
});

test("microkernel decodes binary fasload trace runtime events v2", () => {
  const memory = new WebAssembly.Memory({ initial: 1 });
  const messages = [];
  const microkernel = createMicrokernel({
    memory,
    now: () => 902,
    runtimeBridge: {
      jobId: "job-fasload-v2",
      emit: (msg) => messages.push(msg)
    }
  });

  const payloadPtr = 448;
  const bytes = encodeFasloadTraceV2({
    stepCode: 17,
    rc: -7,
    line: 4912
  });
  writeBytes(memory, payloadPtr, bytes);

  const id = microkernel.imports.kernel_request(KERNEL_OP_RUNTIME_EVENT, payloadPtr, bytes.length);
  microkernel.imports.kernel_poll(id);
  const result = microkernel.imports.kernel_result(id);
  microkernel.imports.kernel_drop_request(id);

  assert.equal(result, 0);
  assert.equal(messages.length, 1);
  assert.equal(messages[0].kind, "wasm.fasload.trace.v2");
  assert.equal(messages[0].jobId, "job-fasload-v2");
  assert.equal(messages[0].ts, 902);
  assert.equal(messages[0].payload.magic, WASM_FASLOAD_TRACE_MAGIC_V2);
  assert.equal(messages[0].payload.version, 2);
  assert.equal(messages[0].payload.stepCode, 17);
  assert.equal(messages[0].payload.stepName, "throw.detected");
  assert.equal(messages[0].payload.rc, -7);
  assert.equal(messages[0].payload.argZ, 0x4000001);
  assert.equal(messages[0].payload.argY, 0x34);
  assert.equal(messages[0].payload.nfn, 0x4000001);
  assert.equal(messages[0].payload.nargs, 0x2);
  assert.equal(messages[0].payload.vsp, 0x100100);
  assert.equal(messages[0].payload.csp, 0x200200);
  assert.equal(messages[0].payload.tsp, 0x300300);
});

test("microkernel decodes binary toplfunc write runtime events v1", () => {
  const memory = new WebAssembly.Memory({ initial: 1 });
  const messages = [];
  const microkernel = createMicrokernel({
    memory,
    now: () => 903,
    runtimeBridge: {
      jobId: "job-toplfunc-v1",
      emit: (msg) => messages.push(msg)
    }
  });

  const payloadPtr = 512;
  const bytes = encodeToplfuncTraceV1({
    writerCode: 4,
    phaseCode: 1,
    targetCode: 1,
    line: 3492,
    rawValue: 0x0a0b0c0d,
    entryIndex: 4488,
    pendingThrow: 1
  });
  writeBytes(memory, payloadPtr, bytes);

  const id = microkernel.imports.kernel_request(KERNEL_OP_RUNTIME_EVENT, payloadPtr, bytes.length);
  microkernel.imports.kernel_poll(id);
  const result = microkernel.imports.kernel_result(id);
  microkernel.imports.kernel_drop_request(id);

  assert.equal(result, 0);
  assert.equal(messages.length, 1);
  assert.equal(messages[0].kind, "wasm.toplfunc.write.v1");
  assert.equal(messages[0].jobId, "job-toplfunc-v1");
  assert.equal(messages[0].ts, 903);
  assert.equal(messages[0].payload.magic, WASM_TOPLFUNC_TRACE_MAGIC_V1);
  assert.equal(messages[0].payload.version, 1);
  assert.equal(messages[0].payload.writerCode, 4);
  assert.equal(messages[0].payload.writerName, "wasm_run_toplevel");
  assert.equal(messages[0].payload.phaseCode, 1);
  assert.equal(messages[0].payload.phaseName, "write");
  assert.equal(messages[0].payload.targetCode, 1);
  assert.equal(messages[0].payload.targetName, "tcr_slot");
  assert.equal(messages[0].payload.line, 3492);
  assert.equal(messages[0].payload.entryIndex, 4488);
  assert.equal(messages[0].payload.pendingThrow, 1);
});

test("microkernel emits runtime.output over sab_ring_v1 event transport", () => {
  const memory = new WebAssembly.Memory({ initial: 1 });
  const egressRing = createSabRing({ capacity: 8192 });
  let fallbackEmitCount = 0;
  const microkernel = createMicrokernel({
    memory,
    runtimeBridge: {
      jobId: "job-sab",
      emit: () => {
        fallbackEmitCount += 1;
      },
      eventTransport: {
        transport: SAB_RING_TRANSPORT,
        sharedBuffer: egressRing.sharedBuffer
      }
    }
  });

  const payloadPtr = 0;
  const bytes = encodeUtf8("sab out\n");
  const dataPtr = 64;
  writeBytes(memory, dataPtr, bytes);
  const dv = new DataView(memory.buffer, payloadPtr, 16);
  dv.setUint32(0, 1, true);
  dv.setUint32(4, 0, true);
  dv.setUint32(8, dataPtr, true);
  dv.setUint32(12, bytes.length, true);

  const id = microkernel.imports.kernel_request(KERNEL_OP_STREAM_WRITE, payloadPtr, 16);
  microkernel.imports.kernel_poll(id);
  microkernel.imports.kernel_drop_request(id);
  assert.equal(fallbackEmitCount, 0, "emit callback fallback not used");

  const drained = drainRuntimeSabMessages({ transport: SAB_RING_TRANSPORT, ring: egressRing });
  assert.equal(drained.errors.length, 0);
  assert.equal(drained.count, 1);
  assert.equal(drained.messages[0].kind, "runtime.output");
  assert.equal(drained.messages[0].payload.entry.text, "sab out\n");
});

test("microkernel routes KERNEL_OP_RUNTIME_EVENT payloads to sab_ring_v1 event transport", () => {
  const memory = new WebAssembly.Memory({ initial: 1 });
  const egressRing = createSabRing({ capacity: 8192 });
  let fallbackEmitCount = 0;
  const microkernel = createMicrokernel({
    memory,
    runtimeBridge: {
      emit: () => {
        fallbackEmitCount += 1;
      },
      eventTransport: {
        transport: SAB_RING_TRANSPORT,
        sharedBuffer: egressRing.sharedBuffer
      }
    }
  });

  const payload = {
    version: 1,
    kind: "command.result",
    jobId: "job-sab",
    streamId: "commands",
    requestId: "req-1",
    seq: 1,
    ts: 10,
    payload: { invocationId: "inv-1", commandId: "runtime.eval.form", result: { ok: true } },
    error: null
  };
  const payloadPtr = 128;
  const bytes = encodeUtf8(JSON.stringify(payload));
  writeBytes(memory, payloadPtr, bytes);

  const id = microkernel.imports.kernel_request(KERNEL_OP_RUNTIME_EVENT, payloadPtr, bytes.length);
  microkernel.imports.kernel_poll(id);
  const result = microkernel.imports.kernel_result(id);
  microkernel.imports.kernel_drop_request(id);

  assert.equal(result, 0);
  assert.equal(fallbackEmitCount, 0, "emit callback fallback not used");
  const drained = drainRuntimeSabMessages({ transport: SAB_RING_TRANSPORT, ring: egressRing });
  assert.equal(drained.count, 1);
  assert.equal(drained.messages[0].kind, "command.result");
  assert.equal(drained.messages[0].requestId, "req-1");
});
