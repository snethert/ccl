# Bignums and native-pointer boundaries through the level-0 loader

This proposal extends the general-array proposal at `e2de2fd9`. The real
ordered compiler completes l0-aprims (26 modules), l0-array (41), l0-bignum32
(69), l0-bignum64 (1), l0-cfm-support (23), and l0-complex (2), then stops at
**:FUNCTION-IMMEDIATE-LAYOUT in l0-def**. On this 32-bit target, l0-bignum64's
single module is only its reader-selected package form; it contributes no
64-bit arithmetic implementation. Both FASL pathname and failure-p are checked.
The two target-directory files compile separately (64 and 104 modules).

Three proposed product files are under `files/`; none is integrated. They
inherit the array proposal's target Lisp accessors and collector unchanged.
The native kernel is unchanged. Independent Claude review remains required.

## Implementation

The original %NEW-PTR refusal is in a native MPN multiplication helper. Those
six MPN entries use native addresses encoded as fixnums and temporary macptrs.
They now have explicit Wasm error boundaries. The existing Wasm selection in
MULTIPLY-BIGNUMS already uses the ordinary Lisp digit algorithm; this packet
compiles and executes that algorithm with addition, subtraction, logical
operations, shifting, division and GCD. UNSIGNEDWIDE->INTEGER likewise refuses
its native external-record pointer argument. This is not a %NEW-PTR allocator
or an implementation of native GMP or native Karatsuba helpers.

The foreign-library source initializes its three native linker sentinels to
NIL. Entry-address conversion, symbol lookup/address retrieval, entrypoint
revival and native shared-library opening explicitly signal errors. The
separate foreign Wasm module interface and its memory ownership contract remain
post-boot work. Existing native branches retain the same reader forms.

The backend now lowers %ILLEGAL-MARKER using the existing target layout value.
It also admits literal references to exact xfunction objects emitted earlier
within the same COMPILE-FILE call. The dynamically scoped ownership list keeps
native function objects and other compilations' xfunctions out. Ordinary FASL
object identity carries the function through a later initializer. This closes
the heap-constant refusal encountered in l0-def before its function-layout
accessor becomes the next blocker.

## Execution and controls

The producer cross-loads the eight complete FASLs after deleting their source
files. Selected complete original numeric, package and lock definitions supply
dependencies missing from the incomplete image. Numeric macro preludes are
copied as complete original EVAL-WHEN forms; production bodies are not rewritten.
These selected dependencies and test witnesses receive no whole-file credit.
The resulting image has 470 modules and executes 25 ordered initializers.
All 83 native observations match in each of four placement/collection modes;
the ordinary modes collect 8 times and the extra-collection modes 115 times.

New native comparisons exercise 80-, 128- and 544-bit signed operands,
multiplication and squaring, carry and borrow, logical operations, shifts at
digit boundaries, division with all sign combinations, GCD and repeated
allocation. Division expectations are independent host-computed exact integer
constants. The other arithmetic comparisons use the existing generic integer
service alongside the loaded original bignum functions. The bignum compile
warnings describe the native host's different helper arities; failure-p is NIL
and the target calls execute with their target definitions.

All twelve native-pointer entrypoints must raise checked errors, run Lisp
UNWIND-PROTECT cleanup and restore the observed TCR fields. Replacing each
entrypoint with a successful function kills its corresponding refusal control.
Together with the function-binding check and 87 inherited controls, the driver
requires all 112 controls in each execution mode.
These controls establish an explicit unsupported boundary, not native condition
class identity. The stored QLFUN constant remains callable independently of a
global function binding. Separate compilation controls refuse a native function
and an xfunction from a previous compilation and check dynamic-scope restoration
on both success and refusal. Marker and foreign-registry observations accompany
the inherited package, lock and array cases.

## Qualification and limits

Fresh R6/R6a passes 21,843 native tests and restores 164 FASLs: 45 are identical
and 119 are decoded-equal. Both changed native files have identical reader forms
under all 17 existing target profiles (34 comparisons). The reader harness binds
the files' unchanged DIGIT-SIZE constant before reading #. expressions; unchanged
foreign reader forms unavailable in the macOS interface database are identified
by their original hashes and compared byte-for-byte.

The complete compiler/runtime corpus passes all 26,048 comparisons with the
final compiler. **Qualification correction:** the retained execution environment
identifies the older collector, despite this packet's summary naming the array
collector. That combination was not qualified by this run. The
[function-definition successor](../loader-def/README.md) records the discrepancy
and runs the corpus with an explicit executed-collector identity check. The
original evidence is unchanged. Four execution modes and a Git-free
different-root replay qualify the loader input identity: all 1,445 generated
FASL, heap, WAT and Wasm artifacts match byte-for-byte, along with every
observation and control result. The inherited collector
is reused by exact source and binary identity; its prior 46-check qualification
is referenced. Final driver identities are bound before and after execution
and at retention. Original failures are retained separately from passing runs. Development exposed
a bypassed control hook and a path-dependent diagnostic FASL; both are retained
with the fixes and final driver identity, without credit for superseded runs.

No target LOAD, foreign module service, function-immediate layout, complete
complex arithmetic or boot is claimed. Accepted files **0/0/0**, originals
**575/535**, and ledger **21/12** remain unchanged. O-90's inherited duplicate
integer definitions remain a separate cleanup.

## Reproduce

```sh
python3 tests/wasm/stage1/loader-new-ptr/run.py /private/tmp/ccl-work/codex/loader-new-ptr/run
python3 tests/wasm/stage1/loader-new-ptr/exercise.py /private/tmp/ccl-work/codex/loader-new-ptr/run
python3 tests/wasm/stage1/loader-new-ptr/qualify.py native /private/tmp/ccl-work/codex/loader-new-ptr-native/run
python3 tests/wasm/stage1/loader-new-ptr/readers.py /private/tmp/ccl-work/codex/loader-new-ptr-readers/final
python3 tests/wasm/stage1/loader-new-ptr/corpus.py /private/tmp/ccl-work/codex/loader-new-ptr-corpus/run
python3 tests/wasm/stage1/loader-new-ptr/replay.py /private/tmp/ccl-work/codex/loader-new-ptr-replay /private/tmp/ccl-work/codex/loader-new-ptr/run
```

Use fresh output directories. `packet.py --help` gives retention arguments.
The replay archives the pinned parent and overlays this proposal, then runs the
producer and execution drivers inside the extraction without Git metadata.
