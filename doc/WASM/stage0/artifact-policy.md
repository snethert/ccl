# Production artifact policy — 14 September 2026

The user authorized this enhancement when accepting S0-LL22-a: “accept
S0-LL22-a, add the production-policy enhancement, and proceed with LL23 and
LL24”. Claude's thirty-sixth audit identified the gap: the control enforced ten
roles, while the production inventory required only four.

The production gate now takes the union of the global `required_record_roles`
and the test entry's optional `required_record_roles`. Local requirements cannot
replace or waive the global minimum. Non-list, duplicate, non-string and empty
role names are refused even when the affected test has no execution record.
An empty local list adds nothing and still requires the global roles.

The existing binding algorithm includes the full semantic test entry. A changed
local role policy therefore invalidates that test and its dependents, while an
unrelated test retains its identity. No binding algorithm change is needed.

| Pending production records | Additional roles |
| --- | --- |
| S0-LL07-a, LL13-b, LL15-a, LL19-a, both LL21-c variants, LL23-a | source, ABI, template, installed binary, host compiler, options |
| S0-ENGINE-a | source, template, installed binary, host compiler, options |
| S0-LL15-b, LL15-c, LL22-b | source, host compiler, image, options |

The global implementation, test, schema and log requirements remain. These ten
test entries are pending work; all 35 accepted records retain their exact
contracts and original acceptance scopes. This prospective policy does not
claim to have retroactively qualified additional artifact roles in old packs.
When an accepted fixture gains a broader delivery claim, its new contract and
producer must declare the applicable roles before that claim is accepted.

A role identifies retained evidence of that facet. For example, hand-built Wasm
uses its actual ABI/interface schema, WAT template and emitted binary; its host
compiler record identifies the compiler executable by digest and version, and
its options file records actual invocation options. Native compiler observation
also requires the input image. A fixture that does not use an image is not
required to invent one. These role declarations do not authenticate their own
truthfulness or prove source-to-binary derivation; producer checks and review
remain necessary.

Stage 1's inventory must require the complete applicable build set, including
its real compiler, ABI, templates, modules, image and options. The four-role
Stage 0 minimum is not an authorization to omit those roles from Stage 1.

`tools/test-artifact-policy.py` applies the actual production role lists to
quarantined synthetic gate records, checks omission of each global/additional
role, tests malformed lists and verifies local/global compatibility. Synthetic
identities and runner labels cannot qualify production execution: the quarantine
has a different inventory context. S0-LL23-a will separately exercise the new
requirements using its real compiled artifacts.

The regression run also checks all 35 accepted metadata bindings. The existing
32 gate, 42 binding and fourteen acceptance controls pass. No historical runtime
payloads are rescanned. One compact packet retains the original inventory before
the change, the new inventory, the user's dated policy decision and the exact
old/new contract identities. The new gate implementation and policy await
independent review; acceptance of LL22-a remains scoped to its reviewed version.
