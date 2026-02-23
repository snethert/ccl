/*
 * Persistence service (minimal VFS + chunk store) for the JS microkernel.
 * In-memory backend plus memory-snapshot default persistence and optional
 * IndexedDB/LMDB-backed integration stores.
 */

export const DEFAULT_CHUNK_SIZE = 256 * 1024;

export const FILE_MODE_READ = 0x1;
export const FILE_MODE_WRITE = 0x2;
export const FILE_MODE_CREATE = 0x4;
export const FILE_MODE_TRUNCATE = 0x8;
export const FILE_MODE_APPEND = 0x10;

function decodeUtf8(bytes) {
  if (typeof bytes === "string") return bytes;
  if (bytes instanceof Uint8Array) {
    if (typeof TextDecoder !== "undefined") {
      return new TextDecoder("utf-8").decode(bytes);
    }
    let out = "";
    for (let i = 0; i < bytes.length; i++) out += String.fromCharCode(bytes[i]);
    return out;
  }
  if (bytes instanceof ArrayBuffer) return decodeUtf8(new Uint8Array(bytes));
  if (ArrayBuffer.isView(bytes)) return decodeUtf8(new Uint8Array(bytes.buffer, bytes.byteOffset, bytes.byteLength));
  throw new TypeError("expected string or byte array");
}

function normalizePathInput(input) {
  const raw = decodeUtf8(input).trim();
  if (!raw) throw new Error("empty path");
  const hadTrailingSlash = raw.length > 1 && raw.endsWith("/");
  let s = raw;
  if (!s.startsWith("/")) s = "/" + s;
  const parts = s.split("/");
  const stack = [];
  for (const part of parts) {
    if (!part || part === ".") continue;
    if (part === "..") {
      if (stack.length) stack.pop();
      continue;
    }
    stack.push(part);
  }
  let path = "/" + stack.join("/");
  if (path !== "/" && path.endsWith("/")) path = path.slice(0, -1);
  return { path: path || "/", hadTrailingSlash };
}

function parentDir(path) {
  if (path === "/") return "/";
  const idx = path.lastIndexOf("/");
  if (idx <= 0) return "/";
  return path.slice(0, idx);
}

function splitParts(path) {
  if (path === "/") return [];
  return path.slice(1).split("/");
}

function implicitDirsForPath(path) {
  const parts = splitParts(path);
  const out = [];
  let cur = "";
  for (let i = 0; i < parts.length - 1; i++) {
    cur += "/" + parts[i];
    out.push(cur);
  }
  return out;
}

function createInMemoryStore({ chunkSize = DEFAULT_CHUNK_SIZE, now = () => Date.now(), readonly = false } = {}) {
  const persist = {
    putMeta: () => {},
    deleteMeta: () => {},
    putChunk: () => {},
    deleteChunk: () => {},
    setManifest: () => {},
  };
  return {
    chunkSize,
    readonly,
    now,
    meta: new Map(), // path -> meta
    chunks: new Map(), // id -> Uint8Array
    nextChunkId: 1,
    persist,
  };
}

function setMeta(store, path, meta) {
  store.meta.set(path, meta);
  store.persist?.putMeta?.(path, meta);
  if (store.persist?.includeMetaKeys) setManifest(store);
}

function deleteMeta(store, path) {
  if (store.meta.has(path)) store.meta.delete(path);
  store.persist?.deleteMeta?.(path);
  if (store.persist?.includeMetaKeys) setManifest(store);
}

function setManifest(store) {
  if (!store.persist?.setManifest) return;
  const manifest = { chunkSize: store.chunkSize, nextChunkId: store.nextChunkId };
  if (store.persist?.includeMetaKeys) {
    manifest.metaKeys = Array.from(store.meta.keys());
  }
  store.persist.setManifest(manifest);
}

function allocChunkId(store) {
  const id = `c${store.nextChunkId++}`;
  setManifest(store);
  return id;
}

function putChunkData(store, id, bytes) {
  store.chunks.set(id, new Uint8Array(bytes));
  store.persist?.putChunk?.(id, bytes);
}

function deleteChunkData(store, id) {
  store.chunks.delete(id);
  store.persist?.deleteChunk?.(id);
}

function putChunks(store, bytes) {
  const chunkIds = [];
  let off = 0;
  while (off < bytes.length) {
    const end = Math.min(bytes.length, off + store.chunkSize);
    const chunk = bytes.subarray(off, end);
    const id = allocChunkId(store);
    putChunkData(store, id, chunk);
    chunkIds.push(id);
    off = end;
  }
  return chunkIds;
}

