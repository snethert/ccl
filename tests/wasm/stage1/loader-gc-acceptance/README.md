# Audit 183: joint hash, FASL and GC integration

The user accepted the three proposals together after Claude's no-defect
audit `18ae70b3`. Fourteen changed files are integrated byte-for-byte from
`fe93c6ed` + `665fa165` + `1760cd0c`; no new product behavior is introduced.
The [integration record](../../../../doc/WASM/stage1/integration-loader-gc.json)
binds all 45 qualified Lisp sources, runtime inputs, the immutable review
and qualification reports. Historical proposal drivers require their pinned
pre-integration revisions; this successor reads the integrated sources.

Whole-file counts remain **21 compiled / 21 cross-loaded / 0 target-loaded
of 167**. Original execution remains **575/535**, admission **2,050/2,231**
(not recounted), and the ledger **21 accepted / 12 missing**. Target code
installation (FASL opcode 72), GC locks for PUTHASH, malformed-input condition
delivery, and callable EQL, STRING= and ASSOC remain incomplete.

The fresh Git-free, different-root integration replay reproduces the entire
reviewed execution summary: 1,197 modules, 66/69 initializers, 145/149
native-equal rows and 141 controls in each of four modes, with 13/229
collections. All **3,628 regenerable artifacts** match the reviewed packet.
The corpus command runs all **26,048 comparisons** freshly against the
integrated compiler, collector and owner. Native R6/R6a (21,843 tests and
164 restored FASLs), 102 reader comparisons across 17 profiles, and 82
collector checks with ten killed faults are reused by exact identity.
No target LOAD, boot or criterion credit follows from integration.

O-97/O-98 are closed, along with O-101/O-102. O-103 records why the two owner
clause omissions are equivalent under the admitted collector: the validation
bound duplicates the getter bound, and the publication assertion checks an
already admitted increment. The TCR/getter equality is a bound check, not
independent counting evidence. Defensive checks remain. O-104 requires a
restored-image collect-then-GETHASH witness when GC locks land; image count
rebasing is not admitted. O-105 carries O-99 immediate target encoding/refusal
and O-100 descriptor refill, seek, `%FASLOAD` buffer and character-limit
controls to target LOAD. The original failure and reviewer evidence stay
in the immutable proposal packet; no duplicate baseline pack is retained.

Commands from the integrated checkout:

```sh
python3 tests/wasm/stage1/loader-gc-acceptance/product.py
python3 tests/wasm/stage1/loader-gc-acceptance/run.py /private/tmp/ccl-work/codex/loader-gc-integration/execution
python3 tests/wasm/stage1/loader-gc-acceptance/run.py /private/tmp/ccl-work/codex/loader-gc-corpus/run --corpus
```

For Git-free replay, extract the integrated revision with `git archive` to
`<workspace>/ccl`, symlink the evidence store beside it, and run the same
commands from that extraction. Keep corpus output in a separate managed
workspace to avoid serializing leases. `run.py` passes the integrated source
provider directly to the shared build/execution drivers and compares the
whole execution summary and every regenerable artifact with the reviewed
GC packet. No driver substitution or source rewriting is used.

After both commands finish, retain from the main checkout:

```sh
python3 tests/wasm/stage1/loader-gc-acceptance/retain.py /private/tmp/ccl-work/codex/audit183-replay/execution /private/tmp/ccl-work/codex/audit183-corpus/run /Users/buildsomething/Source/ccl-evidence/2026-09-26-loader-gc-integration
```

The retention command checks the sibling Git-free `ccl` tree, original input
pins, result inventories and runtime identities before publishing one report
pack and deleting its output directories. Proposal packets remain immutable.
Product acceptance is covered by audit 183; this integration harness remains
available for the next adversarial review.

Integration transfers **379 added / 30 removed product Lisp lines**, plus
six fixture-architecture lines, 22/2 collector C lines and four owner lines.
It changes no behavior beyond the reviewed stack. Author editing and reading
were not separately timed; no target-startup performance claim is made.

Retained packet: `2026-09-26-loader-gc-integration/packet.json`, SHA-256
`b00e70062e62bbb75411124d195bdd8617ce179ceaff86fb72aa5afcb915b0f4`. Fresh corpus execution took 216.31 seconds.
