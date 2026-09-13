# Source origins of the cold initializers

The separate xload witness supplies a source-module origin for all 133 anonymous cold initializers identified in Claude's sixteenth audit. It reuses the reviewed native FASLs and temporarily observes the existing cross-loader in a disposable process. No new compiler patch or full build is needed.

| Result | Count |
| --- | ---: |
| Initializers joined to an actual queue insertion and boot execution | 133 |
| Source modules | 31 |
| Initializers with a retained compiler source context | 131 |
| Initializers without a source range | 2 |
| Analysis controls rejected | 20 |
| Native omission / abort-restoration controls passed | 2 |
| FASLs unchanged | 164 / 164 |

The two missing ranges are queue entries 65 and 106, from `level-0/nfasload.dx64fsl`, at initializer opcode byte offsets 26416 and 44972. Their module provenance is established; their exact source contexts remain unavailable. The other 131 ranges are compiler contexts and need not represent one original form per thunk.

## Why the positional join is justified

The witness captures the original xload reader's completed queue insertion, including the FASL filename, lfuncall opcode offset, target function word, source filename and source-note data. It checks that each invocation added exactly one head cons with the prior queue as its tail. U1 reverses this list once before saving it. The insertion sequence must equal both the resulting host list and the target list read from the image immediately before writing.

The runner then boots that same image with the previously reviewed boot recorder. Its complete event stream is identical to the retained boot stream after replacing only the declared disposable archive root. Each queue position therefore has a witnessed insertion and a witnessed execution under the same ordered, byte-identical FASL inputs. No anonymous function name is used as a join key, and equal queue lengths alone would not suffice.

All 133 opcode offsets match real lfuncall bytes. Source filenames agree with their FASL modules. For the 131 source contexts, the reader validates the source-note structure and class cell, and retains the target words and decoded range. The joiner independently decodes those words and checks byte bounds against the exact corresponding source. The two intentionally changed L0 sources come from the reviewed observation patch, materialized as data; the U1 source archive used by xload remains unchanged.

## Verification and limits

The [fixture](../../../tests/wasm/native-census/xload-origins/README.md) restores the three original dispatch/function objects after success and after an injected abort. A native omission removes one observation while retaining the actual queue; the independent queue check rejects it. Twenty analysis controls exercise missing and extra insertions, altered identities and orders, wrong files/opcodes, missing or substituted source contexts, and invalid layouts/ranges. Re-executing the retained analysis in another directory reproduces joins and controls exactly.

Plain and observed boot image bytes differ and are both retained; no image-byte equivalence is claimed. The unchanged FASLs, original shared source, and complete fresh boot-stream comparison establish this observation's stated scope. The earlier full native regression qualification is reused, not claimed as a new run. The original bootstrap and all compiled inputs are pinned.

The [packet summary](../evidence/cold-initializer-origins-summary.json) records the execution and verification. Original development errors are retained: loading xload outside development mode, missing compile-time FASL definitions, a malformed observer form, treating a structure's class cell as a symbol, and attempting to save a boot image through command-line evaluation instead of U1's stdin recipe. They are separate from the final passing run.

[Claude's seventeenth audit](claude-review.md), committed at 079c14d7, reproduced the native witness and found no defect. It closes the source-origin finding. The [boot graph integration](boot-integration.md) now attaches all 133 boot identities to their source modules, while preserving the two null ranges; Claude's eighteenth audit reviewed that integration without defect. The complete LL15-b/c graph, target-source traversal, reviewed seeds and dynamic-call bounds, and remaining lowering/import/store classifications remain open. Stage 0 stays at 28 accepted and 20 missing required records.
