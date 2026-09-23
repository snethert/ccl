# Wasm32 runtime

`loader.mjs`, `binary.mjs` and `stub.wat` are the accepted single-Worker lazy
installer, updated through the accepted LL10 constants profile using the exact
reviewed bytes.
The Worker owner supplies the trusted catalog, memory, paired tables, exception
tags and synchronous byte provider. The catalog is an integrity authority, not
code signing. The implementation currently imports Node's hashing service.

Compile the paired stubs with the qualified WABT toolchain:

```
wat2wasm --enable-tail-call stub.wat -o stub.wasm
```

`LazyLoader.defer` prepares cold public/internal entries. `host_entry` retains
the public B boundary; compiled calls use the paired internal table directly.
Installation validates bytes and capabilities before publishing either ready
entry. Publication is synchronous within one Worker. Concurrent publication,
browser byte delivery and production image construction remain separate work.

The integration record is
[here](../../doc/WASM/stage1/integration-ll10.json). The
[constants fixture](../../tests/wasm/stage1/constants/README.md) and its reviewed
follow-up retain the executable examples and verification.

The current profile is `wasm32-shared-B-exnref-tail-mv-storage-constants-v1`.
Its function objects occupy 32 bytes, with a tagged shared-pool pointer at raw
offset 24; logical pool index zero is vector offset 4. Owners must provide objects
and catalogs for this layout. Prior-profile declarations are refused. The
[retained layout](../../tests/wasm/stage1/constants/function-layout.json) and
[acceptance](../../doc/WASM/stage1/acceptance-ll10.json) bind the representation.

The accepted [collector core](../../tests/wasm/stage1/collector-core/README.md)
is integrated as `collector.c`, exactly as reviewed. It is a separate owner-installed
Wasm service with imported shared memory, not a lazy Lisp module. The fixture
runner retains its qualified compile flags and owner configuration. Only its
listed layouts and roots are admitted; general poll coverage, allocator retry and memory growth remain open.
The accepted [follow-up](../../tests/wasm/stage1/collector-live/README.md) adds
restart scanning and fixes the reviewed moving-temporary paths. See the
[integration record](../../doc/WASM/stage1/integration-collector-live.json).

The accepted [collector owner](../../tests/wasm/stage1/collector-owner/README.md)
is integrated as `collector-owner.mjs`. It admits memory ownership and roots,
collects before growth and refreshes host views. See its
[integration record](../../doc/WASM/stage1/integration-collector-owner.json).
Internal generated allocation retry remains separate work.

The accepted internal allocation retry is integrated in the compiler and
`allocation-service.mjs`; see [the integration record](../../doc/WASM/stage1/integration-allocation-retry.json).
Retry remains opt-in and the existing lazy profile refuses its owner import.
An assurance may move live data before refusing; invoke generated code outside
an active owner boundary. Raw constructor retry and loader admission follow.

Raw constructor retry and the explicit owner-capability loader profile are now
integrated; see [the integration record](../../doc/WASM/stage1/integration-constructor-retry.json).
A stack guard that signals **never resumes the interrupted reservation**: it
transfers or fails. Frame/binding emitters may hold an unstaged value in a Wasm
local across that guard; a returning handler must not resume it after collection.
Assurance may move roots before refusing, and never executes Lisp or changes
binding-vector shape. Malformed-owner refusals may use code 6 rather than 3.

LL18-a is accepted and integrated; see [the integration record](../../doc/WASM/stage1/integration-ll18.json).
The scanner admits node complex objects and complex-float vectors, but refuses
scalar boxed complex floats and macptrs. Audit 96 independently checked all raw
widths. The accepted literal movement matrix excludes the argument-taking pool
modules and literal-mutation persistence case; the full scope travels with the
acceptance. Owner replay has 40 admission checks; generated retry covers its
omitted standalone generated-boundary check.

The [integer service](../../tests/wasm/stage1/integer-core/README.md) and its
[review follow-up](../../tests/wasm/stage1/integer-core/review-followup/README.md)
are accepted; `integer.c` equals the reviewed source. Its isolated unshared-memory
ABI is not a generated B entry or a collecting owner service. See the
[integration record](../../doc/WASM/stage1/integration-integer-core.json).

`integer-service.mjs` is the accepted single-Worker numeric capability from the
[generated-call unit](../../tests/wasm/stage1/integer-calls/README.md). The compiler
has its opt-in entry, but production loader admission remains separate.

`numeric-capabilities.mjs` binds the integer and allocation capabilities to one
trusted owner, memory, TCR and error tag. The loader admits their exact pair under
`wasm32-shared-B-integer-owner-v1`; invoke generated code outside an active owner
boundary. See the [reviewed composition](../../tests/wasm/stage1/integer-owner/README.md).

