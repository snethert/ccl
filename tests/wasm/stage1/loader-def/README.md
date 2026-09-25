# Function definitions and floating-point files through the ordered loader

Audit 181 found no defect. This proposal was accepted and integrated with its
successors as one reviewed stack; see [the integration and audit dispositions](../loader-stack-acceptance/README.md).
The packet description below records the original proposal and its evidence.
Use the successor integration driver with the current checkout.

This isolated proposal extends `loader-new-ptr` at `928ad5ef`. The ordered
compiler completes `l0-def` (31 modules), `l0-error` (1), and `l0-float` (50),
after the preceding six files, then stops at **:EQ-VECTOR-INITIAL-ELEMENT in
l0-hash**. The two target-directory files compile separately (68 and 104
modules). Both pathname and failure-p are checked. Eleven complete production
FASLs are cross-loaded after their sources are deleted. Selected complete
original dependencies and test witnesses receive no whole-file credit.

Five proposed product files remain under `files/`. The upstream kernel is
unchanged. Claude review is required before integration; accepted file counts
**0/0/0**, original executions **575/535**, and ledger **21/12** remain unchanged.

The function-definition file uses the existing Wasm metadata accessors instead
of native function vectors. Its name registry uses the adopted Stage 1 strong
table. The public flag accessor preserves its optional-NIL and old-value return
semantics in both its loaded function body and direct compiler lowering. Mutable
flags are supported for funcallable instances; ordinary function metadata stays
immutable and its setter refuses. Native catch-frame inspection has an explicit
target error boundary. Wasm nonlocal exits use their existing control records.

Four target Lisp accessors provide single-float halfwords, double/single
significand leading zeros, and destructive single-float scaling through the
existing checked float-word and numeric primitives. The floating-point file
explicitly refuses native-pointer copying. The target LAP and primitives files
now declare their NUMBER-MACROS and HASHENV compilation prerequisites. No
consumer source rewriter is used.

The execution harness binds the three existing EQ-table runtime leaves through
their accepted internal B adapter, as the compiler corpus already does. Their
source and binary identities are checked against the class-growth prerequisite.
Their function objects occupy a declared pinned image region; scratch and result
storage are disjoint from the image, collector and stacks. These are runtime
services, not additional compiled Lisp modules or original-definition credit.

New native comparisons cover function binding/unbinding, names, macro and
special-variable flags, real %DEFUN installation, funcallable metadata writes,
name retention across moving collection, float signs, scaling, copying,
normal/subnormal decoding, signed zero, and the original error-string table.
Both new runtime boundaries require a checked error, Lisp UNWIND-PROTECT cleanup
and restored TCR state; substituting a successful entrypoint kills each control.
Four compiler controls reject missing/extra operands to %WASM-FUNCTION-BITS and
LFUN-BITS. INNER-LFUN-BITS and LFUN-BITS-KNOWN-FUNCTION share the exact same arity
clause. The corpus separately checks an invalid non-NIL flag value and optional
NIL reads for ordinary and funcallable functions.

Whole-file compilation does not establish that every function in those files
has a complete runtime dependency chain. The native-pointer branch of %COPY-FLOAT
has no execution witness because this image admits no macptr constructor. This
packet claims the listed float observations, not the complete numerical library.
Target LOAD and boot remain open. O-90's inherited duplicate integer definitions
remain a separate compiler cleanup.

The prior native-pointer packet's corpus summary named the array collector, but
its retained execution-environment file identifies the older collector. Its
26,048 comparisons therefore did not qualify the claimed collector combination.
The evidence remains immutable. This packet corrects the hook ordering, records
the actually executed collector hash, and checks it against the loader runtime.
The original corpus also incorrectly required an LFUN-BITS NIL argument to fail;
the corrected test uses T for its invalid-type refusal and adds native-compatible
NIL read assertions. Original failures are retained without qualification credit. A replay-harness
lease deadlock was also corrected; the final run binds the corrected harness.

The resulting image contains 595 modules and runs 33 ordered initializers. All
110 native observations agree in each of four placement/collection modes, with
116 runtime controls per mode. Ordinary modes collect 9 times; collecting modes
collect 150 times and poison retired space. Native R6/R6a passes 21,843 tests and
restores all 164 FASLs (45 identical, 119 decoded-equal); the 75 upstream-disabled
tests remain disclosed. Both shared source files
have identical reader forms across all 17 existing target profiles, for 34
comparisons. Their unchanged float macro prelude is hashed and evaluated before
the reader matrix.

The full compiler/runtime corpus passes all 26,048 fresh comparisons with the
final source set and selected collector. The executed collector binary digest
matches the loader runtime. A Git-free replay at a different path reproduces
all results, controls and driver identities, and all 1,825 generated FASL, heap,
WAT and Wasm artifacts are byte-identical. The collector's prior 46-check
qualification is reused by exact source and binary identity.

Reproduce with fresh output directories:

```sh
python3 tests/wasm/stage1/loader-def/run.py /private/tmp/ccl-work/codex/loader-def/run
python3 tests/wasm/stage1/loader-def/exercise.py /private/tmp/ccl-work/codex/loader-def/run
python3 tests/wasm/stage1/loader-def/qualify.py native /private/tmp/ccl-work/codex/loader-def-native/run
python3 tests/wasm/stage1/loader-def/readers.py /private/tmp/ccl-work/codex/loader-def-readers/run
python3 tests/wasm/stage1/loader-def/corpus.py /private/tmp/ccl-work/codex/loader-def-corpus/run
python3 tests/wasm/stage1/loader-def/replay.py /private/tmp/ccl-work/codex/loader-def-replay/run /private/tmp/ccl-work/codex/loader-def/run
```

`packet.py --help` gives retention arguments. The replay archives the pinned
parent and overlays this proposal, then runs the producer and execution drivers
inside that extraction without Git metadata. Final drivers and product inputs
are bound before and after execution and at retention.
