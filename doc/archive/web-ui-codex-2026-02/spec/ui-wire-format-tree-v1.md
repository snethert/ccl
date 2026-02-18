# UI Wire Format Tree v1

Status: Draft  
Version: 1.1.0  
Last updated: 2026-02-17  
Scope: Binary wire format for `KERNEL_OP_UI_RENDER` tree payloads (`decodeTree`)  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/bridge/codec.mjs`, `web-ui/bridge/ui-bridge.mjs`, `scripts/wasm/lib/microkernel.mjs`, `doc/wasm/kernel-request-abi.md`  
Compatibility: `v1.x` preserves magic, header layout, node encoding, and scalar value semantics (`value_type=0..3`); `v1.1+` adds negotiated composite value types (`4=array`, `5=object`) and optional composite tables without changing existing scalar decoding rules.

## 1. Purpose

This contract defines the exact binary format for UI tree payloads rendered through `KERNEL_OP_UI_RENDER`.
It is normative for byte layout, decoding semantics, and failure behavior.

## 2. Binary Profile

1. Endianness: little-endian for all scalar fields.
2. Magic: `0x55494231` (`"UIB1"`).
3. Version: `1`.
4. Minimum payload size: 24 bytes (header).

## 3. Top-Level Payload Layout

Header (`24` bytes):

| Offset | Size | Type | Field | Rules |
|---|---:|---|---|---|
| `0x00` | 4 | `u32` | `magic` | <a id="REQ-UI-WIRE-FORMAT-TREE-V1-706A65EAEB"></a>MUST equal `0x55494231`. |
| `0x04` | 4 | `u32` | `version` | <a id="REQ-UI-WIRE-FORMAT-TREE-V1-75FEF2B2EE"></a>MUST equal `1`. |
| `0x08` | 4 | `u32` | `string_count` | Number of string table entries. |
| `0x0c` | 4 | `u32` | `node_count` | Number of node records. |
| `0x10` | 4 | `u32` | `root_index` | Root node index; ignored when `node_count=0`. |
| `0x14` | 4 | `u32` | `reserved` | Reserved for future use (`v1` writers set `0`). |

After header:

1. String table entries (Section 4).
2. Node records in index order `0..node_count-1` (Section 5).
3. Optional composite value table (Section 5.5), present only when composite values are used.

## 4. String Table Layout

Each string entry is:

| Offset | Size | Type | Field |
|---|---:|---|---|
| `+0` | 4 | `u32` | `byte_length` |
| `+4` | `byte_length` | bytes | UTF-8 string bytes |

Rules:

1. String table is positional; indices refer to entry order.
2. Decoder reads exactly `string_count` entries.
3. Writers SHOULD deduplicate repeated strings for compactness.

## 5. Node Record Layout

Common node prefix:

| Offset | Size | Type | Field | Rules |
|---|---:|---|---|---|
| `+0` | 4 | `u32` | `kind` | `0=text`, `1=element`. |
| `+4` | 4 | `u32` | `flags` | Reserved in `v1`; decoder ignores. |
| `+8` | 4 | `u32` | `key_index` | `0xffffffff` means `null`; else string table index. |

## 5.1 Text Node (`kind=0`)

Layout:

| Offset | Size | Type | Field |
|---|---:|---|---|
| `+12` | 4 | `u32` | `text_index` |

Decoded shape:

1. `kind: "text"`
2. `text: strings[text_index] ?? ""`
3. `key: null` when `key_index == 0xffffffff`, else `strings[key_index]`

Total size: `16` bytes.

## 5.2 Element Node (`kind=1`)

Header extension:

| Offset | Size | Type | Field |
|---|---:|---|---|
| `+12` | 4 | `u32` | `tag_index` |
| `+16` | 4 | `u32` | `prop_count` |
| `+20` | 4 | `u32` | `child_count` |

Then:

1. `prop_count` property entries (`16` bytes each, Section 5.3).
2. `child_count` child indices (`u32` each, contiguous).

Decoded shape:

1. `kind: "element"`
2. `tag: strings[tag_index] ?? "div"`
3. `props: { ... }` from property entries
4. `children`: resolved from child indices in encoded order
5. `key`: same rule as common prefix

## 5.3 Property Entry Layout

| Offset | Size | Type | Field | Rules |
|---|---:|---|---|---|
| `+0` | 4 | `u32` | `prop_key_index` | Key string index. |
| `+4` | 4 | `u32` | `value_type` | See Section 5.4. |
| `+8` | 4 | `u32` | `value_lo` | Value lane A. |
| `+12` | 4 | `u32` | `value_hi` | Value lane B. |

Key decode:

1. `propKey = strings[prop_key_index] ?? ""`

## 5.4 Property Value Types (`v1.1`)

| `value_type` | Name | Decode rule |
|---:|---|---|
| `0` | `null` | `null` |
| `1` | `bool` | `value_lo !== 0` |
| `2` | `number` | IEEE754 `f64` reconstructed from `(value_lo,value_hi)` little-endian lanes |
| `3` | `string` | `strings[value_lo] ?? ""` |
| `4` | `array` | `composites[value_lo]` where composite kind is array |
| `5` | `object` | `composites[value_lo]` where composite kind is object |
| other | unknown | `null` |

Composite types are gated by protocol negotiation:

1. Producers <a id="REQ-UI-WIRE-FORMAT-TREE-V1-9BBB89FA74"></a>MUST NOT emit `value_type=4|5` unless negotiated capability `ui-tree-composite-values-v1` is active.
2. Consumers without active composite capability <a id="REQ-UI-WIRE-FORMAT-TREE-V1-871214838F"></a>MUST fail decode when `value_type=4|5` appears.

## 5.5 Composite Value Table Layout (`v1.1+`)

When any property uses `value_type=4|5`, payload appends this region after node records:

| Offset | Size | Type | Field |
|---|---:|---|---|
| `+0` | 4 | `u32` | `composite_count` |
| `+4` | variable | entries | `composite_count` entries in index order |

Each composite entry:

| Offset | Size | Type | Field | Rules |
|---|---:|---|---|---|
| `+0` | 4 | `u32` | `composite_kind` | `0=array`, `1=object` |
| `+4` | 4 | `u32` | `entry_count` | number of child entries |
| `+8` | variable | bytes | encoded entries | See below |

Array entry encoding (`composite_kind=0`):

1. `entry_count` value descriptors, each `12` bytes:
2. `item_value_type:u32`
3. `item_value_lo:u32`
4. `item_value_hi:u32`

Object entry encoding (`composite_kind=1`):

1. `entry_count` key/value descriptors, each `16` bytes:
2. `item_key_index:u32` (string table index)
3. `item_value_type:u32`
4. `item_value_lo:u32`
5. `item_value_hi:u32`

Composite decode rules:

1. Composite indices are positional in the composite table.
2. Composites MAY contain nested composites by referencing `value_type=4|5`.
3. Cycles are invalid; decoders fail when cycle detection triggers.
4. Object key order <a id="REQ-UI-WIRE-FORMAT-TREE-V1-0069BE6FE8"></a>MUST preserve encoded order.
5. Duplicate object keys <a id="REQ-UI-WIRE-FORMAT-TREE-V1-CE3D15E5E8"></a>MUST resolve by last-write-wins in encoded order.

## 6. Child Resolution Rules

1. Element `children` are initially decoded as child indices.
2. Final child node references are resolved after all nodes are parsed.
3. Child indices that do not resolve to a parsed node are dropped.
4. Child order <a id="REQ-UI-WIRE-FORMAT-TREE-V1-76C44625C5"></a>MUST preserve encoded index order for valid children.

## 7. Decode and Render Failure Behavior

Decoder <a id="REQ-UI-WIRE-FORMAT-TREE-V1-D472AA5995"></a>MUST fail when:

1. Payload is not a `Uint8Array`.
2. Payload is shorter than 24 bytes.
3. Magic/version mismatch.
4. Payload truncates while decoding node metadata.
5. `root_index >= node_count` when `node_count > 0`.
6. Node kind is unsupported (`kind` not `0` or `1`).
7. Composite values are present without negotiated composite capability.
8. Composite table truncates or references invalid indices.
9. Composite graph contains cycles.

`KERNEL_OP_UI_RENDER` integration:

1. If UI service is unavailable: `kernel_result = -ENOSYS`.
2. If decode/render fails: `kernel_result = -EINVAL`.
3. If decode/render succeeds: `kernel_result = 0`.

## 8. Determinism Rules

1. For identical payload bytes, decode output <a id="REQ-UI-WIRE-FORMAT-TREE-V1-858AFCADEF"></a>MUST be identical.
2. Property and child iteration order <a id="REQ-UI-WIRE-FORMAT-TREE-V1-AE0B21FC50"></a>MUST remain encoded order.
3. Unknown property types <a id="REQ-UI-WIRE-FORMAT-TREE-V1-47FDBD3672"></a>MUST deterministically decode as `null`.
4. Missing string indices <a id="REQ-UI-WIRE-FORMAT-TREE-V1-72523EBCCD"></a>MUST use stable fallbacks (`""` or `"div"` as defined).
5. Composite-object key collision behavior <a id="REQ-UI-WIRE-FORMAT-TREE-V1-CC0A4F7768"></a>MUST be deterministic (`last-write-wins`).

## 9. Security Requirements

1. Decoders <a id="REQ-UI-WIRE-FORMAT-TREE-V1-FE7477A442"></a>MUST bounds-check all reads before dereference.
2. Implementations <a id="REQ-UI-WIRE-FORMAT-TREE-V1-B938A5E548"></a>MUST treat payload bytes as untrusted input.
3. Render path <a id="REQ-UI-WIRE-FORMAT-TREE-V1-8CBECBE8C0"></a>MUST avoid executing arbitrary code from payload values.
4. Integrators SHOULD impose upper bounds on payload sizes before decode.
5. Integrators <a id="REQ-UI-WIRE-FORMAT-TREE-V1-381B8E8476"></a>MUST enforce maximum composite nesting depth and entry counts to prevent resource exhaustion.

## 10. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `ui-tree.invalid-payload-type` | Payload is not a `Uint8Array` byte view. | No | Send binary payload bytes. |
| `ui-tree.payload-too-small` | Payload shorter than required header. | No | Send complete header and body bytes. |
| `ui-tree.version-unsupported` | Magic/version mismatch. | No | Use supported format version. |
| `ui-tree.root-index-invalid` | Root index is outside node table. | No | Correct root/node counts and indices. |
| `ui-tree.payload-truncated` | Buffer ended before all declared fields were read. | No | Send full payload bytes. |
| `ui-tree.node-kind-unsupported` | Node kind is not supported in `v1`. | Conditional | Use supported kinds or upgrade both sides. |
| `ui-tree.composite-capability-required` | Composite value payload used without negotiation. | No | Negotiate `ui-tree-composite-values-v1` first. |
| `ui-tree.composite-invalid` | Composite table is malformed, cyclic, or index-invalid. | No | Emit valid acyclic composite payload. |
| `ui-tree.render-invalid` | Render failed after decode (`-EINVAL`). | Conditional | Correct payload and retry render. |
| `ui-tree.service-unavailable` | UI service not installed (`-ENOSYS`). | No | Install/enable UI service. |

## 11. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/bridge-codec.test.mjs`
2. `web-ui/tests/bridge-microkernel.test.mjs`
3. `web-ui/tests/browser.test.mjs`

Pass criteria:

1. Known-good payloads decode to expected tree shape.
2. Invalid payload classes fail deterministically.
3. `KERNEL_OP_UI_RENDER` result codes match Section 7 behavior.

## 12. Conformance

An implementation is conformant only if Sections 2-11 are satisfied.
