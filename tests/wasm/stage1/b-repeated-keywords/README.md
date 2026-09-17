# Repeated keyword aliases

Auxiliary compiler proposal over the accepted LL10 backend. It permits distinct
lambda variables to name the same keyword, matching native U1 CCL on the reference
Mac. Only the first formal receives the first supplied actual value. Later
formals still evaluate their defaults in lambda-list order, with false supplied-p
flags. Duplicate **variable** names remain refused.

For example, calling `(lambda (&key ((:x a) 1) ((:x b) 2)) (values a b))`
with `:x 9 :x 7` returns `9, 2`. Previously the source validator refused this
lambda list. Simply removing that refusal would incorrectly bind both variables
because the existing emitter tested every formal independently.

`backend.py` changes two anchored sites in the accepted compiler generator:
it admits duplicate keyword names and emits the supplied-value match only for
the first occurrence in the front end's source-ordered keyword vector. Default
initialization, supplied-p staging, dynamic binding, and first-actual-wins handling
are unchanged. The additional selection happens at compilation, with no added
runtime instructions for unique keyword names. Shared compiler and runtime files
are unchanged pending adversarial review and acceptance.

The native-derived corpus adds 22 forms, each executed at 1 MiB, 2 MiB and 2 GiB:
missing and NIL values; repeated actuals; three and nonadjacent aliases; implicit
and explicit names; dependent and effectful defaults; direct, indirect, APPLY,
literal, multiple-value and escaped-closure calls; special parameters and unwind;
repeated `:allow-other-keys`, unknown keys and odd argument lists. The complete
constants follow-up also runs, including native cross-function identity and
identity-based restoration. There are 136 modules, 311 native-derived comparisons
(66 new), and nine additional cross-function identity comparisons. The harness
uses a 16-word output reservation for six-value probe results and checks that all
six binding-vector slots are restored after every invocation.

Three separately recompiled mutants bind every alias, bind the last formal, or
let the last actual win. Each fails its focused native oracle. Restoring the
original validator refuses the first new form, proving it exercises the new
admission. Native answers are retained separately for review. The inherited B,
conditions, call-error and lazy-installation corpus runs with the same proposal.
R6/R6a uses a fresh registered build and reversal in a pristine U1 copy, with the
accepted unchanged baseline referenced. This is not a new inventory slot.

From the repository root:

```sh
python3 tests/wasm/stage1/b-repeated-keywords/packet.py verify \
  --packet ../ccl-evidence/2026-09-17-stage1-b-repeated-keywords-r1 \
  --output /tmp/repeated-keywords-review
```

To produce independently, run `run.py --output NEW_DIRECTORY`,
`inherited.py --evidence ../ccl-evidence --output NEW_DIRECTORY`, and
`native.py --evidence ../ccl-evidence --work NEW_DISPOSABLE_DIRECTORY --output
NEW_DIRECTORY`. `packet.py retain` takes those directories as `--run`,
`--inherited` and `--native`. It qualifies the native run and references unchanged
baseline artifacts. Verification checks source and artifact identities, replays
native qualification, recompiles the proposed and mutant backends, and reruns the
inherited corpus; it does not repeat the two native builds.

Existing scope remains: owner-supplied keyword identities, keyword-package alias
names, private condition representations and the accepted collector exclusions.
No timing, ARM execution, acceptance or integration is claimed.
