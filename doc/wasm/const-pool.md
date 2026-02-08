# WASM2 Constant Pool (v1/v2)

**Status:** Draft  
**Goal:** Enable WASM2-compiled modules to reference non-immediate Lisp objects
(symbols, strings, vectors, function references, and function vectors in v1)
by materializing a per-module constant pool at install time.

## Scope

This document defines:
- the constant pool data format attached to compiled module bundles, and
- the materialization rules used by the runtime loader.

It does **not** define the full compiler IR or GC internals, only the data
shape and required loader behavior.

## Where the Constant Pool Lives

Constant pools are attached to compiled module bundle entries emitted by
`scripts/wasm/compile-*.lisp` (e.g., `doc/wasm/wasm-smoke-modules.json`,
`doc/wasm/wasm-ui-modules.json`).

Each module entry MAY include a `constPoolBytes` field containing the binary
constant-pool encoding (see below). For debugging, a parallel `constPool`
object MAY be emitted as well.

```json
{
  "exportName": "ccl_generic_entry_320",
  "entryIndex": 320,
  "moduleVersion": 1,
  "moduleBytes": [ ... ],
  "constPoolBytes": [ 1, 0, 0, 0, ... ]
}
```

## Versioning

- `constPoolBytes` begins with a version field:
  - v1: little-endian `u32 version` (`1`)
  - v2: unsigned LEB128 `version` (`2`)
- Unknown versions MUST fail safely (loader returns error).

## Entry Types (v1/v2)

Each entry is an object with `type` and type-specific fields. v1 supports:

- `symbol`
- `string`
- `fixnum` (immediate tagged fixnum)
- `vector` (simple vector of other pool entries)
- `function` (symbol resolution to `fdefinition`)
- `function-vector` (literal function object slots)
- `entry-function` (compact function object by WASM entry index)
Entries are addressable by index (0-based).

## Indexing Semantics

`const-pool-ref` indices are 0-based and refer directly to the `entries` array
for the module being installed. Indices are stable for the lifetime of that
module instance.

### 1) `symbol`

```json
{ "type": "symbol", "name": "FOO", "package": "CL-USER" }
```

Materialization:
- `package` is resolved via `find-package` when provided.
- The symbol is resolved by name in that package.
- If not found, the loader SHOULD attempt to `intern` the name in the package.
- If the package system is not initialized (minimal image), the loader MAY
  synthesize a symbol with the given name and package predicate as a fallback.
- Keywords use `package: "KEYWORD"`.
- If `package` is missing or null, the loader MAY search across packages by
  name and MUST fail if not found.

### 2) `string`

```json
{ "type": "string", "value": "hello" }
```

Materialization:
- Create a simple base string (UTF-8 in JSON, runtime decodes to Lisp string).

### 3) `vector`

```json
{ "type": "vector", "elements": [0, 1, 2] }
```

Materialization:
- Allocate a simple vector of length `elements.length`.
- Populate elements with the referenced constant pool objects.

### 4) `function`

```json
{ "type": "function", "name": "WASM-UI-TURN", "package": "CCL" }
```

Materialization:
- Resolve the symbol in the given package and return its `fdefinition`.

### 5) `function-vector`

```json
{ "type": "function-vector", "elements": [0, 1, 2, 3] }
```

Materialization:
- Allocate a function vector of length `elements.length`.
- Populate slots with the referenced constant pool objects.
- v1 assumes WASM function vectors are slot‑only (no native code bytes).

### 6) `fixnum`

```json
{ "type": "fixnum", "value": 1234 }
```

Materialization:
- Use the tagged fixnum value directly.

### 7) `entry-function`

```json
{ "type": "entry-function", "entryIndex": 320 }
```

Materialization:
- Allocate a minimal function object with the target entry index in both the
  callable entry slot and fallback entry slot.
- This avoids serializing full function-vector slot graphs when the compiler
  already knows the entry index.

## Loader Requirements

The runtime loader MUST:
- allocate and materialize all constant pool entries before module activation,
- store the resulting vector of Lisp objects as GC roots,
- keep per-module constant pools stable across reloads,
- expose the pool by index to compiled code via a `const-pool-ref` operation
  (see `wasm_const_pool_install` + `wasm_const_pool_ref` exports).

## Compiler Requirements

The compiler MUST:
- dedupe non-immediate constants within a module,
- emit `constPoolBytes` alongside the module bytes,
- lower non-immediate constants to `const-pool-ref` in IR.

## Error Handling

If any entry cannot be materialized (missing package, invalid type, or
unsupported entry), loader MUST fail the module install with `-EINVAL`. Symbol
entries MAY synthesize a symbol if package resolution succeeds but the symbol
is missing.

## Future Extensions

Potential post-v2 entries:
- `cons` and `list` literals
- `pathname`
- `simple-array` with element type
- structured records

## Binary Encoding

### v1 (legacy)

The `constPoolBytes` payload is a little-endian binary blob:

```
u32 version  (must be 1)
u32 count    (number of entries)
entries...   (count entries)
```

Each entry begins with a `u32 type` tag:

- `1` = `symbol`
- `2` = `string`
- `3` = `vector`
- `4` = `function`
- `5` = `function-vector`
- `6` = `fixnum`
- `16` = `entry-function`

Entry payloads:

- `symbol`: `u32 name_len`, `name_len` bytes, `u32 pkg_len`, `pkg_len` bytes
- `string`: `u32 len`, `len` bytes
- `fixnum`: `u32 value` (tagged fixnum)
- `vector`: `u32 count`, `count` x `u32` indices (into the pool)
- `function`: `u32 name_len`, `name_len` bytes, `u32 pkg_len`, `pkg_len` bytes
- `function-vector`: `u32 count`, `count` x `u32` indices (into the pool)
- `entry-function`: `u32 entry_index` (untagged table index)

Strings are UTF‑8 byte sequences; loaders should treat bytes as base‑string
codes for now.

### v2 (current)

v2 keeps the same type tags and materialization semantics, but switches most
structural integer fields to LEB128:

- header: `uleb128 version` (`2`), `uleb128 count`
- per-entry tag: `uleb128 type`
- structural counts/indices/subtags/string lengths: `uleb128`
- `fixnum` payload: `sleb128` tagged fixnum value
- float/int64/uint64 payload words and bignum digit words remain fixed-width
  little-endian `u32` values.

This reduces constant-pool size substantially for index-heavy entries
(`vector`, `gvector`, `function-vector`, `cons`) while preserving loader
behavior.
