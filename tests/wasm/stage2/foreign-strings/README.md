# Explicit UTF-8 string copies

The sixth Stage 2 unit is executed, awaiting independent review. It adds two
internal CCL API functions. Encoding is a
required keyword value; both missing encoding and anything other than `:utf-8`
signal an ordinary Lisp error.

```lisp
(ccl::write-wasm-string buffer simple-string :encoding :utf-8 :offset 0)
(ccl::read-wasm-string buffer byte-count :encoding :utf-8 :offset 0)
```

Write accepts a simple native-shaped 32-bit-character string, validates every
Unicode scalar, encodes a private snapshot, and copies into the owned foreign
allocation. Its return value is the number of bytes copied. Read copies exactly
the specified bytes, decodes strict UTF-8, and allocates a fresh simple Lisp
string. Offsets and read sizes are bytes, not characters. Embedded NUL and BOM
characters are preserved. No terminator is appended, no byte-order mark is
inserted or stripped, and there is no normalization or replacement decoding.
Surrogates, values above U+10FFFF, overlong/truncated sequences and invalid
continuations refuse before publication. Empty strings and end-of-buffer empty
ranges are admitted. Data strings are not subject to the 4096-character name
limit. A read is limited to 0xFFFFFF bytes, keeping its worst-case character
count representable in the target's 24-bit object header.

The service owns process operations 10 and 11 within foreign selector 15. The
Lisp wrapper encodes the declared `:utf-8` choice as discriminator zero; the
service independently checks that discriminator. The existing allocation
identity and byte-range bounds apply, including release, close and trap
retirement. Copying itself does not enter foreign code. Any allocator, call or
release around the copies continues to use FOREIGN. Only a decoded JavaScript
scalar snapshot crosses the output allocation safepoint. The service reloads
the rooted request after collection and then publishes the complete string.
Malformed input does not allocate a Lisp result, change the result slot or
modify the foreign bytes. No Lisp address is passed to the foreign library.

Non-simple/displaced/adjustable strings, other encodings, implicit allocation,
C-style terminators, callbacks, browser generated Lisp/provider integration and
multi-Worker ownership remain outside this unit. This does not close FMT-2 or
any LL obligation. The preceding buffer-finalizer unit still awaits its own
independent review; extending its regression suite does not accept it.

## Verification

Qualification passes **148 checks per engine / 69 killed mutants**, including
**42 string cases / 14 controls**, in Node and Chromium/Firefox/WebKit. The
post-READY witness matches **45 native rows** (15 new), with **88 foreign entries /
67 moving collections**. Product Lisp adds 14 lines (74 API lines total);
whole-file count movement is zero. The first executed run passed. The pack is
`ccl-evidence/2026-09-28-stage2-foreign-strings-r1`; its
[bound result](../../../../doc/WASM/stage2/foreign-string-results.json) records
input identities, dependency reuse, skips and pending review. The unchanged
collector, owner, foreign module, binary admission, namespace and process service
reuse the preceding unit's source-bound evidence.

The existing API driver composes scalar, byte-buffer, finalizer and string
cases; it is not a separate integration harness. The string cases cover two
placements with forced moving collection and retired-space poisoning while
boxing the decoded string, Unicode scalar boundaries, BOM/NUL/empty/long data,
13 malformed UTF-8 encodings, exact byte counts, sentinel preservation, encoding
and arity refusal, invalid characters, range/type refusal and retired handles.
Directed size-limit tests use an observed library stub to distinguish refusal
before the library read from a later library bounds refusal. Other cases use
the real foreign fixture and collector. Source mutants check both independent
size limits, both encoding clauses, encoding/decoding, byte counts, terminators,
BOM handling, output representation and request reload after collection.

The ordinary post-READY Lisp witness appends 15 observations to the existing
30 API/finalizer rows. Native CCL's own UTF-8 codec supplies the oracle;
re-encoding must reproduce the exact source octets for a strict decode. The
foreign library behavior remains fixture-modeled on native CCL, as in the
preceding API unit. Generated target Lisp uses the product service and the
real fixture library. Browser Workers exercise the same service and collector
with synthetic generated-B roots; browser generated Lisp is still deferred.

New arity clauses have directed cases for too few/many fields. Invalid token
kind, object tag/body extent and fixnum checks reuse the common marshalling
clauses already exercised in the API suite; field sites add directed type
refusals. Range validation is the unchanged owned-buffer implementation.
No shared compiler, upstream kernel or collector source changes are required.
The compiler corpus remains deferred until completion of the whole FFI layer.

## Reproduction

Verify both RAM-backed mounts as required by `CLAUDE.md`. Recreate the
[pinned browser driver](../browser-tools/README.md) if needed. From the repo root:

```sh
work=/private/tmp/ccl-work/codex/foreign-strings
python3 -B tests/wasm/stage1/loader-target/build.py "$work/boot" --boot0
python3 -B tests/wasm/stage1/loader-target/build.py "$work/level1" --level1
python3 -B - <<'PY'
from pathlib import Path
sources = ['runtime/wasm32/foreign-api.lisp',
           'tests/wasm/stage2/foreign-api/checks.lisp',
           'tests/wasm/stage2/foreign-finalizers/checks.lisp',
           'tests/wasm/stage2/foreign-strings/checks.lisp']
Path('/private/tmp/ccl-work/codex/foreign-strings/source.lisp').write_text(
    '\n'.join(Path(p).read_text() for p in sources))
PY
python3 -B tests/wasm/stage1/loader-target/build.py "$work/checks" \
  --postimage="$work/boot" --source="$work/source.lisp"
python3 -B tests/wasm/stage2/foreign-api/run.py \
  --boot "$work/boot" --level1 "$work/level1" --checks "$work/checks" \
  --output "$work/run" \
  --playwright /private/tmp/ccl-work/codex/stage2-browser-tools/node_modules/playwright-core/index.mjs \
  --browser-config /absolute/path/to/browser-config.json
```

Successful generated WAT/Wasm and compiler records are disposable. Compiler
images remain in the shared cache; the compact evidence pack retains input and
tool identities, results, exact source changes and necessary original failures.
