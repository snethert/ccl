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
