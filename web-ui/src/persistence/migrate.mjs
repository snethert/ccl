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

const MIGRATIONS = {
  "0": migrate0To1
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
