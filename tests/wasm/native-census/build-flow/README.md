# Retained-build IR and call/code joins

This derivative consumes the reviewed sequential native build, not the later
164 independent file sessions. It reuses the full `payload.ir` already present
in the 12 September rich observation stream. No observer, native source, image,
FASL or Wasm fixture changes, and no native rebuild runs.

```sh
python3 tests/wasm/native-census/build-flow/run.py \
  --evidence /Users/buildsomething/Source/ccl-evidence \
  --base /path/to/reproduced-wrapper-census.json.gz \
  --callbacks /path/to/source-closure-capture/probes/callbacks/capture.json.gz \
  --output /tmp/ccl-build-flow-new

python3 tests/wasm/native-census/build-flow/verify.py \
  --packet /path/to/build-flow-packet \
  --evidence /Users/buildsomething/Source/ccl-evidence \
  --base /path/to/reproduced-wrapper-census.json.gz \
  --work /tmp/ccl-build-flow-verification-new
```

`inputs.json` pins the original stream, the reproducible full graph from
`boot-wrappers/verify.py`, and the selected callback capture from the reviewed
source-closure archive. The runner refuses different bytes. The final packet
reuses the 24 KB callback capture; it does not copy either large prerequisite.
The source-closure and boot-wrappers READMEs describe materializing those inputs.

`flow.py` checks complete raw references before adapting the retained format to
the reviewed `source-closure/analysis.py` and `bounds.py`. It checks family IDs,
parents, operator histograms, call order, direct callee IDs and builtin slots.
Printed names are diagnostic. Assignment flags were not recorded; the optional
hint is false in the adapter, and the actual proof scans every variable use,
including writes in nested functions. The eight reviewed callback captures are
converted to this older format and must keep their four bounds/four refusals.

`run.py` joins pre-pass-2 families to subsequent materialization events. U1 may
return an already assembled function from pass 1 (`compiler/nx.lisp:318`); these
use the separately labeled front-end snapshot and retain an assembly dependency
gap. They must never inherit a zero-call completeness claim. The runner also
keeps exact global-symbol descriptors, operator observations and function-value
references for the next binding/registry join.

`links.py` uses the existing `identity:build` namespace and connects code and
compiler identities in both directions. Local/self calls and the newly bounded
callbacks receive exact targets. Named global and builtin calls remain
unresolved: a designator alone does not bound its callable values. Complete
node records and edge multiplicities are checked against the facts. New records
attach only through actual existing paths; disconnected functions remain listed
in `unattached_functions` and the complete observation files. Existing graph
records, seeds, initializers and trace mappings are preserved. No membership
fan-out is added, and no old widening is removed.

The verifier recomputes all six deterministic outputs from the original stream,
checks the full exchange graph, and reruns the focused controls. This remains an
unqualified native dependency slice; it grants no LL15 or other gate credit.
