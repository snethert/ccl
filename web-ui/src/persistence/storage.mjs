import { DEFAULT_STORE_NAME, DEFAULT_STORE_VERSION, DEFAULT_STORE_BUCKET } from "./schema.mjs";

function ensureIndexedDB() {
  if (typeof indexedDB === "undefined") {
    throw new Error("IndexedDB is not available in this environment");
  }
  return indexedDB;
}

function openDatabase({ name = DEFAULT_STORE_NAME, version = DEFAULT_STORE_VERSION, bucket = DEFAULT_STORE_BUCKET } = {}) {
  const dbFactory = ensureIndexedDB();
  return new Promise((resolve, reject) => {
    const request = dbFactory.open(name, version);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(bucket)) {
        db.createObjectStore(bucket, { keyPath: "workspaceId" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("IndexedDB open failed"));
    request.onblocked = () => reject(new Error("IndexedDB open blocked"));
  });
}

function withStore(db, bucket, mode, fn) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(bucket, mode);
    const store = tx.objectStore(bucket);
    let result = undefined;
    tx.oncomplete = () => resolve(result);
    tx.onerror = () => reject(tx.error ?? new Error("IndexedDB transaction failed"));
    tx.onabort = () => reject(tx.error ?? new Error("IndexedDB transaction aborted"));
    fn(store, (value) => {
      result = value;
    });
  });
}

export async function createIndexedDBStore(options = {}) {
  const name = options.name ?? DEFAULT_STORE_NAME;
  const version = options.version ?? DEFAULT_STORE_VERSION;
  const bucket = options.bucket ?? DEFAULT_STORE_BUCKET;
  const db = await openDatabase({ name, version, bucket });

  return {
    type: "indexeddb",
    name,
    bucket,
    async getSnapshot(workspaceId) {
      return withStore(db, bucket, "readonly", (store, done) => {
        const request = store.get(workspaceId);
        request.onsuccess = () => done(request.result?.payload ?? null);
        request.onerror = () => done(null);
      });
    },
    async putSnapshot(workspaceId, payload) {
      return withStore(db, bucket, "readwrite", (store, done) => {
        const request = store.put({ workspaceId, updatedAt: Date.now(), payload });
        request.onsuccess = () => done(true);
        request.onerror = () => done(false);
      });
    },
    async listSnapshots() {
      return withStore(db, bucket, "readonly", (store, done) => {
        const request = store.getAllKeys();
        request.onsuccess = () => done(request.result ?? []);
        request.onerror = () => done([]);
      });
    },
    async clearSnapshot(workspaceId) {
      return withStore(db, bucket, "readwrite", (store, done) => {
        const request = store.delete(workspaceId);
        request.onsuccess = () => done(true);
        request.onerror = () => done(false);
      });
    },
    close() {
      db.close();
    }
  };
}

export function createMemoryStore() {
  const snapshots = new Map();
  return {
    type: "memory",
    async getSnapshot(workspaceId) {
      return snapshots.get(workspaceId) ?? null;
    },
    async putSnapshot(workspaceId, payload) {
      snapshots.set(workspaceId, payload);
      return true;
    },
    async listSnapshots() {
      return Array.from(snapshots.keys());
    },
    async clearSnapshot(workspaceId) {
      return snapshots.delete(workspaceId);
    },
    close() {}
  };
}
