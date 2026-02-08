import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  createSession
} from "../src/state.mjs";
import {
  createSnapshot,
  restoreStateFromSnapshot,
  createMemoryStore,
  createPersistenceManager
} from "../src/index.mjs";

test("phase-4 snapshot persists sessions and active session", () => {
  let state = createState();
  state = createSession(state, { name: "Alpha", now: 10 });
  const sessionId = state.activeSessionId;
  const snapshot = createSnapshot(state, { now: () => 0 });
  const restored = restoreStateFromSnapshot(snapshot);
  assert.ok(restored.state.sessions[sessionId]);
  assert.equal(restored.state.activeSessionId, sessionId);
});

test("phase-4 restore can mark presentations stale without resolver", () => {
  const state = createState({
    presentations: {
      "pres-1": { id: "pres-1", type: "value", metadata: { summary: "stale" } }
    }
  });
  const snapshot = createSnapshot(state, { now: () => 0 });
  const restored = restoreStateFromSnapshot(snapshot, { markStalePresentations: true });
  assert.equal(restored.state.presentations["pres-1"].metadata.stale, true);
});

test("phase-4 persistence manager saves and restores sessions", async () => {
  const store = createMemoryStore();
  const manager = createPersistenceManager({ store, now: () => 0 });

  let state = createState();
  state = createSession(state, { name: "Alpha", now: 0 });
  const sessionId = state.activeSessionId;

  await manager.saveSession(state, { sessionId });
  const sessions = await manager.listSessions();
  assert.ok(sessions.find((entry) => entry.id === sessionId));

  const restored = await manager.restoreSession(sessionId, { markStalePresentations: true });
  assert.ok(restored.state);
  assert.equal(restored.snapshot.session.id, sessionId);
});
