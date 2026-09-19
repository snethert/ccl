# S1-LL11-a: package bindings and redefinition

An isolated owner installer publishes complete binding manifests over the accepted
LL12 compiler and loader. Nine generated modules run in fresh Workers at 1 MiB
and 2 GiB. Native CCL supplies eight signatures and the behavior of case-sensitive
symbols in two packages, aliases, two mutable environments sharing one inner
entry, and saved functions across two redefinitions.

Each Worker executes four transactions and 24 generated invocations. Two functions
have identical Wasm bytes but separate names/slots. One alias follows mutations of
a saved closure while the original symbol is rebound twice; another package's
closure remains independent. The original top-level code is callable after its
replacement. Both public/internal table entries are installed from authenticated
bytes, with a four-slot reserved prefix preserved.

Before writing, the owner checks the complete independent expected binding list,
manifest generation/predecessor, code ownership, exact binary body extents and
export indices, function/pool metadata and native-derived arity. Failure rolls back
all code rows, claimed slots and symbol cells. There are 32 refusals per placement,
including a failure after seven earlier modules installed, malformed materialized
metadata, missing aliases, occupied/reserved slots and stale runtime manifests.
Seven executable installer mutants fail distinct oracles. Eleven publication
controls and the production role-omission checks cover retained completeness.

The compiler and existing runtime files are byte-identical to accepted LL12;
its native R6/R6a is reused by hash. Native signatures, behavior and all generated
modules are freshly compiled on replay. No new native build or compiler change is
claimed. The installer is not integrated until review and acceptance.

```sh
python3 tests/wasm/stage1/binding-installation/run.py \
  --evidence ../ccl-evidence --output /tmp/ll11-fresh --qualify
python3 tests/wasm/stage1/binding-installation/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-19-stage1-binding-installation-r1 \
  --output /tmp/ll11-replay
```

See `scope.json` for the boundary. This is a synchronous, single-Worker trusted
owner; no Lisp call, collector or reentrant byte-provider callback may run during
installation. It consumes existing symbols and materialized pools/functions, not
an image file. Production materialization under LL14 must initialize top-level
arity/debug words from pool elements zero/one. It never repairs missing metadata.
Only the ordinary B profile is admitted; owner-retry admission and concurrent
publication are separate work. Old entries are retained with no code reclamation.
Arity validation is not a complete verifier of malicious owner debug data.
Body extents include local declarations and are not instruction entrypoints.
