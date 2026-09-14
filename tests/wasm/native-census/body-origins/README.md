# Remaining native body origins

This diagnostic classifies the 634 prototypes outside the reviewed starting-image
read-only witness. It reads the original rich-build stream and reviewed binding
facts; it starts no native process and changes no census graph edge.

`classify.py` checks the partition against the binding delta, joins each ordinary
called value to its exact recorded symbol history, and scans all 4,006,405 events
for the first **function descriptor** carrying each prototype ID. The byte
prefilter selects candidate JSON records only. A numeric literal, opaque record
or equal printed name cannot establish function identity. Event order and the
final counts must match the complete retained stream.

The outputs retain the first descriptor and its exact JSON path, the first
called-binding observation, all called symbol identities, initial-inventory
membership and direct effect-parent context. Original raw event lines are kept
separately, including each direct parent, so the excerpts remain inspectable.

The result is 481 prototypes already in the initial inventory and 153 whose first
descriptors occur at later binding installations. Sixteen of the initial group
carry installer source annotations; 465 have no source annotations. Of the later
group, 152 occur under ASDF compile-initializer entries and one under a Swink load
effect. These are observation categories, not assertions of allocation time or
function subtype. The old inventory does not say which non-read-only heap area
contains a function, so every row keeps `heap_area: UNCLASSIFIED`.

The descriptor can follow an earlier literal-reference ID: the scanner claims
the first complete function descriptor, not the first occurrence of its integer
anywhere. Binding removal remains an observation of the old value plus intent;
it cannot count as a completed installation. The native inventory and installed
objects remain in their original process namespace.

Eighteen controls reject missing/substituted identities, wrong ordering or
initial-inventory membership, removal promoted to installation, wrong installed
objects, missing/cross-process parents, invented heap areas, worklist erasure,
false body/closure credit and malformed/truncated streams. A small parser probe
checks earliest-descriptor selection despite later copies, equal names and an
opaque integer field. It supplements the real-data controls.

```sh
python3 tests/wasm/native-census/body-origins/run.py \
  --evidence /Users/buildsomething/Source/ccl-evidence \
  --output /tmp/ccl-body-origins-run
```

Add `--packet /path/to/packet` with a fresh output directory to verify the packet,
re-read the original stream and require byte identity for all five outputs.
The producer snapshots its executed source before running. Retention contains
one finalized packet, references unchanged inputs, and preserves the exploratory
scripts and results without repeating source trees or prior evidence packs.

`swink-disposition.json` is a separate, source-backed integration worklist.
Revision 2 records the user's browser scope clarification: omit the entire
Swink module and its native remote-lisp clients, including resident and later
bindings. There is no Swink implementation or replacement task. Check browser
startup dependencies and, only if a supported entry can request an excluded
module, the shared loader's unsupported-module path. The six source identities
remain unchanged. The retained diagnostic packet contains revision 1; neither
revision is consumed as an executable rule or applied to the census graph.
Shared CLOS, stream and thread dependencies retain their own obligations.

All 5,007 source/IR body obligations remain open, including the 4,373 prototypes
with witnessed native payloads. No new callee bound, unsupported runtime path,
target lowering or LL15 acceptance is claimed.
