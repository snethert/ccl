# Target DEFTYPE expansion order — 13 September 2026

Status: executed; independent review pending. Packet `NATIVE-TARGET-ALIASES-R1`
is retained in `2026-09-13-target-aliases-r1` through the
[evidence index](../evidence/index.json). This follows Claude's thirty-first audit
and the user's request to investigate its alias observation.

The observation exposed a real defect in the inherited cross-target path. For
`(deftype target-small () 'fixnum)`, the prior wrapper translates TARGET-SMALL
unchanged, then native TYPEP expands it to the host's FIXNUM. It consequently
folds `(typep 536870912 'target-small)` to true. D1 makes that integer a boxed
object, so the correct answer is false. Aliases for BIGNUM, chains and compound
types expose the same ordering problem. Native CCL's answers remain appropriate
for its own representation.

## Correction and witnesses

The [isolated driver](../../../tests/wasm/native-census/target-aliases/driver.lisp)
reads ten literal DEFTYPE forms in the Wasm target context. It follows U1's
EXPAND-TYPE-MACRO constructor through PARSE-MACRO-INTERNAL, including the optional
argument default, and compiles private expander functions. It inserts these only
in a dynamically copied expander table; it does not invoke the global %DEFTYPE
installer or claim to traverse arbitrary top-level DEFTYPE forms yet.

For these aliases, expansion now precedes target translation and native
membership/canonicalization. Newly exposed OR, AND and NOT operands recurse;
FIXNUM uses the source target translator, and BIGNUM uses its complement within
INTEGER. MEMBER values and explicit numeric bounds remain data. The native
ctype optimizer's cross-target refusal remains in force.

| Witness | Executed result |
| --- | --- |
| Constant tests through CCL's actual front end | 16: nine true, seven false; ten differ from the prior path |
| Recursive optimizer | Five expansions, each evaluated on five values; three expose wrong prior answers |
| Expansion provenance | Ten source-defined aliases, 52 successful expansion edges, 209 helper trace records |
| Bounded refusal | Cyclic alias rejected; endlessly growing alias rejected after the expansion allowance |
| Native mutations | Prior builder, expansion after translation, shallow translation, rewriting MEMBER data, uncorrected canonicalization: all five rejected |
| Checker controls | Twenty rejected, including false IR, ordering, routing, file joins and surplus/omitted alias edges |

The canonicalization-only mutation passes all constant probes, because its
membership wrapper is still correct, but fails the optimizer probes. This
separately witnesses the path Claude identified. OR's recursive optimizer
already repairs some exposed leaves in the old path; the packet does not claim
every alias expansion was wrong.

The independent Python oracle checks constant membership against D1, actual IR,
macro input/output and routing, and interprets the bounded optimizer expression
language separately from native evaluation. Target normalization precedes each
recorded membership/canonicalization call. The successful alias-edge sequence is
reconstructed from the literal definitions, including chains and parameters.
The ten restore-file TYPEP events remain joined to their helper records.

## Bounds, reproduction and remaining work

This qualifies the supplied alias forms and their type positions. Arbitrary
user expander bodies, resident aliases, element-type positions such as array
members, native type-system/class objects and general inference remain open.
The wrapper does not claim to bound the execution time of an arbitrary expander
body. Its own expansion allowance is 32 expander calls per normalization, with
64 levels of nested type syntax; cycles are explicit refusals.

The nonconstant expansions execute as native diagnostic functions. They are not
Wasm binaries and do not qualify nonconstant numeric target lowering. The
restore traversal still captures seven definitions with five boundary stops,
22 prototypes, 74 calls, twelve references and seven unbounded calls. This packet
replaces no widening edge and adds no LL15 gate credit.

The first formal producer and retained verifier pass. Normal and repeat captures
are byte-identical. Four corrected-builder mutants retain byte-identical file
traversals; the prior builder shifts the observer identity numbers. That
comparison requires an injective renaming of the identity namespace and exact
equality of every other field. No byte-identity claim is made across that shift.

Development caught three fixture setup mistakes: a helper accidentally used the
CL name PHASE and the native guard refused redefinition; an afunc inspector was
called on a compiled function; and a JSON object list was treated as a hash table.
Their original sources, commands, errors and partial outputs are retained. Later
development captures and intentional mutations are retained in the same compact
packet. Shared compiler/kernel source, source FASLs and global helper bindings
remain unchanged; the original expander table and temporary routing restore.
No observed image becomes an implementation baseline.

Stage 0 stays **31 accepted, 15 missing and two unreviewed required slots**.
S0-LL01-b awaits project acceptance; S0-LL02-b awaits independent review and
acceptance. The alternating plan next takes another standing control, then
returns to native object/helper qualification, the five boundary replacements
and broader source traversal.
