# Starting-image body witnesses

This is an observation of the **original bootstrap image**, not the later
traced image or a reconstruction of the rich build's final heap. It reuses
the exact r4 observer and reviewed in-memory installation in disposable U1
processes. No shared source file, FASL, saved image or kernel is changed.

The rich build reset `dx86cl64.image` from the pinned bootstrap archive before
starting observation. Its initial function inventory walks all heap areas and
reverses the result. The complete read-only region comes first. A fresh native
session reproduces those first 14,720 event rows byte-for-byte: the snapshot,
inventory entry and all 14,718 read-only function records. The remaining
session-created functions and binding inventory differ. They are retained,
reported as different, and never joined by matching numeric IDs or names.

`image.py` independently reads the bootstrap trailer, image header, five
section descriptors, page alignment, managed-static bitmap and read-only
object headers. It is a bounded reader for this exact Darwin x8664 profile:
ABI 1042, platform flags 83, 4 KiB pages and the ten object classes present in
the read-only region. It refuses other profiles/classes. No image format or
native offset is being adopted for Wasm.

The native exporter uses U1's ordinary read-only heap walker. Every function's
ordinal, ID, address and word boundaries must match both the original event
record and the independently decoded image object. This requires the recorded
zero-bias mapping; another mapping is refused, not normalized. For the 4,373
requested functions in that region, it copies the complete function payload,
including all immediate words, using the same primitive as U1 `%COPY-FUNCTION`.
Every byte must equal the corresponding image-file span. Native and disk
walkers thus check each other; matching names are not an identity rule.

The witness names **serialized image bodies** belonging to the old code IDs.
The old execution's live addresses and relocated pointer bytes were not
recorded, and are not reconstructed by this claim. The input image, unchanged
kernel and complete ordered read-only replay supply the identity connection.
The source-note end positions are also exported; 4,130 selected functions have
source ranges. Those are metadata for the next source traversal, not proof
that a newly compiled source body is equivalent to the retained native code.

`analyze.py` derives 501 literal-slot references to other functions in the same
read-only image region. It checks the actual pointer word and slot against the
native address map and the original observer's function-literal list. These
are object references, not proof of executed calls. Other literal kinds and
references outside the read-only region are not decoded as callee bounds.
The entire node suffix remains available in the retained payload and original
image, so those omissions do not erase data.

Twenty-four controls refuse changes to image structure, region, replay IDs,
addresses, instruction bytes, immediate words, requested membership, body
boundaries, source-IR credit and the unresolved worklist. A positive control
changes a dynamic descriptor after the anchored prefix and requires that it
cannot alter any joined body. The producer runs two native sessions; the
verifier checks all retained bytes and runs one more fresh native session.

From the repository root:

```sh
python3 tests/wasm/native-census/resident-bodies/run.py \
  --evidence /Users/buildsomething/Source/ccl-evidence \
  --work /tmp/ccl-resident-bodies-work \
  --output /tmp/ccl-resident-bodies-output
```

The verifier takes `--packet`, `--evidence` and a fresh `--work` directory.
It compares all three analysis outputs byte-for-byte and the complete native
read-only export by value. The full initial inventories are intentionally not
claimed equal. The finalized packet keeps original failures, references the
pristine input trees and retains identical repeat exports once.

No census graph edge is marked complete by this witness. The 5,007 unresolved
source/IR body obligations are unchanged: 4,373 now have concrete native image
bodies and 634 still need other heap/build witnesses. LL15-b/c, all 1,562
computed-call bounds and target qualification remain open.
