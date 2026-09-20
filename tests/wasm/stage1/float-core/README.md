# Mixed floating-point primitive service (auxiliary)

This isolated service is the next LL16 prerequisite. It is **not integrated**,
not a generated Lisp call path, and earns no inventory credit. The accepted
compiler and all shared runtime files are unchanged. The corpus checks exact
arithmetic expectations rather than treating native divergences as agreement.

## Run and replay

From the repository root on the pinned macOS x86-64 host:

```
python3 tests/wasm/stage1/float-core/run.py --evidence ../ccl-evidence --output /tmp/float-new-run
python3 tests/wasm/stage1/float-core/packet.py verify --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-19-stage1-float-core-r1 --output /tmp/float-new-replay
```

The runner records exact commands, tool hashes, native kernel/image hashes and
results. It builds freestanding C to Wasm and reuses the reviewed Stage 0 f64
exactness detector: only its imported memory maximum changes from one page to
32,769 pages. Its arithmetic bodies are unchanged. Native R6 is unnecessary for
this isolated service: no compiler or native source is changed. The stock native
image supplies values; a separate scalar-SSE program supplies f32 flags.

## ABI and ownership

`float_calculate(op, a, b, input, input_end, output, output_end, result, mask, safe)`
takes ten i32 words and returns a service status. Operations 0–3 are add,
subtract, multiply and divide; 4–9 are `< <= = /= >= >`; 10 and 11 coerce to
single and double. Binary arithmetic requires at least one float; integer-only
arithmetic belongs to the accepted integer service. Comparisons also accept two
integers. Unary coercions ignore `b`.

Inputs are 30-bit fixnums, canonical subtag-7 bignums (at most 1,024 magnitude
limbs), single floats or double floats in D1 layout. Mixed arithmetic chooses
double if either input is double, otherwise single. Integer conversion rounds
once from guard/sticky bits, including integer-to-single; comparisons never
round an integer to compare it with a float. Signed zero is retained. Arithmetic
NaN propagation and unordered comparisons follow the declared primitive policy;
NaN payload preservation is not promised.

The owner authenticates object starts and exclusive use of private unshared
memory. The service checks backed, aligned, disjoint input/output/result extents
above the reserved 128 KiB. The C stack occupies the upper half of that reserved
area; the detector uses low scratch bytes. There are no callbacks, collection,
memory growth or recursive calls. The emitted binary is inspected for its actual
stack top, absent data/start/element sections and cycle-free call graph. The
owner must supply sufficient stack backing. Addresses are tested at 128 KiB,
1 MiB and 2 GiB. NIL and T are the accepted fixture identities, not new objects.

The 32-byte publication has eight words: value, detected flags, selected flag,
stage, next allocation pointer, width, operand-A flags, operand-B flags. Width
is 32/64 or zero for a boolean. Stage 1/2 identifies operand conversion and 3
identifies the operation. Mask bits are invalid=1, zero-divide=2, overflow=4,
underflow=8, inexact=16. The first enabled flag in that order wins. Overflow
reports overflow+inexact and underflow reports underflow+inexact. With `safe=0`,
no checks run. Exactness witnesses run only when an inexact/underflow mask needs
them; unchecked flags are not a complete hardware status snapshot.

An enabled condition returns service status zero, the selected flag, NIL and no
allocated object. A future Lisp adapter must signal it. Service refusals are
1 (owner/options), 2 (type or malformed object), 3 (capacity), and 5 (unsupported
operation). They leave input, output and result bytes unchanged; private stack
and detector scratch are not transactional. Successful publication writes result
words last. Allocation exact-fit, empty reservation for conditions, and a result
record at memory end are exercised.

## Qualification and native boundaries

39,627 cases run at three placements (118,881 comparisons), including both
precisions, all arithmetic/comparison operations, eight masks, safe/unchecked
modes, 1,024-limb integers, normal/subnormal rounding boundaries and seeded
random inputs. An independent rational oracle computes the expected rounded
bits and flags. Scalar SSE agrees on all 1,167 distinct f32 arithmetic witnesses.
Fifteen focused compiled faults are rejected, with their corresponding positive
runs required to pass. There are 63 owner/type/resource refusals and six exact
fits. The flags chosen by the integer conversion and the operation are retained
separately.

The native CCL run has 6,153 distinct non-NaN cases: 5,939 agree and **214 differ**.
Every difference is retained with its operands; no compatibility PASS is claimed:

- 134 integer conversions overflow through CCL's explicit library error even
  when hardware exceptions are masked. The raw primitive can instead return
  infinity when unchecked/masked. A Lisp adapter must preserve CCL's explicit
  coercion errors; this primitive does not authorize removing them.
- 80 large-integer/infinity comparisons differ. CCL's bignum/float comparison
  treats the infinity exponent/significand as finite-style data; the primitive
  uses mathematical ordering. Native-compatible lowering needs an explicit
  disposition before LL16 qualification.

NaN inputs are excluded from native comparison because hardware signaling-NaN
behavior is not the approved explicit exception policy. They remain in the
rational/target corpus. The native witness uses masked hardware exceptions and
is a value comparison, not a policy matrix. These limitations prevent promoting
this packet into generated numeric compatibility or LL16 credit.

## Development and remaining work

Testing the first admitted address exposed LLVM introducing a lookup-table data
segment and moving the C stack top 16 bytes past its reservation. Disabling jump
tables removes that segment. The original binary, compiler invocation, disassembly
and failing zero-plus-zero case are retained; rebuilding without that option is
now a rejected fault. A later harness attempt expected this fault at the wrong
case; its original failure and the focused correction are retained too.

The packet pins direct sources and native/detector prerequisites, then a fresh
run rebuilds and compares deterministic outputs. Native executable files and
path-bearing command logs are retained but not asserted byte-identical across
output directories; native values and flags are. No throughput claim is made.

Next: a collecting owner capability and generated mixed numeric calls under the
approved TCR mode, with Lisp condition delivery and the native boundaries above
resolved explicitly. Ratios, complex arithmetic, transcendental functions,
float-to-integer conversion and non-nearest rounding are outside this service.
