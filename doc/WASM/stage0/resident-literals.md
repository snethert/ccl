# Resident dispatch references — 14 September 2026

Status: executed diagnostic; reviewed by Claude's fifty-second audit at `0d4a9b04` without defect. No gate credit.

The 465 unannotated initially resident prototypes now have explicit
function-reference edges in the census. Their recorded literals lead to a small
set of dispatch machinery rather than 465 unrelated source bodies. This is a
dependency join, not proof that every object is a generic function or that its
possible methods have been bounded.

| Referenced read-only function | Resident prototypes |
| --- | ---: |
| `%%ONE-ARG-DCODE` | 275 |
| `%%NTH-ARG-DCODE` | 85 |
| `%%1ST-ARG-DCODE` | 57 |
| `%%1ST-TWO-ARG-DCODE` | 45 |
| `%%0-ARG-DCODE` | 1 |
| `MAKE-INSPECTOR` method | 1 |
| `DESCRIBE-OBJECT` method | 1 |

The last method references one further internal function. All eight targets
have reported source extents in U1's `level-1/l1-dcode.lisp` or
`lib/describe.lisp`. The packet retains those exact extents, including the
internal function's narrower range. They are source annotations, not a claim
that native bytes establish complete IR dependencies.

## Identity and graph scope

The join uses the original first-descriptor event bytes retained by the
[body-origin worklist](body-origins.md). Those events already record each
prototype's immediate function references. Targets resolve through the complete
read-only prefix anchored by the [starting-image witness](resident-bodies.md).
The different dynamic suffix from that witness's fresh process is never used.
An unsupported target identity causes refusal rather than a name-based guess.

The compact delta adds 466 observed reference edges, six code nodes absent from
the previous graph and six explicit unresolved body obligations. The other two
targets already have code nodes and open body obligations. No prior record is
changed. The composed graph has 369,586 nodes and 1,089,809 edges; structural
validation passes. Its unresolved-edge diagnostic rises from 31,091 to 31,097
because the six newly exposed bodies are now accounted for.

These are initial-inventory references, not an exhaustive call graph. A
function-valued literal can be data, dispatch can change later, and native
callable construction still needs a witness. The 5,007 earlier body obligations
remain open, along with the six newly exposed ones; none of the 1,562 open
computed calls is closed. No widening family or excluded-module boundary is
changed. Swink remains outside the browser port, with no implementation task.

## Verification and next work

The [runner and controls](../../../tests/wasm/native-census/resident-literals/README.md)
replay four deterministic outputs and reject 24 damaged variants. Full-record
comparison covers additions as well as omissions and prevents an earlier
unresolved body or seed from being silently changed. The fresh dynamic suffix
can be replaced with invalid JSON without changing the result. Both source
files equal U1. No native execution, shared-source edit, accepted-envelope
rehash or historical archive scan was needed.

The first producer attempt compared a canonicalized event hash with a retained
raw-line hash and refused at `ORIGIN_EVENT_JOIN`. Its run record, failure and
executed sources are retained. The correction compares the original raw bytes.

Next, witness callable construction and method/dispatch registries behind these
references, then join their actual body dependencies. The sixteen observer
wrappers and 153 later installations remain separate provenance worklists.
LL15-b/c stay open and the project ledger stays **40 accepted, 8 missing,
0 unreviewed of 48**. This diagnostic awaits independent review.
