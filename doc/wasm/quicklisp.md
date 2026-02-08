# Quicklisp in CCL→WASM

**Status:** Deferred (post‑MVP)  
**Purpose:** Capture the future Quicklisp support plan, including filesystem
expectations, capability gating, and browser/headless behavior.

## Summary

Quicklisp is not part of the current MVP. When enabled, it must be usable in the
browser without relying on a POSIX model. The plan is to provide a minimal
virtual filesystem (VFS) that is capability‑gated and can start as fully
in‑memory storage. Quicklisp should become available once capability negotiation
and storage backends are wired; when HTTP is available, it can download libraries
and update itself by default.

## Capability profile

**Always in browser MVP**
- `:fs/virtual`
- `:persist/ephemeral`
- `:io/stream`
- `:time/clock`, `:time/timers`

**Conditional**
- `:net/http` when network is allowed
- `:persist/store` when persisted storage is enabled (memory-snapshot default,
  with optional IndexedDB/LMDB integration lanes)

**Behavior**
- If `:net/http` is present, Quicklisp updates and downloads are allowed by
  default.
- If `:net/http` is absent, Quicklisp runs offline against the preloaded dist.
- If `:persist/store` is present, downloaded artifacts and metadata persist
  across reloads.

## VFS design (minimal, Quicklisp‑compatible)

**Goals**
- Provide just enough filesystem behavior for Quicklisp/ASDF to function.
- Keep the VFS explicitly host‑capability‑gated.

**Minimal operations to support**
- `OPEN` (read/write)
- `PROBE-FILE`, `TRUENAME`
- `DIRECTORY`
- `FILE-WRITE-DATE`, `FILE-LENGTH`, `FILE-POSITION`
- `RENAME-FILE`, `DELETE-FILE`
- `ENSURE-DIRECTORIES-EXIST`

If a required capability is missing, signal `CAPABILITY-UNAVAILABLE` with the
appropriate `:capability` key and operation name.

## Storage model and migration path

**Phase 1: In‑memory VFS**
- Backing store is a map: path → `{bytes, mtime, mode, type, size}`.
- Lost on page reload.

**Phase 2: Memory-snapshot persistence (default)**
- Same VFS API; load snapshot file into memory at startup.
- Rewrite snapshot on exit only when dirty.
- Use a minimal metadata index to implement `DIRECTORY` queries.

**Phase 3: Integration stores (optional)**
- IndexedDB/LMDB/OPFS backends behind explicit capability/profile selection.
- Keep behavior/API parity with memory-snapshot backend.

## Overlay layout

The VFS should support a read‑only “blob registry” mount for preloaded dist
content, and a writable overlay for Quicklisp’s caches and downloads.

**Resolution order**
1. Writable overlay
2. Read‑only blob mounts

This keeps preloaded assets immutable while still letting Quicklisp write its
state.
