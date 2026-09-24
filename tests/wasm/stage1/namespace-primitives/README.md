# NSL-1 generated file primitives, R2 (audit 176 follow-up)

Files cross-compiled / cross-loaded / target-loaded: 0 / 0 / 0.
Twelve generated definitions execute; 196 native-equal comparisons and four
explicit bounded-read comparisons pass. This is a
file-primitive proposal, with no new LL15 credit or increase to the accepted
575/535 original-definition floor. Files cross-compiled to deliverable bundles,
cross-loaded, and loaded on the target remain 0/0/0.

`w32-files.lisp` supplies the target definitions of `FD-OPEN`, `FD-READ`,
`FD-LSEEK`, `FD-CLOSE`, `FD-SIZE`, `FD-TELL`, `%REALPATH`, `%UNIX-FILE-KIND`,
and the read-only `FD-WRITE` refusal. It belongs after `l0-io` and the operating
system definitions in the target load order. The definitions are compiled by
CCL's file compiler with the integrated backend and installed at their real CCL
symbol cells. Three generated callers exercise multiple values, argument
side effects, and close during THROW cleanup. They are observers, not native
library replacements. No compiler or shared runtime/Lisp source is edited.

The native side calls the untouched pinned CCL primitives. A small native
adapter copies octets between the observer's vector and a stack macptr because
native `FD-READ` has a pointer ABI. The observer uses an unsigned-byte-8 vector. The client also admits the
seven qualified D1 integer-vector layouts by their byte extent, starting at byte
zero, for the stream consumer ABI. It rejects node vectors and invalid extents.
There is no target macptr. The sibling [consumer packet](../namespace-consumers/README.md)
adds the IO-BUFFER branches and executes OPEN/PROBE-FILE/TRUENAME; bundle
loading remains a later loader task.

The internal B leaf accepts `(operation a b c)` from a generated root frame.
It validates arguments before publishing a request. A stable 8 KiB descriptor
uses the D5 lifetime/generation/wakeup pattern, with a maximum 4 KiB UTF-8 path
and 8,128 response bytes. This larger descriptor is a new, isolated bridge
proposal; it does not silently replace the accepted Stage 0 256-byte descriptor.
The owner receives only copied path bytes and scalar handles, never moving
heap addresses. The Lisp Worker marks itself FOREIGN and waits; the owner
services its private namespace session and publishes completion atomically.
Only the Lisp Worker writes its TCR. It resumes RUNNING, performs the admitted
collection, reloads its rooted byte vector and copies the reply. The namespace
provider and its admission rules are the unchanged sibling proposal.

This implements the scheduler-disabled single-Worker profile. It does not add
nested requests, interrupt delivery, cancellation or JSPI. Stage 0's interrupt
and nested-D5 evidence is separate; it is not execution evidence for this new
bridge. An owner timeout or malformed completion is a checked bridge refusal;
callers must not retry an indeterminate host operation. A valid negative errno
is an ordinary Lisp return. No condition registry is projected: the fixture's
unused legacy condition imports are NIL; malformed bridge operands are checked
refusals, not claimed TYPE-ERROR objects.

The file provider is read-only. `FD-WRITE` and write-open return `-30`; these
policy rows are asserted separately from native comparisons. Read counts may
be short (at most 8,128 bytes); zero at or beyond EOF is success. Seek offsets
and positions are target nonnegative fixnums, with signed fixnum relative
offsets; overflow refuses with `-22` before changing the position. File sizes
fit the provider's 64 MiB byte limit. Paths are virtual scalar strings, not host
paths. The provider's two disclosed `%REALPATH` traversal differences remain
in the parent packet; this unit does not silently broaden its path domain.

Four fresh Workers cover 8 MiB/2 GiB placements, each with movement disabled
and enabled. Each semispace is 32 KiB; every allocation asserts that it did not
trigger implicit collection, so the disabled runs remain nonmoving even with
the three large read buffers. Across them: 240 requests, 120 real collections with the old heap
poisoned, 196 native-equal comparisons including complete buffer post-state, and 24
generated refusal checks comparing all 64 TCR words. Every generated definition
executes. The host also refuses two stale completion identities per request
without writes. Forty-nine directed admission/publication cases cover the
bridge; five altered implementations fail the complete generated caller check.

O-71: a 9,000-byte file witnesses the boundary. A native 8,129-byte read returns
8,129; the target returns 8,128, leaves the last destination byte unchanged,
and reports position 8,128. These four rows are explicitly policy comparisons,
not native-equal credit. After seeking back, an exact-cap read, the remaining
872 bytes, position and EOF match native. Removing the host read cap now fails.
O-72: the target `%REALPATH` substitutes `"."` for an empty simple string; the
owner resolves it against the manifest cwd. Native `%REALPATH ""` runs after
setting its cwd to the matching physical directory and returns the same path.

`audit176.py` also checks the historical R12 integration at `4730cbae` (O-69),
rejects R13 as that identity, and replays the provider in a nested output path
(O-70). All five provider result records equal their retained R1 versions.

The compiler is built directly from the five integrated registration/compiler
files over disposable pinned U1 sources. The small cold compilation takes about
two seconds here. No multi-gigabyte session or corpus copy is required. WAT
assembly uses the shared content-addressed cache. Collector, integer and float
services are the integrated implementations, rebuilt without edits. Native
R6/R6a is reused by unchanged product-source identity; this proposal introduces
only a target file not yet in any product module list.

```sh
python3 tests/wasm/stage1/namespace-primitives/run.py \
  /private/tmp/ccl-work/codex/namespace-primitives-r2/author
```

R2 observations and failures are retained within the namespace consumer pack.
Run from its source commit beside `ccl-evidence`. Retention verifies
source identity, saves records, probe inputs, original failures and hashes,
and deletes the output. Rebuildable modules and native trees are not archived.
The checked-in `--reuse-compiled` option is development-only and cannot produce
a retainable run: the author/replay commands compile their own sources.
