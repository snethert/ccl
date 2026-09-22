# Bootstrap math and execution

**423 original definitions execute and match native (+41); 394 have non-NIL return witnesses (+39). The target worklist admits 1,993 of 2,231 parsed definitions (+10), still a lower bound.** This execution-first proposal builds on the accepted audit-153 integration. Bit-identical native execution, target-word comparisons and approximate libm comparisons are separate counters. The proposal remains isolated under this fixture pending Claude's review. It carries no LL15 credit.

This packet includes the requested shift-domain declaration, input-recipe work, the 22 active libm foreign-call sites, and the next portable operators. Four additional single-float `external-call` sites implement the same primitive interface, giving 26 single/double entries. It also binds the separately authorized admission integration and its final-file native/target qualification.

## Compiler and CCL source

The existing `CASE` forms gain `%SINGLE-FLOAT` (CCL's `%SHORT-FLOAT` source entry), `%DOUBLE-FLOAT`, natural left/right word shifts, and `MINUS1`. Unsigned-word logical operands use a checked 32-bit path when the front end proves their types; other logical arithmetic keeps its existing path. This lets CCL's original byte-order readers return the entire unsigned 32-bit range. No dispatcher override chain or consumer source rewriter is added.

The first remaining histogram entries include function-immediate reflection, native pointer allocation and the FFI exclusion. They remain named dependencies, not portable operator work. The four selected operators are the portable coercion and natural-shift entries; `MINUS1` is an additional small lowering and is explicitly marked unexecuted; its subtraction helper is exercised through the existing paths. The four requested operators all have source-emitted executed witnesses.

Input recipes also exposed `ARRAY-ELEMENT-TYPE`'s missing Wasm branch: its non-simple-vector arm vanished under target features. The proposal adds a branch in `l0-array.lisp`, using the native 32-bit element-type table and indices. Strings and signed/unsigned arrays now execute against native. This is implementation work, not a claim that compiling the old empty branch was correct.

`l1-numbers.lisp` keeps the native definitions and adds `#+wasm32-target` bodies at its destructive float primitive boundary. Each computes through the existing floating service, roots the destination, and copies the boxed result's payload after collection. Ordinary Lisp callers need no rewriting. The new source branches retain every original byte; inverse-edit and seventeen-profile reader checks establish the existing-target forms. Final native R6/R6a passes 21,843 tests, 144 identical FASLs and all 164 restored under the adopted source-location allowance.

## Numerical scope

Pinned, unmodified musl algorithms from the installed Emscripten 3.1.12 SDK are compiled into the existing private-memory `float.c` module. Their license and source hashes are in `libm/`. The runtime calls no host `Math` function. This is a primitive implementation below CCL's Lisp definitions, not a new Lisp arithmetic implementation.

The new entries admit finite, correctly typed single/double inputs with nearest rounding. Checked inexact or underflow trap modes refuse before publication; those flags are **not qualified**. Known invalid, division-by-zero and overflow outcomes use the existing condition path. Unchecked mode validates the enable word and masks its effects, as the accepted arithmetic service does. Original operations 0–11 are unchanged and replay all 59,083 accepted raw cases at three placements.

The finite libm comparisons use a maximum two-ULP envelope and exact signed zeros. The 504 generated primitive comparisons contain 68 one-ULP differences; every difference is retained. Steve adopted pinned musl and this two-ULP comparison limit on 21 September 2026; see `doc/WASM/acceptance.md`. Signed zeros, exact results and domain conditions remain exact. The limit is not bit-identical native credit or a full-domain accuracy proof. The native oracle calls CCL's actual float primitives; it does not use CL EXPT's complex-number branch as the oracle for real POW. A separate raw harness compares seeded inputs against independent host Math, tests refusals and exact allocation fits, and complement-poisons the publication storage. It is test code only.

The service retains the existing owner boundary and JS capability call. It makes no new timing claim or claim that these entries use the accepted scalar fast path. Static libm data moves the private stack, so the build places it below the existing input region and the owner checks the exported stack pointer at construction. The raw module's imports remain exactly memory and the four accepted arithmetic detector functions.

Generated math calls run below and above 2 GiB, before and after movement, and force collection at assurance before every boxed result publication. Native condition witnesses cover log's zero and negative domains. A destructive-result witness compares both the returned value and destination contents with native and separately asserts target pointer identity; EQ on native float values is not an object-identity oracle. Four focused emitted-code faults check shift direction, coercion width, math operation selection and destination payload offset. These are not an exhaustive compiler-mutant sweep.

## Shift and recipe domains

`shift-domains.json` retains native 61-bit and target 30-bit payload answers separately, including both audit-153 examples. Zero-count shifts preserve their argument. Logical right shift exposes the unsigned payload at positive counts; left shift wraps, and arithmetic right shift sign-extends. The admitted-source inventory shows that LDB32 and ROTATE-HASH-CODE can receive negative values. Admission does not restrict every caller to the cross-width agreeing domain.

The review's 89 closed names include seven fixture/primitive names; 82 are original definitions. `progress.json` gives every original a disposition and lists the seven separately. New recipes use actual native structure constructors, observed argument mutation and global post-state. Remaining names are not credited by fabricating OS, stack, class-wrapper or stream state.

Unicode case recipes use the actual native table prefix needed by their selected inputs (1,024 entries); this is not a claim that the whole Unicode image fits the fixture heap. Sparse-vector read recipes clear the unused native lock after construction/population and exercise only reads. `(signed-byte 30)` input vectors are transported as values into the target's tagged fixnum-vector layout, instead of copying the host's upgraded s32 layout. Stream cycles, returned-closure consumers, full hash wrappers and several representation-aware oracles remain explicit recipe work.

## Replay

From the project root, with the sibling evidence repository available:

```sh
python3 tests/wasm/stage1/bootstrap-math/packet.py verify \
  --packet ../ccl-evidence/2026-09-21-stage1-bootstrap-math-r2 \
  --output /tmp/bootstrap-math-replay
```

The verifier re-derives the proposal from the integrated tree, recompiles generated/native cases and both runtime binaries, reruns comparisons, controls and the reader matrix, and compares deterministic outputs. Native R6/R6a is reused only when the final proposal files equal its retained source hashes. `native.py` can rebuild it explicitly. Development failures are retained as original logs with diagnoses; no passing output is substituted for a failure.

## Audit 154 repair

R2 sets the logical FP trap word to native CCL's default (7) for **every** generated case. R1 incorrectly enabled it only for two case-name prefixes; its condition comparisons are superseded. CORE-LOG-CONDITION has neither prefix and compares zero, negative and ordinary inputs with native before and after movement at both placements. Restoring R1's name test fails this case. The original failure is retained by the control. The compiler, CCL source proposal and runtime are unchanged, so native R6/R6a is reused by their exact hashes.

The 44 remaining recipes in `progress.json` describe only the original cohort from audit 153. The current closed frontier has 77 names without recipes, including newly closed names; 44 is not the full remaining frontier or the LL15 remainder. The immediate-bignum uint32 proof refusal from audit 154 remains a compiler carry item.
