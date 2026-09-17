# LL10 constant encoder — first component

Run from the checkout root:

```sh
python3 tests/wasm/stage1/constants/verify.py
```

`Encoder.encode(descriptor)` returns either a tagged immediate word or complete,
8-byte-aligned, pointer-free object bytes. It performs no heap write or allocation
in the target. D1 supplies subtags, fixnum limits and scalar float offsets.
Integers use canonical decimal strings; floating values use exact-width lowercase
hexadecimal bit strings, avoiding host numeric conversion and NaN canonicalization.
Strings use lists of character codes. Specialized vectors use an explicit subtype
and element list; complex float elements are real/imaginary bit-string pairs.
The caller may set `max_bytes`; its default 16 MiB is an encoder resource budget,
not a Lisp array-size promise. Header counts are separately bounded to 24 bits.

Examples: `{'kind': 'integer', 'value': '536870912'}`,
`{'kind': 'string', 'value': [65, 128578]}`,
`{'kind': 'vector', 'type': 'fixnum', 'elements': ['-1', '536870911']}`.
Supported vector types are bit, s8/u8, s16/u16, s32/u32, fixnum, single-float,
double-float, complex-single-float and complex-double-float. D1 has no s64/u64
vector subtype. Single/double float scalar kinds use `value` for the bit string;
character and singleton (`nil`/`t`) kinds return immediate words.

The six test groups include literal byte oracles, integer sign-extension limbs,
float signed zeros/subnormals/infinities/NaN payloads, supplementary characters,
vector widths and padding, target range refusals, and header/resource limits.
Five semantic mutants cover host integer classification, reversed float bytes,
tagged string elements, tagged fixnum-vector elements and omitted vector padding.
The deterministic verification record pins implementation, tests and source inputs.

Source derivation: `xdump/xfasload.lisp` supplies headers, limb order, scalar floats
and allocation alignment; `x8632-misc-byte-count` supplies vector padding;
`x862-vset` explicitly unboxes fixnum-vector elements; x8632 bit-vector access uses
least-significant-bit-first indexing. The character code domain follows U1's
`lib/chars.lisp`, including its full range below #x110000.

This is an isolated supporting component, not S1-LL10-a execution or qualification.
No shared compiler or kernel changed and no native/Wasm comparison is claimed.
Pool graphs, identity/cycle linking, relocation, IR extraction, generated pool
loads and target round-trip remain the next parts of the saved LL10 plan. Keep
this component in that eventual final packet rather than creating a separate
acceptance or archive for it.

Development: the first oracle gave a two-element s16 vector sixteen bytes rather
than eight. Four header bytes plus four payload bytes already satisfy D1 alignment;
the encoder was correct. The original tests, encoder and failing output are in
`development/`. Source inspection also corrected the initial, unexecuted assumption
that fixnum-vector elements were tagged before the first test run.
