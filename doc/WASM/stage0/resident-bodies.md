# Starting-image body witnesses — 14 September 2026

Status: executed diagnostic; reviewed by Claude's fiftieth audit at `579230d5` without defect. No census acceptance
credit is claimed. The [binding-version join](binding-versions.md) left 5,007
observed prototypes without attached compiler bodies. This step obtains exact
native image bodies for 4,373 of them, from the original bootstrap input.

The rich build did not begin from the later traced heap. Its runner restored
the release bootstrap image before loading the observer. The retained input
archive and unchanged kernel therefore provide the right starting point.
The [new witness](../../../tests/wasm/native-census/resident-bodies/README.md)
replays only the initial inventory and inspects that image in fresh disposable
processes. It changes no shared source file and performs no native build.

| Result | Count |
| --- | ---: |
| Objects independently decoded in the image's read-only region | 94,001 |
| Function objects in that complete region | 14,718 |
| Initial event rows reproduced byte-for-byte | 14,720 |
| Previously unjoined prototypes with native image-body witnesses | 4,373 |
| Prototypes outside this witness | 634 |
| Complete function payload bytes compared with the image file | 3,420,096 |
| Instruction-prefix bytes within those payloads | 3,088,744 |
| Selected functions with reported source ranges | 4,130 |
| Direct function-literal slots joined within the read-only region | 501 |

The image decoder and native heap walker are separate implementations. Every
function must agree in ordinal, address, word count, code boundary and original
inventory identity. All selected payload bytes, including immediate operands,
must equal their exact image-file spans. The join uses the unchanged image and
its complete ordered region; matching display names are not sufficient.

The initial inventory's dynamic suffix **does not reproduce** and is not joined.
The complete read-only region does reproduce; its length comes from the image
headers and native area walk, not an arbitrary common-prefix cutoff. The
exporter is loaded after that inventory, so its own functions cannot enter the
anchored region. The three native sessions reproduce the read-only export.

This establishes serialized body identity, not a reconstruction of the old
execution's live addresses or relocated pointer words. Fresh inspection uses
the recorded zero-bias mapping; other mappings are refused. The bounded image
reader implements only the classes and profile in this native bootstrap.
Those native layouts are not Wasm implementation decisions.

The 501 joins are literal object references, not executed-call claims. Source
ranges identify where to look next; they do not establish equivalent compiler
IR by themselves. No global-binding bound, computed-call bound, Wasm lowering
or required source traversal is closed by exposing these bytes. Accordingly,
the census graph and all 5,007 source/IR obligations remain unchanged.

Twenty-four controls reject corrupted headers, wrong region/identity/address,
altered instruction or immediate bytes, missing/duplicate ordering information,
erased worklists and false source-IR credit. A positive control confirms that
a changed descriptor in the dynamic suffix cannot alter a read-only join.
The verifier reproduces the three analysis outputs byte-for-byte and performs
a fresh native export. Original exploratory refusals and the failed first
producer are retained in one compact evidence packet.

Next, use the witnessed source ranges and complete native payloads to establish
source/IR dependencies. The [subsequent origin worklist](body-origins.md) splits
the remaining 634 into 481 initially resident prototypes and 153 later
installations. They still need separate body/construction provenance; numeric
IDs from a new process must not be substituted for the old ones. The 95 unwitnessed global bindings
and 1,562 computed calls also remain on the census worklist. At this execution,
Stage 0 had
**39 accepted, eight missing and one unreviewed of 48**.
The user subsequently accepted LL13-b, taking the ledger to 40/8/0; this
diagnostic itself receives no gate credit.
