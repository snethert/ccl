# Named libraries and the Lisp foreign API

This Stage 2 delivery adds a product Lisp API, its process-service transport and
resident namespace loading. It is executed, awaiting independent review; no
FMT/LL acceptance or Stage 1 count movement is claimed. Product Lisp adds 50
lines; shared compiler and upstream kernel source are unchanged.

Load `runtime/wasm32/foreign-api.lisp` as an ordinary target bundle after READY.
The names currently live in CCL's internal package; they are not additions to
native CCL's foreign interface or its exported symbols. For example:

```lisp
(let ((library (ccl::open-wasm-library "example")))
  (ccl::with-wasm-buffer (buffer library 16)
    (ccl::write-wasm-buffer buffer octets)
    (ccl::wasm-call library "run" (ccl::wasm-buffer-range buffer) 8 0)
    (ccl::read-wasm-buffer buffer 8)))
```

The embedding constructs `foreignLibraries` from a `createNamespace` instance,
a list of `{path, declaration, imports}`, the owning Worker's FOREIGN boundary,
and an `(i32)` failure tag. It passes that registry, Lisp memory, TCR and collector
owner to `foreignService`, then supplies the returned function as `foreign` to
`processService`. Process operation 15 carries the API request. The fixture
extension only supplies namespace bytes, declared imports and GC observations;
all API dispatch, marshalling, handles and error transport are product code.

`open-wasm-library` names an embedding declaration, not a host pathname or URL.
The registry resolves its namespace path, snapshots declarations and declared
import functions, and reads at most 64 MiB by default in chunks of at most 64 KiB.
Configure the namespace's read limit to permit those chunks. Namespace file
handles close before instantiation, including on failed reads. The lower layer
then admits the exact digest, binary ABI, memory/table limits and initialization.
Repeated opens return one Worker-local instance and never repeat initialization.
Canonical path aliases cannot create a second declaration for the same file.
Failed initialization and explicit close are terminal for that registry entry.
A new registry is a new explicit lifetime, not a hidden retry.

This is the resident named-blob provider on Node and browser Workers. Fetching
blobs or mounting host files belongs to the embedding before registry creation;
there is no filesystem/URL fallback or asynchronous read during a Lisp call.
Mounted-directory mailbox loading and browser generated-Lisp integration remain
unqualified. The namespace itself is an accepted dependency, unchanged here.

`wasm-call` uses the declared binary signature. It accepts signed i32/i64 Lisp
integers, single floats for f32 and double floats for f64, and returns all declared
results as Lisp multiple values. Signed zero, infinities and NaN values are
supported; NaN payload preservation is not promised. Lisp pointers never become
foreign scalar arguments. Declared pointer slots require range tokens from the
same library; the token resolves only to an offset in that library's memory.

Libraries, allocations and ranges use positive Worker-local fixnum tokens of
distinct kinds. Tokens expose no address, never reuse an ID, and have an explicit
per-service limit (default 536870911). Exhaustion refuses before allocation or
range publication. Released/closed tokens remain as lifetime tombstones until
the service is discarded; collector-triggered release and token reclamation are
not implemented. A token belongs to its creating Worker/service and must not be
transferred. These are opaque-by-contract identities, not unforgeable capabilities
or a sandbox against Lisp code with unsafe memory access.

Copies accept simple `(unsigned-byte 8)` vectors. Calls snapshot scalar arguments
before FOREIGN, then reload the rooted request after collection; result boxing
can itself collect and reloads the request again before publication. Byte-vector
copies perform no collecting call. The byte layer still enforces strict UTF-8
where declared, but automatic Lisp string encoding is not implemented.

Checked argument/lifetime/encoding failures become ordinary Lisp errors with
status -1; foreign traps, recoverable exceptions and host-import failures use
-2, -3 and -4 respectively. The error also names its API operation. Owner
admission failures remain fatal owner errors and are not converted into a Lisp
condition granting heap access. Detailed foreign exception objects remain
private to the lower layer; this is not a new condition hierarchy.

