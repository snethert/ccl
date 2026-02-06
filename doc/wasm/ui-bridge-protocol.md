# UI Bridge Protocol (WASM UI <-> JS Backend)

**Status:** Draft (v1)  
**Scope:** Wire formats and message semantics for the UI bridge between the WASM/Lisp runner (authoritative UI state) and the JS rendering/input backends.

This protocol is **binary, deterministic, and versioned**. It is designed to be transported over the existing `kernel_request` ABI (copy-based responses).

## Conventions

- **Endianness:** little-endian for all integer fields.
- **Types:** `u32`, `i32`, `f64` denote fixed-width values in the payload.
- **Strings:** UTF-8, **not** NUL-terminated.
- **Null string index:** `0xFFFF_FFFF`.

## Versioning

- Each top-level payload begins with a **magic** and **version**.
- Unknown versions MUST fail safely (return `-EINVAL`).
- Reserved fields MUST be written as 0 and ignored on read.

## Payload Types

- **UI Tree Payload (Render):** encoded VDOM tree.
- **UI Event Batch (Poll):** encoded list of input events.

---

# UI Tree Payload (VDOM)

## Header

```
offset  size  field
0x00    u32   magic       // 0x55494231 = "UIB1"
0x04    u32   version     // 1
0x08    u32   stringCount
0x0C    u32   nodeCount
0x10    u32   rootIndex
0x14    u32   reserved    // 0
```

## String table

Immediately after the header:

```
repeat stringCount times:
  u32 byteLen
  u8  bytes[byteLen]
```

Strings are stored exactly once and referenced by index.

## Node table

Each node is encoded in order. Node indices are 0..nodeCount-1.

### Common node header

```
offset  size  field
0x00    u32   kind        // 0=text, 1=element
0x04    u32   flags       // bit0: hasKey
0x08    u32   keyIndex    // string index or 0xFFFF_FFFF
```

### Text node body

```
offset  size  field
0x0C    u32   textIndex   // string index
```

### Element node body

```
offset  size  field
0x0C    u32   tagIndex    // string index
0x10    u32   propCount
0x14    u32   childCount
```

#### Properties

Each property is a fixed 16-byte record:

```
offset  size  field
0x00    u32   keyIndex
0x04    u32   valueType   // 0=null, 1=bool, 2=number(f64), 3=string
0x08    u32   valueLo
0x0C    u32   valueHi
```

- For **bool**, `valueLo` is 0 or 1, `valueHi` is 0.
- For **string**, `valueLo` is the string index, `valueHi` is 0.
- For **number**, `valueLo`/`valueHi` are the little-endian halves of an `f64`.

#### Children

```
repeat childCount times:
  u32 childNodeIndex
```

## VDOM constraints (v1)

- Props MUST be flat scalars only (string/number/bool/null). No arrays or objects.
- Event handler functions are **not** representable; events are captured by the JS bridge globally and routed by data attributes (e.g., `data-widget-id`, `data-command-id`).
- Keys, tags, and text are strings.

### Canvas/WebGL view convention (v1)

To embed a canvas-backed view in the VDOM, emit a `canvas` element with one of the following props:

- `data-canvas-scene`: JSON string encoding a canvas scene array (see `web-ui/backends/canvas/scene.mjs`).
- `data-webgl-scene`: JSON string encoding a WebGL scene array (same schema as canvas).

The bridge will:

- Create a backend instance for each canvas element.
- Parse the JSON payload and render it using the appropriate backend.
- Hit-test pointer/wheel events against the scene graph.

Target identity for hit-tested canvas/WebGL nodes is encoded as:

```
${viewId}:${sceneNodeId}
```

Where:
- `viewId` is the element’s `data-view-id` if present, otherwise its `data-widget-id`.
- `sceneNodeId` is the `id` of the hit scene node.

This convention preserves stable IDs without exposing DOM handles.

---

# UI Event Batch Payload

## Header

```
offset  size  field
0x00    u32   magic       // 0x55494531 = "UIE1"
0x04    u32   version     // 1
0x08    u32   stringCount
0x0C    u32   eventCount
```

## String table

```
repeat stringCount times:
  u32 byteLen
  u8  bytes[byteLen]
```

## Event record

Each event begins with a common header:

```
offset  size  field
0x00    u32   type
0x04    u32   flags
0x08    u32   targetIndex     // widget id string index or 0xFFFF_FFFF
0x0C    u32   windowIndex     // window id string index or 0xFFFF_FFFF
```

### Event flags (v1)

Flags are type-specific. Unused bits MUST be 0.

- Pointer events:
  - bit 0: down
  - bit 1: up
  - bit 2: move
  - bit 3: enter
  - bit 4: leave
  - bit 5: cancel
- Key events:
  - bit 0: down
  - bit 1: up

### Event types (v1)

| Type | Name | Notes |
| ---: | --- | --- |
| 1 | Pointer | mouse/touch/pen events |
| 2 | Key | key down/up events |
| 3 | Composition | IME composition start/update/end |
| 4 | Text | committed text input |
| 5 | Focus | focus gained |
| 6 | Blur | focus lost |
| 7 | Wheel | wheel/trackpad scroll |

### Pointer event body

```
offset  size  field
0x10    f64   x
0x18    f64   y
0x20    i32   button
0x24    i32   buttons
0x28    i32   modifiers     // bitmask: 1=Shift,2=Ctrl,4=Alt,8=Meta
0x2C    i32   pointerType   // 0=mouse,1=pen,2=touch
0x30    i32   clickCount
0x34    u32   reserved
```

### Key event body

```
offset  size  field
0x10    u32   keyIndex
0x14    u32   codeIndex
0x18    u32   modifiers     // bitmask: 1=Shift,2=Ctrl,4=Alt,8=Meta
0x1C    u32   repeat        // 0/1
0x20    u32   location      // KeyboardEvent.location
0x24    u32   isComposing   // 0/1
0x28    u32   textIndex     // optional string index or 0xFFFF_FFFF
0x2C    u32   reserved
```

### Composition event body

```
offset  size  field
0x10    u32   phase         // 0=start,1=update,2=end
0x14    u32   dataIndex     // string index
0x18    u32   reserved0
0x1C    u32   reserved1
```

### Text event body

```
offset  size  field
0x10    u32   dataIndex     // committed text
0x14    u32   reserved0
0x18    u32   reserved1
0x1C    u32   reserved2
```

### Focus/Blur event body

```
offset  size  field
0x10    u32   relatedIndex  // optional related widget id or 0xFFFF_FFFF
0x14    u32   reserved0
0x18    u32   reserved1
0x1C    u32   reserved2
```

### Wheel event body

```
offset  size  field
0x10    f64   deltaX
0x18    f64   deltaY
0x20    u32   deltaMode     // 0=pixel,1=line,2=page
0x24    u32   modifiers     // bitmask: 1=Shift,2=Ctrl,4=Alt,8=Meta
0x28    u32   reserved0
0x2C    u32   reserved1
```

---

# Integration Notes

- The UI event batch is returned by `KERNEL_OP_UI_POLL` (see `doc/wasm/kernel-request-abi.md`).
- The VDOM tree payload is passed to `KERNEL_OP_UI_RENDER`.
- Text measurement uses `KERNEL_OP_UI_MEASURE_TEXT` and is backend-defined (DOM/Canvas/WebGL).