function deleteChunks(store, chunkIds) {
  if (!chunkIds) return;
  for (const id of chunkIds) deleteChunkData(store, id);
}

function idbRequest(req) {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function idbDone(tx) {
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error);
  });
}

function idbIterate(store) {
  return new Promise((resolve, reject) => {
    const out = [];
    const req = store.openCursor();
    req.onerror = () => reject(req.error);
    req.onsuccess = (event) => {
      const cursor = event.target.result;
      if (!cursor) {
        resolve(out);
        return;
      }
      out.push([cursor.key, cursor.value]);
      cursor.continue();
    };
  });
}

async function openIndexedDb(name, version) {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(name, version);
    req.onerror = () => reject(req.error);
    req.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains("meta")) db.createObjectStore("meta");
      if (!db.objectStoreNames.contains("chunks")) db.createObjectStore("chunks");
      if (!db.objectStoreNames.contains("manifest")) db.createObjectStore("manifest");
    };
    req.onsuccess = () => resolve(req.result);
  });
}

function createIdbPersist(db, store) {
  const queue = [];
  let draining = false;

  function enqueue(op) {
    queue.push(op);
    if (!draining) drain();
  }

  async function drain() {
    draining = true;
    while (queue.length) {
      const ops = queue.splice(0, queue.length);
      const tx = db.transaction(["meta", "chunks", "manifest"], "readwrite");
      const metaStore = tx.objectStore("meta");
      const chunkStore = tx.objectStore("chunks");
      const manifestStore = tx.objectStore("manifest");
      for (const op of ops) {
        switch (op.type) {
        case "putMeta":
          metaStore.put(op.value, op.key);
          break;
        case "deleteMeta":
          metaStore.delete(op.key);
          break;
        case "putChunk":
          chunkStore.put(op.value, op.key);
          break;
        case "deleteChunk":
          chunkStore.delete(op.key);
          break;
        case "setManifest":
          manifestStore.put(op.value, "manifest");
          break;
        default:
          break;
        }
      }
      try {
        await idbDone(tx);
      } catch (err) {
        // Best-effort persistence: keep going even if a write fails.
        // eslint-disable-next-line no-console
        console.warn("persist-service: idb write failed", err);
      }
    }
    draining = false;
  }

  return {
    putMeta: (key, value) => enqueue({ type: "putMeta", key, value }),
    deleteMeta: (key) => enqueue({ type: "deleteMeta", key }),
    putChunk: (key, value) => enqueue({ type: "putChunk", key, value }),
    deleteChunk: (key) => enqueue({ type: "deleteChunk", key }),
    setManifest: (value) => enqueue({ type: "setManifest", value }),
    flush: async () => { while (draining || queue.length) await new Promise((r) => setTimeout(r, 0)); },
  };
}

export async function createIndexedDbPersistenceStore({
  dbName = "ccl-persist",
  dbVersion = 1,
  chunkSize = DEFAULT_CHUNK_SIZE,
  now = () => Date.now(),
} = {}) {
  if (typeof indexedDB === "undefined") {
    throw new Error("indexedDB is not available");
  }
  const db = await openIndexedDb(dbName, dbVersion);
  const store = createInMemoryStore({ chunkSize, now, readonly: false });
  const tx = db.transaction(["meta", "chunks", "manifest"], "readonly");
  const manifest = await idbRequest(tx.objectStore("manifest").get("manifest"));
  if (manifest && typeof manifest.chunkSize === "number") {
    store.chunkSize = manifest.chunkSize >>> 0;
  }
  if (manifest && typeof manifest.nextChunkId === "number") {
    store.nextChunkId = manifest.nextChunkId >>> 0;
  }
  const metaEntries = await idbIterate(tx.objectStore("meta"));
  for (const [key, value] of metaEntries) {
    store.meta.set(String(key), value);
  }
  const chunkEntries = await idbIterate(tx.objectStore("chunks"));
  let maxChunkId = store.nextChunkId;
  for (const [key, value] of chunkEntries) {
    const id = String(key);
    store.chunks.set(id, value instanceof Uint8Array ? value : new Uint8Array(value));
    if (id.startsWith("c")) {
      const num = parseInt(id.slice(1), 10);
      if (Number.isFinite(num)) maxChunkId = Math.max(maxChunkId, num + 1);
    }
  }
  store.nextChunkId = maxChunkId;
  store.persist = createIdbPersist(db, store);
  setManifest(store);
  return store;
}

