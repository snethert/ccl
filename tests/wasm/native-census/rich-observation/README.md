# Native compiler and loader identity collection

This observation unit gathers the identities missing from the first retained-input
census projection. It records actual expansion calls, compiled function objects,
function-cell installations, FASL write/read positions, executed initializers and
instruction emission. It runs in disposable U1 archives on macOS x86-64.

The unit touches nine shared source files. It changes no existing target-specific
source or kernel source. `build_patch.py` derives the patch from pinned U1 and the
reviewed original observation patch. `unit.py` uses the reviewed apply/recovery
mechanism, with a nine-file scope guard. Applying and removing it restores exact
original source bytes; an unrelated edit or damaged backup stops recovery.

`install.py` selects the changed definitions into a disposable native process. It
does not load all of level 0 into a full image: that would replay boot aliases.
The installer loads U1's FASL environment before the selected loader definitions.
The native R6 comparison uses the same installation recipe before observation and
after removal, and retains its own clean baseline. It does not assert that this
different preparation recipe reproduces earlier runners' artifact hashes.

## What is recorded

- Complete object graphs for observed forms and compiler IR, with weak object
  identities, explicit opaque objects, and separate function-code identities.
  Printed descriptions are annotations, never parsed as executable forms.
- All three actual `*macroexpand-hook*` invocation sites in U1: ordinary, symbol
  and compiler macro expansion. The original hook and every returned value pass
  through unchanged. Normal returns and exceptional exits are distinguished.
  The observation is inline: adding a shared helper DEFUN consumed three
  compiler gensyms and changed later FASLs. Removing that definition restores
  the original compilation inputs. The correction neither normalizes bytes nor
  adjusts compiler counters; both sides use the same baseline preparation.
- Each afunc's materialized native function, including nested functions. The
  real callable passed to compile-time evaluation and its returned values are
  recorded, not inferred from other compilation in the same interval.
- Function-cell removal intent immediately before the primitive clear, and
  completed installation after the primitive store, including SETF cell origins
  and replaced definitions. No logger runs in the unbound interval. Two full
  development runs exposed why this matters: CCL also replaces the metadata
  reader and `STRING-DOWNCASE`, which the observer itself uses.
- A compiled function's exact FASL opcode position and the loader's actual
  deserialized function at that position. A subsequent rewrite of the same file
  replaces its preceding write map. Preexisting FASLs remain explicitly distinct.
- The invoked reader function and actual dispatch-table mode. The image builder
  returns tagged target-image words instead of callable host functions, and can
  queue initializers for later execution. Its reader completions and function
  words stay separate from host execution and host code identities.
- Real loader effect opcodes, their nesting, executed callable objects, values
  and normal/exceptional completion. This includes direct definition/variable
  opcodes and `$FASL-LFUNCALL`. Compiler emission remains a separate event.
- Each emitted evaluated vinsn template, its operands, the current afunc, and
  actual live dispatch-handler frames obtained through CCL's stack reader.
  Native handlers are neither wrapped nor edited. Tail-elided frames are
  unavailable; a live ancestor is not mislabelled as an exact leaf operator.
- Resident code and function bindings before/after a session, plus actual cold
  startup callback objects and completion in an observation-only saved image.

CCL may create distinct expanders for a compilation environment, a global macro
binding and a FASL. Matching their printed names would conflate different code.
The corpus checks the actual called expander's materialization identity instead.
The JSON writer preserves the original encoding while writing ordinary string
spans together. ASCII controls, quotes, backslashes, Unicode and large integers
have independent byte comparisons and parser round trips.

The rebuild stream covers the parent compiler process and the FASLs it actually
loads. CCL's boot-image subprocess does not load this observer. Compiling L1 in
the parent therefore does not witness its later installation in that subprocess.
The separate cold-start stream and clean-image inspection cover their own
processes. The corpus's L0/L1/L2 names identify its three test layers; they do not
expand that execution scope.

## Run and verify

