# Persistence Service Specification (WASM Microkernel)

Status: Draft

## Scope

This document specifies a persistence service for the JS microkernel that replaces
the current in-memory map of blobs with a durable, chunked storage layer and a
minimal directory index. The scope is intentionally narrow: provide only the
metadata and directory behavior required by ASDF and Quicklisp, while remaining
capability-gated and browser-appropriate.

This spec complements:
- doc/wasm/capability-matrix.md
- doc/wasm/kernel-request-abi.md
- doc/wasm/streams-spec.md
- doc/wasm/quicklisp.md

## Goals

- Provide a capability-gated persistence service supporting both ephemeral and
  durable backends.
- Store file data as chunks to avoid large monolithic values and to permit
  efficient range reads.
- Maintain a minimal metadata index to answer DIRECTORY, PROBE-FILE, and
  FILE-WRITE-DATE without loading file contents.
- Support a read-only blob mount (preloaded dist) plus a writable overlay.
- Keep semantics predictable and small; do not emulate POSIX.

## Non-goals

- Full POSIX filesystem semantics (permissions, links, devices, uid/gid, etc.).
- Transparent sharing of storage across browser origins.
- Perfect atomicity across multiple independent runners without shared memory.
- Full-text search or rich metadata queries.

## Capability Integration

- :persist/ephemeral enables in-memory storage with identical API behavior.
- :persist/store enables durable storage (IndexedDB or OPFS-backed).
- :fs/virtual enables pathname resolution, directory queries, and file metadata.

When a required capability is absent, operations must signal
CAPABILITY-UNAVAILABLE with :capability and :operation keys.

## Layering Model

1. Chunked Blob Store
   - Stores raw byte chunks keyed by an internal chunk id.
   - Backend can be in-memory (ephemeral) or IndexedDB (durable).

2. Minimal VFS Metadata Index
   - Maps normalized paths to file or directory metadata.
   - References chunk ids for file data.

3. Mount and Overlay Resolution
   - Read-only mounts for preloaded dist content.
   - Writable overlay for Quicklisp caches and downloads.
   - Resolution order: writable overlay, then read-only mounts.

## Path and Namespace Rules

- Paths are UTF-8, case-sensitive, and use forward slashes.
- No device names, drive letters, or OS-specific syntax.
- Normalize by removing redundant slashes and dot segments.
- The root path is "/". Directories may be represented with or without a
  trailing slash, but canonicalization removes the trailing slash.
- Pathnames in Lisp are mapped to these normalized paths by the :fs/virtual
  layer.

## Data Model

### File Metadata (minimal)

Required fields:
- path: normalized string
- type: "file" or "dir"
- size: u64 (bytes)
- mtime: u64 (ms since Unix epoch)
- readonly: boolean
- content: for files only
  - chunk_size: u32
  - chunk_count: u32
  - chunk_ids: array of chunk ids, ordered
  - etag: optional content hash

Optional fields:
- ctime: u64 (ms since epoch)
- version: u64 (monotonic write counter for conflict detection)

### Chunk Records

- chunk_id: unique string or u64
- bytes: Uint8Array
- size: u32
- hash: optional content hash

### Directory Records

- path: normalized string
- type: "dir"
- mtime: u64
- readonly: boolean

Directories are lightweight: they may be implicit (derived from file prefixes)
or explicit (stored as a directory record). ENSURE-DIRECTORIES-EXIST creates
explicit entries. DIRECTORY queries must return both explicit directories and
implicit directories derived from file prefixes.

## Chunking Requirements

- Files are stored as fixed-size chunks. Default chunk_size is 256 KiB.
- The chosen chunk_size is stored in the file metadata and can vary per file.
- Reads must support range reads by pulling only the required chunks.
- Writes may be implemented as full rewrite, but must be staged and committed
  atomically to avoid torn files.

## Minimal Operations (host-side requirements)