function readRange(store, meta, pos, maxBytes) {
  const size = meta.size >>> 0;
  if (pos >= size) return new Uint8Array(0);
  const end = Math.min(size, pos + maxBytes);
  const out = new Uint8Array(end - pos);
  let outOff = 0;
  const chunkSize = meta.content.chunk_size;
  let idx = Math.floor(pos / chunkSize);
  let offInChunk = pos % chunkSize;
  while (outOff < out.length) {
    const chunkId = meta.content.chunk_ids[idx++];
    const chunk = store.chunks.get(chunkId) || new Uint8Array(0);
    const take = Math.min(chunk.length - offInChunk, out.length - outOff);
    out.set(chunk.subarray(offInChunk, offInChunk + take), outOff);
    outOff += take;
    offInChunk = 0;
  }
  return out;
}

function readAll(store, meta) {
  return readRange(store, meta, 0, meta.size >>> 0);
}

function hasImplicitDir(store, path) {
  if (path === "/") return true;
  const prefix = path + "/";
  for (const key of store.meta.keys()) {
    if (key.startsWith(prefix)) return true;
  }
  return false;
}

function listEntries(store, dirPath) {
  const entries = new Map();
  const prefix = dirPath === "/" ? "/" : dirPath + "/";
  for (const [path, meta] of store.meta.entries()) {
    if (!path.startsWith(prefix)) continue;
    if (path === dirPath) continue;
    entries.set(path, meta.type);
    for (const d of implicitDirsForPath(path)) {
      if (!d.startsWith(prefix) || d === dirPath) continue;
      if (!entries.has(d)) entries.set(d, "dir");
    }
  }
  return entries;
}

function makeDirMeta(path, readonly, now) {
  return {
    path,
    type: "dir",
    size: 0,
    mtime: now(),
    readonly: !!readonly,
  };
}

function makeFileMeta(path, readonly, now, chunkSize, chunkIds, size) {
  return {
    path,
    type: "file",
    size: size >>> 0,
    mtime: now(),
    readonly: !!readonly,
    content: {
      chunk_size: chunkSize >>> 0,
      chunk_count: chunkIds.length >>> 0,
      chunk_ids: chunkIds.slice(),
      etag: null,
    },
  };
}

