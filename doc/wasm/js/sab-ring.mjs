export const SAB_RING_TRANSPORT = "sab_ring_v1";

export const SAB_RING_HEADER = Object.freeze({
  write_idx: 0,
  read_idx: 1,
  capacity: 2,
  flags: 3
});

export const SAB_RING_HEADER_WORDS = 4;
export const SAB_RING_HEADER_BYTES = SAB_RING_HEADER_WORDS * Int32Array.BYTES_PER_ELEMENT;
export const SAB_RING_LEN_PREFIX_BYTES = 4;

function u32(value) {
  return value >>> 0;
}

function i32(value) {
  return value | 0;
}

function assertSharedArrayBuffer(sharedBuffer, label) {
  if (typeof SharedArrayBuffer === "undefined") {
    throw new Error(`${label}: SharedArrayBuffer is not available in this runtime`);
  }
  if (!(sharedBuffer instanceof SharedArrayBuffer)) {
    throw new Error(`${label}: sharedBuffer must be a SharedArrayBuffer`);
  }
}

function normalizeBytes(bytes) {
  if (bytes instanceof Uint8Array) return bytes;
  if (bytes instanceof ArrayBuffer) return new Uint8Array(bytes);
  if (ArrayBuffer.isView(bytes)) return new Uint8Array(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  throw new TypeError("sab-ring: expected Uint8Array/ArrayBuffer/view");
}

function resolveCapacity(sharedBuffer, capacity) {
  const available = sharedBuffer.byteLength - SAB_RING_HEADER_BYTES;
  if (available <= SAB_RING_LEN_PREFIX_BYTES) {
    throw new Error("sab-ring: sharedBuffer is too small for header + payload");
  }
  const chosen = Number.isInteger(capacity) ? capacity : available;
  if (!Number.isInteger(chosen) || chosen <= SAB_RING_LEN_PREFIX_BYTES || chosen > available) {
    throw new Error(`sab-ring: invalid capacity ${String(capacity)} (available=${available})`);
  }
  return chosen;
}

function writeWrapped(dst, capacity, offset, src) {
  if (!src.length) return;
  const start = u32(offset) % capacity;
  const first = Math.min(src.length, capacity - start);
  dst.set(src.subarray(0, first), start);
  if (first < src.length) {
    dst.set(src.subarray(first), 0);
  }
}

function readWrapped(src, capacity, offset, dst) {
  if (!dst.length) return;
  const start = u32(offset) % capacity;
  const first = Math.min(dst.length, capacity - start);
  dst.set(src.subarray(start, start + first), 0);
  if (first < dst.length) {
    dst.set(src.subarray(0, dst.length - first), first);
  }
}

function writeU32LEWrapped(dst, capacity, offset, value) {
  const start = u32(offset) % capacity;
  const v = u32(value);
  dst[start] = v & 0xff;
  dst[(start + 1) % capacity] = (v >>> 8) & 0xff;
  dst[(start + 2) % capacity] = (v >>> 16) & 0xff;
  dst[(start + 3) % capacity] = (v >>> 24) & 0xff;
}

function readU32LEWrapped(src, capacity, offset) {
  const start = u32(offset) % capacity;
  const b0 = src[start];
  const b1 = src[(start + 1) % capacity];
  const b2 = src[(start + 2) % capacity];
  const b3 = src[(start + 3) % capacity];
  return u32(b0 | (b1 << 8) | (b2 << 16) | (b3 << 24));
}

function normalizeTimeout(timeoutMs) {
  if (timeoutMs === undefined || timeoutMs === null) return undefined;
  if (timeoutMs === Infinity) return undefined;
  const n = Number(timeoutMs);
  if (!Number.isFinite(n) || n < 0) return 0;
  return n;
}

function canWait() {
  return typeof Atomics.wait === "function";
}

function tryWait(header, index, expected, timeoutMs) {
  if (!canWait()) return "unsupported";
  try {
    const normalized = normalizeTimeout(timeoutMs);
    if (normalized === undefined) {
      return Atomics.wait(header, index, expected);
    }
    return Atomics.wait(header, index, expected, normalized);
  } catch (_err) {
    // Atomics.wait can throw on runtimes that disallow blocking the current agent.
    return "unsupported";
  }
}

export function initializeSabRing(sharedBuffer, options = {}) {
  assertSharedArrayBuffer(sharedBuffer, "initializeSabRing");
  const capacity = resolveCapacity(sharedBuffer, options.capacity);
  const flags = Number.isInteger(options.flags) ? options.flags : 0;
  const header = new Int32Array(sharedBuffer, 0, SAB_RING_HEADER_WORDS);
  Atomics.store(header, SAB_RING_HEADER.write_idx, 0);
  Atomics.store(header, SAB_RING_HEADER.read_idx, 0);
  Atomics.store(header, SAB_RING_HEADER.capacity, i32(capacity));
  Atomics.store(header, SAB_RING_HEADER.flags, i32(flags));
  return sharedBuffer;
}

export function attachSabRing(sharedBuffer, options = {}) {
  assertSharedArrayBuffer(sharedBuffer, "attachSabRing");
  const header = new Int32Array(sharedBuffer, 0, SAB_RING_HEADER_WORDS);
  const available = sharedBuffer.byteLength - SAB_RING_HEADER_BYTES;
  let capacity = u32(Atomics.load(header, SAB_RING_HEADER.capacity));
  if (capacity === 0 && options.initialize === true) {
    initializeSabRing(sharedBuffer, {
      capacity: Number.isInteger(options.capacity) ? options.capacity : available,
      flags: Number.isInteger(options.flags) ? options.flags : 0
    });
    capacity = u32(Atomics.load(header, SAB_RING_HEADER.capacity));
  }
  if (capacity === 0) {
    throw new Error("attachSabRing: ring header is uninitialized");
  }
  if (capacity > available) {
    throw new Error(`attachSabRing: capacity ${capacity} exceeds available bytes ${available}`);
  }
  if (Number.isInteger(options.capacity) && options.capacity !== capacity) {
    throw new Error(`attachSabRing: capacity mismatch (expected ${options.capacity}, observed ${capacity})`);
  }
  const data = new Uint8Array(sharedBuffer, SAB_RING_HEADER_BYTES, capacity);

  function loadWrite() {
    return u32(Atomics.load(header, SAB_RING_HEADER.write_idx));
  }

  function loadRead() {
    return u32(Atomics.load(header, SAB_RING_HEADER.read_idx));
  }

  function availableBytesFrom(writeIdx, readIdx) {
    return u32(writeIdx - readIdx);
  }

  function availableBytes() {
    return availableBytesFrom(loadWrite(), loadRead());
  }

  function freeBytes() {
    const used = availableBytes();
    if (used > capacity) return 0;
    return capacity - used;
  }

  function isEmpty() {
    return availableBytes() === 0;
  }

  function isFull(frameBytes = 0) {
    const payloadBytes = Number.isInteger(frameBytes) ? Math.max(0, frameBytes) : 0;
    const required = SAB_RING_LEN_PREFIX_BYTES + payloadBytes;
    return freeBytes() < required;
  }

  function enqueueFrame(frameBytes) {
    const payload = normalizeBytes(frameBytes);
    const totalBytes = SAB_RING_LEN_PREFIX_BYTES + payload.length;
    if (totalBytes > capacity) {
      return {
        ok: false,
        reason: "frame_too_large",
        neededBytes: totalBytes,
        capacity
      };
    }

    const writeIdx = loadWrite();
    const readIdx = loadRead();
    const used = availableBytesFrom(writeIdx, readIdx);
    if (used > capacity) {
      return {
        ok: false,
        reason: "corrupt_indices",
        usedBytes: used,
        capacity
      };
    }
    const free = capacity - used;
    if (free < totalBytes) {
      return {
        ok: false,
        reason: "ring_full",
        neededBytes: totalBytes,
        freeBytes: free
      };
    }

    const writeOff = writeIdx % capacity;
    writeU32LEWrapped(data, capacity, writeOff, payload.length);
    if (payload.length > 0) {
      writeWrapped(data, capacity, (writeOff + SAB_RING_LEN_PREFIX_BYTES) % capacity, payload);
    }
    Atomics.store(header, SAB_RING_HEADER.write_idx, i32(writeIdx + totalBytes));
    Atomics.notify(header, SAB_RING_HEADER.write_idx, 1);
    return {
      ok: true,
      transport: SAB_RING_TRANSPORT,
      frameBytes: payload.length,
      totalBytes
    };
  }

  function peekFrameLength() {
    const writeIdx = loadWrite();
    const readIdx = loadRead();
    const availableCount = availableBytesFrom(writeIdx, readIdx);
    if (availableCount < SAB_RING_LEN_PREFIX_BYTES) {
      return null;
    }
    const readOff = readIdx % capacity;
    const frameLength = readU32LEWrapped(data, capacity, readOff);
    const totalBytes = SAB_RING_LEN_PREFIX_BYTES + frameLength;
    if (availableCount < totalBytes) {
      return null;
    }
    return frameLength;
  }

  function dequeueFrame() {
    const writeIdx = loadWrite();
    const readIdx = loadRead();
    const availableCount = availableBytesFrom(writeIdx, readIdx);
    if (availableCount < SAB_RING_LEN_PREFIX_BYTES) {
      return { ok: false, empty: true, reason: "ring_empty" };
    }

    const readOff = readIdx % capacity;
    const frameLength = readU32LEWrapped(data, capacity, readOff);
    const totalBytes = SAB_RING_LEN_PREFIX_BYTES + frameLength;
    if (availableCount < totalBytes) {
      return { ok: false, empty: true, partial: true, reason: "partial_frame" };
    }

    const frame = new Uint8Array(frameLength);
    if (frameLength > 0) {
      readWrapped(data, capacity, (readOff + SAB_RING_LEN_PREFIX_BYTES) % capacity, frame);
    }
    Atomics.store(header, SAB_RING_HEADER.read_idx, i32(readIdx + totalBytes));
    Atomics.notify(header, SAB_RING_HEADER.read_idx, 1);
    return {
      ok: true,
      transport: SAB_RING_TRANSPORT,
      frame,
      frameBytes: frameLength,
      totalBytes
    };
  }

  function waitForReadable(timeoutMs) {
    if (!isEmpty()) return "not-equal";
    const expected = Atomics.load(header, SAB_RING_HEADER.write_idx);
    return tryWait(header, SAB_RING_HEADER.write_idx, expected, timeoutMs);
  }

  function waitForWritable(requiredBytes = 0, timeoutMs) {
    const needed = Number.isInteger(requiredBytes) ? Math.max(0, requiredBytes) : 0;
    if (freeBytes() >= needed) return "not-equal";
    const expected = Atomics.load(header, SAB_RING_HEADER.read_idx);
    return tryWait(header, SAB_RING_HEADER.read_idx, expected, timeoutMs);
  }

  function notifyReadable(count = 1) {
    return Atomics.notify(header, SAB_RING_HEADER.write_idx, Math.max(0, count | 0));
  }

  function notifyWritable(count = 1) {
    return Atomics.notify(header, SAB_RING_HEADER.read_idx, Math.max(0, count | 0));
  }

  function snapshot() {
    const writeIdx = loadWrite();
    const readIdx = loadRead();
    const used = availableBytesFrom(writeIdx, readIdx);
    return {
      transport: SAB_RING_TRANSPORT,
      write_idx: writeIdx,
      read_idx: readIdx,
      capacity,
      flags: u32(Atomics.load(header, SAB_RING_HEADER.flags)),
      usedBytes: used,
      freeBytes: used > capacity ? 0 : capacity - used
    };
  }

  return {
    transport: SAB_RING_TRANSPORT,
    sharedBuffer,
    header,
    data,
    enqueueFrame,
    dequeueFrame,
    enqueue: enqueueFrame,
    dequeue: dequeueFrame,
    peekFrameLength,
    availableBytes,
    freeBytes,
    isEmpty,
    isFull,
    waitForReadable,
    waitForWritable,
    notifyReadable,
    notifyWritable,
    snapshot
  };
}

export function createSabRing(options = {}) {
  const existing = options.sharedBuffer ?? null;
  if (existing) {
    const header = new Int32Array(existing, 0, SAB_RING_HEADER_WORDS);
    const initialized = u32(Atomics.load(header, SAB_RING_HEADER.capacity)) !== 0;
    if (options.initialize === true || !initialized) {
      initializeSabRing(existing, {
        capacity: options.capacity,
        flags: options.flags
      });
    }
    return attachSabRing(existing, {
      capacity: Number.isInteger(options.capacity) ? options.capacity : undefined
    });
  }

  if (!Number.isInteger(options.capacity)) {
    throw new Error("createSabRing: options.capacity is required when creating a new ring");
  }
  const sharedBuffer = new SharedArrayBuffer(SAB_RING_HEADER_BYTES + options.capacity);
  initializeSabRing(sharedBuffer, {
    capacity: options.capacity,
    flags: options.flags
  });
  return attachSabRing(sharedBuffer, { capacity: options.capacity });
}
