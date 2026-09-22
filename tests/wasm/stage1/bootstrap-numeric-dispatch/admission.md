# Digit primitive admission

The direct checks are in `bignum-check.mjs`; a Wasm trap is never accepted as a
checked refusal. The raw entries are internal LAP replacements over typed
bignums, including non-normalized scratch bignums. They do not claim canonical
integer-service input validation or an arbitrary-memory capability boundary.

| Predicate | Deciding case or contract |
| --- | --- |
| Object has tag 6 | NIL, fixnum and character passed to the digit reader |
| Header is backed | Object at memory end |
| Header subtag is 7 | Simple-vector header in otherwise backed storage |
| Digit count is positive | Subtag-7 zero-count header |
| Entire rounded payload is backed | Three digits declared in the final eight bytes of memory |
| Digit index is a fixnum | Character index |
| Digit index is below count | Index equal to count and negative index (unsigned bound) |
| Both store halves are fixnums | Separate high-half and low-half character cases; signed halves are admitted and truncated as native compose-digit does |
| Resize count is a positive fixnum no larger than the old count | Zero, character, count above old count and negative count |
| Allocation count is positive and fits the 24-bit header count | Zero, character, negative and first count above header capacity |
| Copy destination has a bignum object | NIL destination; the same object validator implements source and destination checks |
| Byte offsets/count are nonnegative fixnums | Negative source offset and character count; one identical loop applies the same predicate to all three operands |
| Copy source extent fits | Source starts one byte late with full payload count |
| Copy destination extent fits | Destination starts one byte late with full payload count |

The tag itself aligns the raw object base. The header count is at most 24 bits,
so rounding its four-byte words cannot overflow an i32. Copy arithmetic uses
i64 before comparison. Native `memory.copy` supplies overlap semantics, tested
in both source/destination objects and within one object. No call or allocation
occurs between validation and a digit store, header change or copy. Operand
evaluation uses the existing rooted `bootstrap-operands` path.

The allocation helper retains the existing owner assurance and root reload;
these checks are not duplicated here. The direct shortening cases check both
zero padding and valid tail objects, then collect with the resized object live.