`float.c` now supplies both the original mathematical `float_calculate` entry
and the accepted Lisp-coercion `float_calculate_lisp` entry. The latter preserves
native silent bignum rounding while retaining small-integer and subsequent
arithmetic flags. `float-detector.wat` is unchanged. Build with the reviewed
[follow-up flags](../../tests/wasm/stage1/float-calls/review-followup/run.py),
including exports for **both** entries; the original raw entry retains its
accepted behavior. The detector imports the service's private memory.

`float-service.mjs` calls the Lisp-coercion entry and publishes a result into the
root frame after assurance. `service.mjs` is the reviewed Lisp adapter; its
filename is retained so `floating-capabilities.mjs` is byte-identical to the
reviewed source. The latter binds floating, integer and allocation capabilities
to one trusted owner. The loader admits their exact identities under
`wasm32-shared-B-floating-owner-v1`. Generated floating calls and Lisp conditions
are opt-in through `compile-float-call-form`. See the
[integration record](../../doc/WASM/stage1/integration-float-calls.json) and
[scope](../../tests/wasm/stage1/float-calls/review-followup/README.md).
The joined numeric subset is accepted as LL16-a; see the [acceptance record](../../doc/WASM/stage1/acceptance-ll16.json) for its policy and performance limits.

The audit-115 owner and scalar performance corrections are accepted and
integrated; see the [integration record](../../doc/WASM/stage1/integration-numeric-fastpaths.json).
The owner validates live state on each assurance and enumerates pinned image
objects at admission/collection. `scalar-service.mjs` can bind the existing
floating import directly to Wasm for eligible finite scalar operations. It
falls back before writes for shortages, bignums, nonfinite values and demanding
checked FP modes. No loader profile or compiler change is required.

The reviewed `scalar.wasm` is shipped alongside its exact `scalar.wat` source:

```sh
wat2wasm --enable-threads scalar.wat -o scalar.wasm
```

Its accepted SHA-256 is `1fff023a631895a04b4cd73203501a1dd6b762b5aa240b81b64cb6e68e165071`. The Worker owner
must pass its bytes and this expected digest to the existing factory:

```js
const scalarBytes = fs.readFileSync('runtime/wasm32/scalar.wasm');
const bundle = floatingCapabilities({
  ...options,
  scalarBytes,
  scalarDigest: '1fff023a631895a04b4cd73203501a1dd6b762b5aa240b81b64cb6e68e165071',
});
```

This repository-root example assumes the owner's existing `fs`, `options` and
`floatingCapabilities` bindings. Supplying these options selects the direct
Wasm export; omitting them intentionally retains the slow service. It is an
explicit owner configuration, not an automatic global switch.

Eligible double arithmetic measures about 150 ns/op here versus native CCL's
17 ns; these descriptive measurements are below formal v3 benchmark discipline.
Bignum/exceptional fallback cost and application throughput are separate. The
compiler and primitive binaries are unchanged; LL16-a is accepted at its reviewed subset/policy scope.

Strong EQ backing vectors: `hash.c`, `hash-adapter.wat` and the collector’s moved-key scanner are integrated at the reviewed LL18-b scope. Fixed capacity, internal owner-installed callable entries; production installation and CL hash-form lowering remain open.

All runtime JavaScript modules now use the reviewed synchronous `sha256.mjs` and `bytes.mjs` helpers. No runtime module imports Node crypto or uses Buffer. Factories keep their existing signatures; load binary bytes with the host’s file or fetch APIs before calling them. Loader/installer snapshots always own copies. SHA-256 remains construction/installation work, and very large inputs may block the Worker. See the [integration record](../../doc/WASM/stage1/integration-portable-digests.json) for exact bytes, checks and audit-117 browser limitations. The earlier `fs` example is a Node host example, not a runtime dependency.

D2 production templates: `materializer.mjs` is integrated at LL21-a scope. The compiler’s opt-in `*wasm32-template-memory*` emits canonical unshared imports, including child modules; the default shared output is unchanged. The materializer binds the owner’s ABI, classification and engine policy and verifies final bytes before compilation. It qualifies code only, not unshared runtime services or a new lazy-loader profile.

Per-function code sets: `bundle.mjs` integrates the accepted LL21-b owner/build API (`validate`, `compile`, `publish`). Each module holds one generated function’s public and internal B roles. The trusted inventory binds code IDs, slots, generations, ABI/layout versions and D2 records. All instances link before publication; mid-publication failure clears the newly written slots. Retain old modules and slots across redefinition. This adds no merged fallback or new lazy-loader profile. The measured 19-module set takes about 37.1 ms for full validated installation; the 1.93 ms cold figure is lazy-tier decode/validation, not eager compilation.

Symbols: `symbols.c` and `symbol-adapter.wat` integrate LL09-a and its audit-121 follow-up. The synchronous pinned-image service implements INTERN, FIND-SYMBOL, MAKE-SYMBOL and name/package readers with versioned hash admission. The internal B adapter preserves complete results across fixed, direct and indirect delivery. Owner allocation, tables and topology remain bounded; no global registration or moving package scanner. Surrogate names refuse; Unicode scalar values including noncharacters remain admitted.

