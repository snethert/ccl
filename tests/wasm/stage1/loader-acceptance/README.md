# Accepted loader integration and audit 179 follow-up

The user accepted `c642d339` as the NSL-2 P2-0 design of record and instructed
“accept and integrate” after audit 179 (`5771567a`, no defect). Its six
compiler/loader files and three runtime files are now integrated byte for byte
from `2026-09-25-loader-design-r1`. Architecture generator inputs are installed
at `tests/wasm/stage1/architecture`; only the generator's relative root depth
changes, and it regenerates the reviewed architecture source exactly.

The [integration record](../../../../doc/WASM/stage1/integration-loader.json)
binds every before/after/reviewed hash, the audit, user authorization and
qualification references. `check.py` verifies the nine product files, three
generator inputs, complete 42-file compiler identity, architecture regeneration
and the reviewed native/reader/corpus records. It reports identity reuse without
claiming new execution. The original packet and all earlier evidence remain
unchanged.

`run.py` builds the integrated compiler and loader in a clean U1 extraction,
copies the integrated runtime without a proposal overlay, and executes the
two-file fixture in all four placement/collection configurations. Both FASLs,
heap, static bytes, templates and materialized modules match the reviewed
artifact identities. Two cold-load functions and six observations per run
match native; each collecting run performs six moving collections.

Audit follow-up:

- **O-84:** the [owner contract](../../../../doc/WASM/contracts/cross-image-owner.md)
  states that `manifest.codeDigest` is the fixture's independent code anchor.
  Its `expected.modules` is derived from the bundle and only checks consistency.
  The future production boot owner must carry its expected inventory from a
  trusted manifest or independent build record.
- **O-85:** two new image controls occupy the public or tail slot after
  admission, before installation. Each requires `OCCUPIED`, unchanged memory,
  unchanged entries in both tables, and preservation of the sentinel function.
  Deleting either conjunct from the publication guard is caught by its own row.
  The image suite has **68 checks: 67 refusals and one successful installation**.
- **O-86:** cross-loading a native FASL and a Wasm FASL with only version byte
  `#x80` rewritten to `#x67` both refuse with `Wrong FASL version`. Neither
  creates output; host cross-loader parameters are restored. The successful
  FASLs still load afterwards. This establishes format separation, not payload
  integrity or arbitrary malformed-input safety.
- **O-87:** the `symbol shape` reason stays exact. Removing that guard reaches
  a different heap-boundary refusal; a broad “any error” assertion would lose
  the control. No product change is needed.

The keyword-import deletion mutant is still killed, and all 19 inherited D2
checks pass. The reviewed **21,843 native tests, 164 restored FASLs, 51 reader
comparisons in 17 profiles and 26,048 compiler comparisons are reused by exact
source identity**, including the comparison of all 27 old loader-structure
accessors/predicate. Audit 179 independently replayed this qualification.
There is no new native build or corpus run for the byte-identical integration.

```sh
# Identity only; no execution.
python3 tests/wasm/stage1/loader-acceptance/check.py

# Fresh integrated producer, target runs, image/FASL controls and mutants.
python3 tests/wasm/stage1/loader-acceptance/run.py \
  /private/tmp/ccl-work/codex/loader-integration/run
```

Retained integration evidence is `2026-09-25-loader-integration` in the sibling
evidence store. `packet.json` binds new reports and drivers; unchanged source
and qualification are referenced by their existing packet hashes. Regenerable
binaries are identified by hash. Disposable outputs are removed after retention.

Production files remain **0/0/0** (fixtures **2/2/0**), accepted originals remain
**575/535**, and the ledger remains **21 accepted / 12 missing**. Acceptance is
of this P2-0 implementation, with no new criterion credit. Next is the ordered
level-0 build through the integrated loader: `SET-PACKAGE` for real files and
the nine retained first stops. The independent 12/21 compiles and 452 modules
are diagnostics, not an ordered boot or target-side LOAD.