These operations are the conceptual API; the ABI mapping is defined elsewhere.

### Blob Store Operations

- put_blob(key, bytes, options) -> {size, etag}
- get_blob(key, range?) -> bytes
- delete_blob(key)
- stat_blob(key) -> {size, mtime, etag?}
- list_blobs(prefix, limit?, cursor?) -> {keys, cursor?}

### VFS Operations (Quicklisp/ASDF minimum)

- open(path, mode, options) -> stream handle
  - modes: read, write, read-write, create, truncate, append
- probe_file(path) -> metadata or not found
- truename(path) -> canonical path or not found
- directory(path, pattern?, options) -> list of paths
- file_write_date(path) -> mtime or not found
- file_length(path) -> size or not found
- rename_file(src, dst)
- delete_file(path)
- ensure_directories_exist(path)
- mkdir(path, parents? = false)
- rmdir(path)

Directory operations:
- mkdir creates an explicit directory record. If parents is true, create missing
  ancestors. If the directory already exists, return success (idempotent).
- rmdir removes an explicit directory record only if the directory is empty.
  If the directory contains files or implicit child directories, return -ENOTEMPTY.
- delete_file MUST NOT remove directories; use rmdir for that.

Error behavior:
- Not found: -ENOENT
- Read-only mount: -EACCES
- Already exists: -EEXIST
- Directory not empty: -ENOTEMPTY
- Missing capability: CAPABILITY-UNAVAILABLE
- Unsupported feature: -ENOSYS

## Stream Integration

- File streams are implemented as stream endpoints backed by the chunk store.
- STREAM_OPEN must accept a file-open kind with path and mode flags.
- STREAM_READ and STREAM_WRITE operate on the current file position in the
  stream endpoint.
- FILE-POSITION is implemented in Lisp using stream operations and metadata.

## Overlay and Mount Semantics

- Each mount has a prefix and a read-only flag.
- Resolution:
  - For reads, check writable overlay first; if not present, fall through to
    read-only mounts in order.
  - For writes, only the writable overlay is eligible.
- RENAME-FILE across different mounts is not supported; signal -EXDEV.

## Consistency and Atomicity

- open(write/truncate) writes into a staging entry and commits on close.
- rename_file is atomic within the writable overlay.
- delete_file removes metadata and schedules chunks for GC.
- If a crash occurs during a staged write, incomplete staging entries must be
  removed on next startup.

## Garbage Collection

- Chunk records are reclaimed when no file metadata references them.
- Implementations may use reference counts or mark-and-sweep.
- GC may be lazy; it must not break observable file semantics.

## Backend Requirements

### Ephemeral backend

- In-memory maps for metadata and chunk data.
- Same API and error behavior as persistent backend.

### Persistent backend (IndexedDB preferred)

- Object stores:
  - files: metadata keyed by normalized path
  - chunks: chunk bytes keyed by chunk_id
  - dirs: optional explicit directory records
  - manifest: schema version and global settings
- Directory queries use prefix-range cursors for efficiency.
- All multi-record updates (metadata + chunks) are transactional.

## Versioning and Migration

- A manifest record stores schema version and default chunk_size.
- On upgrade, migration must preserve file data and metadata.
- The service must reject incompatible schema versions with a clear error.

## Minimal ASDF and Quicklisp Compatibility Notes

- DIRECTORY must support prefix listing and wildcard filtering at the Lisp
  layer without loading file contents.
- FILE-WRITE-DATE and FILE-LENGTH must be served from metadata.
- RENAME-FILE must be atomic for typical download-then-rename workflows.
- ENSURE-DIRECTORIES-EXIST must create explicit directory entries as needed.

## Open Questions

- What default chunk_size is optimal for IDB in target browsers?
- Should we expose a fast range-read opcode to avoid per-chunk stream overhead?
- Should a read-only blob mount participate in DIRECTORY results by default?
- Do we need a per-world namespace or a shared global store keyed by workspace?
