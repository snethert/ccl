# D1 integer service for LL16

This isolated freestanding C service implements exact integer `+`, `-`, `*`,
`ash`, `integer-length` and both values of `truncate` in Wasm. It is an
auxiliary prerequisite, **not S1-LL16-a execution**. No shared compiler,
loader, runtime or upstream kernel file changes. Generated Lisp dispatch,
handleable numeric conditions, mixed floats and the D6 policy path remain
required before the LL16 slot can run.

The two lowest tag bits encode a signed 30-bit fixnum. Bignums use D1 subtag
7 and little-endian 32-bit two's-complement digits, with a minimal sign word,
eight-byte object alignment and zero padding. Results normalize back to
fixnums whenever possible. Sign/magnitude scratch makes carry, borrow,
truncating division and arithmetic right shift explicit. `integer-length`
counts the complement of a negative integer. Shift counts are full integers:
large negative shifts become zero or minus one, never an i32 masked shift;
large positive shifts refuse the resource request, except shifting zero.

The API is `integer_calculate(op, a, b, input, input_end, output, output_end,
scratch, scratch_end, result) -> status`. Operations are numbered 0 through 5
in the order above. On success the four result words contain the first value,
second value (zero for unary results), count and next allocation pointer.
No imported function, poll, collection or growth can intervene. The caller
must publish the returned roots before allowing any safepoint. The emitted
call graph is decoded and checked for cycles and indirect calls; there is no
recursive numeric fallback. No performance claim is made: multiplication is
schoolbook and division uses bitwise long division.

An owner supplies disjoint, backed, eight-byte-aligned input, allocation,
scratch and publication regions. The low 128 KiB is reserved for this isolated
module's C stack. Input pointers must be authenticated object starts by that
owner; header/extent checking here is **not an object-start census**. Operands
must be normalized integers. The module accepts unshared memory; sharing or
concurrent mutation is not admitted. It does not allocate in a real Lisp heap
or use the production collector owner yet. Scratch holds four magnitude
arrays, each with two guard words, and costs 16,416 bytes. The resource budget
is 32,768 magnitude bits, not a claim about Common Lisp's maximum integer
size; a positive boundary value may need an additional D1 sign word.

Status 1 means owner error; 2, malformed/noncanonical integer; 3, resource
capacity; 4, zero divisor; 5, unsupported operation. The input region, output
reservation and result publication are unchanged on every refusal; scratch
may change. Both `truncate` results are prepared before checking their combined
allocation. These statuses are service outcomes, not Lisp conditions or a
retry protocol. The compiler adapter must distinguish its resource request
and root/reload its operands around any collecting assurance call.

Run:

```sh
python3 tests/wasm/stage1/integer-core/run.py \
  --evidence ../ccl-evidence --output /tmp/integer-new
python3 tests/wasm/stage1/integer-core/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-19-stage1-integer-core-r1 \
  --output /tmp/integer-replay-new
```

The exact Python oracle supplies 4,424 cases. Native CCL reproduces them at
three safety/speed policies, 13,272 comparisons. Wasm executes at 1 MiB and
2 GiB, 8,848 comparisons, plus 636 chained operations using target-produced
bignums as the next input without host rematerialization. Factorial grows to
160! and divides back to one. Forty-eight owner/resource/shape refusals check
preservation. Twelve single-site compiled mutants have focused cases, each
also run on the correct module; no failed build counts as mutant rejection.
The native kernel/image are pinned accepted baseline artifacts, run without an
init file in a disposable directory. The source interpretation is pinned to
the target architecture, ARM digit/sign and normalization routines and shared
32-bit bignum definitions. No native source or image is modified, so no new
R6 build is necessary.

The packet retains original development failures: executing the read-only
retained kernel instead of a copy, and an incorrect expected first-case label
for the carry mutant. Both were harness errors; the positive arithmetic agreed
on its first run. The carry control now uses an explicit focused input rather
than relying on corpus ordering.
