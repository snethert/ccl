# Portable synchronous runtime digests

Auxiliary runtime proposal; no inventory credit. LL21 is paused by user direction.
Shared runtime and compiler files remain unchanged by this proposal. LL18-b was
accepted and integrated separately before this work.

`derive.py` replaces five `node:crypto` imports with one synchronous SHA-256
implementation and removes every runtime `Buffer` dependency. Factories and
capability identities keep their existing signatures. The loader still exports
`sha`; digests and manifest heads remain lowercase hexadecimal SHA-256 of the
same bytes. Import names use UTF-8 byte lengths. Loader and installer snapshots
always copy, including ArrayBuffer inputs, rather than borrowing their storage.

`sha256.mjs` uses the FIPS 180-4 compression and padding rules. It processes full
blocks without a full-input copy, allocates at most two padding blocks, and keeps
all working state local to the call. `bytes.mjs` accepts buffers and buffer views
(including offsets and DataViews); hashing strings and manifest serialization use
TextEncoder. It does not introduce async factories or depend on Web Crypto.
Callers retain the existing trusted-owner/exclusive-access obligation for mutable
input bytes. This is binary integrity binding, not a signature scheme.

Run with explicit local tools (the retained run uses Playwright Core 1.55.0 and
Chromium 145.0.7632.6):

```sh
python3 tests/wasm/stage1/portable-digests/run.py \
  --evidence ../ccl-evidence --output /tmp/portable-digests \
  --playwright /absolute/path/to/playwright-core/index.mjs \
  --browser /absolute/path/to/chromium
```

The runner reconstructs its inputs from three retained archives. It compares
every Wasm binary it replays against Node crypto; the browser Worker additionally
compares those bytes against Web Crypto. Literal tests include the
[NIST SHA-256 examples](https://www.nist.gov/itl/ai/ai-standards-and-guidelines-group/nsrl-test-data)
(`abc`, the two-block string, and a million `a`s), empty input, offsets, DataViews,
UTF-8, padding boundaries, deterministic random inputs, and a 512 MiB + 9 byte
input exercising the upper length word. These are implementation checks, not
FIPS validation/certification.

The browser is served with COOP/COEP and runs real module Workers without a Node
shim. All runtime modules import successfully. Actual collector, integer, float,
detector, scalar, bundle and loader factories construct synchronously; wrong
digests and changed bytes refuse with the existing diagnostics. Both the Page
test harness and Web Crypto are outside the synchronous runtime.

The complete accepted installer scenarios run at 1 MiB and 2 GiB in both Node
and Chromium, one browser Worker per placement as in the original Node fixture.
Their answers equal the retained installation/redefinition results. Separate
checks mutate the owner's returned bytes before later use to prove both loader
and installer snapshots own their bytes. A Unicode manifest checks the actual
installer's head digest. The joined numeric eager and cold executions remain
byte-identical to the accepted scalar packet. Compiler, primitive binaries and
numeric execution semantics are unchanged; native R6/R6a is reused, not rerun.

Fault controls cover SHA padding/length endianness, view offsets, UTF-8, aliased
snapshots, all service digest checks, and the two real snapshot call sites.

The completed run has 358 shared checks, 391 additional Node differential rows
(including the large length case), 96 Wasm binaries hashed, and thirteen rejected
faults. The eager/cold numeric outputs each retain 72,200 comparisons and 31,836
collections; the installation replay retains 48 invocations and 64 refusals.
These are repeated checks of unchanged behavior, not new slot credit.

Retained replay:

```sh
python3 tests/wasm/stage1/portable-digests/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-20-stage1-portable-digests-r1 \
  --output /tmp/portable-digests-replay \
  --playwright /absolute/path/to/playwright-core/index.mjs \
  --browser /absolute/path/to/chromium
```

## Scope and development finding

This qualifies construction and these selected execution paths on the recorded
Chromium build and Node. It does not qualify Firefox, Safari, the complete
browser engine matrix, production hosting, or the rest of the IDE. Synchronous
hashing remains construction/installation work and is not added to arithmetic.
There is no new numeric performance claim.

A development adaptation reused one Chromium Worker for the low and high
placements. Its second installer run reported OBJECT_EXTENT where the retained
fixture expects MODULE_IDENTITY. Adding the arguments to the error text made
that run pass. The same bytes pass with a fresh Worker per placement, and in
Node. The failing logs and the diagnostic edit are retained; the cause is not
established. No runtime bounds check was changed to obtain the passing result.
This mixed-placement/reused-Worker case remains a browser investigation item,
not a claim established by this packet.