export function createPersistenceService({ errno, now = () => Date.now(), chunkSize = DEFAULT_CHUNK_SIZE, overlay = null, readOnlyMounts = [] } = {}) {
  if (!errno) throw new Error("createPersistenceService: errno is required");
  const overlayStore = overlay || createInMemoryStore({ chunkSize, now, readonly: false });
  const roMounts = readOnlyMounts.map((m) => ({
    prefix: normalizePathInput(m.prefix || "/").path,
    store: m.store || createInMemoryStore({ chunkSize, now, readonly: true }),
  }));

  function findInStore(store, path) {
    const meta = store.meta.get(path) || null;
    if (meta) return { meta, implicit: false };
    if (hasImplicitDir(store, path)) return { meta: makeDirMeta(path, store.readonly, store.now), implicit: true };
    return null;
  }

  function resolveRead(path) {
    const inOverlay = findInStore(overlayStore, path);
    if (inOverlay) return { store: overlayStore, readonly: overlayStore.readonly, ...inOverlay };
    for (const m of roMounts) {
      if (!path.startsWith(m.prefix)) continue;
      const found = findInStore(m.store, path);
      if (found) return { store: m.store, readonly: true, ...found };
    }
    return null;
  }

  function overlayHasEntriesUnder(path) {
    const prefix = path === "/" ? "/" : path + "/";
    for (const key of overlayStore.meta.keys()) {
      if (key === path) continue;
      if (key.startsWith(prefix)) return true;
    }
    return false;
  }

  function anyReadOnlyEntriesUnder(path) {
    const prefix = path === "/" ? "/" : path + "/";
    for (const m of roMounts) {
      for (const key of m.store.meta.keys()) {
        if (key === path) continue;
        if (key.startsWith(prefix)) return true;
      }
    }
    return false;
  }

  function ensureDirs(pathBytes) {
    const { path, hadTrailingSlash } = normalizePathInput(pathBytes);
    if (overlayStore.readonly) return { ok: false, errno: errno.EACCES };
    const dirPath = hadTrailingSlash ? path : parentDir(path);
    const parts = splitParts(dirPath);
    let cur = "";
    for (const part of parts) {
      cur += "/" + part;
      const existing = overlayStore.meta.get(cur);
      if (existing && existing.type !== "dir") return { ok: false, errno: errno.EINVAL };
      if (!existing) setMeta(overlayStore, cur, makeDirMeta(cur, false, overlayStore.now));
    }
    return { ok: true, value: dirPath };
  }

  function probe(pathBytes) {
    try {
      const { path } = normalizePathInput(pathBytes);
      const found = resolveRead(path);
      if (!found) return { ok: false, errno: errno.ENOENT };
      const { meta, readonly } = found;
      return {
        ok: true,
        value: {
          kind: meta.type,
          readonly,
          size: meta.type === "file" ? meta.size >>> 0 : 0,
          mtimeMs: meta.mtime >>> 0,
        },
      };
    } catch (_e) {
      return { ok: false, errno: errno.EINVAL };
    }
  }

  function truename(pathBytes) {
    try {
      const { path } = normalizePathInput(pathBytes);
      const found = resolveRead(path);
      if (!found) return { ok: false, errno: errno.ENOENT };
      return { ok: true, value: path };
    } catch (_e) {
      return { ok: false, errno: errno.EINVAL };
    }
  }

  function directory(pathBytes) {
    try {
      const { path } = normalizePathInput(pathBytes);
      const found = resolveRead(path);
      if (!found || found.meta.type !== "dir") return { ok: false, errno: errno.ENOENT };
      const seen = new Map();
      const overlayEntries = listEntries(overlayStore, path);
      for (const [p, kind] of overlayEntries.entries()) {
        seen.set(p, { path: p, kind, readonly: overlayStore.readonly });
      }
      for (const m of roMounts) {
        if (!path.startsWith(m.prefix) && m.prefix !== "/") continue;
        const roEntries = listEntries(m.store, path);
        for (const [p, kind] of roEntries.entries()) {
          if (seen.has(p)) continue;
          seen.set(p, { path: p, kind, readonly: true });
        }
      }
      return { ok: true, value: Array.from(seen.values()) };
    } catch (_e) {
      return { ok: false, errno: errno.EINVAL };
    }
  }

  function fileWriteDate(pathBytes) {
    try {
      const { path } = normalizePathInput(pathBytes);
      const found = resolveRead(path);
      if (!found || found.implicit) return { ok: false, errno: errno.ENOENT };
      return { ok: true, value: found.meta.mtime >>> 0 };
    } catch (_e) {
      return { ok: false, errno: errno.EINVAL };
    }
  }

  function renameFile(srcBytes, dstBytes) {
    try {
      const src = normalizePathInput(srcBytes).path;
      const dst = normalizePathInput(dstBytes).path;
      if (overlayStore.readonly) return { ok: false, errno: errno.EACCES };
      const srcMeta = overlayStore.meta.get(src);
      if (!srcMeta) {
        const ro = resolveRead(src);
        return { ok: false, errno: ro ? errno.EACCES : errno.ENOENT };
      }
      if (srcMeta.type !== "file") return { ok: false, errno: errno.EISDIR };
      const dstMeta = resolveRead(dst);
      if (dstMeta && dstMeta.meta.type === "dir") return { ok: false, errno: errno.EISDIR };
      const ensure = ensureDirs(dstBytes);
      if (!ensure.ok) return ensure;
      const existing = overlayStore.meta.get(dst);
      if (existing && existing.type === "file") deleteChunks(overlayStore, existing.content?.chunk_ids);
      deleteMeta(overlayStore, src);
      const moved = { ...srcMeta, path: dst };
      setMeta(overlayStore, dst, moved);
      return { ok: true, value: 0 };
    } catch (_e) {
      return { ok: false, errno: errno.EINVAL };
    }
  }

  function deleteFile(pathBytes) {
    try {
      const { path } = normalizePathInput(pathBytes);
      if (overlayStore.readonly) return { ok: false, errno: errno.EACCES };
      const meta = overlayStore.meta.get(path);
      if (!meta) {
        const ro = resolveRead(path);
        return { ok: false, errno: ro ? errno.EACCES : errno.ENOENT };
      }
      if (meta.type !== "file") return { ok: false, errno: errno.EISDIR };
      deleteChunks(overlayStore, meta.content?.chunk_ids);
      deleteMeta(overlayStore, path);
      return { ok: true, value: 0 };
    } catch (_e) {
      return { ok: false, errno: errno.EINVAL };
    }
  }

  function deleteEmptyDirectory(pathBytes) {
    try {
      const { path } = normalizePathInput(pathBytes);
      if (overlayStore.readonly) return { ok: false, errno: errno.EACCES };
      const meta = overlayStore.meta.get(path);
      if (!meta) {
        const ro = resolveRead(path);
        return { ok: false, errno: ro ? errno.EACCES : errno.ENOENT };
      }
      if (meta.type !== "dir") return { ok: false, errno: errno.ENOTEMPTY };
      if (overlayHasEntriesUnder(path) || anyReadOnlyEntriesUnder(path)) {
        return { ok: false, errno: errno.ENOTEMPTY };
      }
      deleteMeta(overlayStore, path);
      return { ok: true, value: 0 };
    } catch (_e) {
      return { ok: false, errno: errno.EINVAL };
    }
  }

  function deleteDirectoryTree(pathBytes, validate) {
    try {
      const { path } = normalizePathInput(pathBytes);
      if (!validate) return { ok: false, errno: errno.EINVAL };
      if (overlayStore.readonly) return { ok: false, errno: errno.EACCES };
      const hasOverlay = overlayStore.meta.has(path) || overlayHasEntriesUnder(path);
      if (!hasOverlay) {
        const ro = resolveRead(path);
        return { ok: false, errno: ro ? errno.EACCES : errno.ENOENT };
      }
      const prefix = path === "/" ? "/" : path + "/";
      for (const [p, meta] of Array.from(overlayStore.meta.entries())) {
        if (p === path || p.startsWith(prefix)) {
          if (meta.type === "file") deleteChunks(overlayStore, meta.content?.chunk_ids);
          deleteMeta(overlayStore, p);
        }
      }
      return { ok: true, value: 0 };
    } catch (_e) {
      return { ok: false, errno: errno.EINVAL };
    }
  }

  function openFile(pathBytes, modeFlags) {
    try {
      const { path } = normalizePathInput(pathBytes);
      const wantRead = (modeFlags & FILE_MODE_READ) !== 0;
      const wantWrite = (modeFlags & FILE_MODE_WRITE) !== 0;
      const wantCreate = (modeFlags & FILE_MODE_CREATE) !== 0;
      const wantTruncate = (modeFlags & FILE_MODE_TRUNCATE) !== 0;
      const wantAppend = (modeFlags & FILE_MODE_APPEND) !== 0;
      if (!wantRead && !wantWrite) return { ok: false, errno: errno.EINVAL };
      if (wantWrite && overlayStore.readonly) return { ok: false, errno: errno.EACCES };

      const overlayMeta = overlayStore.meta.get(path) || null;
      const roMeta = overlayMeta ? null : resolveRead(path)?.meta || null;
      const existing = overlayMeta || roMeta;
      if (existing && existing.type === "dir") return { ok: false, errno: errno.EISDIR };

      if (!existing && !wantCreate && wantWrite) return { ok: false, errno: errno.ENOENT };
      if (!existing && !wantWrite && wantRead) return { ok: false, errno: errno.ENOENT };

      if (wantWrite) {
        const ensure = ensureDirs(pathBytes);
        if (!ensure.ok) return ensure;
      }

      let buffer = null;
      let length = 0;
      const existingSize = existing ? existing.size >>> 0 : 0;
      if (wantWrite) {
        if (wantTruncate || !existing) {
          buffer = new Uint8Array(0);
          length = 0;
        } else {
          const srcStore = overlayMeta ? overlayStore : resolveRead(path)?.store;
          buffer = existing ? readAll(srcStore || overlayStore, existing) : new Uint8Array(0);
          length = buffer.length;
        }
      }

      let position = 0;
      if (wantAppend && (wantWrite || wantRead)) {
        position = wantWrite ? length : (existing ? existing.size >>> 0 : 0);
      }

      function fileSize() {
        if (buffer) return length;
        return existingSize;
      }

      const handle = {
        readable: wantRead,
        writable: wantWrite,
        read(maxBytes) {
          if (!this.readable) return -errno.EBADF;
          const meta = overlayStore.meta.get(path) || roMeta;
          if (buffer) {
            const end = Math.min(length, position + maxBytes);
            const out = buffer.subarray(position, end);
            position = end;
            return new Uint8Array(out);
          }
          if (!meta) return new Uint8Array(0);
          const store = overlayMeta ? overlayStore : resolveRead(path)?.store || overlayStore;
          const out = readRange(store, meta, position, maxBytes);
          position += out.length;
          return out;
        },
        write(bytes) {
          if (!this.writable) return -errno.EBADF;
          const data = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
          const end = position + data.length;
          if (!buffer || end > buffer.length) {
            // For large buffers (>1 GiB), grow to exact size + 1 MiB slack
            // instead of doubling, to avoid multi-GiB over-allocation that
            // can cause OOM on WASM32 save-image (2+ GiB heap images).
            let newLen;
            if (buffer && buffer.length > 1_073_741_824) {
              newLen = end + 1_048_576;
            } else {
              newLen = Math.max(end, buffer ? buffer.length * 2 : end);
            }
            const next = new Uint8Array(newLen);
            if (buffer && buffer.length) next.set(buffer.subarray(0, length));
            buffer = next;
          }
          buffer.set(data, position);
          position = end;
          length = Math.max(length, end);
          return data.length;
        },
        seek(whence, offset) {
          const offNum = Number(offset);
          if (!Number.isFinite(offNum)) return -errno.EINVAL;
          let off = Math.trunc(offNum);
          let base = 0;
          switch (whence >>> 0) {
          case 0: // SEEK_SET
            // WASM32 workaround: lisp_lseek passes int32_t offsets via
            // int64 sign-extension.  Positions > 2 GiB appear as negative.
            // Recover the unsigned uint32 value.
            if (off < 0 && off >= -2147483648) {
              off = off + 4294967296;
            }
            base = 0;
            break;
          case 1: // SEEK_CUR
            base = position;
            break;
          case 2: // SEEK_END
            base = fileSize();
            break;
          default:
            return -errno.EINVAL;
          }
          const next = base + off;
          if (next < 0) return -errno.EINVAL;
          position = next;
          return position;
        },
        truncate(newLength) {
          if (!this.writable) return -errno.EBADF;
          const lenNum = Number(newLength);
          if (!Number.isFinite(lenNum)) return -errno.EINVAL;
          const nextLen = Math.trunc(lenNum);
          if (nextLen < 0) return -errno.EINVAL;
          if (!buffer) {
            buffer = new Uint8Array(nextLen);
            length = nextLen;
            return 0;
          }
          if (nextLen > buffer.length) {
            const next = new Uint8Array(nextLen);
            if (length) next.set(buffer.subarray(0, length));
            buffer = next;
          }
          length = nextLen;
          return 0;
        },
        close() {
          if (!this.writable) return 0;
          const finalBytes = buffer ? buffer.subarray(0, length) : new Uint8Array(0);
          const old = overlayStore.meta.get(path);
          if (old && old.type === "file") deleteChunks(overlayStore, old.content?.chunk_ids);
          const chunkIds = putChunks(overlayStore, finalBytes);
          const meta = makeFileMeta(path, false, overlayStore.now, overlayStore.chunkSize, chunkIds, finalBytes.length);
          setMeta(overlayStore, path, meta);
          return 0;
        },
      };

      return { ok: true, value: handle };
    } catch (_e) {
      return { ok: false, errno: errno.EINVAL };
    }
  }

  return {
    probe,
    truename,
    directory,
    fileWriteDate,
    renameFile,
    deleteFile,
    ensureDirs,
    deleteEmptyDirectory,
    deleteDirectoryTree,
    openFile,
    _debug: { overlayStore, roMounts },
  };
}

