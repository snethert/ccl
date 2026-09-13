# Macro and special-operator wrappers in the census

All 1,059 function-cell values previously called opaque now have checked contents and graph dependencies. They are ordinary CCL representations: 1,028 macro wrappers and 31 special-operator wrappers. The earlier label was an exporter omission, not an observed runtime defect.

| Wrapper content | Census dependency |
| --- | --- |
| Macro expansion function | The exact native function object, with a `macroexpand` edge |
| Special-operator symbol | Its symbol identity and the handler found in the saved image's `*nx1-alphatizers*` table, with `compile` edges |
| Shared first slot | The native error path for attempting to apply a macro or special form as a function, with a `run` edge |

The [post-boot fixture](../../../tests/wasm/native-census/boot-wrappers/README.md) reads the retained image. It introduces no startup hook, compiler change, FASL rebuild or saved image. The observation image remains evidence only; implementation still starts from pristine U1.

## Identity and scope

The existing exporter writes and closes its original event stream before invoking an optional extension. The extension shares that export's object map, preserving all original IDs. It records the wrapper slots and function/symbol descriptors in a separate file. A second native reading starts from the original binding events and checks literal slot contents and handler references independently of the wrapper rows.

The wrappers reference 1,043 distinct function identities, including both expansion functions and special-form handlers. One function already has a legacy description; 1,042 descriptions are newly exposed. Reused function nodes must match their complete same-image descriptor. No cross-process or name-only callable equivalence is introduced.

The graph update resolves exactly the 1,059 wrapper-value nodes, adds 1,075 nodes and 2,180 edges, and refreshes the scope gap's explanatory text while leaving that gap unresolved. Seeds, event ordering, cold-origin records and external trace observations remain unchanged. The graph has 329,036 nodes and 818,542 edges. The unresolved-node count decreases by exactly 1,059, from 29,361 to 28,302; unresolved edges remain 17,329. These are census diagnostics, not additional Stage 0 acceptance slots.

Descriptions and handler lookup belong to the saved image after boot. They do not establish historical handler execution or immutable contents at every earlier event. The wrapper targets are now known; their complete body dependencies, target lowering and Wasm implementations still belong to the remaining closure work.

## Verification

The disabled extension and two independent extended exports all reproduce the reviewed 52,441-event stream byte-for-byte. The wrapper files from both extended exports also match exactly. The image and kernel copies remain unchanged.

Three native controls reject invalid vector size, wrong dispatch value and invalid payload type. Twenty-six analysis controls reject missing or duplicate wrappers, altered payload/handler identities, omitted graph dependencies, incorrect phases, surplus records, changed function metadata and edits to seeds, initializers or trace modules. The independent graph checker derives complete records and edge multiplicities from the literal-slot witness. The full census passes schema and structural checks; the standalone verifier reproduces the retained update and full graph byte-for-byte.

The first analysis run refused the dispatch value because the checker compared a decoded Lisp fixnum with the raw target word. U1's xloader stores the raw `#xc9cd0000000000` word directly; the Lisp value is that number shifted right by three. The correction records and checks both forms against the pinned U1 definitions. The original failed analysis, successful native exports, source and log are retained. No runtime or kernel adjustment was made.

One compact [packet](../evidence/boot-wrappers-summary.json) holds the extension and focused checks, referring to the existing image, base graph and native qualification. It awaits independent review. Stage 0 remains 28 accepted, 20 missing and zero unreviewed required records; no acceptance envelope changes.