```sh
python3 tests/wasm/native-census/rich-observation/run.py \
  --inputs /absolute/path/to/macos-u1-inputs \
  --kernel /absolute/path/to/the/pinned/dx86cl64 \
  --work /private/tmp/new-rich-census-work \
  --output /private/tmp/new-rich-census-output
```

The runner retains one baseline FASL archive and only changed observed FASLs,
runs all 21,843 eligible native tests before/after, compares the three unchanged
corpus FASLs, executes state-omission/reordering controls, captures cold startup,
and rebuilds after removal. Cold-start output uses external sharing under the
event lock: the initial thread opens it and the listener finishes it. The retained
first cold run exposed the private-stream error; its corrected continuation is
separately pinned and reuses the successful compilation/test stages.
Its eight intentional FASL changes correspond to the
nine patched sources: `nx0.lisp` is included by `nx.lisp`.
Observed rebuilds have a four-hour administrative deadline, recorded with each
command. Detailed object/operand capture is much slower than a clean build.

`--resume` reuses a failed run's retained clean baseline only after checking its
input pins, original source state and restored native output digests. The failed
run record and stream stay retained; the next observed build gets a new name.
This avoids repeating successful baseline builds and tests during development.

```sh
python3 tests/wasm/native-census/rich-observation/analyze.py EVENTS.jsonl.gz JOINS.json.gz
python3 tests/wasm/native-census/rich-observation/test_controls.py PROBE-JOINS.json.gz CONTROLS.json
python3 tests/wasm/native-census/rich-observation/test_unit.py UNIT-CONTROLS.json
python3 tests/wasm/native-census/rich-observation/verify.py \
  --work /private/tmp/restored-rich-census-work \
  --output /private/tmp/new-verification \
  --pack /private/tmp/completed-rich-census-output
```

`analyze.py` checks pairing and completion and joins identities without name-based
substitution. `check.py` carries independent expectations for a three-layer
corpus. The corpus's native assertions check retained older functions, distinct
macro expansions, multiple values, SETF, indirect calls and prerequisite state.
`mutant-driver.lisp` suppresses actual installation, expander or loader observations
while that unchanged native corpus still passes; the semantic reader must reject
each incomplete stream, with identical native corpus binaries. `test_controls.py`
additionally damages sixteen joined records, including initializer phase order
and reader mode. `test_reader.py` checks host functions and target-image words,
rejects eight dispatch/type corruptions and can replay the original failing
image-word record with `--regression`.
`test_unit.py` checks restoration and five refusal conditions. Two focused native
mutants put the callback back in the unbound window; both must fail while the
correctly placed observations pass.

`inspect_traced.py` runs the existing image inspector against the exact kernel and
image retained by the external file trace. It also records existing foreign entry
points and libraries, and joins evaluated kernel-import offsets to U1's explicit
assembly table. It neither resolves new entry points nor invokes imports. Three
table controls reject missing entries, invalid offsets and duplicate names. This
inspection needs no new administrator trace.

The retained r1 packet preserves the original attempt-4 `run.json` as FAIL for
its cold-start step, alongside its successful build, R6 and regression results.
`completion/run.json` records the corrected cold-only branch and clean rebuild.
Its retained `postprocess.py` checks both source versions and analyzes their
respective streams. The generic `verify.py --pack` command above expects a fresh
runner that completed all stages in one execution.

## Acceptance boundary

Expansion events identify the invoked hook and the supplied expander. The native
corpus uses the default FUNCALL hook; the events alone do not establish how an
arbitrary custom hook delegates internally.

These records supply input to LL15-b/c. They do not themselves claim a qualified
Wasm census, a complete static bound on every dynamic call, minimal initializer
state dependencies, or target disposition of all native imports/stores. Full
native build observation is also distinct from executing the registered Wasm
front end over the selected source closure. Seed/bound review and the complete
census exchange/gate path remain necessary; external review remains separate.
Raw compilation records also include the observation code in the eight changed
FASLs. Census assembly must distinguish those calls using the retained patch and
clean baseline, rather than treating every raw dynamic call as a port dependency.

The observed sources, FASLs and saved image are evidence only. The port starts
from pristine U1 source and bootstrap, never this disposable image.
