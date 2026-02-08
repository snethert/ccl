import { SCHEMA_VERSION } from "./schema.mjs";

function normalizeSnapshotInput(snapshot) {
  if (!snapshot) return null;
  if (snapshot.schemaVersion) return snapshot;
  const state = snapshot.state ?? snapshot;
  return {
    schemaVersion: "0",
    createdAt: snapshot.createdAt ?? null,
    workspaceId: snapshot.workspaceId ?? state?.workspace?.id ?? null,
    metadata: snapshot.metadata ?? {},
    session: snapshot.session ?? null,
    state
  };
}

function migrate0To1(snapshot, options = {}) {
  const now = options.now ?? (() => Date.now());
  return {
    schemaVersion: "1",
    createdAt: snapshot.createdAt ?? now(),
    workspaceId: snapshot.workspaceId ?? snapshot.state?.workspace?.id ?? null,
    metadata: snapshot.metadata ?? {},
    session: snapshot.session ?? null,
    state: snapshot.state ?? {},
    migrationLog: [
      {
        fromVersion: "0",
        toVersion: "1",
        timestamp: now(),
        notes: "Wrapped legacy snapshot into versioned envelope"
      }
    ]
  };
}

function migrate1To2(snapshot, options = {}) {
  const now = options.now ?? (() => Date.now());
  const nextLog = Array.isArray(snapshot.migrationLog) ? [...snapshot.migrationLog] : [];
  nextLog.push({
    fromVersion: "1",
    toVersion: "2",
    timestamp: now(),
    notes: "Added recording store and command history persistence"
  });
  return {
    ...snapshot,
    schemaVersion: "2",
    session: snapshot.session ?? null,
    migrationLog: nextLog
  };
}

function migrate2To3(snapshot, options = {}) {
  const now = options.now ?? (() => Date.now());
  const nextLog = Array.isArray(snapshot.migrationLog) ? [...snapshot.migrationLog] : [];
  nextLog.push({
    fromVersion: "2",
    toVersion: "3",
    timestamp: now(),
    notes: "Added recording snapshot truncation metadata compatibility"
  });
  return {
    ...snapshot,
    schemaVersion: "3",
    session: snapshot.session ?? null,
    migrationLog: nextLog
  };
}

function migrate3To4(snapshot, options = {}) {
  const now = options.now ?? (() => Date.now());
  const nextLog = Array.isArray(snapshot.migrationLog) ? [...snapshot.migrationLog] : [];
  nextLog.push({
    fromVersion: "3",
    toVersion: "4",
    timestamp: now(),
    notes: "Added session registry support to persistence schema"
  });
  return {
    ...snapshot,
    schemaVersion: "4",
    session: snapshot.session ?? null,
    migrationLog: nextLog
  };
}

const MIGRATIONS = {
  "0": migrate0To1,
  "1": migrate1To2,
  "2": migrate2To3,
  "3": migrate3To4
};

export function applyMigrations(snapshot, options = {}) {
  const now = options.now ?? (() => Date.now());
  const targetVersion = options.targetVersion ?? SCHEMA_VERSION;
  let current = normalizeSnapshotInput(snapshot);
  if (!current) return null;

  while (current.schemaVersion !== targetVersion) {
    const migrate = MIGRATIONS[current.schemaVersion];
    if (!migrate) {
      throw new Error(`No migration available from version ${current.schemaVersion}`);
    }
    current = migrate(current, { now });
  }
  return current;
}
