# Generated callable objects, live bindings and recursion

This auxiliary LL05 proposal replaces opaque function handles and the host
name resolver with generated Wasm checks and table dispatch. All Lisp calls,
including named calls, resolve at dispatch. FUNCTION reads the current symbol
function cell; quoted symbols stay designators. Old retained function objects
continue to use their own code IDs after a binding changes. Table linking also
permits self-recursion and mutual recursion without cyclic module imports.

The fixture materializes a proposed logical function object: a D1 node header
with five tagged words (code ID, environment, version, arity metadata, debug
metadata). It uses D1's existing seven-slot symbol and fcell offset. The
[layout](layout.json) is checked against the adopted D1 schema. Native embedded
code vectors are not inherited. Object construction, closure capture and the
production image loader are not implemented here.

The generated resolver checks the tag, complete header and memory extent,
positive tagged code ID/version, issued registry range, version equality,
signature, role, table bounds and non-null entry. It resolves symbols once,
replaces the rooted designator with the function object and passes that object
as SELF. Every child call uses the accepted B protocol and result budget.
Registry metadata is owner-supplied: loader authentication of table entries
remains required. A corrupt actual Wasm signature paired with dishonest
registry metadata is outside this unit's claim.

The source compiler emits real frontend IR for quoted symbols, FUNCTION,
named and computed calls, APPLY and recursion. Python, native CCL and Wasm
compare results, identities and heap effects, including changed bindings and
retained old functions. The fixture resets symbol cells between cases; native
setup changes and restores the corresponding native cells. It does not claim
a generated SETF/SYMBOL-FUNCTION implementation or concurrent publication.

Both low and above-2-GiB stack placements run, with ordinary table entries and
transparent Wasm observation wrappers. The wrapper checks resolved SELF and
physical root ownership. Negative cases cover malformed and truncated headers,
end-of-memory objects, symbol chains, unbound cells, code/version corruption,
registry substitutions, missing slots and checked recursive stack exhaustion.
Distinct objects sharing code retain their separate environment fields; that
is not a proof of capture semantics. Compiler mutants are recompiled through
CCL and rejected by the unchanged oracles.

No LL05 inventory slot is claimed. Full conditions, lexical closure allocation,
GC/safepoints, lazy installation and tail transfers remain. APPLY's validation
and copy still require no intervening execution or concurrent list mutation.

```sh
python3 tests/wasm/stage1/b-callables/native.py \
  --evidence ../ccl-evidence --work "$NEW_WORK" --output "$NEW_NATIVE"
python3 tests/wasm/stage1/registration/qualify.py \
  --output "$NEW_NATIVE" --inputs ../ccl-evidence/macos-u1-inputs \
  --kernel ../ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 \
  --destination "$NEW_QUALIFICATION"
python3 tests/wasm/stage1/b-callables/run.py \
  --evidence ../ccl-evidence --native "$NEW_NATIVE" \
  --qualification "$NEW_QUALIFICATION" --output "$NEW_OUTPUT"
python3 tests/wasm/stage1/b-callables/verify.py \
  --packet "$PACKET" --evidence ../ccl-evidence
```

The replay requalifies R6/R6a and recompiles every positive/mutant binary.
Unchanged native evidence is referenced rather than duplicated.
