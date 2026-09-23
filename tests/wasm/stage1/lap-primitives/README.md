# Target definitions of native LAP entries

Written by Claude on `wasm2-claude-lap`, reviewed by Codex and accepted by
Steve. Fifty-six
of the LAP entries that the 4,369 live startup functions call (audit 159's
platform classification, `lap-nosource` class) get ordinary Lisp
definitions in [`level-0/WASM32/w32-lap.lisp`](../../../../level-0/WASM32/w32-lap.lisp),
with `level-0/X86/X8632` as the semantic reference.

Four backend lowerings are added to `wasm32-backend.lisp`, and the float
service gains square root as operations 44 and 45:

- `%WASM-FLOAT-WORD` / `%WASM-SET-FLOAT-WORD` read and write one raw word of
  a float object (single: word 0; double: 0 low, 1 high) as an
  `(UNSIGNED-BYTE 32)`, after the existing real-operand and index checks.
- `%WASM-FIXNUM-QUOTIENT` / `%WASM-FIXNUM-REMAINDER` are `i32.div_s` and
  `i32.rem_s` on two fixnums; the Lisp `%FIXNUM-TRUNCATE` handles the zero
  and `-1` divisors before calling them.
- `%WASM-FLOAT-TO-FIXNUM` converts a float to a fixnum, truncating or
  rounding to nearest even, after an exponent check that keeps the Wasm
  conversion trap unreachable and a range check on the result.
- `%WASM-STRIP-TAG` is the native `STRIP-TAG-TO-FIXNUM` computation.
- `sqrt`/`sqrtf` from the pinned musl sources already in `libm/` become
  transcendental operations 44 and 45 in `float.c`, `transcend.c` and the
  owner's operation ceiling in `float-service.mjs`; the existing
  classification reports a negative argument as an invalid operation.

`level-1/l1-clos.lisp` gains `#+wasm32-target` branches at the three sites
where other targets clone the slot-id LAP prototypes; the target calls the
closure constructors in `w32-lap.lisp` instead.

## Execution

The fixture runs on the generic-dispatch driver over the integrated tree:
`backend.py` derives no patch; the unit applied to the pristine U1 copy is
every source under `compiler/`, `level-0/`, `level-1/`, `lib/`, `library/`
and `xdump/` that differs from U1, as committed. `run.py` compiles the
corpus with `w32-lap.lisp` as a whole file and executes it against the
64-bit native image: 28 entries whose contract does not depend on word size
run directly against the image's LAP functions (185 cases); thirteen probes
carry those whose 64-bit contract differs (`%STRING-HASH` and `%PNAME-HASH`
against a native reference fold, `%ALLOCATE-LIST` without the native second
value, the conditional stores with target-relative offsets,
`%MAKE-SHORT-FLOAT-FROM-FIXNUMS`, single-float square root and the invalid
case, `STRIP-TAG-TO-FIXNUM` by class of answer, `CALLED-FOR-MV-P`, an
overlapping gvector copy, and the NIL symbol-pointer round trip); and the
five bignum digit entries execute through their unchanged original callers
`FIX-BIG-LOGAND`, `FIX-BIG-LOGANDC1`, `FIX-BIG-LOGANDC2`, `LOGTEST-FIX-BIG`
and `BIGNUM-LOGTEST` (188 cases). `check.mjs` adds the review's boundary
cases: nearest conversion refuses with checked code 5, never a trap, at
536870911.5, 2147483647.49, 2147483647.5, 2147483647.75, ±2^31,
-536870913.5, NaN and infinity, while 536870911.4, -536870912 and
-536870912.5 convert. Truncating conversion has its own refusal list;
536870911.5 truncates to the valid fixnum 536870911. The whole corpus passes 25,772 comparisons at both
placements before and after movement, with the generic-dispatch structure,
population and owner checks; nothing earlier is lost.

Not yet executed: `%ARRAY-HEADER-DATA-AND-OFFSET` (its probe needs a
displaced `MAKE-ARRAY`), the three hashes with no oracle (`%DFLOAT-HASH`,
`%SFLOAT-HASH`, `%BIGNUM-HASH`), the slot-id closures (need class
fixtures), `FAST-MOD-3`, `SET-%SHORT-FLOAT-EXP`, `%FUNCTION-REGISTER-USAGE`.

Codex's review (`71026330`) found three defects in the first two commits,
all corrected here: `%SYMPTR->SYMBOL` now recognizes NIL's symbol pointer
first; the conversion guard admits magnitudes below 2^30 so that rounding
cannot reach the conversion trap; the proposed `CLASS-OF`, `FALSE` and
`%ILOGCOUNT` are withdrawn in favour of the integrated definitions.

```sh
python3 tests/wasm/stage1/lap-primitives/run.py /tmp/ccl-lap-run
```

## The two design concerns, as resolved

- `LOGAND`, `LOGIOR` and `LOGXOR` keep the word path when both operands are
  proven `(UNSIGNED-BYTE 32)` and the fixnum path when every operand is a
  fixnum at run time. Any other integer operand now goes, two at a time from
  the rooted operand frame, to CCL's own `LOGAND-2`, `LOGIOR-2` or
  `LOGXOR-2`; a non-integer is a type failure. The generic corpus witness
  `CORE-LOGICAL` therefore returns its six values on a bignum instead of
  refusing with code 32.
- `float.c` no longer carries a copy of the transcendental switch: it
  includes `transcend.c`, which is the one authoritative text, and
  `build-float.py` copies both into the build directory.