Shared initialization: `initialization-owner.mjs` integrates LL13-a and its reviewed admission follow-up. Construct `InitializationOwner` with `{memory, layout, layoutDigest, modules, table, tail_table}`; use those same actual Worker-local tables in the trusted installation callback. Supply distinct tables with at least the declared capacity (distinctness is enforced by the loader after a claim, not by this owner). `process(0, callback)` initializes the process and bootstrap Worker once; `worker(id, callback)` claims and initializes another Worker’s regions. Fresh control storage must be zero and reserved words must remain zero. Callbacks are synchronous, failures terminal, busy claims refuse without waiting. This bounded shared profile provides no scheduler or image builder.

Initializer phases: `bootstrap-schedule.mjs` integrates the accepted auxiliary `BootstrapSchedule({memory, plan, digest, modules})`; `run(install)` installs in phase/prerequisite order and requires generated completion/effects before ready. The trusted synchronous installer receives private module/row copies and returns an invocation callback. State regions are exclusive to one Worker; failure is terminal, with no rollback. This is the phase protocol, not native startup membership or LL15 qualification. Before using it for production startup identity, bind the loader’s actual installed digest to the plan; the reviewed interface trusts that adapter. Only declared state/completion/ready words are checked, so retain the owner’s separate write-boundary checks.

Digest-bound initializer installation: `bootstrap-install.mjs` exports `scheduleInstaller({modules, loaderOptions, imports, invoke})`. Pass its `install` function to `BootstrapSchedule.run`. It owns a private validated byte catalog, obtains entries through the production lazy loader, and binds each installed digest to the plan before returning the invocation callback; `installed()` returns copied records. The synchronous `invoke(entry, row)` callback and import capabilities remain trusted. This closes the catalog-substitution gap for this adapter, while arbitrary scheduler callbacks remain trusted. The accepted thirteen native reset effects remain generated evidence awaiting the production symbol owner; this is not complete startup or LL15 qualification.

`config.mjs` validates a trusted process configuration synchronously. `browser-config.mjs` supplies reported browser concurrency and Wasm page size; its milliseconds and Lisp stack sizes are explicit policy. R2 generated startup effects and full-TCR harnesses remain in the accepted evidence packet; the superseded R1 spin body must not be used.


The reviewed bootstrap policy helpers are integrated as `bootstrap-tables.mjs`
and `bootstrap-populations.mjs`. They implement the accepted Stage 1 strong
retention policy, with measured fixed capacities; EQL/EQUAL construction still
refuses until its service is supplied. `bootstrap-termination/` contains the
corrected reviewed entry data, five compiled modules, binding map and read-only
image-admission guard. Cancellation, lookup and draining return one NIL in the
admitted empty state; registration refuses. Entry data is compiler input, not
an automatically loaded native Lisp file. Production root discovery, installation
at CCL symbols, scheduling disablement and the READY join remain required.

The accepted math R2 service includes pinned musl transcendental algorithms.
Build it with `python3 runtime/wasm32/build-float.py --output /tmp/ccl-float-build`.
`libm/COPYRIGHT` and `libm/provenance.json` carry licence and source identities.
The checked finite-input profile uses nearest rounding; inexact and underflow
trap modes remain explicit refusals. Native comparisons use the adopted two-ULP
limit, with exact identities, signed zeros and domain conditions exact. This
is not a full-domain accuracy bound or a new performance claim. `transcend.c`
contains the authoritative switch and is included by `float.c`;
`build-float.py` copies both source files into the build directory.

Audit-158 integration adds the six single/double inverse-hyperbolic operations to
the existing float module. The eight unmodified musl source files are bound by
`libm/hyperbolic-provenance.json`; the existing COPYRIGHT and two-ULP policy apply.
`build-float.py` includes them in its ordinary source glob.

Funcallable objects use a seven-field function header with the last field
pointing to the seven-element traced vector at CCL's logical immediate indices.
Ordinary functions retain the six-field layout. The installer now admits the
existing floating-owner profile as well as the legacy profile, using the same
trusted bundle and digest checks. This permits constructor allocation retry;
it does not implement method dispatch. See
[the storage decision and remaining obligations](../../doc/WASM/stage1/function-storage.md).


The accepted [standard GF dispatch integration](../../doc/WASM/stage1/integration-bootstrap-generic.json)
adds native three-field populations to the moving collector and pinned-image
owner. Members are retained strongly under the Stage 1 policy; the GC-link
word must be zero and the population type must be 0 or 1. Four-field termination
populations remain refused. Standard method selection runs in compiled CCL
Lisp; it recomputes applicability per call. Cross-dumped class/global
installation, custom combinations and the full image/READY join remain separate.
