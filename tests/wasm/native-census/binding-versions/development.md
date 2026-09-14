# Development record — 14 September 2026

Three original producer failures are retained with their executed source
snapshots, inputs, commands and tracebacks.

1. `run-r1` incorrectly required the loader's entry and return positions to
   match. The first real function reader entered after its opcode at position
   137 and returned after its payload at position 228. The correction checks
   file and opcode equality, forward position movement and paired reader
   identity; joins still use the entry position. The original events and the
   inspection script/output are retained.
2. `run-r2` expected a numeric symbol identity on every binding event. The
   stream encodes NIL as a literal atom, including calls that remove an already
   unbound NIL function cell. The correction preserves literal-NIL histories
   separately, without inventing a numeric identity or joining names. Equality
   with the removal event's intended sentinel identifies an already-unbound
   old value. Original failure and inspection are retained.
3. `run-r3` reached the graph/control checks but its same-name probe mutated
   the original symbol dictionary through an alias while constructing the
   second input. The correction copies the original observation before making
   the mutation and checks both parser output and history separation. Its
   original facts, histories, failure and exact source are retained. Two
   additional positive checks cover history separation and missing-change
   detection. This was a test-driver defect, not a native execution failure.

`run-r4` is the finalized producer run. The independent replay uses the same
original retained stream and requires identical analysis bytes. No native
session, source patch, FASL write or accepted-envelope mutation occurs here.
