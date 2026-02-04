/*
 * Reference JS microkernel implementation for the kernel_request ABI (MVP).
 *
 * This is intentionally small and "boring": it provides a request table and a
 * copy-based response mechanism suitable for bring-up and for environments
 * without SharedArrayBuffer/Atomics.
 */

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

export const KERNEL_STREAM_KIND_PIPE = 0x00000000;
export const KERNEL_STREAM_KIND_NAMED_RO = 0x00000001;

// Minimal errno set. The kernel and microkernel must agree on numeric values.
// For wasm32-wasi bring-up builds, use wasi-libc/WASI errno numbers.
export const ERRNO = Object.freeze({
  // Values from /usr/include/wasm32-wasi/wasi/api.h:
  // __WASI_ERRNO_2BIG=1, __WASI_ERRNO_AGAIN=6, __WASI_ERRNO_BADF=8,
  // __WASI_ERRNO_NOENT=44, __WASI_ERRNO_INVAL=28, __WASI_ERRNO_NOSYS=52.
  E2BIG: 1,
  EWOULDBLOCK: 6, // EAGAIN
  EBADF: 8,
  EINVAL: 28,
  ENOENT: 44,
  ENOSYS: 52,
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

function encodeTimeNowResponse(nowMs) {
  return encodeU64LE(nowMs);
}

function readU32LE(memory, ptr) {
  const dv = new DataView(memory.buffer);
  return dv.getUint32(u32(ptr), true);
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
  now = () => Date.now(),
} = {}) {
  if (!memory) throw new Error("createMicrokernel: memory is required");

  const requests = new Map(); // id -> { status, result, response: Uint8Array }
  const pendingStdinReads = []; // request ids waiting on stdin
  let nextRequestId = 1;

  const logs = [];
  const decoder = typeof TextDecoder !== "undefined" ? new TextDecoder("utf-8") : null;

  function decodeUtf8(bytes) {
    if (decoder) return decoder.decode(bytes);
    let out = "";
    for (let i = 0; i < bytes.length; i++) {
      out += String.fromCharCode(bytes[i]);
    }
    return out;
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

  function recordRequestDone(id, result, responseBytes = null) {
    requests.set(id, {
      status: KERNEL_STATUS_DONE,
      result: i32(result),
      response: responseBytes ? normalizeBytes(responseBytes) : new Uint8Array(0),
    });
  }

  function recordRequestPending(id, pending) {
    requests.set(id, {
      status: KERNEL_STATUS_PENDING,
      result: 0,
      response: new Uint8Array(0),
      pending,
    });
  }

  function recordRequestError(id, errno) {
    // "ERROR" is reserved for ABI-level failures; most op failures are DONE with negative errno.
    requests.set(id, {
      status: KERNEL_STATUS_ERROR,
      result: i32(-Math.abs(errno | 0)),
      response: new Uint8Array(0),
    });
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

  function kernel_request(opcode, payloadPtr, payloadLen) {
    const id = nextRequestId++;
    const op = u32(opcode);

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
        const capabilityBits = asyncStdin ? 0x1 : 0; // bit0: requests may return PENDING
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
          recordRequestDone(id, bytes.length);
          break;
        }
        if (sid === 2) {
          writeStderr(bytes);
          recordRequestDone(id, bytes.length);
          break;
        }
        const stream = streams.get(u32(sid));
        if (!stream || !stream.writable) {
          recordRequestDone(id, -ERRNO.EBADF);
          break;
        }
        if (stream.kind === "pipe") {
          recordRequestDone(id, stream.write(bytes));
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
    const req = requests.get(u32(requestId));
    return req ? u32(req.status) : KERNEL_STATUS_ERROR;
  }

  function kernel_result(requestId) {
    const req = requests.get(u32(requestId));
    return req ? i32(req.result) : i32(-ERRNO.EINVAL);
  }

  function kernel_response_size(requestId) {
    const req = requests.get(u32(requestId));
    return req ? u32(req.response.length) : 0;
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
    const req = requests.get(u32(requestId));
    if (!req || !req.response || req.response.length === 0) return 0;

    const want = Math.min(u32(dstLen), req.response.length);
    if (want === 0) return 0;
    if (!inBounds(memory, dstPtr, want)) return 0;

    copyInto(memory, dstPtr, req.response.subarray(0, want));
    return u32(want);
  }

  function kernel_drop_request(requestId) {
    // Idempotent drop (required: guest must drop exactly once; host ignores repeats).
    const id = u32(requestId);
    const req = requests.get(id);
    if (req?.status === KERNEL_STATUS_PENDING && req.pending?.kind === "stdin_read") {
      const idx = pendingStdinReads.indexOf(id);
      if (idx >= 0) {
        pendingStdinReads.splice(idx, 1);
      }
    }
    requests.delete(id);
  }

  const imports = {
    kernel_request,
    kernel_poll,
    kernel_result,
    kernel_response_size,
    kernel_copy_response,
    kernel_drop_request,
  };

  return {
    imports,
    feedStdin,
    closeStdin,
    registerNamedBlob,
    registerNamedBlobs,
    getLogs: () => logs.slice(),
    _debug: { requests, pendingStdinReads, streams, namedBlobs },
  };
}
