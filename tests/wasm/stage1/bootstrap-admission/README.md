# Bootstrap admission, execution and foreign boundaries

**382 original definitions execute and match native (+33); 355 have a non-NIL
return witness (+32).** The real 57-file worklist admits **1,983 of 2,231 parsed
definitions**, up from 1,685 of 2,145. Forty-four files read completely, up from
42. This remains a lower bound, not a complete bootstrap or LL15 qualification.
No proposed compiler or CCL source is integrated by this packet.

Audit 152's execution evidence was accepted separately at `cf721c0a`. Its
source proposal was held. This packet carries that execution forward, fixes
the foreign-source scope, and implements the requested admission work.

## Compiler and execution

The proposal edits the existing dispatcher and binding emitter. It adds no C
or JS runtime service and no source rewriter. CCL's own source passes through
its front end, including macros and declarations.

- Sequential `&AUX` initialization and CCL's `&LEXPR` argument convention. The
  latter uses a rooted, reversed stack argument frame and returns the primary
  value, including NIL for zero values, as the pinned native compiler does.
  Capturing that stack descriptor is refused. Ordinary multiple values remain
  unchanged. CCL's own variadic arithmetic and logical definitions now run.
- Global `SETQ`, `LIST*`, `VECTOR`, dynamic list/vector allocation, `NTH-VALUE`,
  `LOGBITP`, target shifts, generic vector access and typed integer-vector
  access. Operands survive later allocating operands and collection. Allocation
  retries reload roots after a real collection. Padding is zero.
- The target architecture now uses the 32-bit CCL array-type mapper. This
  preserves unsigned-word string views used by `%SCHARCODE`, instead of
  silently changing them into character reads. Signed and unsigned 32-bit
  reads box values outside the target fixnum range minimally.
- Primitive self-calls in top-level native arithmetic definitions use the
  same numeric lowering as ordinary calls. Otherwise unary `-` and binary
  `LOGXOR` inside their own definitions recurse indefinitely. Local functions
  retain their ordinary self-call path. LOGXOR uses the existing rooted logical
  operation helper, with the same fixnum-only domain as LOGAND/LOGIOR.
- All 17 prior compiler TYPE-ERROR crashes came from calling a missing native
  FFI expansion hook. They now refuse `NATIVE-FFI-EXCLUDED`. The remaining
  environment diagnostics are retained: 36 compile-time program errors and
  32 simple errors. They are not counted as successful compilations.

New originals include `+`, `-`, `*`, `/`, all six numeric comparisons, LOGAND,
LOGIOR, LOGXOR, MAX, MIN, VECTOR, GETF, SETPROP, PLISTP, PL-SEARCH, plist and
alist helpers, byte-order readers and array predicates. `progress.json` lists
all 33 and carries the remaining input dependencies forward.

The run has 3,334 rows and 13,336 target comparisons: 13,248 native-compatible
comparisons, four previously declared signed-zero differences, and 84 explicit
host-protocol comparisons. There are 6,668 collections between calls and 766
inside calls, including 96 allocation-retry collections. The retry import in
this fixture is a controlled collector callback: it reclaims dead objects and
refuses if still short. It is not another qualification of production owner
identity or memory growth. The runtime and collector bytes are unchanged.
Eighty-eight checked access/allocation refusals also assert TCR restoration;
failed stores and malformed allocation regions are checked before publication.

`admission.json` names every source-emitted, executed operator witness.
`%AREF1`/`ASET1`, REALPART/IMAGPART/COMPLEX route to ordinary Lisp dependencies;
the new dispatch for these and `%SLOT-UNBOUND-MARKER` is not execution credit.
Native function-immediate reflection is still owed: NTH-IMMEDIATE and its setter
now refuse `FUNCTION-IMMEDIATE-LAYOUT`, with directed admission cases. Native
code/immediates cannot be read from D1 callable metadata by changing an offset.

Domains stay explicit. Dynamic allocation covers simple vectors, strings and
u8 vectors, plus lists. Generic UVREF/UVSET covers those same vector kinds.
Typed access additionally covers signed 8/16/32, unsigned 16/32 and fixnum
vectors. Wide reads box; typed stores require a representable fixnum in the
field's range. Other raw kinds, escaping LEXPR, bignum logical operands,
nonintegral integer division and general rational arithmetic are not claimed.
The admission count does not establish these argument domains or callee closure.

## Foreign source and host routing

All 409 sites remain in `foreign-sites.json` and its table. Of these, 124 are
excluded with their enclosing definition, 169 remain under existing platform
conditionals, 61 use one of 31 explicit target protocol constants, and 55 are
active unresolved function calls. No active foreign constant or type read
remains. Both original module lists retain `linux-files.lisp`.

The proposal removes the 19 excluded-subsystem constants identified in audit
152, plus eight boundary constants for fcntl, poll, fpathconf and sysconf.
Native processes, credentials, signals, terminals, sockets, mappings and dynamic
libraries get `#-wasm32-target` on their calling definitions. They do not get
fake protocol constants or provider obligations. `foreign-boundaries.json`
names every excluded definition and the decisions for the boundary constants.
Remaining callers of excluded definitions are open dependencies, not successful
stubs. File-provider, memory-operation, math and clock dependencies remain named.

The target OS routing prototype compiles all nine records. New generated
callers exercise cold and warm CPU-count caching, semaphore wait and timed wait.
Each is checked against independent protocol expectations and the same target
Lisp run on native CCL. These are excluded from the original-definition count.
The prototype is not installed in the module list. Its special-variable alist
is fixture plumbing, not a production capability boundary. Production requires
owner-sealed capabilities and a scheduler contract; browser main-thread blocking
waits are not admitted. No live OS-provider or browser-execution claim is made.

## Native qualification and replay

The fresh native R6/R6a build passes 21,843 tests, keeps 146 FASLs byte-identical and restores all 164. Edited native files must
have identical executable bytes and non-location data under the adopted
source-location allowance. The 17 existing target readers are compared at every
substitution, with exact inverse edits proving all surrounding bytes unchanged.
This is a compositional proof, not a full foreign-profile file-read claim.

Conditionalizing a DEFUN can remove its source note, not just move its span.
The written comparator records bounded notes, parent links, location directives,
and PC maps. It permits an otherwise empty debug-info slot and its presence bit
to disappear only when its properties consisted entirely of these location
records. It compares every other constant, property, bit and code byte. Three
controls reject a changed code byte, a non-location bit and a callee identity.
The first comparator failure and the exact original files are retained.

```sh
python3 tests/wasm/stage1/bootstrap-admission/run.py /tmp/admission-run
python3 tests/wasm/stage1/bootstrap-admission/packet.py verify \
  --packet ../ccl-evidence/2026-09-21-stage1-bootstrap-admission-r1 \
  --output /tmp/admission-replay
```

Retention checks source copies against the committed fixture. Verification
recompiles and executes the corpus, replays the reader proof and decodes the
retained native binaries again. The expensive native test build is reused only
by exact proposal identity. Necessary development failures are retained once.
Integration and slot credit remain subject to independent review and acceptance.
