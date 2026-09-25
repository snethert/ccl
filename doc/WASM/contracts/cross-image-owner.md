# Cross-loaded image owner contract

This describes the `admitCrossImage` owner boundary accepted with NSL-2 P2-0
after audit 179. The [integration record](../stage1/integration-loader.json)
binds the implementation. It qualifies installation of a built image;
the production boot owner and target-side LOAD remain subsequent work.

The embedding owner supplies a trusted image manifest, D2 materialization
policy, expected code inventory, memory regions, registry, distinct public and
tail tables, capabilities, module/template bytes, and the heap payload. These
inputs must refer to the same image and Worker. The owner's manifest supplies
`heap.digest` and `codeDigest`; admission checks the complete serialized bundle
against that code digest, and the heap record binds the same digest. D2 then
checks template, materialized module, ABI, classification and policy identities.

`expected.modules` lists `[name, code_id, generation]` in trusted inventory
order. A production boot owner must obtain this inventory from its trusted
manifest or independently retained build record. Deriving it from the bundle
being admitted does not independently check membership, ordering or generation.
Likewise, computing the expected code digest from that bundle would remove the
external integrity anchor.

The P2-0 diagnostic `boot.mjs` derives `expected.modules` from the bundle.
In that fixture the independently supplied `manifest.codeDigest` is the code
integrity anchor; the inventory equality checks are consistency checks.
Negative tests intentionally rebind digests and inventory to reach individual
validation clauses. They do not demonstrate an independent owner inventory.
This distinction is audit 179's O-84 and must be preserved when implementing
the production boot owner.

The saved image holds logical code IDs. `expected.slots` maps those IDs to
owner-selected engine table slots; `table_capacity` and `reserved_slots`
describe that owner's allocation. The same artifact may use different slots
in another Worker. Serialized slots are refused in this image path. Logical
IDs index the code registry; public and tail slots are a separate resource.

Admission validates and compiles the complete code set before publication.
Installation checks that both table roles remain unoccupied, instantiates all
modules, publishes the pair, rechecks registry/static owners, installs the
heap, and fills registry entries. A publication or pre-installation failure
preserves existing slots and heap memory. The owner serializes installation
within its Worker; there is no concurrent publisher or Lisp callback during
publication. Cold-load functions run explicitly after successful installation.

Host-side FASLs are trusted build inputs. Wasm version `#x80` is disjoint from
native FASL versions, and cross-loading a native version refuses before output.
The format itself has no payload-integrity digest. Artifact digests bind what
the build produced; they do not retroactively authenticate the source FASL.
The two directed version refusals therefore qualify format separation, not
arbitrary-corruption detection or an untrusted target FASL reader.
