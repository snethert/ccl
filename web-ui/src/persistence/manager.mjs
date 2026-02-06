import { DEFAULT_FLUSH_DELAY, SCHEMA_VERSION } from "./schema.mjs";
import { createSnapshot, restoreStateFromSnapshot } from "./serialize.mjs";

export function createPersistenceManager(options = {}) {
  const store = options.store;
  if (!store) {
    throw new Error("Persistence store is required");
  }
  const workspaceId = options.workspaceId ?? null;
  const schemaVersion = options.schemaVersion ?? SCHEMA_VERSION;
  const flushDelay = Number.isFinite(options.flushDelay) ? options.flushDelay : DEFAULT_FLUSH_DELAY;
  const allowlist = options.allowlist ?? {};
  const now = options.now ?? (() => Date.now());
  const metadata = options.metadata ?? {};

  let enabled = true;
  let timer = null;
  let pendingState = null;
  let lastWrite = null;
  let lastError = null;

  async function persistState(state) {
    const snapshot = createSnapshot(state, { schemaVersion, allowlist, now, metadata });
    const id = workspaceId ?? snapshot.workspaceId ?? "workspace-0";
    await store.putSnapshot(id, snapshot);
    lastWrite = snapshot.createdAt;
    lastError = null;
    return snapshot;
  }

  function schedulePersist(state) {
    if (!enabled) return;
    pendingState = state;
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
    timer = setTimeout(() => {
      timer = null;
      void flushNow();
    }, flushDelay);
  }

  async function flushNow() {
    if (!enabled) return null;
    if (!pendingState) return null;
    const state = pendingState;
    pendingState = null;
    try {
      return await persistState(state);
    } catch (err) {
      lastError = err;
      throw err;
    }
  }

  async function restoreState() {
    const id = workspaceId ?? "workspace-0";
    const snapshot = await store.getSnapshot(id);
    if (!snapshot) return null;
    const restored = restoreStateFromSnapshot(snapshot, { schemaVersion, allowlist, now });
    return restored?.state ?? null;
  }

  function setEnabled(value) {
    enabled = Boolean(value);
    if (!enabled && timer) {
      clearTimeout(timer);
      timer = null;
    }
  }

  function getStatus() {
    return {
      enabled,
      pending: Boolean(pendingState),
      lastWrite,
      lastError
    };
  }

  function close() {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
    if (typeof store.close === "function") {
      store.close();
    }
  }

  return {
    schedulePersist,
    flushNow,
    restoreState,
    setEnabled,
    getStatus,
    close
  };
}
