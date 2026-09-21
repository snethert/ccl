# Bootstrap member witnesses and execution

**301 original definitions execute and match native (+49); 290 have a non-NIL
witness (+97).** This proposal targets execution after audit 148: member witnesses first, then
previously unexecuted closed definitions, then reader environments. It changes
no shared source. The final counts are in `execution/summary.json` and
`execution/member-witnesses.json`; compilation and execution remain distinct.

The compiler proposal uses the integrated backend directly, with one selection
step: typed NUMCMP and zero-EQ operations select the existing `%I<>` and
`%IZEROP` emitters. Both now have source-emitted, executed witnesses and focused
wrong-sense controls. The architecture supplement supplies the D1 lock and
array-header constants missing from the integrated target. These are the
corresponding 32-bit native constants, not host 64-bit values.

The runtime proposal changes two existing inventory predicates to admit
nonempty ISTRUCTs of general length. `library/lispequ.lisp` defines `%istruct`
as a node gvector whose first field is a registration cell and whose remaining
fields are tagged values. Both the moving collector and pinned-image owner
trace every field. Empty objects still refuse. The focused check moves every
field for lengths 1, 2, 3, 4, 6, 8, 14 and 33 at both placements, and checks empty
object refusal and preservation. Constructor results also move in the native
comparison corpus. No new C or JS runtime service is introduced.

Member recipes use real native arrays, locks, floating complexes, null/dead
macptrs and canonical ISTRUCT registration cells. Other predicates receive
native-allocated tagged layout fixtures. These establish member recognition,
not initialized CLOS, thread, stream or package subsystems. Locks omit their
host kernel pointer. Scalar complexes and macptrs are pinned; this packet does
not broaden the collector's raw-object allowlist. Pinned node fields are
explicit roots, so their heap children move. Generated constructor results are
allocated in the moving heap, including environments, type records and
restarts. The old negative and boundary recipes remain alongside new members.

Per-case global cells are initialized from explicit portable values on both
sides. Native DEFGLOBALs cannot be PROGV-bound, so the disposable native oracle
saves/restores their real cells with UNWIND-PROTECT. It compares the resulting
global state as well as returned values and argument mutations. Configuration
functions do not claim their host effects: for example GC-VERBOSE's tested
behavior is updating the configuration bits, not printing from a running GC.

`EXTENDED-CHAR-P` always returns NIL in this CCL source. The NIL-only report also
retains the remaining empty-state symbol recipes and actual no-op functions;
none is presented as a positive member witness.

The six additional source refusals cover SIGNAL arity, unsupported condition
classes, odd/unknown initargs, condition-reader arity and the unsupported
bit-vector AREF kind. `%COPY-U8-TO-STRING` and `%COPY-STRING-TO-U8` retain their
executed tests. SYMBOL-NAME's one-token reader-conditional change is already in
the accepted integration, bound by its R6 source-location evidence; this packet
adds no CCL source edits.

## Reader environment and limits

The target worklist now evaluates the files' own compile-time DEFCONSTANTs in
`l0-bignum32.lisp`, `l0-float.lisp` and `l1-cl-package.lisp`. This resolves their
three reader failures without rewriting DEFUNs or skipping failed forms.
The parsed lower bound grows from 1,919 to 2,005 definitions, with 1,574 admitted
(previously 1,522). Historical admission stays 1,864/2,492. Other compile-time
effects are not executed by this inventory. Nineteen files
still stop at a foreign function, variable or type lookup. Their exact paths,
offsets and messages remain in `worklist-throughput.json`; the denominator is
still explicitly incomplete. No Darwin constants or foreign-interface database
are substituted for a Wasm provider.

Two additional recipes exposed declared limits and remain uncredited:
`%PATH-MEMBER` reads beyond a string's logical end before its loop termination
test, which the target's checked character load refuses; `%SET-SIMPLE-ARRAY-P`
returns a raw header flag word containing a target-specific subtype. The latter
needs a representation-aware oracle, as does `%ARRAY-HEADER-SUBTYPE`. Neither
is silently labelled a native match. Development records retain the attempts.
The remaining closed definitions without qualified environments are listed in
`execution-frontier.json`. This is not completion of LL15 or dependency closure
of the real startup image.

## Replay

From a checkout of this commit:

```
python3 tests/wasm/stage1/bootstrap-witnesses/packet.py verify \
  --packet ../ccl-evidence/2026-09-21-stage1-bootstrap-witnesses-r1 \
  --output /tmp/ccl-bootstrap-witnesses-verify
```

The proposal has a fresh native R6/R6a build. Existing native tests and reader
qualification are reused only against exact qualified FASL, snapshot and source
hashes. Every new native input is re-executed on replay. The retained verifier
also reruns generated execution, focused scanner checks and fault controls.
Acceptance and integration await Claude's review. No additional ledger credit.