export function createInMemoryPersistenceStore(options = {}) {
  return createInMemoryStore(options);
}

function encodeBase64(bytes) {
  const data = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  if (typeof Buffer !== "undefined" && Buffer.from) {
    return Buffer.from(data).toString("base64");
  }
  let binary = "";
  for (let i = 0; i < data.length; i++) binary += String.fromCharCode(data[i]);
  if (typeof btoa === "function") return btoa(binary);
  throw new Error("base64 encoder is not available");
}

function decodeBase64(text) {
  if (typeof text !== "string") return new Uint8Array(0);
  if (typeof Buffer !== "undefined" && Buffer.from) {
    return new Uint8Array(Buffer.from(text, "base64"));
  }
  if (typeof atob === "function") {
    const binary = atob(text);
    const out = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) out[i] = binary.charCodeAt(i) & 0xff;
    return out;
  }
  throw new Error("base64 decoder is not available");
}

function snapshotDirname(filePath) {
  if (typeof filePath !== "string" || filePath.length === 0) return ".";
  const slash = Math.max(filePath.lastIndexOf("/"), filePath.lastIndexOf("\\"));
  if (slash < 0) return ".";
  if (slash === 0) return filePath[0];
  return filePath.slice(0, slash);
}

function loadSnapshotStore(store, snapshot) {
  if (!snapshot || typeof snapshot !== "object") {
    throw new Error("invalid snapshot payload");
  }
  if (snapshot.format !== "ccl-persist-snapshot-v1") {
    throw new Error(`unsupported snapshot format: ${String(snapshot.format)}`);
  }
  if (typeof snapshot.chunkSize === "number" && Number.isFinite(snapshot.chunkSize) && snapshot.chunkSize > 0) {
    store.chunkSize = snapshot.chunkSize >>> 0;
  }
  if (typeof snapshot.nextChunkId === "number" && Number.isFinite(snapshot.nextChunkId) && snapshot.nextChunkId > 0) {
    store.nextChunkId = snapshot.nextChunkId >>> 0;
  }

  store.meta.clear();
  store.chunks.clear();

  const metaEntries = Array.isArray(snapshot.meta) ? snapshot.meta : [];
  for (const entry of metaEntries) {
    if (!Array.isArray(entry) || entry.length !== 2) continue;
    const key = String(entry[0]);
    const value = entry[1];
    if (value && typeof value === "object") {
      store.meta.set(key, value);
    }
  }

  const chunkEntries = Array.isArray(snapshot.chunks) ? snapshot.chunks : [];
  for (const entry of chunkEntries) {
    if (!Array.isArray(entry) || entry.length !== 2) continue;
    const chunkId = String(entry[0]);
    const encoded = entry[1];
    store.chunks.set(chunkId, decodeBase64(encoded));
  }

  let maxChunkId = store.nextChunkId;
  for (const key of store.chunks.keys()) {
    if (!String(key).startsWith("c")) continue;
    const num = parseInt(String(key).slice(1), 10);
    if (Number.isFinite(num)) maxChunkId = Math.max(maxChunkId, num + 1);
  }
  store.nextChunkId = maxChunkId;
}

