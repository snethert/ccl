# UI Wire Format Tree Delta v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Incremental patch payload format for UI tree updates  
Depends on: `web-ui/spec/ui-wire-format-tree-v1.md`, `web-ui/spec/protocol-version-negotiation-v1.md`, `web-ui/spec/performance-slo-and-budgets-v1.md`  
Compatibility: `v1.x` preserves delta opcodes, apply order semantics, and baseline-state requirements; incompatible patch model changes require `v2`.

## 1. Purpose

This contract defines incremental tree update payloads for high-frequency UI updates.

## 2. Applicability

Delta payloads are optional and capability-gated (`ui-tree-delta-v1`).

Rules:

1. Producer <a id="REQ-UI-WIRE-FORMAT-TREE-DELTA-V1-0ACEFC80DB"></a>MUST send full-tree payload before first delta sequence for a stream.
2. Consumer <a id="REQ-UI-WIRE-FORMAT-TREE-DELTA-V1-704F801503"></a>MUST reject delta payloads when no baseline tree is installed.

## 3. Delta Payload Envelope

Binary header:

| Offset | Size | Type | Field |
|---|---:|---|---|
| `0x00` | 4 | `u32` | `magic = 0x55494431` (`UID1`) |
| `0x04` | 4 | `u32` | `version = 1` |
| `0x08` | 4 | `u32` | `base_seq` |
| `0x0c` | 4 | `u32` | `delta_seq` |
| `0x10` | 4 | `u32` | `op_count` |

## 4. Operation Set

Opcode set:

1. `1 = replace-node`
2. `2 = remove-node`
3. `3 = insert-child`
4. `4 = update-prop`
5. `5 = remove-prop`
6. `6 = reorder-children`

Apply rules:

1. Operations <a id="REQ-UI-WIRE-FORMAT-TREE-DELTA-V1-6042BF40D0"></a>MUST apply in encoded order.
2. Unknown opcodes <a id="REQ-UI-WIRE-FORMAT-TREE-DELTA-V1-EFDAA214F2"></a>MUST fail decode.
3. Failed apply <a id="REQ-UI-WIRE-FORMAT-TREE-DELTA-V1-19F631F498"></a>MUST abort remaining ops in same delta payload.

## 5. Sequencing and Recovery

1. `delta_seq` <a id="REQ-UI-WIRE-FORMAT-TREE-DELTA-V1-C49681AFE7"></a>MUST increase monotonically.
2. `base_seq` <a id="REQ-UI-WIRE-FORMAT-TREE-DELTA-V1-2D5B9DEFE4"></a>MUST match currently installed baseline/delta state.
3. Sequence mismatch <a id="REQ-UI-WIRE-FORMAT-TREE-DELTA-V1-E6F22DB994"></a>MUST trigger full-tree resync request.

## 6. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `ui-tree-delta.baseline-missing` | Delta received without baseline tree. | Conditional | Send full-tree baseline first. |
| `ui-tree-delta.sequence-mismatch` | `base_seq` does not match consumer state. | Conditional | Resync with full tree and resume delta stream. |
| `ui-tree-delta.op-unsupported` | Delta opcode unknown/unsupported. | No | Use supported opcode set or upgrade major version. |
| `ui-tree-delta.apply-failed` | One or more delta ops failed against current tree. | Conditional | Resync baseline and retry deltas. |

## 7. Conformance

An implementation is conformant only if Sections 2-6 are enforced.
