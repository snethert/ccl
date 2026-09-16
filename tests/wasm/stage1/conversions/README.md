# S1-LL07-a: generated typed conversions

The proposed backend compiles a bounded internal primitive language through
CCL's real front end and registered Wasm pass 2. Source lambdas call private
primitive names; pass 2 checks their exact symbols and argument/result
representations before emitting checked operations. Code-ID and slot types
cannot enter as unvalidated parameters. Fourteen source refusals exercise
cross-family uses, unsupported forms, cycles and malformed input.

These are **raw internal primitives**, with the explicit [ABI](abi.json),
not B Lisp entries. Fixnums and nodes, raw addresses, issued logical code IDs
and typed table slots remain distinct. B's tagged value stack is unchanged;
integrating primitive calls into general Lisp call lowering remains LL05.

The fixture compares compiled native mathematical references with an
independent Python model, then runs the generated modules in one Node Worker.
The native reference uses numeric words and sparse memory, not native pointers.
Actual target memory grows to 2 GiB plus one page. Header loads use the D1
negative displacement at low, below-2-GiB, above-2-GiB and final placements.
Synthetic pointers near 4 GiB are converted only. Whole owned memory regions
are checked on returns and refusals; untouched gigabytes are not scanned.

The array payload calculation checks the exclusive 2^24 element limit
without allocating a large array, and checks multiplication overflow separately.
A monotonic ID registry proves issuance and exhaustion. Slot validation checks
actual table size/presence and owner-supplied signature/role metadata; accepted
slots dispatch a generated identity function. The same bits 4 are exercised
as issued ID 1 and slot 4, with the wrong handle kind refused. The registries
are single-owner and stable during use. No full loader, concurrent registry,
reclamation, allocator or Lisp condition system is claimed.

Twenty one-site compiler mutants are compiled through the same front end and
rejected by the unchanged result, refusal and memory oracles. Native R6/R6a
uses the accepted pristine 1A baseline, a new registered build/test and a new
removal build. The upstream kernel and main checkout are untouched by this
proposal. Integration follows Claude review and user acceptance.

```sh
python3 tests/wasm/stage1/conversions/native.py \
  --evidence ../ccl-evidence --work "$NEW_WORK" --output "$NEW_NATIVE"
python3 tests/wasm/stage1/registration/qualify.py \
  --output "$NEW_NATIVE" --inputs ../ccl-evidence/macos-u1-inputs \
  --kernel ../ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 \
  --destination "$NEW_QUALIFICATION"
python3 tests/wasm/stage1/conversions/run.py \
  --evidence ../ccl-evidence --native "$NEW_NATIVE" \
  --qualification "$NEW_QUALIFICATION" --output "$NEW_OUTPUT"
python3 tests/wasm/stage1/conversions/verify.py \
  --packet "$PACKET" --evidence ../ccl-evidence
```

The retained verifier hydrates references to unchanged evidence, replays the
native qualifier, recompiles every positive and mutant compiler, compares
binaries, and reproduces all executions. Failed development captures are
retained separately; none is promoted to a passing result.
