# Retained-build binding versions

This diagnostic consumes the original rich-build stream and the reviewed
build-flow facts. It runs no native session and modifies no shared source.
Every global-call symbol is joined by its original identity, never its name,
to the before/after inventories and observed function-cell store hooks.

`collect.py` reads the entire stream, validates sequence and completion counts,
and decodes only inventories, bindings and FASL function transfers. Function
objects, macro wrappers, special-operator wrappers and the witnessed unbound
sentinel remain distinct. The wrapper marker comes from U1's native x8664
xloader, not the Wasm layout. NIL is a distinguished literal in this observer's
encoding and retains that identity without an invented numeric symbol ID.

`history.py` retains all observed versions. An installation is recorded after
the store; a removal records its old value and intended sentinel before the
store. Removal completion is never manufactured by replay. Confirmed values
separated by no removal intent are compared for unobserved changes. A missing
checkpoint entry is not treated as proof that a symbol is unbound: enumeration
also depends on package and SETF registry membership. Generic-function internals
and closure environments are not bounded by prototype identity.

Ordinary functions join to materialized compiler bodies directly, or through
the latest preceding FASL write at the loader's exact file/opcode position.
Entry position is after the opcode; return position is after the whole function
payload. Native reader identities are checked; cross-dump image words never
become native code IDs. A resident-before identity without a witnessed source
body remains a body obligation. Macro expander prototypes remain in the history
and never enter the ordinary-call candidate list.

`links.py` retargets each of the 98,213 global-call edges to its actual symbol
cell and gives that cell one **unresolved** edge holding its observed ordinary
prototypes. A complete caller-to-cell edge means the designator is known; the
next unresolved edge explicitly prevents interpreting it as a complete callee
bound. The patch removes only obsolete name placeholders whose final incoming
edge was replaced. Builtin placeholders, all computed calls, old widening
families, seeds, initializers, module dispositions and trace mappings remain
unchanged. Body links to the previously unattached assembly population remain
open; this derivative does not traverse assembly.

The checker derives the exact permitted patch from the pinned original calls
and checked histories, including whole node records and edge multiplicity.
It is a consistency checker sharing construction helpers with the producer;
the raw-stream replay and adversarial review are separate checks. Controls
damage versions, symbol IDs, roles, write generations, obligations, endpoints,
membership and scope. Positive probes keep equal names with different symbol
IDs separate, keep an unknown wrapper unclassified, and report an omitted
change as a continuity gap.

Run from the repository root, using the previously verified wrapper graph:

```sh
python3 tests/wasm/native-census/binding-versions/run.py \
  --evidence /Users/buildsomething/Source/ccl-evidence \
  --base /private/tmp/ccl-wrapper-work-r2/census.json.gz \
  --output /tmp/ccl-binding-versions-fresh
```

`inputs.json` pins the graph and four direct evidence inputs. The base can be
reconstructed by the reviewed boot-wrapper verifier if its temporary copy is
gone. No earlier native build or accepted envelope needs to be rerun.

`verify.py` takes `--packet`, `--evidence`, `--base` and a fresh `--work`
directory. It checks this packet and its direct dependencies, replays the
original stream, revalidates the full graph and reruns the controls. All five
analysis outputs must reproduce byte-identically. The packet is diagnostic:
there is no accepted LL15 envelope, exhaustive runtime bound or target
qualification claim.
