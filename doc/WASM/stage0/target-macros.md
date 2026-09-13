# Source-derived target macro slice — 13 September 2026

Status: executed; reviewed without defect by [Claude's twenty-fourth audit](claude-review.md) at cb516b22. Packet `NATIVE-TARGET-MACROS-R1`
is retained in `2026-09-13-target-macros-r1` and bound by the
[evidence index](../evidence/index.json).

The [isolated extension](../../../tests/wasm/native-census/target-macros/README.md)
reconstructs fourteen macros from eight pinned U1 source forms. Seven of these
macros are actually used, ten times, while CCL's real front end traverses
`lib/dumplisp.lisp`. This replaces dependence on inherited native expander bodies
for that specific slice. It does not qualify the complete macro environment.

| Source-derived material | Mechanism |
| --- | --- |
| `GVECTOR`, `ALLOCATE-TYPED-VECTOR` | Read from `library/lispequ.lisp`; each expander lexically includes the freshly read `TYPE-KEYWORD-CODE` definition from `level-1/sysutils.lisp`. The helper reads the current target descriptor. |
| `%ISTRUCT`, `%NULL-PTR` | Read directly from `library/lispequ.lisp` and `lib/macros.lisp`. Their complete expansions are checked. |
| Four `BASIC-STREAM` accessors | Re-execute the source definition of `DEFINE-ACCESSORS` on the source group, producing slot indices 0–3. |
| Six `PFE` accessors | Use the same source generator on the callback-entry group, producing slot indices 0–5. |

The accessor generator's constant definitions and `ADD-ACCESSOR-TYPES` forms
are not installed or executed. This is an accessor-expansion proof, not a full
replay of those top-level forms. The indices are Lisp vector element positions;
they establish neither Wasm byte offsets nor a callback runtime implementation.

All eight forms are read under the registered Wasm target with read-time
evaluation disabled. The ordinary host compiler then builds native functions
that can execute during cross-compilation. This is expected: macro code runs
on the compiler host, while the code it constructs is compiled for the target.
The native parser, compiler, ordinary compiler macros, descriptor accessors and
other bootstrap helpers remain dependencies of the accepted clean native image.
Their transitive target qualification is not claimed by rebuilding these forms.

Routing uses the original macro function's actual EQ identity and its operator
name. The private reconstructed function is called through a dynamically bound
macro hook. Global macro/function definitions are not replaced. A real local
`MACROLET` binding of `GVECTOR` still expands to its local constant, 42; a mutant
that routes by name alone is rejected. Original and selected callable IDs,
source slices, reader contexts, complete input/output syntax and invocation
sequence are retained. Uninterned symbols carry identity as well as print name.

The 293 traversal hook invocations are joined in order to the unchanged
driver's original records. Ten use the reconstructed macros; 283 retain
46 distinct expander identities as explicit remaining dependencies. One native
architecture dispatcher can serve multiple operator names, and one operator
can have multiple expanders. The identity check allows those real relationships.

## Verification and limits

Two fresh native sessions reproduce both raw captures byte-for-byte. The D1
istruct subtag, 130, appears in both expansion and actual acode. Temporarily
changing the diagnostic table entry to 234 changes both; the metadata is then
restored. An absent type signals the source helper's condition. No diagnostic
allocation or Wasm runtime execution occurs.

Four native mutants reject: use the host's subtag, substitute the wrong stream
slot, bypass source routing, and route a local macro by name alone. Twenty
checker controls reject omissions, insertions, incorrect source/helper/identity
joins, changed expansions, erased sensitivity/refusal and false qualification.
The reviewed description checker also passes on the genuine new traversal.
Hook and target state restore on normal and nonlocal return. Pristine U1 source
and FASLs remain unchanged; no shared-source patch or native rebuild is needed.

The development archive retains the two initial native failures caused by a
directory pathname missing its trailing slash, with their original sources,
commands and logs. It also retains reproductions of two checker development
failures: incorrectly requiring each dispatcher identity to have one operator
name, and expecting an order error when deletion of the last event correctly
raised a count error. Initial checker failures appeared in the session; their
retained logs are explicitly labeled reproductions. No failed runtime binary
was produced or overwritten.

The traversal still captures seven definitions, two top-level initializer bodies
and four deferred initializers: 22 prototypes, 74 calls and twelve references.
Five foreign/file-boundary stops and seven unbounded calls remain. No widening
edge is replaced and no new gate credit is claimed. Stage 0 remains **28 accepted,
19 missing and one awaiting review**, the latter being S0-LL02-a.

Next census work must extend source reconstruction to the remaining expanders
and their target-sensitive helpers, then handle the five boundary stops under
their existing contracts. Generalizing top-level traversal and walking the
remaining source modules still precede complete call bounds and LL15 closure.
