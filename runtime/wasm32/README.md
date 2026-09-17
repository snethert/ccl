# Wasm32 runtime

`loader.mjs`, `binary.mjs` and `stub.wat` are the accepted single-Worker lazy
installer from `tests/wasm/stage1/b-lazy-calls`, integrated without source changes.
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
[here](../../doc/WASM/stage1/integration-b-lazy-calls.json). The reviewed fixture
and direct-context composition retain the executable examples and verification.