`with-wasm-buffer` releases on normal completion, error and nonlocal exit,
preserving multiple values. A release failure on normal completion signals;
during an existing error or nonlocal exit it is suppressed to preserve that
primary exit. After a trap, remaining handles retire without further foreign
releases. Explicit release is idempotent. Audit 196's O-170/O-173 semantics are
specified in the [byte-buffer contract](../foreign-buffers/README.md).

## Verification

Results and exact counts are bound in
[foreign-api-results.json](../../../../doc/WASM/stage2/foreign-api-results.json).
The portable suite runs the real namespace, library layer, service and collector
in Node and Chromium/Firefox/WebKit Workers. It covers two heap/stack placements,
all four scalar representations, moving collections and result boxing collection,
private-memory growth, copying, one-time initialization, checked refusals and
terminal instance lifetimes. Mutants must fail their directed semantic case.
The extra integer range guard is deliberately not counted as independently
mutation-sensitive: lower-layer scalar admission repeats the i32 bound, and
at most two signed limbs already bound i64. Its survivor is retained.

Admission facts supplied by unchanged dependencies are not new independent
claims: `session.open` guarantees a file, namespace sizes are integer byte lengths,
and admitted binary signatures contain only the four scalar types. Unsigned
Lisp words plus misc tag 6 imply the minimum object address. Synthetic malformed
objects check spans, headers and sizes; the service trusts the port's generated
root discipline, not arbitrary host-provided pointers.

The target loads the API and witness through ordinary post-READY `%FASLOAD`.
Twenty rows compare with native CCL using a native model of the fixture library:
full signed integer bounds, floats, copies, aliases, closures, dynamic bindings,
multiple values, nonlocal exits, recoverable failures, traps, destructor traps,
primary error preservation, close and stale handles. The fixture forces moving
GC in initialization, calls, allocation and release, poisons retired space, and
checks all 64 TCR words except the six collector-owned words permitted to move.

The older buffer Lisp witness also replays through the changed boot-driver
extension seam. Its portable suite adds O-171's surviving-handle assertion,
O-172's live-handle asynchronous entry refusal and O-170's refused destructor
entry. The unchanged scalar/owner implementation reuses audit 196's qualification
by source identity. Process-service checks cover the new dispatch, missing
capability and unaltered fatal exception identity. No compiler corpus replay;
it remains deferred until the entire foreign layer is complete.

An initial witness stopped with checked 4 while printing a nonzero double.
A separate literal-only `1.25d0` probe reproduces the same stop with no foreign
API loaded. This unresolved printer frontier is retained explicitly. The final
scalar witness compares the nonzero double with its native literal; portable
checks inspect its exact representation. No float-printer acceptance is inferred.

## Reproduction

Use the verified RAM mounts and the shared compiler cache. From the repo root:

```sh
work=/private/tmp/ccl-work/codex/foreign-api
python3 -B tests/wasm/stage1/loader-target/build.py "$work/boot" --boot0
python3 -B tests/wasm/stage1/loader-target/build.py "$work/level1" --level1
cat runtime/wasm32/foreign-api.lisp > "$work/source.lisp"
printf '\n' >> "$work/source.lisp"
cat tests/wasm/stage2/foreign-api/checks.lisp >> "$work/source.lisp"
python3 -B tests/wasm/stage1/loader-target/build.py "$work/checks" \
  --postimage="$work/boot" --source="$work/source.lisp"
python3 -B tests/wasm/stage2/foreign-api/run.py \
  --boot "$work/boot" --level1 "$work/level1" --checks "$work/checks" \
  --playwright /absolute/path/to/playwright-core/index.mjs \
  --browser-config /absolute/path/to/browser-config.json
node tests/wasm/stage1/loader-target/process-check.mjs
```

Concatenation supplies the unchanged API source followed by its witness in one
ordinary bundle; it does not rewrite either source. Build the older buffer Lisp
fixture with its existing README and run its dependency driver against the same
boot/level-1 products. Retain hashes, results and minimal original failures,
then discard successful compilation products. The finalized evidence pack is
`ccl-evidence/2026-09-28-stage2-foreign-api-r1`.

Next: Lisp callbacks and owner-queued finalization, Lisp string encoding,
browser Lisp/provider integration and multi-Worker D5. O-167 must land before
any multi-Worker admission. No callbacks or automatic finalizers are supplied
by this API.
