# Reviewed READY compiler integration

This integrates the four compiler lowerings reviewed in audits 171–173,
byte-identical to READY R9: MAKE-STRING allocation, literal T/NIL type tests,
class-mode slot-unbound signaling, and packed bit vectors. It adds no
original-definition execution credit and no LL15 slot credit. The class-mode
default is unchanged (off); READY closure and callback obligations remain open.

After the R10–R12 integration supersedes this backend, the standing check
binds the R9 product sources at their integration commit `7668f42d` and the
raw bit-layout observation in the current harness. It does not claim that the
current backend is still R9. Use `ready-runtime-acceptance/check.py` for the
current stack. The historical check runs from the current checkout:

```sh
python3 tests/wasm/stage1/ready-acceptance/check.py --output /private/tmp/ccl-work/codex/ready-integration/identity.json
```

It binds all 33 native-qualified source files and runtime pins at `7668f42d` to R9,
including the exact raw bit-tail and zero-padding observation in the current
worker. Unrelated later worker witnesses may change; the independent byte
check, its two lengths and collection loop must remain byte-equal to R9. The
26,048 target comparisons and four cold boots are reused from reviewed R9;
this command reports no new execution. The raw byte observations must survive
any replacement harness: matching reads and writes alone cannot establish
low-bit-first representation (audit 173's mutant proves this).

The new compiler's `:bit-vector-kind` outcome is explicitly accepted as
`:admitted`. R9's isolated driver already applies that transition. Historical
parent fixture inputs retain their original refusal and replay at their own
source revisions.

At commit `7668f42d`, fresh native R6/R6a used the final integrated files in a
pristine U1 build (run this historical command at that revision):

```sh
python3 tests/wasm/stage1/ready-acceptance/native.py --output /private/tmp/ccl-work/codex/ready-integration/native
```

Use a new output directory. `qualification.json` binds all source hashes,
the native result hash and elapsed time; a generic native-run record alone
is insufficient. Retain results before deleting the managed output tree.

Full READY R9 replay remains `tests/wasm/stage1/ready/packet.py verify` **at
commit `f48be155`**, using its documented arguments. Its patch generator and
pins intentionally precede integration; it is not a replay command for this
integrated checkout. No old fixture is modified to manufacture compatibility.

The acceptance is recorded in
`doc/WASM/stage1/acceptance-ready-compiler.json`. O-58 remains disclosed: the
unreached slot-unbound `%error` fallback has a NIL frame argument.
