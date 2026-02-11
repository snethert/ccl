/*
 * Reference JS microkernel implementation for the kernel_request ABI (MVP).
 *
 * This is intentionally small and "boring": it provides a request table and a
 * copy-based response mechanism suitable for bring-up and for environments
 * without SharedArrayBuffer/Atomics.
 */

import { createMemorySnapshotPersistenceStore, createPersistenceService } from "./persist-service.mjs";
import { attachSabRing, SAB_RING_TRANSPORT } from "./sab-ring.mjs";

export const KERNEL_ABI_VERSION = 1;

export const KERNEL_STATUS_PENDING = 0;
export const KERNEL_STATUS_DONE = 1;
export const KERNEL_STATUS_ERROR = 2;

export const KERNEL_OP_CAPS = 0x00000000;
export const KERNEL_OP_LOG = 0x00000001;
export const KERNEL_OP_STREAM_WRITE = 0x00000002;
export const KERNEL_OP_STREAM_READ = 0x00000003;
export const KERNEL_OP_TIME_NOW = 0x00000004;
export const KERNEL_OP_STREAM_OPEN = 0x00000005;
export const KERNEL_OP_STREAM_CLOSE = 0x00000006;
export const KERNEL_OP_COMPILED_MODULES_REFRESH = 0x00000007;
export const KERNEL_OP_FS_PROBE = 0x00000008;
export const KERNEL_OP_FS_TRUENAME = 0x00000009;
export const KERNEL_OP_FS_DIRECTORY = 0x0000000a;
export const KERNEL_OP_FS_FILE_WRITE_DATE = 0x0000000b;
export const KERNEL_OP_FS_RENAME = 0x0000000c;
export const KERNEL_OP_FS_DELETE = 0x0000000d;
export const KERNEL_OP_FS_ENSURE_DIRS = 0x0000000e;
export const KERNEL_OP_FS_DELETE_EMPTY_DIR = 0x0000000f;
export const KERNEL_OP_FS_DELETE_TREE = 0x00000010;
export const KERNEL_OP_STREAM_SEEK = 0x00000011;
export const KERNEL_OP_STREAM_TRUNCATE = 0x00000012;
export const KERNEL_OP_UI_POLL = 0x00000020;
export const KERNEL_OP_UI_RENDER = 0x00000021;
export const KERNEL_OP_UI_MEASURE_TEXT = 0x00000022;
export const KERNEL_OP_RUNTIME_EVENT = 0x00000023;
export const KERNEL_OP_RUNTIME_COMMAND_POLL = 0x00000024;

export const KERNEL_STREAM_KIND_PIPE = 0x00000000;
export const KERNEL_STREAM_KIND_NAMED_RO = 0x00000001;
export const KERNEL_STREAM_KIND_FILE = 0x00000002;

// Minimal errno set. The kernel and microkernel must agree on numeric values.
// For wasm32-wasi bring-up builds, use wasi-libc/WASI errno numbers.
export const ERRNO = Object.freeze({
  // Values from wasi-libc (wasi/api.h):
  // __WASI_ERRNO_2BIG=1, __WASI_ERRNO_ACCES=2, __WASI_ERRNO_AGAIN=6,
  // __WASI_ERRNO_BADF=8, __WASI_ERRNO_INVAL=28, __WASI_ERRNO_ISDIR=31,
  // __WASI_ERRNO_NOENT=44, __WASI_ERRNO_NOTEMPTY=55, __WASI_ERRNO_NOSYS=52,
  // __WASI_ERRNO_XDEV=75.
  E2BIG: 1,
  EACCES: 2,
  EWOULDBLOCK: 6, // EAGAIN
  EBADF: 8,
  EINVAL: 28,
  EISDIR: 31,
  ENOENT: 44,
  ENOTEMPTY: 55,
  ENOSYS: 52,
  EXDEV: 75,
});

function u32(x) {
  return x >>> 0;
}

function i32(x) {
  return x | 0;
}

function inBounds(memory, ptr, len) {
  const p = u32(ptr);
  const n = u32(len);
  const size = memory?.buffer?.byteLength ?? 0;
  return p <= size && n <= size - p;
}

function defaultStdoutWriter(bytes) {
  try {
    if (typeof process !== "undefined" && process?.stdout?.write && typeof Buffer !== "undefined") {
      process.stdout.write(Buffer.from(bytes));
      return;
    }
  } catch (_e) {
    // fall through
  }
  // Best-effort fallback: show something readable.
  const decoder = typeof TextDecoder !== "undefined" ? new TextDecoder("utf-8") : null;
  const text = decoder ? decoder.decode(bytes) : `[${bytes.length} bytes]`;
  // eslint-disable-next-line no-console
  console.log(text);
}

function defaultStderrWriter(bytes) {
  try {
    if (typeof process !== "undefined" && process?.stderr?.write && typeof Buffer !== "undefined") {
      process.stderr.write(Buffer.from(bytes));
      return;
    }
  } catch (_e) {
    // fall through
  }
  const decoder = typeof TextDecoder !== "undefined" ? new TextDecoder("utf-8") : null;
  const text = decoder ? decoder.decode(bytes) : `[${bytes.length} bytes]`;
  // eslint-disable-next-line no-console
  console.error(text);
}

function encodeCapsResponse({ capabilityBits = 0, maxResponseBytes = 0 } = {}) {
  const buf = new ArrayBuffer(16);
  const dv = new DataView(buf);
  dv.setUint32(0, KERNEL_ABI_VERSION, true);
  dv.setUint32(4, u32(capabilityBits), true);
  dv.setUint32(8, u32(maxResponseBytes), true);
  dv.setUint32(12, 0, true);
  return new Uint8Array(buf);
}

function encodeU64LE(value) {
  const buf = new ArrayBuffer(8);
  const dv = new DataView(buf);
  const v = typeof value === "bigint" ? value : BigInt(Math.trunc(value));
  if (typeof dv.setBigUint64 === "function") {
    dv.setBigUint64(0, v, true);
  } else {
    // Older runtimes: encode via two u32 lanes.
    const lo = Number(v & 0xffffffffn) >>> 0;
    const hi = Number((v >> 32n) & 0xffffffffn) >>> 0;
    dv.setUint32(0, lo, true);
    dv.setUint32(4, hi, true);
  }
  return new Uint8Array(buf);
}

function encodeMeasureResponse(metrics) {
  const buf = new ArrayBuffer(32);
  const dv = new DataView(buf);
  const width = Number(metrics?.width ?? 0);
  const height = Number(metrics?.height ?? 0);
  const ascent = Number(metrics?.ascent ?? 0);
  const descent = Number(metrics?.descent ?? 0);
  dv.setFloat64(0, Number.isFinite(width) ? width : 0, true);
  dv.setFloat64(8, Number.isFinite(height) ? height : 0, true);
  dv.setFloat64(16, Number.isFinite(ascent) ? ascent : 0, true);
  dv.setFloat64(24, Number.isFinite(descent) ? descent : 0, true);
  return new Uint8Array(buf);
}

const _textEncoder = typeof TextEncoder !== "undefined" ? new TextEncoder() : null;

function encodeUtf8(text) {
  if (_textEncoder) return _textEncoder.encode(String(text));
  const s = String(text);
  const out = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i) & 0xff;
  return out;
}

