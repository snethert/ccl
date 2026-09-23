# LAP acceptance and integration

Steve accepted Codex's second review with “accept”. The final proposal is
`27f5bc02`, including the preceding `964eb005` and `7f6a4208`. The review is
`c47b0a47`. Integration copies the seven functional files byte for byte and
corrects only documentation. There is no LL15 completion credit.

The reviewed corpus admits 56 target LAP definitions. It runs 28 entries
directly against native LAP (185 cases), thirteen architecture/protocol
probes (49 cases), and five bignum entries through their original callers
(188 cases). The full inherited corpus passes 25,772 comparisons. The review
adds 504 logical-operation comparisons, including full-heap allocation retry.
The two execution modes and their existing collector/owner checks are reused
by exact source and artifact hashes; integration adds no new execution credit.

Native qualification uses the final source, the existing source-location
comparator and the pristine U1 baseline:

```sh
python3 tests/wasm/stage1/lap-acceptance/native.py --output /tmp/ccl-lap-native
python3 tests/wasm/stage1/lap-acceptance/readers.py --native-output /tmp/ccl-lap-native --output /tmp/ccl-lap-readers
```

Run this at the integration commit. The runner checks source identity against
the reviewed commit before building, so later source changes must use their
own qualification. The original target replay remains:

```sh
python3 tests/wasm/stage1/lap-primitives/run.py /tmp/ccl-lap-target
```

The generic logical fallback calls CCL's own LOGAND-2, LOGIOR-2 and LOGXOR-2;
it does not duplicate bignum arithmetic. Ordinary file compilation keeps
allocation retry off by default; the pressure probe explicitly enables the
existing mode for the library callees. The scalar fast path and fixnum path
are preserved. The float service's single transcendental switch includes
square-root operations 44 and 45.

The declared unexecuted entries remain uncredited: slot-id closures,
displaced-array data/offset access, the three hashes lacking an oracle,
FAST-MOD-3, SET-%SHORT-FLOAT-EXP and %FUNCTION-REGISTER-USAGE. Runtime/thread
LAP, real image installation and the READY join remain separate obligations.