function createSnapshotPayload(store) {
  const sortedMeta = Array.from(store.meta.entries())
    .sort((a, b) => String(a[0]).localeCompare(String(b[0])));
  const sortedChunks = Array.from(store.chunks.entries())
    .sort((a, b) => String(a[0]).localeCompare(String(b[0])))
    .map(([key, bytes]) => [String(key), encodeBase64(bytes)]);
  return {
    format: "ccl-persist-snapshot-v1",
    version: 1,
    chunkSize: store.chunkSize >>> 0,
    nextChunkId: store.nextChunkId >>> 0,
    meta: sortedMeta,
    chunks: sortedChunks,
  };
}

export function createMemorySnapshotPersistenceStore({
  snapshotFile = null,
  fsModule = null,
  chunkSize = DEFAULT_CHUNK_SIZE,
  now = () => Date.now(),
  autoFlushOnExit = true,
  resetOnCorrupt = false,
} = {}) {
  const store = createInMemoryStore({ chunkSize, now, readonly: false });
  const hasSnapshotFile = typeof snapshotFile === "string" && snapshotFile.length > 0;
  const fsApi = fsModule && typeof fsModule.readFileSync === "function" ? fsModule : null;
  let dirty = false;
  let closed = false;
  let listenersInstalled = false;

  if (hasSnapshotFile && fsApi) {
    try {
      const raw = fsApi.readFileSync(snapshotFile, "utf8");
      const parsed = JSON.parse(raw);
      loadSnapshotStore(store, parsed);
    } catch (err) {
      const missingFile = err?.code === "ENOENT";
      if (!missingFile && !resetOnCorrupt) {
        throw new Error(`createMemorySnapshotPersistenceStore: failed to read snapshot ${snapshotFile}: ${err?.message ?? err}`);
      }
    }
  }

  function markDirty() {
    dirty = true;
  }

  function flushSync() {
    if (!dirty) return false;
    if (!hasSnapshotFile || !fsApi) return false;
    const payload = createSnapshotPayload(store);
    const out = JSON.stringify(payload, null, 2);
    const dir = snapshotDirname(snapshotFile);
    const pid = typeof process !== "undefined" && Number.isFinite(process?.pid) ? process.pid : 0;
    const tmpPath = `${snapshotFile}.tmp-${pid}-${Date.now()}`;
    if (typeof fsApi.mkdirSync === "function" && dir && dir !== ".") {
      fsApi.mkdirSync(dir, { recursive: true });
    }
    fsApi.writeFileSync(tmpPath, `${out}\n`, "utf8");
    fsApi.renameSync(tmpPath, snapshotFile);
    dirty = false;
    return true;
  }

  function flushOnExit() {
    try {
      flushSync();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn("persist-service: snapshot flush on exit failed", err?.message ?? err);
    }
  }

  function removeExitListeners() {
    if (!listenersInstalled) return;
    listenersInstalled = false;
    if (typeof process !== "undefined" && typeof process.off === "function") {
      process.off("beforeExit", flushOnExit);
      process.off("exit", flushOnExit);
    } else if (typeof process !== "undefined" && typeof process.removeListener === "function") {
      process.removeListener("beforeExit", flushOnExit);
      process.removeListener("exit", flushOnExit);
    }
  }

  if (autoFlushOnExit && hasSnapshotFile && fsApi &&
      typeof process !== "undefined" && typeof process.on === "function") {
    process.on("beforeExit", flushOnExit);
    process.on("exit", flushOnExit);
    listenersInstalled = true;
  }

  store.persist = {
    putMeta: markDirty,
    deleteMeta: markDirty,
    putChunk: markDirty,
    deleteChunk: markDirty,
    setManifest: markDirty,
    includeMetaKeys: true,
    flush: () => flushSync(),
    isDirty: () => dirty,
    close: () => {
      if (!closed) {
        flushSync();
        removeExitListeners();
        closed = true;
      }
      return Promise.resolve();
    },
  };

  return store;
}

