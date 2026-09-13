# First source-file traversal

This driver reads every top-level form of pristine U1 `lib/dumplisp.lisp` in the
registered Wasm census target context. It captures real front-end bodies through
the accepted pass-2 escape and continues at the next independently indexed form.
Unsupported forms remain explicit. It emits no target code or FASL, installs no
source functions, and replaces no existing graph edges.

```sh
python3 tests/wasm/native-census/source-traversal/run.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --work NEW-DISPOSABLE-DIRECTORY --output NEW-OUTPUT-DIRECTORY
```

Both directories must be new and outside the evidence repository. The runner
extracts pristine U1 source and the bootstrap interface data, starts the retained
clean r7 image, and loads the three accepted LL08-a registration binaries. The
architecture/backend binaries are loaded through their actual module entries.
No new registration patch, native rebuild, or whole-archive scan is needed.
The process is disposable and no image is saved.

The source module is deliberately fixed by its digest. A host reader and a
read-suppressed reader independently agree on all sixteen form boundaries.
These supply the source inventory, never the target input forms. Each source
slice is read again under the target backend, features, FASL target, foreign data
and package nicknames, then passed to U1's real `fcomp-form`. The driver preserves
the file definition environment, uses ordinary compiler handling for declarations,
and catches the pass-2 escape once per top-level form. Each successful DEFUN
capture stops before its load plan is completed; no definition is installed.
The checker independently names the sixteen U1 forms and required source calls.

This first file contains only IN-PACKAGE, DEFVAR, DECLAIM and simple top-level
DEFUN forms. General top-level PROGN, INCLUDE, local macros, conditional top-level
forms, and arbitrary reader effects need additional traversal work and controls.
Bodies may contain reader conditionals and local functions; captured children
and their call/reference sites retain their own compiler identities. Offsets are
character offsets; the pinned source is ASCII. The current module's trailing
whitespace is checked through EOF.

`normal.json.gz` is the raw capture. `facts.json.gz` preserves each captured body,
operator inventory, call/reference record, and unsupported form. IDs belong only
to that native capture; integration must bind them to the packet identity. Source
membership is metadata rather than a new module-to-all-functions edge.
`commands.json`, `run.json`, the logs and summary describe the execution. The two
native negative runs stop after the first capture or actually read under the host
context. Twenty-one analysis controls mutate the genuine capture and derived facts.
The successful duplicate capture is not retained twice; equality is recorded.

For focused replay, without executing native CCL again:

```sh
python3 tests/wasm/native-census/source-traversal/verify.py \
  --packet RETAINED-PACKET --source lib/dumplisp.lisp
```

Replay checks semantics and controls; the packet manifest separately records file
identities. The [report](../../../../doc/WASM/stage0/source-traversal.md) explains
the eight stopped definitions, inherited macro environment and remaining work.
This is diagnostic evidence, not a complete census or an LL15 acceptance result.
