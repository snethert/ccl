# Target numeric and layout helper paths — 13 September 2026

Status: executed; reviewed without defect by [Claude's twenty-seventh audit](claude-review.md) at 2c08b98c. Packet `NATIVE-TARGET-HELPERS-R1`
is retained in `2026-09-13-target-helpers-r1` and bound by the
[evidence index](../evidence/index.json).

The next helper slice exposes a concrete host/target mismatch in the previously
unqualified macro environment. Native `EQL-IFF-EQ-P` rewrites `(eql x 1.0f0)` and
`(eql x 536870912)` to EQ on this 64-bit host. Wasm32/D1 boxes those values, so
that substitution is invalid for the target. This is a defect in inheriting
native compiler-helper assumptions for the census, not in native CCL or the
accepted runtime fixtures. The new probes reproduce the mismatch; the existing
dumplisp traversal does not encounter it and remains byte-identical.

## Source construction and target behavior

The isolated [driver](../../../tests/wasm/native-census/target-helpers/driver.lisp)
reads `EQL-IFF-EQ-P` under the registered target's reader state, removing its
64-bit-only single-float branch. Source reading alone does not repair native
`FIXNUMP`: the private helper lexically binds that call to the body of U1's
`NX1-TARGET-FIXNUMP`, which reads the current target architecture's bounds.
The private EQL compiler macro includes this helper through FLET and uses the
existing source-expander construction and routing. Global function cells are
unchanged.

The same mechanism rebuilds `NX-LOOKUP-TARGET-UVECTOR-SUBTAG` for the private
BASIC-STREAM-P and VECTORP compiler macros. This lookup consults the active target
descriptor and retains its unsupported-type condition. Seven source reads cover
six distinct pinned forms; one helper is deliberately read a second time under
host state for a rejection control. Five compiled functions include the three
selected entries and two deliberately incorrect EQL alternatives. Actual AFUNC
records join each returned native function to its compiler input.

| Numeric constant | Required expansion under Wasm32/D1 |
| --- | --- |
| 0, 536870911, -536870912 | EQ |
| 536870912, -536870913, 1152921504606846976 | EQL |
| Single float 1.0f0, double float 1.0d0 | EQL |

Each of these eight probes also goes through the real front end. Immediate cases
have an EQ operator and no call; boxed cases retain a builtin call to EQL at
index 10 in U1's pinned builtin vector. The captured target has 32-bit words,
fixnum shift 2 and signed 30-bit bounds, matching D1's x8632 source basis.
These are compiler-IR checks; they do not execute generated Wasm equality.

Five descriptor probes record stream tags 50 and 122, the target range, a
temporary range of [-8, 7], and a missing BASIC-STREAM description. Changing the
range makes `(eql x 8)` retain EQL. Removing the description produces the actual
unsupported-type condition. Temporary descriptor changes are protected by
`unwind-protect`, and the restored lookup is checked afterward.

## Genuine traversal and remaining scope

All 293 expansion events in the dumplisp traversal remain source-routed. The
three selected entries account for 21 events and 40 recorded helper calls:

| Compiler macro | Expansion events | Helper calls |
| --- | ---: | ---: |
| EQL | 17 | 34 |
| BASIC-STREAM-P | 2 | 2 |
| VECTORP | 2 | 4 |

Every helper call is joined to its parent macro event. The checker checks inputs,
answers, short-circuit behavior, lookup keys/values and the resulting expansion.
Normal/repeat raw captures match byte for byte. All six native sessions, including
the inherited-helper reference and deliberately incorrect modes, produce the
same dumplisp traversal bytes. Its seven captured definitions, five boundary
stops, 22 code prototypes, 74 calls, twelve references and seven unresolved calls
are unchanged. No prior packet or graph is rewritten.

The earlier inventory exposed 68 native helper names. This slice supplies two
of those bodies in three private macro entries, plus the target fixnum predicate;
66 other original helper names remain outside the slice. That count is not a
claim that the two helpers are now qualified for all inputs. In particular,
`NX-FORM-TYPEP` still uses native inferred type facts for nonconstant expressions.
`OPTIMIZE-TYPEP`, transitive helper calls, the four computed helper sites and the
three native object references from the preceding packet remain unqualified.
This result bounds the numeric constants and layout paths tested here. Full
macro-environment qualification and source closure remain open.

## Verification and retention

Four native controls reject: the inherited helper and the host-range mutation
fail the boxed-integer oracle; the host-reader mutation fails the single-float
oracle; host subtag selection fails the target-descriptor oracle. Fifteen checker
controls reject missing or inserted records, wrong call/event joins, wrong EQL
builtin targets, incorrect helper answers, lost restoration and false scope
promotion. The retained packet verifier replays these checks and direct source
bindings without scanning earlier evidence payloads.

Two development native sessions failed while loading the fixture: an unmatched
closing parenthesis, then a missing closing parenthesis in later metadata work.
Both original drivers, commands, exit codes and logs are retained in the single
development archive. Successful exploratory captures and the inherited-defect
witness are retained there too. Early source/reference captures allocated IDs
in a different order; preallocating identities repaired that comparison without
changing file semantics. The first formal run succeeded. No failed emitted binary
existed: private compiler functions were built only in memory.

The experiment uses a disposable U1 copy and the retained clean r7 image. Source
and on-disk FASLs remain unchanged. Temporary routing, target descriptors and the
owner-only pass-2 observation are restored; global helper bindings are preserved.
Implementation still starts from clean U1 source and bootstrap.

Stage 0 remains **30 accepted, 18 missing, zero unreviewed required slots** after
the separately committed B acceptance. This diagnostic awaits independent review
and earns no gate credit. The alternating plan next takes an independent standing
control, then resumes helper/type/object qualification, the five boundary
replacements and wider source traversal.
