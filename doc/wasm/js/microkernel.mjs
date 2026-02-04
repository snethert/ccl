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

// Minimal errno set. The kernel and microkernel must agree on numeric values.
// For wasm32-wasi bring-up builds, use wasi-libc/WASI errno numbers.
export const ERRNO = Object.freeze({
  // Values from /usr/include/wasm32-wasi/wasi/api.h:
  // __WASI_ERRNO_2BIG=1, __WASI_ERRNO_AGAIN=6, __WASI_ERRNO_BADF=8,
  // __WASI_ERRNO_INVAL=28, __WASI_ERRNO_NOSYS=52.
  E2BIG: 1,
  EWOULDBLOCK: 6, // EAGAIN
  EBADF: 8,
  EINVAL: 28,
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

function encodeTimeNowResponse(nowMs) {
  const buf = new ArrayBuffer(8);
  const dv = new DataView(buf);
  const ms = typeof nowMs === "bigint" ? nowMs : BigInt(Math.trunc(nowMs));
  if (typeof dv.setBigUint64 === "function") {
    dv.setBigUint64(0, ms, true);
  } else {
    // Older runtimes: encode via two u32 lanes.
    const lo = Number(ms & 0xffffffffn) >>> 0;
    const hi = Number((ms >> 32n) & 0xffffffffn) >>> 0;
    dv.setUint32(0, lo, true);
    dv.setUint32(4, hi, true);
  }
  return new Uint8Array(buf);
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

export function createMicrokernel({
  memory,
  writeStdout = defaultStdoutWriter,
  writeStderr = defaultStderrWriter,
  // Optional hooks for tests/embedding:
  logSink = null, // (level, text, bytes) => void
  now = () => Date.now(),
} = {}) {
  if (!memory) throw new Error("createMicrokernel: memory is required");

  const requests = new Map(); // id -> { status, result, response: Uint8Array }
  let nextRequestId = 1;

  const logs = [];
  const decoder = typeof TextDecoder !== "undefined" ? new TextDecoder("utf-8") : null;

  // Simple stdin queue for STREAM_READ (sid 0). Empty-but-not-closed returns EWOULDBLOCK.
  const stdinQueue = [];
  let stdinClosed = false;

  function feedStdin(bytes) {
    stdinQueue.push({ bytes: normalizeBytes(bytes), off: 0 });
  }

  function closeStdin() {
    stdinClosed = true;
  }

  function takeStdin(maxBytes) {
    const want = u32(maxBytes);
    if (want === 0) return new Uint8Array(0);

    let available = 0;
    for (const c of stdinQueue) {
      available += c.bytes.length - c.off;
      if (available >= want) break;
    }
    if (available === 0) return null;

    const n = Math.min(want, available);
    const out = new Uint8Array(n);
    let outOff = 0;

    while (outOff < n && stdinQueue.length) {
      const head = stdinQueue[0];
      const remain = head.bytes.length - head.off;
      const take = Math.min(remain, n - outOff);
      out.set(head.bytes.subarray(head.off, head.off + take), outOff);
      head.off += take;
      outOff += take;
      if (head.off >= head.bytes.length) {
        stdinQueue.shift();
      }
    }

    return out;
  }

  function recordRequestDone(id, result, responseBytes = null) {
    requests.set(id, {
      status: KERNEL_STATUS_DONE,
      result: i32(result),
      response: responseBytes ? normalizeBytes(responseBytes) : new Uint8Array(0),
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
        // Stage 1 sync host: no async completion, no wait, no shared-memory assumptions.
        const caps = encodeCapsResponse({ capabilityBits: 0, maxResponseBytes: 0 });
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
        } else if (sid === 2) {
          writeStderr(bytes);
          recordRequestDone(id, bytes.length);
        } else {
          recordRequestDone(id, -ERRNO.ENOSYS);
        }
        break;
      }

      case KERNEL_OP_STREAM_READ: {
        if (u32(payloadLen) !== 8) {
          recordRequestError(id, ERRNO.EINVAL);
          break;
        }
        const sid = readU32LE(memory, u32(payloadPtr) + 0);
        const maxBytes = readU32LE(memory, u32(payloadPtr) + 4);
        if (sid !== 0) {
          recordRequestDone(id, -ERRNO.ENOSYS);
          break;
        }
        const chunk = takeStdin(maxBytes);
        if (chunk && chunk.length) {
          recordRequestDone(id, chunk.length, chunk);
        } else if (stdinClosed) {
          recordRequestDone(id, 0);
        } else {
          recordRequestDone(id, -ERRNO.EWOULDBLOCK);
        }
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
    requests.delete(u32(requestId));
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
    getLogs: () => logs.slice(),
    _debug: { requests },
  };
}
