# Resident function-literal joins

This diagnostic adds exact initial-state references for the 465 unannotated
resident prototypes in the reviewed remaining-body worklist. It runs no native
process and changes no shared source.

The original raw first-descriptor events already include the function literals.
Each event joins the worklist by its original byte hash, process, descriptor,
event and object identity. Their targets join the complete read-only inventory
prefix anchored by the reviewed starting-image witness. The fresh capture's
dynamic suffix is deliberately ignored. Neither names nor coincident numeric
IDs bridge separate executions.

Each of the 465 prototypes references one of seven read-only functions: five
dispatch routines and two methods. Following the method's nested literal adds
one internal function. The retained exporter supplies reported source extents
for all eight; those extents are copied from two pinned, unchanged U1 files.
This does not prove how a callable object was constructed, its subtype, all
methods it can dispatch to, or source/IR dependency completeness.

The additive exchange delta contains 466 observed literal-reference edges and
six newly exposed code nodes, each with an unresolved body obligation. All
earlier nodes, edges, seeds and obligations remain unchanged. A complete literal
edge means the observed reference was joined; it is not an exhaustive callee
bound. References describe the initial inventory, not later mutation of a
dispatch slot. No broad widening edge is removed and no gate credit is claimed.

Twenty-four controls reject omitted or inserted facts, references and graph
records, cross-process substitution, mismatched function identities, unanchored
targets, damaged source extents, false subtype/IR/callee claims, changed earlier
obligations and changed seeds. A positive control replaces the entire fresh
dynamic suffix with invalid JSON and requires the same result.

```sh
python3 tests/wasm/native-census/resident-literals/run.py \
  --evidence /Users/buildsomething/Source/ccl-evidence \
  --base /path/to/reconstructed-boot-wrappers-census.json.gz \
  --output /tmp/ccl-resident-literals
```

The base is the reviewed boot-wrappers graph named in `inputs.json`; the runner
composes the pinned build-flow and binding-version deltas. `join.apply` appends
this delta to that composed graph. Add `--packet /path/to/retained/packet` and a
fresh output directory to replay all four outputs byte-for-byte. Verification
covers this packet and its direct inputs, not the historical evidence store.
