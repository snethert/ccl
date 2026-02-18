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
  const presentationResolver = options.presentationResolver ?? null;
  const now = options.now ?? (() => Date.now());
  const metadata = options.metadata ?? {};
  const sessionPrefix = options.sessionPrefix ?? "session:";

  let enabled = true;
  let timer = null;
  let pendingState = null;
  let lastWrite = null;
  let lastError = null;

  function sessionKey(sessionId) {
    return `${sessionPrefix}${sessionId}`;
  }

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
    const restored = restoreStateFromSnapshot(snapshot, {
      schemaVersion,
      allowlist,
      now,
      presentationResolver
    });
    return restored?.state ?? null;
  }

  async function saveSession(state, options = {}) {
    if (!state) {
      throw new Error("State is required to save a session");
    }
    const sessionId = options.sessionId ?? state.activeSessionId ?? null;
    if (!sessionId) {
      throw new Error("Session id is required to save a session");
    }
    const sessionMeta =
      options.session ??
      state.sessions?.[sessionId] ??
      { id: sessionId, name: options.name ?? "Session", createdAt: now() };
    const snapshot = createSnapshot(state, {
      schemaVersion,
      allowlist,
      now,
      metadata: { ...metadata, kind: "session" },
      session: sessionMeta
    });
    await store.putSnapshot(sessionKey(sessionId), snapshot);
    return snapshot;
  }

  async function restoreSession(sessionId, options = {}) {
    if (!sessionId) {
      throw new Error("Session id is required to restore a session");
    }
    const snapshot = await store.getSnapshot(sessionKey(sessionId));
    if (!snapshot) return null;
    const restored = restoreStateFromSnapshot(snapshot, {
      schemaVersion,
      allowlist,
      now,
      presentationResolver: options.presentationResolver ?? presentationResolver,
      markStalePresentations: options.markStalePresentations ?? false
    });
    return restored ?? null;
  }

  async function deleteSession(sessionId) {
    if (!sessionId) {
      throw new Error("Session id is required to delete a session");
    }
    return store.clearSnapshot(sessionKey(sessionId));
  }

  async function listSessions() {
    if (typeof store.listSnapshots !== "function") return [];
    const keys = await store.listSnapshots();
    const sessions = [];
    for (const key of keys) {
      if (typeof key !== "string" || !key.startsWith(sessionPrefix)) continue;
      const sessionId = key.slice(sessionPrefix.length);
      const snapshot = await store.getSnapshot(key);
      const meta = snapshot?.session ?? snapshot?.metadata?.session ?? null;
      sessions.push({ id: sessionId, ...(meta ?? {}) });
    }
    return sessions;
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
    saveSession,
    restoreSession,
    deleteSession,
    listSessions,
    setEnabled,
    getStatus,
    close
  };
}
