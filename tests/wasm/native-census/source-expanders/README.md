# Source macro and compiler-macro reconstruction

This isolated extension reconstructs all expansion bodies observed by the
reviewed dumplisp traversal. It reuses the fourteen earlier metadata/accessor
macros, adds the remaining macro/compiler-macro bodies and the architecture
dispatcher, and routes by actual binding identity and operator name. It retains
helper calls and native object references without qualifying them for Wasm.

From the repository root on the macOS x86-64 reference host, use fresh paths:

```sh
python3 tests/wasm/native-census/source-expanders/run.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --work /private/tmp/ccl-source-expanders-work-review \
  --output /private/tmp/ccl-source-expanders-review
```

Replay only the retained packet and its direct bindings:

```sh
python3 tests/wasm/native-census/source-expanders/verify.py \
  --packet /Users/buildsomething/Source/ccl-evidence/2026-09-13-source-expanders-r1
```

The runner executes seven native sessions: source, repeat, inherited reference,
and four negative controls. Source/repeat captures must be byte-identical. The
inherited traversal must also be byte-identical, with every expansion event equal
except for the deliberately selected callable ID. Twenty-seven checker controls
and five parser cases run locally. Source and FASLs must remain unchanged.

The accepted registration, clean r7 image, description extension and first macro
fixture are reused unchanged. Native pass 2 is temporarily observed while
building the private expander functions; its original entry and all returned
values are preserved, and normal/nonlocal restoration is checked. No original
CCL macro or compiler-macro binding is replaced. No saved implementation image,
functional compiler patch, census graph replacement or gate acceptance results.

See the [scope report](../../../../doc/WASM/stage0/source-expanders.md).