function writeU64LE(dv, offset, value) {
  const v = typeof value === "bigint" ? value : BigInt(Math.trunc(value));
  if (typeof dv.setBigUint64 === "function") {
    dv.setBigUint64(offset, v, true);
  } else {
    const lo = Number(v & 0xffffffffn) >>> 0;
    const hi = Number((v >> 32n) & 0xffffffffn) >>> 0;
    dv.setUint32(offset, lo, true);
    dv.setUint32(offset + 4, hi, true);
  }
}

function encodeTimeNowResponse(nowMs) {
  return encodeU64LE(nowMs);
}

function readU32LE(memory, ptr) {
  const dv = new DataView(memory.buffer);
  return dv.getUint32(u32(ptr), true);
}

function readU64LE(memory, ptr) {
  const lo = readU32LE(memory, ptr);
  const hi = readU32LE(memory, u32(ptr) + 4);
  return (BigInt(hi) << 32n) | BigInt(lo);
}

function readI64LE(memory, ptr) {
  return BigInt.asIntN(64, readU64LE(memory, ptr));
}

const MAX_SAFE_BIGINT = BigInt(Number.MAX_SAFE_INTEGER);

function toSafeNumber(value) {
  if (typeof value === "bigint") {
    if (value > MAX_SAFE_BIGINT || value < -MAX_SAFE_BIGINT) return null;
    return Number(value);
  }
  if (!Number.isFinite(value)) return null;
  if (Math.abs(value) > Number.MAX_SAFE_INTEGER) return null;
  return Math.trunc(value);
}

function sliceBytes(memory, ptr, len) {
  return new Uint8Array(memory.buffer, u32(ptr), u32(len));
}

function copyInto(memory, dstPtr, srcBytes) {
  const dst = new Uint8Array(memory.buffer, u32(dstPtr), srcBytes.length);
  dst.set(srcBytes);
}

