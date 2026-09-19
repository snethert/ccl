# Raw constructor retry and owner-capability admission

Auxiliary proposal extending the accepted internal allocation retry. No LL06 or
LL18 slot credit is claimed. Shared compiler and runtime files remain at their
accepted versions until review and integration.

With retry enabled, binding-vector growth, restart construction and implicit
condition construction enter the owner only on shortage, before loading their
allocation addresses. Construction and publication still contain no collecting
call. Default entry points retain the accepted Wasm bytes.

The binding record roots the incoming symbol and value before vector growth;
the TCR roots the old vector, which is reloaded after assurance. PROGV's symbol
preflight validates without allocation, and its values cursor stays in a root
slot across each binding. Restart constructors consume argument root slots,
and condition constructors consume the implicit-error frame's datum/expected
slots, loading them after assurance. Conditions use the existing sealed native
class registry; this does not implement general CLOS.

The harness now gives condition-system specials real binding indices and
materializes their condition registry as inventoried D1 objects. Each new form
has literal expectations that pristine native CCL must reproduce first. Ordinary
runs and a test-only pressure variant cover low and above-2-GiB heaps. The latter
fills remaining heap with valid unreachable conses immediately before each raw
constructor's preflight. It cannot move live objects: movement requires the
compiler's own slow path. Retired spaces are poisoned. Compiled mutants remove
retries or restore stale value, cursor, vector, restart and condition loads.

The loader adds `wasm32-shared-B-owner-retry-v1`. Only that profile admits exactly
one `owner.ensure : (i32) -> ()` function import, bound by identity to the trusted
owner's `allocationEnsure` capability. The reader accounts for imported
functions in export indices. The old profile still refuses function imports.
Start functions, segments, and defined memory/table/global objects remain
forbidden. Cold installation cannot call the capability or write Lisp memory;
cold execution must reproduce eager observations. This is trusted-owner
capability admission, not code signing or authentication of a hostile owner.

Invoke generated Lisp outside an active `CollectorOwner.atSafepoint` boundary.
Only the allocation service opens that synchronous boundary. Nested service
entry is a checked refusal; six lazy-execution cases check this contract. A
failed assurance can already have moved objects or grown memory. Live roots
remain valid, but callers cannot assume rollback or retain raw heap addresses.

Run and qualify:

```sh
python3 tests/wasm/stage1/constructor-retry/run.py \
  --evidence ../ccl-evidence --output /tmp/constructor-retry-run --qualify
python3 tests/wasm/stage1/constructor-retry/native.py \
  --evidence ../ccl-evidence --work /tmp/constructor-retry-native-work \
  --output /tmp/constructor-retry-native
```

Replay the retained packet:

```sh
python3 tests/wasm/stage1/constructor-retry/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-19-stage1-constructor-retry-r1 \
  --output /tmp/constructor-retry-review
```

Remaining qualification includes the complete LL06 root/control matrix and
LL18 ownership/lifetime contract. Retired semispace reuse remains open. This
unit neither adds arbitrary heap kinds nor changes the collector or owner.
