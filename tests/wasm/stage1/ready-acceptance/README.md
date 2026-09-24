# Reviewed READY compiler integration

This integrates the four compiler lowerings reviewed in audits 171–173,
byte-identical to READY R9: MAKE-STRING allocation, literal T/NIL type tests,
class-mode slot-unbound signaling, and packed bit vectors. It adds no
original-definition execution credit and no LL15 slot credit. The class-mode
default is unchanged (off); READY closure and callback obligations remain open.

The identity check runs on the integrated checkout:

```sh
python3 tests/wasm/stage1/ready-acceptance/check.py --output /private/tmp/ccl-work/codex/ready-integration/identity.json
```

It binds all 33 native-qualified source files and the runtime pins to R9,
including the unchanged worker's raw bit-tail and zero-padding checks. The
26,048 target comparisons and four cold boots are reused from reviewed R9;
this command reports no new execution. The raw byte observations must survive
any replacement harness: matching reads and writes alone cannot establish
low-bit-first representation (audit 173's mutant proves this).

The new compiler's `:bit-vector-kind` outcome is explicitly accepted as
`:admitted`. R9's isolated driver already applies that transition. Historical
parent fixture inputs retain their original refusal and replay at their own
source revisions.

Fresh native R6/R6a uses the final integrated files in a pristine U1 build:

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
