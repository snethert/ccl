# Wire Format Tree

## Status
⏸️ Not started

## Purpose

Binary encoding for VDOM trees transmitted between the Lisp runtime and the
JavaScript renderer. Uses a compact little-endian binary format (magic "UIB1")
with a string table, flat node list, and property entries. Designed for
efficient WASM↔JS boundary crossing.

## Depends On
None.

## Interface

```
Header (24 bytes, little-endian):
  +0x00  u32  magic         = 0x55494231 ("UIB1")
  +0x04  u32  version       = 1
  +0x08  u32  string_count
  +0x0c  u32  node_count
  +0x10  u32  root_index    (ignored when node_count=0)
  +0x14  u32  reserved      = 0

String Table Entry:
  +0  u32  byte_length
  +4  bytes  UTF-8 (exact byte_length, no padding)

Text Node (kind=0, 16 bytes):
  +0  u32  kind=0  +4 u32 flags=0  +8 u32 key_index  +12 u32 text_index

Element Node (kind=1, variable):
  +0  u32  kind=1  +4 u32 flags=0  +8 u32 key_index
  +12 u32 tag_index  +16 u32 prop_count  +20 u32 child_count
  Then: prop_count × Property (16 bytes each)
  Then: child_count × u32 child indices

Property (16 bytes):
  +0 u32 key_index  +4 u32 value_type  +8 u32 value_lo  +12 u32 value_hi

Value types: 0=null, 1=bool, 2=number(f64), 3=string, 4=array, 5=object
  Types 4,5 require ui-tree-composite-values-v1 capability negotiation
```

`0xffffffff` for key_index means null key. Missing string indices decode as
`""` (text) or `"div"` (element tags).

## Invariants

1. Magic MUST equal 0x55494231 and version MUST equal 1
2. All reads MUST be bounds-checked before dereference
3. When node_count > 0, root_index MUST be < node_count
4. Payload MUST be a complete Uint8Array or decode fails atomically
5. Composite value graph MUST be acyclic (decoders detect and fail on cycles)
6. Identical payload bytes produce identical decoded tree (deterministic)
7. Child order after decode MUST match encoded index order

## Behavior

1. Writers SHOULD deduplicate repeated strings in the string table
2. Missing string indices decode to fallback values ("" or "div"), not errors
3. Object composite key order MUST preserve encoded order
4. Duplicate object keys resolve by last-write-wins in encoded order
5. Child indices are resolved after all nodes are parsed; invalid indices are dropped
6. Value types 4 and 5 MUST NOT be emitted without capability negotiation
7. Consumers without composite capability MUST fail on value_type 4 or 5

## Anti-Patterns

1. Never trust payload bounds without explicit checks
2. Never execute code from property values
3. Never allow circular composite references
4. Never reorder properties or child indices during decode
5. Never skip magic/version validation
6. Never accept composite values without prior capability negotiation

## Out of Scope

- VDOM diffing/reconciliation (see [renderer](renderer.md))
- Semantic meaning of property values (renderer-specific)
- Encoding from Lisp side (compiler/runtime concern)

## Conformance Check
Run: `node spec/web-ui/checks/wire-format-tree.test.mjs`
