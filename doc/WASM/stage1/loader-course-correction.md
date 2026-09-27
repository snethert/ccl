# Loader course correction — 26 September 2026

The user's finding is upheld against checkout `6b834922`. Codex pursued
host cross-loading of level-1 after completing the level-0 producer, although
the adopted [NSL-P2 design](namespace-loader-plan.md) requires a level-0 boot
image followed by target loading of level-1. The next implementation work is
target bundle installation and the real bootstrap. Extending level-1
cross-loading is no longer the work queue.

## Finding and current scope

The relayed review describes `e9301356` at **29 compiled / 24 cross-loaded /
0 target-loaded**. The checkout has since reached **36/36/0 of 167**:
21 level-0 files and 15 level-1 files compiled and cross-loaded. Audits 184
and 185 and their accepted results remain evidence of the work actually
executed. They do not demonstrate the adopted boot path. The latest
namespace weak-table substitutions at `6b834922` still await review.

- Opcode 72 is `$fasl-wasm32-function` in
  [faslenv.lisp](../../../xdump/faslenv.lisp). Its handler in
  [xwasm32-fasload.lisp](../../../xdump/xwasm32-fasload.lisp) is installed
  in the **host** `*xload-fasl-dispatch-table*`. The target table in
  [nfasload.lisp](../../../level-0/nfasload.lisp) has no corresponding
  handler and retains `%bad-fasl` for that opcode. The existing
  [target control](../../../tests/wasm/stage1/loader-fasl/controls/fasl.mjs)
  explicitly expects its refusal. In-memory data-op parsing is qualified;
  loading a file's Wasm code on the target is not.
- The level-1 producer follows the **compilation** module list. Its
  [execution driver](../../../tests/wasm/stage1/loader-level1/run.py) builds
  a different image containing all level-0, whole `l1-utils`, `l1-numbers`
  and `l1-sort`, plus selected support forms and witnesses. Neither image
  establishes native runtime load order. The initial seven and current four
  startup refusals are observations of those fixtures; they cannot by
  themselves diagnose failures of the real level-0 bootstrap.
- `a55b18c6` already added the host cold-evaluator SETF-name extension that
  the relayed review warned against. That extension is not a prerequisite
  for target loading. It remains in the checkout with its reviewed evidence;
  this correction neither removes code nor claims that target SETF-name
  evaluation has been qualified. Further host evaluator extensions for
  level-1 are out of the bootstrap work queue.
- Host compilation of level-1 is still necessary. The old `%CURRENT-TCR`
  compilation stop was addressed; the current stop is
  `:BOOTSTRAP-TYPECHECK` in `l1-streams`. Record that as a producer boundary,
  separate from the immediate target-loader work.

BT-20 continues to count actual events: the historical 36/36/0 is retained,
with the level split above. It does not authorize enlarging the boot image
with level-1 or treating a cross-loaded file as a target-loaded file.

## Implementation sequence and evidence

1. Connect target code loading to NSL-3's versioned, self-contained bundle
   and the existing installer. Closing opcode 72 means validated code
   identity, digest, roles and signatures; owned request bytes; traced Lisp
   roots; and construction of the D1 function object. Keep logical code IDs
   separate from engine slots. A returned slot alone is insufficient.
   Qualify malformed/truncated input and failed-install state preservation.
2. Build the boot image from the complete level-0 inputs and run its real
   `%toplevel-function%` in a fresh Worker. Reach boot0 only after its cold
   functions, early-class cells, package resizing, documentation and binding
   indices complete. Retain the first actual failure without selected-form
   supplementation, replacement initializers or caught-error continuation.
   NSL-P2 permits a diagnostic mark at the final load handoff; that means
   boot0 can be investigated before target file loading is complete.
3. Continue through `%fasload *xload-startup-file*`. The Wasm backend names
   `ccl:level-1.w32fsl` as that startup file.
   [level-1.lisp](../../../level-1/level-1.lisp) drives the initial runtime
   sequence, including library files, and loads
   [l1-boot-2.lisp](../../../level-1/l1-boot-2.lisp), which performs further
   loads itself; `l1-boot-3` also remains in the outer sequence. Preserve
   these source-defined calls and their order. CLOS is built on the target.
4. Establish NSL-P2's boot1 and READY evidence, including a separately
   compiled post-image bundle loaded by target `%fasload`, required-bundle
   omission, and `startup-ccl` stopping before the listener. Count target
   files only as their actual target loads complete.

The [target loader review checkpoint](../../../tests/wasm/stage1/loader-target/README.md)
now executes opcode 72 through the original target reader, with moving import
roots and namespace/session wiring. The level-0-only image completes 21 target
file loads through `l1-files`, then stops in `l1-typesys` at `%extend-vector`.
The producer compiles 56 runtime files, stopping at `%PTR-EQL` in foreign-types.
These actual counts supersede the earlier zero-target-load checkpoint; they do
not change accepted criteria. The user approved the stdout/stderr and initial
process startup boundary in decision A2, then requested development stop and a
review commit. READY remains unestablished. The handoff enumerates profile
exclusions, the failing compiler corpus, remaining qualification gaps and the
final native/reader evidence. Claude review remains outstanding.

## Completion — 27 September 2026

The checkpoint above is superseded by the completed
[target loader](../../../tests/wasm/stage1/loader-target/README.md). The image
still contains level-0 only. All 82 selected runtime bundles compile; all 81
nested runtime loads complete through the target `%fasload`, and the outer
level-1 file hands off through `:toplevel` to `startup-ccl`. Two ordinary
post-image `--load` files then return successfully in each of two fresh Workers.
Both reach READY with Unicode stdout/stderr and independent mutable state.
Required-bundle omission and an empty namespace stop before the post-image marker.

The final evidence pack is
`ccl-evidence/2026-09-26-stage1-loader-completion-r1` beside the checkout.
`checks/ready-r23` binds load order, the retained native callbacks, image and
code identities, observed module calls, both Workers and both refusal paths.
The source census enumerates replacements separately; decision A3 removes the
numerical cap without granting original-definition credit. The interactive
listener and in-image compiler remain outside decision A2's READY boundary.
