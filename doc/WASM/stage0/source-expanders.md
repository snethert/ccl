# Source expansion bodies for dumplisp — 13 September 2026

Status: executed; independent review pending. Packet `NATIVE-SOURCE-EXPANDERS-R1`
is retained in `2026-09-13-source-expanders-r1` and bound by the
[evidence index](../evidence/index.json).

Every one of the dumplisp traversal's **293 macro-hook invocations now selects
a function rebuilt from pinned source**. This extends the [reviewed first
slice](target-macros.md), which rebuilt seven of the expanders actually used.
The source-derived run and the inherited-expander reference produce identical
traversal bytes. Their expansion traces match field for field except for the
deliberately selected function identity. The missing kernel-pointer description
still produces the same error.

| Accounted-for material | Count |
| --- | --- |
| Source forms, including earlier helper/generator forms | 54 |
| Registry entries: ordinary macros / compiler macros / architecture names | 29 / 30 / 2 |
| Distinct rebuilt expander functions | 60 |
| Actual invocations: ordinary / compiler / architecture | 91 / 200 / 2 |
| Named helper references / distinct call-or-reference sites | 214 / 212 |
| Native helper binding names / unbounded helper call sites | 68 / 4 |
| Explicit native object references in expansions | 3 |

The two architecture names share one dispatcher function. `DOTIMES` has both an
ordinary macro and a compiler macro. These relationships explain the differing
counts; names alone cannot identify the binding. All 46 previously inherited
expander identities have source-rebuilt counterparts for this observed file.
Unused members of the earlier fourteen-macro registry remain available but add
no observed coverage.

## Reconstruction and comparison

The [manifest](../../../tests/wasm/native-census/source-expanders/manifest.json)
selects definitions by source, position, operator and binding role. An independent
Python scanner checks the end of each source form, including strings, character
literals and nested block comments. Lisp reads those forms with target state set
and read-time evaluation disabled. The ordinary native compiler builds private
host-executable functions from the macro bodies using U1's `PARSE-MACRO-1`.
This matches the construction in U1's `DEFINE-COMPILER-MACRO`; its global
installation forms are not evaluated. The architecture dispatcher is compiled
directly from its source function body.

The private registry stores both the original and rebuilt callable identities.
Routing requires the original identity and operator name, preserving local
macro bindings. Compiler macros that decline expansion must return the original
form by EQ, not merely a structurally equal copy. Every invocation records input,
output, source, binding role, target context, return identity and normal or
exceptional completion. Uninterned symbols retain identity as well as names.
Both source and reference sessions perform identical preparation before choosing
which functions to invoke; both callable IDs are allocated before that choice.

A temporary observer of the host backend's pass-2 entry records the actual
pre-pass-2 AFUNC and joins it to the returned native function. It forwards all
values from the original entry, observes only its owner process, and restores
the entry on normal and nonlocal exits. The compiler IR is read, not edited.
The original global macro/compiler-macro bindings and target state remain
unchanged. Source and on-disk FASLs also remain unchanged. This is isolated
in-memory compilation and observation, with no shared-source patch or native
build, and no generated Wasm code.

## Dependencies that remain open

Rebuilding the expander body does not reconstruct every helper it calls. The
recorded AFUNCs expose **68 native helper names**, from `PARSE-BODY` and `GENSYM`
to target-sensitive helpers such as `OPTIMIZE-TYPEP` and
`NX-LOOKUP-TARGET-UVECTOR-SUBTAG`. Each named reference joins its real compiler
site to the current function identity and source note. Four computed call sites
remain explicitly unbounded, in the DECLAIM, SETF, APPLY and architecture
dispatcher bodies. The 214 helper rows include the shared dispatcher's repeated
binding view; there are 212 distinct named-reference sites.

The three object references are identified, not unexplained data: a compiler
lexical environment used by declaration processing, the `IOBLOCK` class cell,
and the `RESTART` class wrapper. Type, name where applicable, identity and exact
expansion uses are retained. Their full contents and target materialization are
not qualified here. Helper calls may themselves expand macros or consult native
type information; reconstruction of the visible hook bodies alone does not
prove transitive target independence. The environment therefore remains marked
unqualified, and no widening edge or required startup dependency is removed.

The actual source-file result remains seven captured definitions, two top-level
initializer bodies and four deferred initializers: 22 code prototypes, 74 calls
and twelve references. Five foreign/file-boundary stops and seven unbounded
calls in that file remain, separate from the four helper call sites above.

## Verification and next work

Two source runs reproduce both raw captures byte-for-byte; the inherited run
produces identical traversal bytes and equivalent expansion events. The stream
subtag appears as 50 in both expansion and actual acode. Changing only the test
descriptor to 122 changes both, then restores it. A local DOTIMES macro still
returns 42. The no-change compiler-macro probe preserves EQ identity.

Four native mutants reject: bypass the rebuilt IF, read host layout metadata,
copy a compiler macro's unchanged input, or route by name alone. Twenty-seven
checker controls reject omissions, insertions, incorrect joins, changed expansion
semantics and false qualification; five independent parser cases pass. The
earlier description checker also passes on the new traversal.

The development archive retains the initial name-only mutant's diagnostic-encoder
failure and the two scanner refusals on SETF block comments, with original
sources and logs. The final name-only control retains the wrong IR and is
rejected specifically for losing local-shadow precedence. The first formal
run succeeded. Earlier successful diagnostic iterations are retained in the
same compact archive; no earlier packet or runtime binary is overwritten.

Stage 0 remains **29 accepted, 19 missing, zero unreviewed required slots**.
This packet is a census input awaiting independent review; it does not close a
required slot.
The next census work is to qualify or explicitly bound the exposed helper and
object dependencies, resolve the five boundary stops under their existing
contracts, and generalize top-level traversal to the rest of the source tree.
The alternating plan still calls for an independent standing control or the
B desk-decision record between census deliverables.
