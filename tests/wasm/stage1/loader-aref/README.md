# General AREF/ASET through the ordered level-0 loader

The [bignum/native-pointer successor](../loader-new-ptr/README.md) extends this
pending proposal through l0-complex and reaches function layout in l0-def.

This proposal follows the accepted audit-180 integration at `33aeb696`.
The ordered compiler now completes **l0-aprims and l0-array** (26 and 41
modules), then stops at **%NEW-PTR in l0-bignum32**. Both FASL pathname and
failure-p are checked. The two target-directory files compile separately;
they are not misreported as the first files in the ordered compiler sequence.

Three product files are proposed under `files/`: the Wasm backend, w32-lap,
and the freestanding collector. They are not integrated. The ordinary CCL
AREF, ASET, %ARRAY-INDEX and displacement-walking bodies remain unchanged.
No existing-target source or upstream native kernel source changes.

## Implementation

The four GENERAL-AREF2/3 and GENERAL-ASET2/3 acode operators call target Lisp
accessors. Those accessors validate the array header and rank, check each
logical subscript, compute its row-major index, follow displacement chains,
and use the existing UVREF/UVSET element boundary. Array, indices and store
value are evaluated once in source order through the ordinary call lowering.
Allocation while later arguments are evaluated retains the earlier operands.

The collector now scans both arrayH (234) and vectorH (242) as tagged-cell
containers. Array headers require a minimum five-cell prefix and a rank
consistent with the header width; vector headers have five cells. Extent
validation precedes the rank read. The data-vector cell is traced through
displaced chains. These checks describe scanner layout, not complete array
constructor semantics. The existing final object-extent check also refuses
truncation, so deletion of the earlier extent conjunct is not claimed isolated.

## Witnesses and limits

The complete l0-array FASL is cross-loaded with l0-aprims and the two target
files after their source files are deleted. The resulting 327-module image runs
19 initializers and 44 native-equal observations in each of four placement and
collection modes, with 8 collections per plain run and 70 per collecting run.
Each run also passes 87 controls (the inherited 33 plus 54 array controls). The incomplete image still needs
selected complete original package/lock dependencies and MAKE-STRING. These
support files receive no whole-file credit. No production body is rewritten.

Native uses MAKE-ARRAY to construct the test inputs. Target fixture helpers
construct the corresponding D1 headers using the existing %GVECTOR boundary;
this is explicitly test scaffolding, not a replacement MAKE-ARRAY. The cases
exercise ranks zero through four, two/three-dimensional read and assignment,
displaced array and vector-header chains, fill-pointer-independent indexing,
simple vectors, packed bits, characters, unsigned 32-bit and signed 16-bit
backings, assignment evaluation order, collection during argument evaluation,
and a globally rooted array whose cons elements survive movement.

Refusals cover negative, upper-bound and non-fixnum indices on every axis for
both reads and writes, empty dimensions, wrong ranks, non-arrays and invalid
bit/character stores. They preserve header/backing contents and TCR fields.
Four exact helper-clause deletions independently expose header-kind, rank,
lower-bound and upper-bound checks. The explicit index type check chooses the
argument error; subsequent checked fixnum operations can also refuse that
input, so these rows do not claim an isolated deletion kill or condition-class
identity in the early loader image. The inherited 33 lock controls remain.

The collector has 46 positive/refusal checks, including the prior owner suite,
movement of each header family with its sole backing/payload references,
repeated collection with poisoned old space, and malformed header refusals.
Three independent shape-guard deletions are killed by their own refusal row.

Fresh R6/R6a passes 21,843 native tests and restores 164 FASLs: 45 are identical
and 119 are decoded-equal. No existing-target reader branches changed. The
compiler passes all 26,048 corpus comparisons. When the allocation-pressure
witness exposed the missing header scanner, the full corpus was executed again
with the new collector, reusing the exact compiled Lisp modules. Both executions
are retained distinctly; the final one qualifies the new runtime. A Git-free
replay at another absolute path compares 1,011 generated Wasm FASLs, heaps,
WAT and Wasm files, plus every observation and control result.
Final driver identities are bound before and after execution and at retention.

General MAKE-ARRAY, floating/complex array backings, statically specialized
SIMPLE-TYPED-AREF2/3 lowerings, saved-image array admission, target LOAD and a
complete boot are outside this packet. The new source remains subject to
Claude's independent review. Accepted production counts **0/0/0**, originals
**575/535**, and ledger **21/12** remain unchanged. O-90's pre-existing duplicate
integer definitions remain a separate cleanup, outside this proposal identity.

## Reproduce

```sh
python3 tests/wasm/stage1/loader-aref/run.py /private/tmp/ccl-work/codex/loader-aref/run
python3 tests/wasm/stage1/loader-aref/exercise.py /private/tmp/ccl-work/codex/loader-aref/run
python3 tests/wasm/stage1/loader-aref/collector.py /private/tmp/ccl-work/codex/loader-aref-collector/run
python3 tests/wasm/stage1/loader-aref/qualify.py native /private/tmp/ccl-work/codex/loader-aref-native/run
python3 tests/wasm/stage1/loader-aref/qualify.py corpus /private/tmp/ccl-work/codex/loader-aref-corpus/run
python3 tests/wasm/stage1/loader-aref/runtime-corpus.py /private/tmp/ccl-work/codex/loader-aref-corpus/run
python3 tests/wasm/stage1/loader-aref/replay.py /private/tmp/ccl-work/codex/loader-aref-replay /private/tmp/ccl-work/codex/loader-aref/run
```

The replay wrapper archives the pinned integration and overlays this proposal;
the producer and execution drivers run inside the Git-free extraction. `packet.py
--help` gives retention inputs. Development failures retain the original missing
lowering, unsupported fixture allocator, missing string support, accidental use
of an acode name as a function, target-reader mutation mismatch, and the original
collector refusal. Retention references regenerated code/listings by hash.