function normalizeBytes(bytes) {
  if (bytes instanceof Uint8Array) return bytes;
  if (bytes instanceof ArrayBuffer) return new Uint8Array(bytes);
  if (ArrayBuffer.isView(bytes)) return new Uint8Array(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  throw new TypeError("expected Uint8Array/ArrayBuffer/view");
}

function takeFromQueue(queue, maxBytes) {
  const want = u32(maxBytes);
  if (want === 0) return new Uint8Array(0);

  let available = 0;
  for (const c of queue) {
    available += c.bytes.length - c.off;
    if (available >= want) break;
  }
  if (available === 0) return null;

  const n = Math.min(want, available);
  const out = new Uint8Array(n);
  let outOff = 0;

  while (outOff < n && queue.length) {
    const head = queue[0];
    const remain = head.bytes.length - head.off;
    const take = Math.min(remain, n - outOff);
    out.set(head.bytes.subarray(head.off, head.off + take), outOff);
    head.off += take;
    outOff += take;
    if (head.off >= head.bytes.length) {
      queue.shift();
    }
  }

  return out;
}

export function createMicrokernel({
  memory,
  writeStdout = defaultStdoutWriter,
  writeStderr = defaultStderrWriter,
  // If true, some requests may remain PENDING until host data arrives.
  // This is a Stage-2 (async) feature; leave false for Stage-1 sync bring-up.
  asyncStdin = false,
  // Optional initial named byte sources (Map, array of [name, bytes], or object).
  namedBytes = null,
  // Optional hooks for tests/embedding:
  logSink = null, // (level, text, bytes) => void
  traceRequests = null, // (event) => void
  now = () => Date.now(),
  compiledModulesInstaller = null, // ({ registry, nil, memory, microkernel }) => installed count
  compiledModulesAsync = false,
  persistence = null,
  uiService = null, // { pollEvents, renderTree, measureText, setWake? }
  runtimeBridge = null, // { emit, jobId?, streamIds?, strict?, commandTransport?, eventTransport? }
} = {}) {
  if (!memory) throw new Error("createMicrokernel: memory is required");

  const requests = new Map(); // id -> { status, result, response: Uint8Array }
  const requestOps = new Map(); // id -> opcode
  const pendingStdinReads = []; // request ids waiting on stdin
  let nextRequestId = 1;
  const supportsPending = asyncStdin || compiledModulesAsync || Boolean(uiService?.supportsPending);
  let api = null;
  const requestTracer = typeof traceRequests === "function" ? traceRequests : null;

  function normalizePersistenceConfig(raw) {
    const cfg = raw === true ? {} : raw;
    if (!cfg) return null;
    if (typeof cfg !== "object") return {};
    const backend = typeof cfg.backend === "string" ? cfg.backend : "";
    if (!backend || backend === "memory" || backend === "in-memory") return cfg;
    if (backend === "memory-snapshot") {
      const {
        backend: _backend,
        snapshotFile = null,
        fsModule = null,
        autoFlushOnExit = true,
        resetOnCorrupt = false,
        ...rest
      } = cfg;
      const overlay = createMemorySnapshotPersistenceStore({
        snapshotFile,
        fsModule,
        chunkSize: typeof rest.chunkSize === "number" ? rest.chunkSize : undefined,
        now,
        autoFlushOnExit: autoFlushOnExit !== false,
        resetOnCorrupt: resetOnCorrupt === true,
      });
      return { ...rest, overlay };
    }
    throw new Error(`createMicrokernel: unsupported persistence backend '${backend}'`);
  }

  const persistenceConfig = normalizePersistenceConfig(persistence);
  const persistenceService = persistenceConfig
    ? createPersistenceService({ ...persistenceConfig, errno: ERRNO, now })
    : null;

  const logs = [];
  const decoder = typeof TextDecoder !== "undefined" ? new TextDecoder("utf-8") : null;
  const pendingUiPolls = [];
  const pendingRuntimeCommandPolls = [];
  const runtimeEmit = typeof runtimeBridge?.emit === "function" ? runtimeBridge.emit : null;
  const runtimeJobId = runtimeBridge?.jobId ?? null;
  const runtimeStreamIds = typeof runtimeBridge?.streamIds === "object" && runtimeBridge?.streamIds
    ? runtimeBridge.streamIds
    : { stdout: "stdout", stderr: "stderr" };
  const runtimeSeqByStream = new Map();
  let runtimeRecordingSeq = 1;
  let runtimeEntrySeq = 1;
  const runtimeCommandDebug = { transport: "disabled", fallbackAllowed: false };
  const runtimeEventDebug = { transport: "emit_callback_v1", fallbackAllowed: true, dropped: 0 };

  function resolveSabReaderTransport(rawTransport, label) {
    if (!rawTransport) return null;
    const transportId = typeof rawTransport.transport === "string" ? rawTransport.transport : null;
    if (transportId !== SAB_RING_TRANSPORT) {
      throw new Error(`createMicrokernel: unsupported ${label} '${String(transportId)}'`);
    }
    if (
      typeof rawTransport.peekFrameLength === "function" &&
      typeof rawTransport.dequeueFrame === "function"
    ) {
      return {
        transport: SAB_RING_TRANSPORT,
        reader: rawTransport
      };
    }
    if (
      rawTransport.reader &&
      typeof rawTransport.reader.peekFrameLength === "function" &&
      typeof rawTransport.reader.dequeueFrame === "function"
    ) {
      return {
        transport: SAB_RING_TRANSPORT,
        reader: rawTransport.reader
      };
    }
    if (
      rawTransport.ring &&
      typeof rawTransport.ring.peekFrameLength === "function" &&
      typeof rawTransport.ring.dequeueFrame === "function"
    ) {
      return {
        transport: SAB_RING_TRANSPORT,
        reader: rawTransport.ring
      };
    }
    if (typeof SharedArrayBuffer !== "undefined" && rawTransport.sharedBuffer instanceof SharedArrayBuffer) {
      return {
        transport: SAB_RING_TRANSPORT,
        reader: attachSabRing(rawTransport.sharedBuffer)
      };
    }
    throw new Error(
      `createMicrokernel: ${label} sab_ring_v1 requires sharedBuffer or reader/ring with dequeueFrame + peekFrameLength`
    );
  }

  function resolveSabWriterTransport(rawTransport, label) {
    if (!rawTransport) return null;
    const transportId = typeof rawTransport.transport === "string" ? rawTransport.transport : null;
    if (transportId !== SAB_RING_TRANSPORT) {
      throw new Error(`createMicrokernel: unsupported ${label} '${String(transportId)}'`);
    }
    if (typeof rawTransport.enqueueFrame === "function") {
      return {
        transport: SAB_RING_TRANSPORT,
        writer: rawTransport
      };
    }
    if (rawTransport.writer && typeof rawTransport.writer.enqueueFrame === "function") {
      return {
        transport: SAB_RING_TRANSPORT,
        writer: rawTransport.writer
      };
    }
    if (rawTransport.ring && typeof rawTransport.ring.enqueueFrame === "function") {
      return {
        transport: SAB_RING_TRANSPORT,
        writer: rawTransport.ring
      };
    }
    if (typeof SharedArrayBuffer !== "undefined" && rawTransport.sharedBuffer instanceof SharedArrayBuffer) {
      return {
        transport: SAB_RING_TRANSPORT,
        writer: attachSabRing(rawTransport.sharedBuffer)
      };
    }
    throw new Error(
      `createMicrokernel: ${label} sab_ring_v1 requires sharedBuffer or writer/ring with enqueueFrame`
    );
  }

  const runtimeCommandTransport = resolveSabReaderTransport(
    runtimeBridge?.commandTransport ?? null,
    "runtimeBridge.commandTransport"
  );
  if (runtimeCommandTransport) runtimeCommandDebug.transport = runtimeCommandTransport.transport;
  const runtimeEventTransport = resolveSabWriterTransport(
    runtimeBridge?.eventTransport ?? null,
    "runtimeBridge.eventTransport"
  );
  if (runtimeEventTransport) {
    runtimeEventDebug.transport = runtimeEventTransport.transport;
    runtimeEventDebug.fallbackAllowed = false;
  }

  function peekRuntimeCommandFrame() {
    if (!runtimeCommandTransport) return null;
    const frameBytes = runtimeCommandTransport.reader.peekFrameLength();
    if (!Number.isInteger(frameBytes) || frameBytes < 0) return null;
    return { frameBytes };
  }

  function dequeueRuntimeCommandFrame() {
    if (!runtimeCommandTransport) return null;
    const dequeued = runtimeCommandTransport.reader.dequeueFrame();
    if (!dequeued?.ok) return null;
    return dequeued.frame;
  }

  function decodeUtf8(bytes) {
    if (decoder) return decoder.decode(bytes);
    let out = "";
    for (let i = 0; i < bytes.length; i++) {
      out += String.fromCharCode(bytes[i]);
    }
    return out;
  }

  function nextRuntimeSeq(streamId) {
    const current = runtimeSeqByStream.get(streamId) ?? 0;
    const next = current + 1;
    runtimeSeqByStream.set(streamId, next);
    return next;
  }

  function tryEmitRuntimeMessage(message) {
    if (runtimeEventTransport) {
      const bytes = encodeUtf8(JSON.stringify(message));
      const res = runtimeEventTransport.writer.enqueueFrame(bytes);
      if (res && res.ok === false) {
        runtimeEventDebug.dropped += 1;
        return {
          ok: false,
          errno: ERRNO.EWOULDBLOCK,
          reason: res.reason ?? "runtime event sab enqueue failed"
        };
      }
      return { ok: true };
    }
    if (!runtimeEmit) {
      return { ok: false, errno: ERRNO.ENOSYS, reason: "runtime emit unavailable" };
    }
    try {
      runtimeEmit(message);
      return { ok: true };
    } catch (_err) {
      return { ok: false, errno: ERRNO.EINVAL, reason: "runtime emit failed" };
    }
  }

  function emitRuntimeOutput(streamId, bytes) {
    const text = decodeUtf8(bytes);
    if (!text) return;
    const ts = now();
    const seq = nextRuntimeSeq(streamId);
    const recordingId = `rec-${runtimeRecordingSeq++}`;
    const entryId = `ent-${runtimeEntrySeq++}`;
    const message = {
      version: 1,
      kind: "runtime.output",
      jobId: runtimeJobId,
      streamId,
      requestId: null,
      seq,
      ts,
      payload: {
        recording: { id: recordingId, jobId: runtimeJobId, streamId },
        entry: {
          id: entryId,
          recordingId,
          kind: "text",
          streamId,
          seq,
          ts,
          text
        }
      },
      error: null
    };
    const emitted = tryEmitRuntimeMessage(message);
    if (!emitted.ok) {
      // Best effort only for stream write side effects.
    }
  }

  // Per-runner stream table (SID -> endpoint).
  //
  // Standard streams:
  //   0 stdin (readable)
  //   1 stdout (writable)
  //   2 stderr (writable)
  //
  // SIDs >= 3 are allocated via KERNEL_OP_STREAM_OPEN.
  const streams = new Map();
  let nextSid = 3;

  const namedBlobs = new Map();

  function registerNamedBlob(name, bytes) {
    if (name == null || name === "") {
      throw new Error("registerNamedBlob: name is required");
    }
    namedBlobs.set(String(name), normalizeBytes(bytes));
  }

  function registerNamedBlobs(entries) {
    if (!entries) return;
    if (entries instanceof Map) {
      for (const [name, bytes] of entries.entries()) {
        registerNamedBlob(name, bytes);
      }
      return;
    }
    if (Array.isArray(entries)) {
      for (const [name, bytes] of entries) {
        registerNamedBlob(name, bytes);
      }
      return;
    }
    if (typeof entries === "object") {
      for (const [name, bytes] of Object.entries(entries)) {
        registerNamedBlob(name, bytes);
      }
    }
  }

  // Simple stdin queue for STREAM_READ (sid 0). Empty-but-not-closed returns EWOULDBLOCK (or PENDING in Stage 2).
  const stdinQueue = [];
  let stdinClosed = false;

  function feedStdin(bytes) {
    stdinQueue.push({ bytes: normalizeBytes(bytes), off: 0 });
    drainPendingStdinReads();
  }

  function requestInterrupt(options = {}) {
    const exports =
      options?.exports ??
      options?.kernel?.instance?.exports ??
      options?.kernel?.exports ??
      null;
    const requestFn = exports?.wasm_request_interrupt_tcr;
    if (typeof requestFn !== "function") {
      return false;
    }
    const tcr = options?.tcr ?? (typeof exports?.wasm_get_current_tcr === "function"
      ? exports.wasm_get_current_tcr()
      : null);
    if (!tcr) return false;
    return Boolean(requestFn(tcr));
  }

  function closeStdin() {
    stdinClosed = true;
    drainPendingStdinReads();
  }

  function takeStdin(maxBytes) {
    return takeFromQueue(stdinQueue, maxBytes);
  }

  function createPipeStream() {
    const q = [];
    let closed = false;

    return {
      kind: "pipe",
      readable: true,
      writable: true,
      write(bytes) {
        if (closed) return i32(-ERRNO.EBADF);
        const b = normalizeBytes(bytes);
        if (b.length) q.push({ bytes: b, off: 0 });
        return i32(b.length);
      },
      read(maxBytes) {
        if (maxBytes === 0) return new Uint8Array(0);
        const chunk = takeFromQueue(q, maxBytes);
        if (chunk && chunk.length) return chunk;
        if (closed) return new Uint8Array(0); // EOF
        return null; // empty
      },
      close() {
        closed = true;
      },
    };
  }

  function createNamedReadStream(bytes) {
    const data = normalizeBytes(bytes);
    let off = 0;
    let closed = false;

    return {
      kind: "named-ro",
      readable: true,
      writable: false,
      size: data.length,
      read(maxBytes) {
        if (closed) return new Uint8Array(0);
        const want = u32(maxBytes);
        if (want === 0) return new Uint8Array(0);
        const remain = data.length - off;
        if (remain <= 0) return new Uint8Array(0);
        const take = Math.min(remain, want);
        const chunk = data.subarray(off, off + take);
        off += take;
        return chunk;
      },
      close() {
        closed = true;
      },
    };
  }

  // Install standard streams.
  streams.set(0, { kind: "stdin", readable: true, writable: false });
  streams.set(1, { kind: "stdout", readable: false, writable: true });
  streams.set(2, { kind: "stderr", readable: false, writable: true });

  registerNamedBlobs(namedBytes);

  function readPathPayload(payloadPtr, payloadLen, allowFlags = false) {
    if (u32(payloadLen) !== 16) return { error: ERRNO.EINVAL };
    const flags = readU32LE(memory, u32(payloadPtr) + 0);
    const pathPtr = readU32LE(memory, u32(payloadPtr) + 4);
    const pathLen = readU32LE(memory, u32(payloadPtr) + 8);
    if (!allowFlags && flags !== 0) return { error: ERRNO.EINVAL };
    if (u32(pathLen) !== 0 && !inBounds(memory, pathPtr, pathLen)) return { error: ERRNO.EINVAL };
    return { flags: u32(flags), pathBytes: sliceBytes(memory, pathPtr, pathLen) };
  }

  function readPathPairPayload(payloadPtr, payloadLen) {
    if (u32(payloadLen) !== 24) return { error: ERRNO.EINVAL };
    const flags = readU32LE(memory, u32(payloadPtr) + 0);
    const srcPtr = readU32LE(memory, u32(payloadPtr) + 4);
    const srcLen = readU32LE(memory, u32(payloadPtr) + 8);
    const dstPtr = readU32LE(memory, u32(payloadPtr) + 12);
    const dstLen = readU32LE(memory, u32(payloadPtr) + 16);
    if (flags !== 0) return { error: ERRNO.EINVAL };
    if (u32(srcLen) !== 0 && !inBounds(memory, srcPtr, srcLen)) return { error: ERRNO.EINVAL };
    if (u32(dstLen) !== 0 && !inBounds(memory, dstPtr, dstLen)) return { error: ERRNO.EINVAL };
    return {
      flags: u32(flags),
      srcBytes: sliceBytes(memory, srcPtr, srcLen),
      dstBytes: sliceBytes(memory, dstPtr, dstLen),
    };
  }

  function encodeProbeResponse(info) {
    const buf = new ArrayBuffer(24);
    const dv = new DataView(buf);
    dv.setUint32(0, info.kind === "dir" ? 1 : 0, true);
    dv.setUint32(4, info.readonly ? 1 : 0, true);
    writeU64LE(dv, 8, info.size ?? 0);
    writeU64LE(dv, 16, info.mtimeMs ?? 0);
    return new Uint8Array(buf);
  }

  function encodeDirectoryResponse(entries) {
    let total = 4;
    const encoded = [];
    for (const entry of entries) {
      const pathBytes = encodeUtf8(entry.path);
      encoded.push({ kind: entry.kind, pathBytes });
      total += 8 + pathBytes.length;
    }
    const buf = new ArrayBuffer(total);
    const dv = new DataView(buf);
    dv.setUint32(0, encoded.length, true);
    let off = 4;
    for (const item of encoded) {
      dv.setUint32(off, item.kind === "dir" ? 1 : 0, true);
      dv.setUint32(off + 4, item.pathBytes.length, true);
      new Uint8Array(buf, off + 8, item.pathBytes.length).set(item.pathBytes);
      off += 8 + item.pathBytes.length;
    }
    return new Uint8Array(buf);
  }

  function recordRequestDone(id, result, responseBytes = null) {
    requests.set(id, {
      status: KERNEL_STATUS_DONE,
      result: i32(result),
      response: responseBytes ? normalizeBytes(responseBytes) : new Uint8Array(0),
    });
    if (requestTracer) {
      try {
        requestTracer({
          phase: "done",
          id: u32(id),
          op: requestOps.get(u32(id)) ?? null,
          result: i32(result),
        });
      } catch (_err) {
        // best effort
      }
    }
  }

  function recordRequestPending(id, pending) {
    requests.set(id, {
      status: KERNEL_STATUS_PENDING,
      result: 0,
      response: new Uint8Array(0),
      pending,
    });
    if (requestTracer) {
      try {
        requestTracer({
          phase: "pending",
          id: u32(id),
          op: requestOps.get(u32(id)) ?? null,
          pending,
        });
      } catch (_err) {
        // best effort
      }
    }
  }

  function recordRequestError(id, errno) {
    // "ERROR" is reserved for ABI-level failures; most op failures are DONE with negative errno.
    requests.set(id, {
      status: KERNEL_STATUS_ERROR,
      result: i32(-Math.abs(errno | 0)),
      response: new Uint8Array(0),
    });
    if (requestTracer) {
      try {
        requestTracer({
          phase: "error",
          id: u32(id),
          op: requestOps.get(u32(id)) ?? null,
          errno: i32(Math.abs(errno | 0)),
        });
      } catch (_err) {
        // best effort
      }
    }
  }

  function drainPendingStdinReads() {
    for (;;) {
      if (pendingStdinReads.length === 0) return;

      const id = pendingStdinReads[0];
      const req = requests.get(id);
      if (!req) {
        pendingStdinReads.shift();
        continue;
      }
      if (req.status !== KERNEL_STATUS_PENDING || req.pending?.kind !== "stdin_read") {
        pendingStdinReads.shift();
        continue;
      }

      const maxBytes = u32(req.pending.maxBytes);
      if (maxBytes === 0) {
        pendingStdinReads.shift();
        recordRequestDone(id, 0);
        continue;
      }

      const chunk = takeStdin(maxBytes);
      if (chunk && chunk.length) {
        pendingStdinReads.shift();
        recordRequestDone(id, chunk.length, chunk);
        continue;
      }
      if (stdinClosed) {
        pendingStdinReads.shift();
        recordRequestDone(id, 0);
        continue;
      }
      return;
    }
  }

  function drainPendingUiPolls() {
    if (!uiService || typeof uiService.pollEvents !== "function") return;
    for (;;) {
      if (pendingUiPolls.length === 0) return;
      const id = pendingUiPolls[0];
      const req = requests.get(id);
      if (!req || req.status !== KERNEL_STATUS_PENDING || req.pending?.kind !== "ui_poll") {
        pendingUiPolls.shift();
        continue;
      }
      const res = uiService.pollEvents({
        maxEvents: req.pending.maxEvents,
        maxBytes: req.pending.maxBytes,
        allowPending: false,
      });
      if (res?.pending) {
        return;
      }
      const payload = res?.payload ? normalizeBytes(res.payload) : new Uint8Array(0);
      const count = Number.isInteger(res?.count) ? res.count : 0;
      recordRequestDone(id, count, payload);
      pendingUiPolls.shift();
    }
  }

  function drainPendingRuntimeCommandPolls() {
    for (;;) {
      if (pendingRuntimeCommandPolls.length === 0) return;
      const id = pendingRuntimeCommandPolls[0];
      const req = requests.get(id);
      if (!req || req.status !== KERNEL_STATUS_PENDING || req.pending?.kind !== "runtime_command_poll") {
        pendingRuntimeCommandPolls.shift();
        continue;
      }
      const maxBytes = u32(req.pending.maxBytes);
      const next = peekRuntimeCommandFrame();
      if (!next) {
        return;
      }
      if (next.frameBytes > maxBytes) {
        recordRequestDone(id, -ERRNO.E2BIG);
        pendingRuntimeCommandPolls.shift();
        continue;
      }
      const frame = dequeueRuntimeCommandFrame();
      if (!frame) return;
      recordRequestDone(id, 1, frame);
      pendingRuntimeCommandPolls.shift();
    }
  }

  function kernel_request(opcode, payloadPtr, payloadLen) {
    const id = nextRequestId++;
    const op = u32(opcode);
    requestOps.set(id, op);
    if (requestTracer) {
      try {
        requestTracer({
          phase: "request",
          id: u32(id),
          op,
          payloadLen: u32(payloadLen),
        });
      } catch (_err) {
        // best effort
      }
    }

    // Validate payload pointer range early and turn it into a request failure (no throw).
    if (!inBounds(memory, payloadPtr, payloadLen)) {
      recordRequestError(id, ERRNO.EINVAL);
      return u32(id);
    }

    try {
      switch (op) {
      case KERNEL_OP_CAPS: {
        if (u32(payloadLen) !== 0) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        const capabilityBits = supportsPending ? 0x1 : 0; // bit0: requests may return PENDING
        const caps = encodeCapsResponse({ capabilityBits, maxResponseBytes: 0 });
        recordRequestDone(id, 0, caps);
        break;
      }

      case KERNEL_OP_LOG: {
        if (u32(payloadLen) < 8) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        const level = readU32LE(memory, u32(payloadPtr) + 0);
        const flags = readU32LE(memory, u32(payloadPtr) + 4);
        if (flags !== 0) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        const msgBytes = sliceBytes(memory, u32(payloadPtr) + 8, u32(payloadLen) - 8);
        const text = decoder ? decoder.decode(msgBytes) : null;
        const entry = { level: u32(level), text, bytes: new Uint8Array(msgBytes) };
        logs.push(entry);
        if (logSink) {
          logSink(entry.level, entry.text, entry.bytes);
        } else {
          // eslint-disable-next-line no-console
          (entry.level >= 3 ? console.error : console.log)(entry.text ?? `[${entry.bytes.length} bytes]`);
        }
        recordRequestDone(id, 0);
        break;
      }

      case KERNEL_OP_RUNTIME_EVENT: {
        if (u32(payloadLen) === 0) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        if (!runtimeEventTransport && !runtimeEmit) {
          recordRequestDone(id, -ERRNO.ENOSYS);
          break;
        }
        const bytes = sliceBytes(memory, u32(payloadPtr), u32(payloadLen));
        const text = decodeUtf8(bytes);
        let message = null;
        try {
          message = JSON.parse(text);
        } catch (_err) {
          recordRequestDone(id, -ERRNO.EINVAL);
          break;
        }
        const emitted = tryEmitRuntimeMessage(message);
        recordRequestDone(id, emitted.ok ? 0 : -Math.abs(emitted.errno | 0));
        break;
      }

      case KERNEL_OP_RUNTIME_COMMAND_POLL: {
        if (u32(payloadLen) !== 8) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        const maxBytes = readU32LE(memory, u32(payloadPtr) + 0);
        const flags = readU32LE(memory, u32(payloadPtr) + 4);
        if (maxBytes === 0) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        if (!runtimeCommandTransport) {
          recordRequestDone(id, -ERRNO.ENOSYS);
          break;
        }
        const next = peekRuntimeCommandFrame();
        if (!next) {
          const allowPending = (flags & 0x1) !== 0;
          if (allowPending && supportsPending) {
            recordRequestPending(id, { kind: "runtime_command_poll", maxBytes });
            pendingRuntimeCommandPolls.push(id);
          } else {
            recordRequestDone(id, 0);
          }
          break;
        }
        if (next.frameBytes > maxBytes) {
          recordRequestDone(id, -ERRNO.E2BIG);
          break;
        }
        const frame = dequeueRuntimeCommandFrame();
        if (!frame) {
          const allowPending = (flags & 0x1) !== 0;
          if (allowPending && supportsPending) {
            recordRequestPending(id, { kind: "runtime_command_poll", maxBytes });
            pendingRuntimeCommandPolls.push(id);
          } else {
            recordRequestDone(id, 0);
          }
          break;
        }
        recordRequestDone(id, 1, frame);
        break;
      }

      case KERNEL_OP_STREAM_WRITE: {
        if (u32(payloadLen) !== 16) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        const sid = readU32LE(memory, u32(payloadPtr) + 0);
        const flags = readU32LE(memory, u32(payloadPtr) + 4);
        if (flags !== 0) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        const dataPtr = readU32LE(memory, u32(payloadPtr) + 8);
        const dataLen = readU32LE(memory, u32(payloadPtr) + 12);
        if (!inBounds(memory, dataPtr, dataLen)) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        const bytes = sliceBytes(memory, dataPtr, dataLen);
        if (sid === 1) {
          writeStdout(bytes);
          emitRuntimeOutput(runtimeStreamIds.stdout ?? "stdout", bytes);
          recordRequestDone(id, bytes.length);
          break;
        }
        if (sid === 2) {
          writeStderr(bytes);
          emitRuntimeOutput(runtimeStreamIds.stderr ?? "stderr", bytes);
          recordRequestDone(id, bytes.length);
          break;
        }
        const stream = streams.get(u32(sid));
        if (!stream || !stream.writable) {
          recordRequestDone(id, -ERRNO.EBADF);
          break;
        }
        if (typeof stream.write === "function") {
          const wrote = stream.write(bytes);
          if (typeof wrote === "number") {
            recordRequestDone(id, i32(wrote));
          } else {
            recordRequestDone(id, -ERRNO.EINVAL);
          }
          break;
        }
        recordRequestDone(id, -ERRNO.ENOSYS);
        break;
      }

      case KERNEL_OP_STREAM_READ: {
        if (u32(payloadLen) !== 8) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        const sid = readU32LE(memory, u32(payloadPtr) + 0);
        const maxBytes = readU32LE(memory, u32(payloadPtr) + 4);
        if (u32(maxBytes) === 0) {
          recordRequestDone(id, 0);
          break;
        }
        if (sid === 0) {
          const chunk = takeStdin(maxBytes);
          if (chunk && chunk.length) {
            recordRequestDone(id, chunk.length, chunk);
          } else if (stdinClosed) {
            recordRequestDone(id, 0);
          } else if (asyncStdin) {
            recordRequestPending(id, { kind: "stdin_read", maxBytes: u32(maxBytes) });
            pendingStdinReads.push(id);
          } else {
            recordRequestDone(id, -ERRNO.EWOULDBLOCK);
          }
          break;
        }

        const stream = streams.get(u32(sid));
        if (!stream || !stream.readable) {
          recordRequestDone(id, -ERRNO.EBADF);
          break;
        }
        if (typeof stream.read === "function") {
          const chunk = stream.read(u32(maxBytes));
          if (typeof chunk === "number") {
            recordRequestDone(id, i32(chunk));
            break;
          }
          if (chunk && chunk.length) {
            recordRequestDone(id, chunk.length, chunk);
          } else if (chunk) {
            recordRequestDone(id, 0);
          } else {
            recordRequestDone(id, -ERRNO.EWOULDBLOCK);
          }
          break;
        }
        recordRequestDone(id, -ERRNO.ENOSYS);
        break;
      }

      case KERNEL_OP_STREAM_SEEK: {
        if (u32(payloadLen) !== 16) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        const sid = readU32LE(memory, u32(payloadPtr) + 0);
        const whence = readU32LE(memory, u32(payloadPtr) + 4);
        const offset = readI64LE(memory, u32(payloadPtr) + 8);
        if (u32(sid) <= 2) {
          recordRequestDone(id, -ERRNO.EBADF);
          break;
        }
        const stream = streams.get(u32(sid));
        if (!stream || typeof stream.seek !== "function") {
          recordRequestDone(id, -ERRNO.EBADF);
          break;
        }
        const offNum = toSafeNumber(offset);
        if (offNum == null) {
          recordRequestDone(id, -ERRNO.E2BIG);
          break;
        }
        let res;
        try {
          res = stream.seek(u32(whence), offNum);
        } catch (_e) {
          recordRequestDone(id, -ERRNO.EINVAL);
          break;
        }
        if (typeof res === "number") {
          if (res < 0) {
            recordRequestDone(id, i32(res));
            break;
          }
          recordRequestDone(id, 0, encodeU64LE(res));
          break;
        }
        if (typeof res === "bigint") {
          recordRequestDone(id, 0, encodeU64LE(res));
          break;
        }
        recordRequestDone(id, -ERRNO.EINVAL);
        break;
      }

      case KERNEL_OP_STREAM_TRUNCATE: {
        if (u32(payloadLen) !== 16) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        const sid = readU32LE(memory, u32(payloadPtr) + 0);
        const flags = readU32LE(memory, u32(payloadPtr) + 4);
        const length = readU64LE(memory, u32(payloadPtr) + 8);
        if (flags !== 0) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        if (u32(sid) <= 2) {
          recordRequestDone(id, -ERRNO.EBADF);
          break;
        }
        const stream = streams.get(u32(sid));
        if (!stream || typeof stream.truncate !== "function") {
          recordRequestDone(id, -ERRNO.EBADF);
          break;
        }
        if (length < 0n) {
          recordRequestDone(id, -ERRNO.EINVAL);
          break;
        }
        const lenNum = toSafeNumber(length);
        if (lenNum == null || lenNum < 0) {
          recordRequestDone(id, -ERRNO.E2BIG);
          break;
        }
        let res;
        try {
          res = stream.truncate(lenNum);
        } catch (_e) {
          recordRequestDone(id, -ERRNO.EINVAL);
          break;
        }
        if (typeof res === "number" && res < 0) {
          recordRequestDone(id, i32(res));
          break;
        }
        recordRequestDone(id, 0);
        break;
      }

      case KERNEL_OP_TIME_NOW: {
        if (u32(payloadLen) !== 0) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        const t = now();
        recordRequestDone(id, 0, encodeTimeNowResponse(t));
        break;
      }

      case KERNEL_OP_STREAM_OPEN: {
        if (u32(payloadLen) !== 16) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        const kind = readU32LE(memory, u32(payloadPtr) + 0);
        const flags = readU32LE(memory, u32(payloadPtr) + 4);
        const argPtr = readU32LE(memory, u32(payloadPtr) + 8);
        const argLen = readU32LE(memory, u32(payloadPtr) + 12);
        if (flags !== 0) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        if (u32(argLen) !== 0 && !inBounds(memory, argPtr, argLen)) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }

        if (u32(kind) === KERNEL_STREAM_KIND_PIPE) {
          if (u32(argLen) !== 0) {
            recordRequestError(id, ERRNO.EINVAL);
            break;
          }
          const sid = nextSid++;
          streams.set(sid, createPipeStream());
          recordRequestDone(id, sid);
          break;
        }

        if (u32(kind) === KERNEL_STREAM_KIND_NAMED_RO) {
          if (u32(argLen) === 0) {
            recordRequestError(id, ERRNO.EINVAL);
            break;
          }
          const nameBytes = sliceBytes(memory, argPtr, argLen);
          const name = decodeUtf8(nameBytes);
          const blob = namedBlobs.get(name);
          if (!blob) {
            recordRequestDone(id, -ERRNO.ENOENT);
            break;
          }
          const sid = nextSid++;
          streams.set(sid, createNamedReadStream(blob));
          recordRequestDone(id, sid, encodeU64LE(blob.length));
          break;
        }

        if (u32(kind) === KERNEL_STREAM_KIND_FILE) {
          if (!persistenceService) {
            recordRequestDone(id, -ERRNO.ENOSYS);
            break;
          }
          if (u32(argLen) !== 16) {
            recordRequestError(id, ERRNO.EINVAL);
            break;
          }
          const modeFlags = readU32LE(memory, u32(argPtr) + 0);
          const pathPtr = readU32LE(memory, u32(argPtr) + 4);
          const pathLen = readU32LE(memory, u32(argPtr) + 8);
          const reserved = readU32LE(memory, u32(argPtr) + 12);
          if (reserved !== 0) {
            recordRequestError(id, ERRNO.EINVAL);
            break;
          }
          if (u32(pathLen) !== 0 && !inBounds(memory, pathPtr, pathLen)) {
            recordRequestError(id, ERRNO.EINVAL);
            break;
          }
          const res = persistenceService.openFile(sliceBytes(memory, pathPtr, pathLen), u32(modeFlags));
          if (!res.ok) {
            recordRequestDone(id, -res.errno);
            break;
          }
          const sid = nextSid++;
          const handle = res.value;
          streams.set(sid, {
            kind: "file",
            readable: !!handle.readable,
            writable: !!handle.writable,
            read: handle.read,
            write: handle.write,
            seek: handle.seek,
            truncate: handle.truncate,
            close: handle.close,
          });
          recordRequestDone(id, sid);
          break;
        }

        recordRequestDone(id, -ERRNO.ENOSYS);
        break;
      }

      case KERNEL_OP_STREAM_CLOSE: {
        if (u32(payloadLen) !== 8) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        const sid = readU32LE(memory, u32(payloadPtr) + 0);
        const flags = readU32LE(memory, u32(payloadPtr) + 4);
        if (flags !== 0) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        if (u32(sid) <= 2) {
          recordRequestDone(id, 0);
          break;
        }
        const stream = streams.get(u32(sid));
        if (!stream) {
          recordRequestDone(id, -ERRNO.EBADF);
          break;
        }
        try {
          stream.close?.();
        } finally {
          streams.delete(u32(sid));
        }
        recordRequestDone(id, 0);
        break;
      }

      case KERNEL_OP_FS_PROBE: {
        if (!persistenceService) {
          recordRequestDone(id, -ERRNO.ENOSYS);
          break;
        }
        const payload = readPathPayload(payloadPtr, payloadLen);
        if (payload.error) {
          recordRequestError(id, payload.error);
          break;
        }
        const res = persistenceService.probe(payload.pathBytes);
        if (!res.ok) {
          recordRequestDone(id, -res.errno);
          break;
        }
        recordRequestDone(id, 0, encodeProbeResponse(res.value));
        break;
      }

      case KERNEL_OP_FS_TRUENAME: {
        if (!persistenceService) {
          recordRequestDone(id, -ERRNO.ENOSYS);
          break;
        }
        const payload = readPathPayload(payloadPtr, payloadLen);
        if (payload.error) {
          recordRequestError(id, payload.error);
          break;
        }
        const res = persistenceService.truename(payload.pathBytes);
        if (!res.ok) {
          recordRequestDone(id, -res.errno);
          break;
        }
        recordRequestDone(id, 0, encodeUtf8(res.value));
        break;
      }

      case KERNEL_OP_FS_DIRECTORY: {
        if (!persistenceService) {
          recordRequestDone(id, -ERRNO.ENOSYS);
          break;
        }
        const payload = readPathPayload(payloadPtr, payloadLen);
        if (payload.error) {
          recordRequestError(id, payload.error);
          break;
        }
        const res = persistenceService.directory(payload.pathBytes);
        if (!res.ok) {
          recordRequestDone(id, -res.errno);
          break;
        }
        recordRequestDone(id, 0, encodeDirectoryResponse(res.value));
        break;
      }

      case KERNEL_OP_FS_FILE_WRITE_DATE: {
        if (!persistenceService) {
          recordRequestDone(id, -ERRNO.ENOSYS);
          break;
        }
        const payload = readPathPayload(payloadPtr, payloadLen);
        if (payload.error) {
          recordRequestError(id, payload.error);
          break;
        }
        const res = persistenceService.fileWriteDate(payload.pathBytes);
        if (!res.ok) {
          recordRequestDone(id, -res.errno);
          break;
        }
        recordRequestDone(id, 0, encodeU64LE(res.value));
        break;
      }

      case KERNEL_OP_FS_RENAME: {
        if (!persistenceService) {
          recordRequestDone(id, -ERRNO.ENOSYS);
          break;
        }
        const payload = readPathPairPayload(payloadPtr, payloadLen);
        if (payload.error) {
          recordRequestError(id, payload.error);
          break;
        }
        const res = persistenceService.renameFile(payload.srcBytes, payload.dstBytes);
        recordRequestDone(id, res.ok ? 0 : -res.errno);
        break;
      }

      case KERNEL_OP_FS_DELETE: {
        if (!persistenceService) {
          recordRequestDone(id, -ERRNO.ENOSYS);
          break;
        }
        const payload = readPathPayload(payloadPtr, payloadLen);
        if (payload.error) {
          recordRequestError(id, payload.error);
          break;
        }
        const res = persistenceService.deleteFile(payload.pathBytes);
        recordRequestDone(id, res.ok ? 0 : -res.errno);
        break;
      }

      case KERNEL_OP_FS_ENSURE_DIRS: {
        if (!persistenceService) {
          recordRequestDone(id, -ERRNO.ENOSYS);
          break;
        }
        const payload = readPathPayload(payloadPtr, payloadLen);
        if (payload.error) {
          recordRequestError(id, payload.error);
          break;
        }
        const res = persistenceService.ensureDirs(payload.pathBytes);
        recordRequestDone(id, res.ok ? 0 : -res.errno);
        break;
      }

      case KERNEL_OP_FS_DELETE_EMPTY_DIR: {
        if (!persistenceService) {
          recordRequestDone(id, -ERRNO.ENOSYS);
          break;
        }
        const payload = readPathPayload(payloadPtr, payloadLen);
        if (payload.error) {
          recordRequestError(id, payload.error);
          break;
        }
        const res = persistenceService.deleteEmptyDirectory(payload.pathBytes);
        recordRequestDone(id, res.ok ? 0 : -res.errno);
        break;
      }

      case KERNEL_OP_FS_DELETE_TREE: {
        if (!persistenceService) {
          recordRequestDone(id, -ERRNO.ENOSYS);
          break;
        }
        const payload = readPathPayload(payloadPtr, payloadLen, true);
        if (payload.error) {
          recordRequestError(id, payload.error);
          break;
        }
        const validate = (payload.flags & 0x1) !== 0;
        const res = persistenceService.deleteDirectoryTree(payload.pathBytes, validate);
        recordRequestDone(id, res.ok ? 0 : -res.errno);
        break;
      }

      case KERNEL_OP_COMPILED_MODULES_REFRESH: {
        if (u32(payloadLen) !== 8) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        if (typeof compiledModulesInstaller !== "function") {
          recordRequestDone(id, -ERRNO.ENOSYS);
          break;
        }
        const registry = readU32LE(memory, u32(payloadPtr) + 0);
        const nil = readU32LE(memory, u32(payloadPtr) + 4);
        const result = compiledModulesInstaller({ registry, nil, memory, microkernel: api });
        if (result && typeof result.then === "function") {
          if (!compiledModulesAsync) {
            recordRequestDone(id, -ERRNO.EWOULDBLOCK);
            break;
          }
          recordRequestPending(id, { kind: "compiled_modules" });
          result.then((res) => {
            const req = requests.get(id);
            if (!req || req.status !== KERNEL_STATUS_PENDING) return;
            const installed = typeof res === "number" ? res : (res?.installed ?? 0);
            recordRequestDone(id, installed);
          }).catch((_e) => {
            const req = requests.get(id);
            if (!req || req.status !== KERNEL_STATUS_PENDING) return;
            recordRequestDone(id, -ERRNO.EINVAL);
          });
          break;
        }
        {
          const installed = typeof result === "number" ? result : (result?.installed ?? 0);
          recordRequestDone(id, installed);
        }
        break;
      }

      case KERNEL_OP_UI_POLL: {
        if (u32(payloadLen) !== 12) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        if (!uiService || typeof uiService.pollEvents !== "function") {
          recordRequestDone(id, -ERRNO.ENOSYS);
          break;
        }
        const maxEvents = readU32LE(memory, u32(payloadPtr) + 0);
        const maxBytes = readU32LE(memory, u32(payloadPtr) + 4);
        const flags = readU32LE(memory, u32(payloadPtr) + 8);
        const res = uiService.pollEvents({
          maxEvents: u32(maxEvents),
          maxBytes: u32(maxBytes),
          allowPending: (u32(flags) & 0x1) !== 0,
        });
        if (res?.pending) {
          recordRequestPending(id, { kind: "ui_poll", maxEvents: u32(maxEvents), maxBytes: u32(maxBytes) });
          pendingUiPolls.push(id);
          break;
        }
        if (res?.error) {
          recordRequestDone(id, -Math.abs(res.error | 0));
          break;
        }
        const payload = res?.payload ? normalizeBytes(res.payload) : new Uint8Array(0);
        if (u32(maxBytes) !== 0 && payload.length > u32(maxBytes)) {
          recordRequestDone(id, -ERRNO.E2BIG);
          break;
        }
        const count = Number.isInteger(res?.count) ? res.count : 0;
        recordRequestDone(id, count, payload);
        break;
      }

      case KERNEL_OP_UI_RENDER: {
        if (!uiService || typeof uiService.renderTree !== "function") {
          recordRequestDone(id, -ERRNO.ENOSYS);
          break;
        }
        const payload = sliceBytes(memory, u32(payloadPtr), u32(payloadLen));
        const r = uiService.renderTree(normalizeBytes(payload));
        recordRequestDone(id, i32(r ?? 0));
        break;
      }

      case KERNEL_OP_UI_MEASURE_TEXT: {
        if (u32(payloadLen) !== 16) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        if (!uiService || typeof uiService.measureText !== "function") {
          recordRequestDone(id, -ERRNO.ENOSYS);
          break;
        }
        const fontPtr = readU32LE(memory, u32(payloadPtr) + 0);
        const fontLen = readU32LE(memory, u32(payloadPtr) + 4);
        const textPtr = readU32LE(memory, u32(payloadPtr) + 8);
        const textLen = readU32LE(memory, u32(payloadPtr) + 12);
        if (!inBounds(memory, fontPtr, fontLen) || !inBounds(memory, textPtr, textLen)) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        const fontBytes = sliceBytes(memory, u32(fontPtr), u32(fontLen));
        const textBytes = sliceBytes(memory, u32(textPtr), u32(textLen));
        const font = decodeUtf8(fontBytes);
        const text = decodeUtf8(textBytes);
        const metrics = uiService.measureText({ font, text });
        recordRequestDone(id, 0, encodeMeasureResponse(metrics));
        break;
      }

      default:
        recordRequestDone(id, -ERRNO.ENOSYS);
        break;
      }
    } catch (_e) {
      // Catch unexpected implementation errors and surface them as ABI-level errors.
      recordRequestError(id, ERRNO.EINVAL);
    }

    return u32(id);
  }

  function kernel_poll(requestId) {
    const id = u32(requestId);
    const reqBefore = requests.get(id);
    if (reqBefore?.status === KERNEL_STATUS_PENDING && reqBefore.pending?.kind === "runtime_command_poll") {
      drainPendingRuntimeCommandPolls();
    }
    const req = requests.get(id);
    const status = req ? u32(req.status) : KERNEL_STATUS_ERROR;
    if (requestTracer) {
      try {
        requestTracer({
          phase: "poll",
          id,
          op: requestOps.get(id) ?? null,
          status,
        });
      } catch (_err) {
        // best effort
      }
    }
    return status;
  }

  function kernel_result(requestId) {
    const id = u32(requestId);
    const req = requests.get(id);
    const result = req ? i32(req.result) : i32(-ERRNO.EINVAL);
    if (requestTracer) {
      try {
        requestTracer({
          phase: "result",
          id,
          op: requestOps.get(id) ?? null,
          result,
        });
      } catch (_err) {
        // best effort
      }
    }
    return result;
  }

  function kernel_response_size(requestId) {
    const id = u32(requestId);
    const req = requests.get(id);
    const size = req ? u32(req.response.length) : 0;
    if (requestTracer) {
      try {
        requestTracer({
          phase: "response_size",
          id,
          op: requestOps.get(id) ?? null,
          size,
        });
      } catch (_err) {
        // best effort
      }
    }
    return size;
  }

  /*
   * Response ABI note (copy-based, MVP):
   * The microkernel stores each response payload as a JS-owned Uint8Array and
   * returns it to the guest by copying into WASM linear memory via:
   *   kernel_response_size(request_id)
   *   kernel_copy_response(request_id, dst_ptr, dst_len)
   *   kernel_drop_request(request_id)
   *
   * This is the portability/correctness baseline: it avoids buffer lifetime
   * pitfalls and works in environments without SharedArrayBuffer/Atomics.
   *
   * TODO(zero-copy): Add optional zero-copy variants that place response bytes
   * directly in guest memory (e.g. caller-provided output buffers, or a
   * microkernel-managed arena/ring buffer inside env.memory) with explicit
   * lifetime/invalidations. Keep the copy-based ABI as the required fallback.
   */
  function kernel_copy_response(requestId, dstPtr, dstLen) {
    const id = u32(requestId);
    const req = requests.get(id);
    if (!req || !req.response || req.response.length === 0) {
      if (requestTracer) {
        try {
          requestTracer({
            phase: "copy_response",
            id,
            op: requestOps.get(id) ?? null,
            copied: 0,
          });
        } catch (_err) {
          // best effort
        }
      }
      return 0;
    }

    const want = Math.min(u32(dstLen), req.response.length);
    if (want === 0) {
      if (requestTracer) {
        try {
          requestTracer({
            phase: "copy_response",
            id,
            op: requestOps.get(id) ?? null,
            copied: 0,
          });
        } catch (_err) {
          // best effort
        }
      }
      return 0;
    }
    if (!inBounds(memory, dstPtr, want)) {
      if (requestTracer) {
        try {
          requestTracer({
            phase: "copy_response",
            id,
            op: requestOps.get(id) ?? null,
            copied: 0,
          });
        } catch (_err) {
          // best effort
        }
      }
      return 0;
    }

    copyInto(memory, dstPtr, req.response.subarray(0, want));
    const copied = u32(want);
    if (requestTracer) {
      try {
        requestTracer({
          phase: "copy_response",
          id,
          op: requestOps.get(id) ?? null,
          copied,
        });
      } catch (_err) {
        // best effort
      }
    }
    return copied;
  }

  function kernel_drop_request(requestId) {
    // Idempotent drop (required: guest must drop exactly once; host ignores repeats).
    const id = u32(requestId);
    const op = requestOps.get(id) ?? null;
    const req = requests.get(id);
    if (req?.status === KERNEL_STATUS_PENDING && req.pending?.kind === "stdin_read") {
      const idx = pendingStdinReads.indexOf(id);
      if (idx >= 0) {
        pendingStdinReads.splice(idx, 1);
      }
    }
    if (req?.status === KERNEL_STATUS_PENDING && req.pending?.kind === "ui_poll") {
      const idx = pendingUiPolls.indexOf(id);
      if (idx >= 0) {
        pendingUiPolls.splice(idx, 1);
      }
    }
    if (req?.status === KERNEL_STATUS_PENDING && req.pending?.kind === "runtime_command_poll") {
      const idx = pendingRuntimeCommandPolls.indexOf(id);
      if (idx >= 0) {
        pendingRuntimeCommandPolls.splice(idx, 1);
      }
    }
    requests.delete(id);
    requestOps.delete(id);
    if (requestTracer) {
      try {
        requestTracer({
          phase: "drop",
          id,
          op,
        });
      } catch (_err) {
        // best effort
      }
    }
  }

  const imports = {
    kernel_request,
    kernel_poll,
    kernel_result,
    kernel_response_size,
    kernel_copy_response,
    kernel_drop_request,
  };

  api = {
    imports,
    feedStdin,
    requestInterrupt,
    closeStdin,
    registerNamedBlob,
    registerNamedBlobs,
    getLogs: () => logs.slice(),
    persistence: persistenceService,
    _debug: {
      requests,
      pendingStdinReads,
      pendingUiPolls,
      pendingRuntimeCommandPolls,
      runtimeCommand: runtimeCommandDebug,
      runtimeEvent: runtimeEventDebug,
      streams,
      namedBlobs,
      persistence: persistenceService
    },
  };
  if (uiService && typeof uiService.setWake === "function") {
    uiService.setWake(drainPendingUiPolls);
  }
  return api;
}
