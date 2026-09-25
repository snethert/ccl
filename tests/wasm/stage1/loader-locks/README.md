# LOADER: native lock boundary and the first common level-0 file

Proposal over SET-PACKAGE (`efb21e66`), whose shared changes are still under
review. HOSTFM-P2's amended adoption is recorded at `99969288`. This packet
does not integrate either proposal or claim BOOT0, target LOAD or file credit.

The real ordered `cross-xload-level-0` entry now compiles **l0-aprims.lisp**,
with all four compiler results checked, into 26 top-level modules. Its next
stop is **GENERAL-AREF2 in l0-array.lisp**. The two target-directory files are
compiled separately through the existing directory compiler, as in SET-PACKAGE;
they are not misreported as an ordered three-file compiler prefix.

The complete three production FASLs are cross-loaded together after their
sources are deleted. The target executes their cold-load initializers, including
l0-aprims' package-lock allocation and semaphore predicate registration.
Additional complete definitions from seven source files supply the incomplete
image's package, symbol and lock dependencies. Their exact assembled source and
origin list are retained; those seven files receive no whole-file credit.

## Design and scope

CCL's public lock constructors, accessors and wrappers remain unchanged. The
single-Worker implementation replaces native rwlock pointers with traced pairs
of owner token and signed depth: negative for readers, positive for recursive
writers. It supports recursive acquisition, one-reader promotion, acquisition
flags and ordinary WITH-READ-LOCK/WITH-WRITE-LOCK cleanup. A wait for another
owner, read/write conflict or promotion with multiple read acquisitions refuses
before altering lock state. The profile has one exclusive Worker and scheduling
disabled; this is not a concurrent D5 rwlock implementation.

Five native boundaries have explicit failing Wasm entries: native system-lock
revival, semaphore creation, both native C-string pointer helpers and disposable
macptr allocation. They never return invented handles or apparent success.
`dispositions.json` names their consumers and open obligations. In particular,
RESTORE-LISP-POINTERS remains a live potential consumer of revival: these refusals
do not discharge its startup dependency or prove the absence of native handles.
Foreign-Wasm support scheduled after boot1 is a different interface.

Only two proposed shared files change, under `files/`. All native branches stay
in place. The compiler, image installer, collector and D2 implementation are
the unchanged SET-PACKAGE proposal. Runtime locks are transient; saving them
in an application image is not qualified.

## Verification

Four fresh runs cover both heap/table placements, with and without extra moving
collections: **262 modules, 18 initializers, 32 native-equal rows**, with one
allocation-triggered collection in each plain run and 51 collections in each
extra-collection run. There are 33 controls per run. An additional directed
omission of only the package-lock initializer is caught by the package-lock
observation. Native comparisons include actual package locks, fresh independent
locks, recursive readers/writers, promotion, acquisition flags, THROW cleanup,
allocation while write-held, and a global held lock across collection. Allocation
forces collection even without the extra-collection switch; retired space is
poisoned. Errors unwind through ordinary lock cleanup. Refusal controls check
preserved lock state and restored TCR fields, and three exact single-clause
deletions demonstrate that owner/depth coherence and both fixnum-type guards are
independently observed. Numeric non-fixnums isolate the type guards; another
valid vector isolates state identity; an oversized vector isolates exact length.
The vector-kind guard is also enforced by the subsequent checked SVREF accesses.
Errors use the declared early service; class-mode condition identity is not
claimed by this incomplete loader image.

Fresh R6/R6a passes 21,843 native tests, restores all 164 FASLs, and compares
45 identical plus 119 decoded-equal FASLs. Both changed files read identically
under all 17 existing-target profiles (34 comparisons); an inverted reader guard
fails. The unchanged package-lookup reader proof is inherited by exact identity.
The complete proposed source set passes 26,048 fresh compiler comparisons.
The Git-free different-path replay compares FASLs, heaps, static bytes, code
sets, D2 binaries/templates and all target observations exactly.
There are 801 byte-identical artifacts in that replay.

One native limitation is retained: promoting an already write-held lock returns
NIL, then its next unlock times out. A separate pinned native probe records
WRITE T and PROMOTE-ALREADY-WRITING NIL before the timeout. That sequence is not
a passing native comparison. The target's already-writing promotion branch is
not credited as native-equal. No native source is changed to hide the result.

The sibling evidence packet's summary records final counts. Accepted production
files remain **0/0/0**, original definitions **575/535**, ledger **21/12**.
Both this packet and SET-PACKAGE require adversarial review before integration.

## Reproduce

```sh
python3 tests/wasm/stage1/loader-locks/run.py /private/tmp/ccl-work/codex/loader-locks-run/run
python3 tests/wasm/stage1/loader-locks/exercise.py /private/tmp/ccl-work/codex/loader-locks-run/run
python3 tests/wasm/stage1/loader-locks/initializer_control.py /private/tmp/ccl-work/codex/loader-locks-run/run
python3 tests/wasm/stage1/loader-locks/readers.py /private/tmp/ccl-work/codex/loader-locks-readers/run
python3 tests/wasm/stage1/loader-locks/qualify.py native /private/tmp/ccl-work/codex/loader-locks-native/run
python3 tests/wasm/stage1/loader-locks/qualify.py corpus /private/tmp/ccl-work/codex/loader-locks-corpus/run
python3 tests/wasm/stage1/loader-locks/replay.py /private/tmp/ccl-work/codex/loader-locks-replay/run /private/tmp/ccl-work/codex/loader-locks-run/run
```

The replay command makes a Git-free source snapshot, including this proposal,
then invokes its drivers there. Drivers themselves do not need Git. Outputs
must be new directories; leases protect active work. `packet.py` retains one
bounded pack and references unchanged predecessor evidence. Intermediate
failures and the native timeout remain diagnostic evidence, never successes.
