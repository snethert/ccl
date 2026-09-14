# Checked wasm32 conversions — S0-LL07-a

One hand-built scalar corpus exercises four distinct conversion families in
Node/V8 on macOS. Two module variants differ only in the installed entry's
return bias. Each runs 136 cases: 83 successful operations and 53 expected
refusals. Nineteen single-site WAT/JavaScript mutants run against the unchanged
case list and Python oracle; each fails at its declared first case.

Run from the repository root into a fresh directory outside the checkout:

```sh
python3 tests/wasm/stage0/conversions/run.py --output /private/tmp/ccl-conversions
python3 tests/wasm/stage0/conversions/run.py --verify /private/tmp/ccl-conversions
```

The runner uses installed `node` and `wat2wasm`, retaining their resolved paths,
versions, executable digests and actual compiler arguments. It needs capacity
to grow a WebAssembly memory from one page to 32,769 pages. Growth failure is a
failed run. The memory is sparse: tests touch a few small regions, not every
byte of a 2 GiB heap. Each child has a 60-second deadline. Failed producer
outputs stay at the requested path; failed verification replays retain their
temporary directory and report its location.

`program.wat` implements checked fixnums, raw/tagged addresses, a bounded ID
registry and a separate typed-slot registry. Refusal codes are in `abi.json`;
they are fixture status values, not an implemented Lisp condition system.
`execute.mjs` validates JavaScript inputs, records both signed engine results
and unsigned address results, grows real memory and captures literal bytes.
Address normalization uses `>>> 0`; address arithmetic stays in checked Wasm
operations or JavaScript Number byte offsets. Views are refreshed after growth.

`cases.json` supplies literal expectations. `oracle.py` independently recomputes
them using Python integers, little-endian bytes and explicit sets of issued IDs
and installed slots. `binary.py` decodes the final binary's function signatures,
exports, memory/table limits and element segments. Its reservation map comes
from the active element segment. It is an interface decoder, not a general
instruction interpreter; compilation and instantiation validate executable
instructions. There is no C link or inferred production C-pointer reservation.

Slots carry an explicit kind alongside the integer payload. A tagged ID word
with payload 4 is rejected even though ordinary slot 4 is callable. The fixture
does not claim to infer a value's origin from its bits or authenticate a caller
that falsely labels an integer. ID counters are initialized near exhaustion
directly; the test does not issue half a billion definitions.

The full result must remain blocked solely as unreviewed under its slot
inventory. The runner also removes each of the ten required artifact roles
from that genuine result and requires the unchanged production gate to refuse
it. Review and project acceptance are separate steps.

Scope and retained evidence: [conversion report](../../../../doc/WASM/stage0/conversions.md).
This is not a full D1 layout, generated B backend, allocator, collector, browser
or multi-Worker proof. Shared compiler and kernel sources are untouched.