function decodeMaybeString(value) {
  if (typeof value === "string") return value;
  if (value instanceof Uint8Array) {
    return decodeUtf8(value);
  }
  if (value instanceof ArrayBuffer) return decodeUtf8(new Uint8Array(value));
  if (ArrayBuffer.isView(value)) return decodeUtf8(new Uint8Array(value.buffer, value.byteOffset, value.byteLength));
  return value;
}

function decodeChunkValue(value) {
  if (value instanceof Uint8Array) return value;
  if (value instanceof ArrayBuffer) return new Uint8Array(value);
  if (ArrayBuffer.isView(value)) return new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
  if (typeof Buffer !== "undefined" && Buffer.isBuffer(value)) return new Uint8Array(value);
  return new Uint8Array(0);
}

function decodeMetaValue(value) {
  const raw = decodeMaybeString(value);
  if (raw == null) return null;
  if (typeof raw === "string") {
    try {
      return JSON.parse(raw);
    } catch (_e) {
      return null;
    }
  }
  return raw;
}

function encodeMetaValue(value) {
  return JSON.stringify(value);
}

export function createLmdbPersistenceStore({
  lmdb,
  path,
  name = "ccl-persist",
  chunkSize = DEFAULT_CHUNK_SIZE,
  now = () => Date.now(),
} = {}) {
  if (!lmdb || typeof lmdb.open !== "function") {
    throw new Error("createLmdbPersistenceStore: lmdb module with open() is required");
  }
  if (!path) throw new Error("createLmdbPersistenceStore: path is required");

  const db = lmdb.open({ path, maxDbs: 1, encoding: "binary" });
  const META_PREFIX = `${name}:m:`;
  const CHUNK_PREFIX = `${name}:c:`;
  const MANIFEST_KEY = `${name}:manifest`;
  const asBinary = typeof lmdb.asBinary === "function" ? lmdb.asBinary : null;

  const store = createInMemoryStore({ chunkSize, now, readonly: false });

  const manifest = decodeMetaValue(db.get(MANIFEST_KEY));
  if (manifest && typeof manifest.chunkSize === "number") {
    store.chunkSize = manifest.chunkSize >>> 0;
  }
  if (manifest && typeof manifest.nextChunkId === "number") {
    store.nextChunkId = manifest.nextChunkId >>> 0;
  }

  const metaKeys = Array.isArray(manifest?.metaKeys) ? manifest.metaKeys : [];
  const chunkIds = new Set();
  for (const metaKey of metaKeys) {
    const raw = db.get(META_PREFIX + String(metaKey));
    const meta = decodeMetaValue(raw);
    if (!meta) continue;
    store.meta.set(String(metaKey), meta);
    if (meta.type === "file" && meta.content?.chunk_ids) {
      for (const id of meta.content.chunk_ids) chunkIds.add(id);
    }
  }

  let maxChunkId = store.nextChunkId;
  for (const id of chunkIds) {
    const raw = db.get(CHUNK_PREFIX + String(id));
    if (raw == null) continue;
    const bytes = decodeChunkValue(raw);
    store.chunks.set(String(id), bytes);
    if (String(id).startsWith("c")) {
      const num = parseInt(String(id).slice(1), 10);
      if (Number.isFinite(num)) maxChunkId = Math.max(maxChunkId, num + 1);
    }
  }
  store.nextChunkId = maxChunkId;

  store.persist = {
    putMeta: (key, value) => { db.putSync(META_PREFIX + String(key), encodeMetaValue(value)); },
    deleteMeta: (key) => { db.removeSync(META_PREFIX + String(key)); },
    putChunk: (key, value) => {
      const bytes = value instanceof Uint8Array ? value : new Uint8Array(value);
      db.putSync(CHUNK_PREFIX + String(key), asBinary ? asBinary(bytes) : bytes);
    },
    deleteChunk: (key) => { db.removeSync(CHUNK_PREFIX + String(key)); },
    setManifest: (value) => { db.putSync(MANIFEST_KEY, encodeMetaValue(value)); },
    includeMetaKeys: true,
    close: () => {
      const op = db.close?.();
      return op && typeof op.then === "function" ? op : Promise.resolve();
    },
  };

  setManifest(store);
  return store;
}
