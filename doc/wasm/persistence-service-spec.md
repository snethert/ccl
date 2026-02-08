# Persistence Service Specification (WASM Microkernel)

Status: Draft

## Scope

This document specifies a persistence service for the JS microkernel that uses a
memory-first runtime store with snapshot-file bootstrap/flush, plus optional
host-backed integration stores. The scope is intentionally narrow: provide only
the metadata and directory behavior required by ASDF and Quicklisp, while
remaining capability-gated and browser-appropriate.

This spec complements:
- doc/wasm/capability-matrix.md
- doc/wasm/kernel-request-abi.md
- doc/wasm/streams-spec.md
- doc/wasm/quicklisp.md

## Goals

- Provide a capability-gated persistence service with a memory-first default
  backend and optional durable integration backends.
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
- :persist/store enables persisted storage via snapshot-file backend (default)
  and optional host-backed integrations (IndexedDB/LMDB/OPFS-style).
- :fs/virtual enables pathname resolution, directory queries, and file metadata.

When a required capability is absent, operations must signal
CAPABILITY-UNAVAILABLE with :capability and :operation keys.

## Layering Model

1. Snapshot Bootstrap/Flush Layer
   - Loads snapshot bytes into memory at startup.
   - Flushes full snapshot atomically on exit when dirty.

2. Chunked Blob Store
   - Stores raw byte chunks keyed by an internal chunk id.
   - Runtime operations execute against in-memory state.

3. Minimal VFS Metadata Index
   - Maps normalized paths to file or directory metadata.
   - References chunk ids for file data.

4. Mount and Overlay Resolution
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

### Chunk Store Operations (internal)

The chunk store must support:
- put_chunk(id, bytes)
- get_chunk(id) -> bytes (or a range of bytes)
- delete_chunk(id)

### VFS Operations (minimum)

- open(path, mode, options) -> stream handle
  - modes: read, write, read-write, create, truncate, append
- probe_file(path) -> metadata or not found
- truename(path) -> canonical path or not found
- directory(path, pattern?, options) -> list of paths
- file_write_date(path) -> mtime or not found
- rename_file(src, dst)
- delete_file(path)
- ensure_directories_exist(path)
- delete_empty_directory(path)
- delete_directory_tree(path, validate?)

Directory semantics:
- ensure_directories_exist creates explicit directory records (idempotent).
- delete_empty_directory removes an explicit directory record only if empty.
- delete_directory_tree recursively deletes a directory tree; implementations
  MUST require a validation predicate (or explicit validate flag) before
  performing recursive deletion.
- delete_file MUST NOT remove directories.
- rename_file MUST overwrite the target when requested by the caller's mode
  (ASDF uses rename-overwriting-target semantics for staging).

Error behavior:
- Not found: -ENOENT
- Read-only mount: -EACCES
- Directory not empty: -ENOTEMPTY
- Missing capability: CAPABILITY-UNAVAILABLE
- Unsupported feature: -ENOSYS

## Kernel Request ABI Mapping (Minimum)

This section defines the payload and response layouts for the minimal
persistence operations. Opcode values are assigned in
doc/wasm/kernel-opcode-registry.md; names are listed here for clarity.

All integers are little-endian. Strings are UTF-8 bytes, not NUL-terminated.

### Common Path Payload (single path)

```
offset  size  field
0x00    u32   flags        (reserved, must be 0)
0x04    u32   path_ptr     (guest pointer)
0x08    u32   path_len     (bytes)
0x0c    u32   reserved     (0)
```

### Common Path Payload (two paths)

```
offset  size  field
0x00    u32   flags        (reserved, must be 0)
0x04    u32   src_ptr      (guest pointer)
0x08    u32   src_len      (bytes)
0x0c    u32   dst_ptr      (guest pointer)
0x10    u32   dst_len      (bytes)
0x14    u32   reserved     (0)
```

### KERNEL_OP_FS_PROBE

Payload: common path payload (single path).

Response payload (24 bytes):

```
offset  size  field
0x00    u32   kind         (0=file, 1=dir)
0x04    u32   flags        (bit0=readonly, others 0)
0x08    u64   size_bytes   (0 for dir)
0x10    u64   mtime_ms     (unix ms)
```

Result: 0 on success; -ENOENT if missing.

### KERNEL_OP_FS_TRUENAME

Payload: common path payload (single path).

Response payload: normalized path bytes.

Result: 0 on success; -ENOENT if missing.

### KERNEL_OP_FS_DIRECTORY

Payload: common path payload (single path).

Response payload: packed entry list.

```
offset  size  field
0x00    u32   count
0x04    ...   entries

entry:
0x00    u32   kind         (0=file, 1=dir)
0x04    u32   path_len
0x08    u8[]  path_bytes   (length = path_len)
```

Entries are packed with no padding; the next entry begins immediately after
its path bytes. Returned paths are normalized and do not include trailing
slashes.

Result: 0 on success; -ENOENT if directory missing.

### KERNEL_OP_FS_FILE_WRITE_DATE

Payload: common path payload (single path).

Response payload (8 bytes):

```
offset  size  field
0x00    u64   mtime_ms
```

Result: 0 on success; -ENOENT if missing.

### KERNEL_OP_FS_RENAME

Payload: common path payload (two paths).

Result: 0 on success; -ENOENT if source missing; -EACCES for read-only
targets; -EXDEV if mounts differ.

