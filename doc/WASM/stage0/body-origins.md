# Origins of the remaining native prototypes — 14 September 2026

Status: executed diagnostic; reviewed by Claude's fifty-first audit at `6aaedc7e` without defect. This answers the
nonblocking observation in Claude's fiftieth audit of the
[starting-image witness](resident-bodies.md). The classification reads retained
evidence only; no native process or build is run.

All 634 remaining prototypes are accounted for by their first function
descriptors in the original rich stream, joined by identity to the reviewed
binding histories:

| First observed group | Prototypes | Evidence and next witness |
| --- | ---: | --- |
| Initial inventory, installer source annotation | 16 | Source notes point to the observation install file. Establish wrapper/original-function relationships from that installation; do not treat observer wrappers as pristine implementation bodies. |
| Initial inventory, no source annotation | 465 | Actual resident-function and before-binding records exist. Obtain native callable-object and construction provenance; a CLOS or generated-function subtype must be witnessed rather than inferred from its name. |
| Later installation during ASDF compilation | 152 | First descriptors appear at completed binding-store hooks under compile-initializer entries. Trace the retained source position and initializer into the runtime constructor. |
| Later installation while loading Swink | 1 | `SWINK::READ-SEXP`, code 15717373, is installed at event 2889318 under load-effect event 2889316. Preserve that identity and handle its module/profile boundary explicitly. |

The first two groups total 481 initially resident prototypes; the latter two
total 153 later installations. All 634 remain outside the anchored read-only
body witness. Calling the first group “dynamic at start” would overstate the
evidence: the original inventory spans several heap areas and does not record
an area on these rows. Every worklist record therefore retains an unclassified
heap area.

“First” means the earliest complete function descriptor, not allocation time
or an integer's first appearance in a literal-reference list. The scanner
checks every event's sequence and the complete stream counts. It retains raw
first-descriptor and direct-parent events, exact symbol identities and source
contexts. An installation witness proves the new function-cell value was seen
after its store; it does not identify a complete source/IR body by itself.

The [implementation and worklist](../../../tests/wasm/native-census/body-origins/README.md)
have eighteen rejection controls. A separate replay reproduces all five output
files byte-for-byte. The exploratory report's `resident_before` headline
incorrectly counted empty dictionary entries as residents; its per-row lists
and 481/153 split were correct. The original script/output are retained, and
the producer derives counts from actual row membership.

## Swink profile disposition

The user's supplied Claude research identifies Swink as the native remote-debugger
transport. U1 source confirms the passive socket in `SWINK:START-SERVER`, the
client socket in `CCL::CONNECT-TO-SWINK`, the lazy SWINK provider and both system
registrations. The Cocoa remote client delegates to that same connection path.

The original packet's disposition worklist records unsupported native TCP
transport. Following the user's clarification on 14 September, the
[current worklist, revision 2](../../../tests/wasm/native-census/body-origins/swink-disposition.json)
states the browser scope directly: **omit Swink and its native remote-lisp
clients from the browser port**. There is no Swink implementation, replacement
server, client, socket stub or host-service deliverable. The historical packet
and its six U1 source identities remain unchanged.

The exclusion covers all module bindings, including the 25 initially resident
unannotated prototypes identified by Claude's fifty-first audit and the later
`READ-SEXP` installation. Keep their native witnesses and check that the
required browser startup closure has no dependency on the omitted modules.
If a supported browser entry can request an excluded module, the shared module
loader must report that through its tested unsupported-module path; this does
not require Swink code. Shared stream, CLOS, thread and mailbox-debugger
dependencies retain their own obligations under the [census contract](../contracts/census.md).

No graph edge or profile disposition has been applied by this diagnostic.
The census still needs complete body traversal and call bounds; the ledger
remains **40 accepted, eight missing and zero unreviewed of 48**.
