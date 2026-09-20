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
