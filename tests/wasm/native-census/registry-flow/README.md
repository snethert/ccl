# Same-execution registry/compiler witness

Reload native U1 `lib/describe.lisp` and run a private method replacement/removal
probe in a fresh disposable release image. The real native pass 2 is forwarded
unchanged. A strong EQ identity table joins its IR and emitted functions to
actual method installations in the same process. No shared source is patched,
no FASL or image is saved, and no Wasm code or gate result is produced.

```sh
python3 tests/wasm/native-census/registry-flow/run.py \
  --evidence /Users/buildsomething/Source/ccl-evidence \
  --work /private/tmp/ccl-registry-flow-work-NEW \
  --output /private/tmp/ccl-registry-flow-NEW
```

Add `--packet /Users/buildsomething/Source/ccl-evidence/2026-09-15-registry-flow-r1`
to re-execute and compare all seven deterministic outputs. Work/output paths must
be new, separate directories. Four sessions run: observation twice, a reference
without installed hooks, and an actual omitted-installation-hook control. The
reference loads the same fixture definitions and uses the same reload policy.

The observer temporarily replaces the native backend's pass-2 slot and three
function cells: standard method addition, standard method removal and the dcode
setter. `unwind-protect` restores them; an escaping `throw` tests the exceptional
path. Source files, kernel and release image remain unchanged. The collector
holds objects strongly for the session so an object ID cannot be reused.

`first.json.gz` retains flat IR, materialized native code prefixes, nested
operation entry/completion records, before/after registries and function
descriptions. Method installation joins require an earlier compiler completion,
the same function/prototype identity and equal code bytes. `joins.json.gz`
contains exact references into this capture; the checker bounds its full records
against the capture. Twenty-three checker mutations and the real omission run
are rejected. Raw native captures are evidence, not authenticated event streams.

The observed scope is 225 native compilation roots / 401 emitted functions,
240 additions, 239 removals, 12 setter calls, and three behavioral calls. Of the
240 installations, 163 have compiler-body joins and 77 retain construction gaps.
The counts qualify this fixed corpus, not arbitrary source files. Initial and
final snapshots cover the 118 GFs touched by these hooks. Inline dcode stores,
class changes, dispatch-table cache writes and effective-method execution are
not exhaustively intercepted. A snapshot with unbound slots is explicitly
uninitialized. The unit does not call a GF after emptying its method list.

The initial code inventory and changed method-code rows are identical with and
without observation. Symbolic signatures select these comparison rows only;
they never create compiler or original-build identity joins. `describe` and
`probe` label dynamic execution context, not a source-location claim for every
helper compiled in that context. Reported source notes remain separate fields.

This is native census input. It neither makes native inspector operations part
of the browser profile nor adds Swink work. See the
[scope report](../../../../doc/WASM/stage0/registry-flow.md).