### KERNEL_OP_FS_DELETE

Payload: common path payload (single path).

Result: 0 on success; -ENOENT if missing; -EISDIR if path is a directory.

### KERNEL_OP_FS_ENSURE_DIRS

Payload: common path payload (single path).

Result: 0 on success; -EACCES for read-only mounts.

### KERNEL_OP_FS_DELETE_EMPTY_DIR

Payload: common path payload (single path).

Result: 0 on success; -ENOENT if missing; -ENOTEMPTY if non-empty.

### KERNEL_OP_FS_DELETE_TREE

Payload: common path payload (single path), with flags bit0 set to 1 to
acknowledge recursive deletion. If bit0 is 0, return -EINVAL.

Result: 0 on success; -ENOENT if missing.

## Stream Integration

- File streams are implemented as stream endpoints backed by the chunk store.
- STREAM_OPEN must accept a file-open kind with path and mode flags.
- STREAM_READ and STREAM_WRITE operate on the current file position in the
  stream endpoint.
- STREAM_SEEK and STREAM_TRUNCATE apply to file-backed streams only.
- FILE-POSITION is implemented in Lisp using stream operations and metadata.

### STREAM_OPEN FILE kind (proposed)

This spec requires a file-backed stream kind for STREAM_OPEN.

Arg payload (passed via STREAM_OPEN arg_ptr/arg_len):

```
offset  size  field
0x00    u32   mode_flags
0x04    u32   path_ptr
0x08    u32   path_len
0x0c    u32   reserved
```

mode_flags:
- 0x1 READ
- 0x2 WRITE
- 0x4 CREATE
- 0x8 TRUNCATE
- 0x10 APPEND

STREAM_OPEN returns a stream SID on success or a negative errno on failure.

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
- Snapshot flush must use temp-file + atomic rename semantics so prior snapshot
  remains valid after interrupted writes.

## Garbage Collection

- Chunk records are reclaimed when no file metadata references them.
- Implementations may use reference counts or mark-and-sweep.
- GC may be lazy; it must not break observable file semantics.

## Backend Requirements

### Ephemeral backend

- In-memory maps for metadata and chunk data.
- Same API and error behavior as persistent backend.

### Default persisted backend (memory-snapshot)

- Startup: load snapshot file into in-memory metadata/chunk maps.
- Runtime: all reads/writes operate on in-memory state only.
- Flush: on clean exit and dirty state, write full snapshot atomically.
- Clean run with no mutations must not rewrite snapshot file.

### Integration persistent backends (optional)

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

## Minimal ASDF Compatibility Notes

- DIRECTORY must support prefix listing and wildcard filtering at the Lisp
  layer without loading file contents.
- FILE-WRITE-DATE must be served from metadata.
- RENAME-FILE must be atomic for typical download-then-rename workflows.
- ENSURE-DIRECTORIES-EXIST must create explicit directory entries as needed.
- DELETE-EMPTY-DIRECTORY and DELETE-DIRECTORY-TREE are used by ASDF's
  filesystem utilities and must be supported.

## Development Roadmap Checklist

1. [ ] Register opcodes in doc/wasm/kernel-opcode-registry.md for all FS ops in this spec.
2. [ ] Mirror payload/response layouts in doc/wasm/kernel-request-abi.md.
3. [ ] Implement path normalization: normalizePath(pathBytes) -> string (no ., .., duplicate slashes).
4. [ ] Implement chunk store API: putChunk, getChunk (range), deleteChunk.
5. [ ] Implement metadata index API: getMeta, putMeta, deleteMeta, listByPrefix.
6. [ ] Implement mount resolution: resolveRead and resolveWrite with overlay-first semantics.
7. [ ] Implement ensureDirectoriesExist with explicit directory records.
8. [ ] Implement directory listing: directory(path) returns explicit and implicit dirs.
9. [ ] Implement probeFile and truename using normalized paths.
10. [ ] Implement fileWriteDate from metadata without reading content.
11. [ ] Implement renameFile with overwrite semantics and -EXDEV on cross-mount.
12. [ ] Implement deleteFile with -EISDIR for directories.
13. [ ] Implement deleteEmptyDirectory and deleteDirectoryTree with validation requirement.
14. [ ] Implement write staging: beginWrite, write, commit, abort with atomic commit.
15. [ ] Wire microkernel op handlers for all FS opcodes; return negative errno on failure.
16. [ ] Add STREAM_OPEN FILE kind and mode flags (READ/WRITE/CREATE/TRUNCATE/APPEND).
17. [ ] Implement file-backed stream endpoint with position tracking and mode enforcement.
18. [ ] Add in-memory backend (ephemeral) using maps for metadata and chunks.
19. [ ] Add default memory-snapshot persisted backend (file bootstrap + dirty
    atomic flush on exit).
20. [ ] Keep IndexedDB/LMDB/OPFS-style stores as optional integration backends.
21. [ ] Add startup recovery for incomplete staged writes.
22. [ ] Add chunk GC to delete unreferenced chunks.
23. [ ] Add JS-side validation harness for create/read/rename/delete and directory ops.

## Open Questions

- What default chunk_size is optimal across snapshot-file and IDB backends?
- Should we expose a fast range-read opcode to avoid per-chunk stream overhead?
- Should a read-only blob mount participate in DIRECTORY results by default?
- Do we need a per-world namespace or a shared global store keyed by workspace?
