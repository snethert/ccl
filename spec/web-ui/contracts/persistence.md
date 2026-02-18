# Persistence

## Status
⏸️ Not started

## Purpose

File-primary persistence model. Files are authored units — edited, saved,
and versioned as wholes. Storage uses content-addressed immutable blobs,
hierarchical trees, atomic snapshots, and mutable references. Designed for
crash safety, offline operation, and explicit divergence handling.

## Depends On
- [security](security.md) — persistence operations respect capability state

## Interface

```
Blob      Immutable content-addressed bytes (authored or binary content)
Tree      {[path_component]: Entry}         // hierarchical directory
Snapshot  {root: Tree, metadata: object}    // point-in-time state
Reference Mutable pointer to a Snapshot     // e.g. workspace/main, autosave/latest

Path      POSIX-like UTF-8 NFC-normalized string
          Separator: /   Root: /   Case-sensitive
          No NUL or / in path components
          Explicit component length limits enforced
```

**Reference examples:**
`workspace/main`, `autosave/latest`, `session/<id>`

**Snapshot kinds:**
- User-save: explicit save/save-all (authoritative)
- Autosave: idle-coalesced, time-triggered (safety-only)
- Crash checkpoint: atomic ref movement for recovery

## Invariants

1. Files are authored units — tooling MUST NOT fragment into semantic nodes
2. Objects (blobs, trees, snapshots) are immutable and content-addressed
3. Persistence is append-only — no in-place mutation of objects
4. Reference updates are crash-safe (journaled or atomically equivalent)
5. Recovery resolves each reference to exactly one complete snapshot state
6. Paths are meaningful, POSIX-like, UTF-8 NFC-normalized with enforced limits
7. No silent data loss — highest priority invariant

## Behavior

1. User-save snapshots are authoritative; autosave MUST NOT overwrite user-save history
2. Autosave triggers: idle, time-coalesced, boundary events (safety-only)
3. Edit/save/history operations work offline after initial bootstrap
4. Sync moves objects and references, never file-level surprise rewrites
5. Divergence is represented as explicit reference state, not ad-hoc conflict filenames
6. Protected references use single-writer lease semantics
7. Secondary writers default to explicit branch/session refs or read-only
8. Under storage pressure: (a) stop autosaves, (b) evict derived artifacts, (c) refuse user saves only as last resort with export/recovery path

## Anti-Patterns

1. Never mutate blobs in-place — objects are immutable
2. Never require object-centric workflow from users — filesystem semantics are primary
3. Never replace file content for indexing — tooling layers on top
4. Never create conflict litter (e.g., `file.txt.conflict`) — use explicit ref state
5. Never silently advance user-visible references in background
6. Never break file primacy for semantic canonicality without explicit policy
7. Never emit surprise filename rewrites from tooling

## Out of Scope

- Storage backend implementation details (IndexedDB, OPFS, memory)
- Sync protocol wire format
- File format specifications (e.g., Lisp source encoding)

## Conformance Check
Run: `node spec/web-ui/checks/persistence.test.mjs`
