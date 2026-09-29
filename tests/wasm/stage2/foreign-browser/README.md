# Generated Lisp foreign calls in browser Workers

This Stage 2 unit executes the existing product Lisp foreign API and its complete
61-row witness in Chromium, Firefox and WebKit, through the same Worker body as
Node. Qualification results and review status are recorded in
[the Stage 2 binding](../../../../doc/WASM/stage2/foreign-browser-results.json).
Product Lisp, shared compiler and upstream kernel sources are unchanged. Two
numeric-service JavaScript guards now compare import fields independently of
object property order or additional engine metadata, fixing the WebKit startup
refusal caused by its extra `type` field.

`loader-target/boot-worker.mjs` contains the previous Node driver's boot,
installation, ordinary runtime loading and post-READY `%FASLOAD` execution.
`boot0.mjs` supplies Node filesystem, output, clock and observation capabilities.
The browser embedding supplies a digest-checked HTTP input provider and the
existing resident namespace/file mailbox on the page. A dedicated Worker runs
Lisp and may block on that mailbox; the page services requests against immutable
namespace snapshots. Archive buffers are fetched on demand and transferred to
the Worker, with size/digest checks before transfer and existing archive admission
inside the Worker. A ten-minute diagnostic timeout records the last output and
request/archive counts; the original three-minute Firefox timeout is retained.
No source rewriting or replacement startup functions are used.

Both embeddings use `foreign-api/fixture.mjs`. The embedding provides the fixture
library's bytes, declared imports and collection observations. Product namespace,
foreign library/service, callback invocation and collector code remain unchanged.
The browser fetches library bytes before entering Lisp; synchronous foreign calls
use that resident namespace. This qualifies an HTTP-preloaded resident provider,
not a mounted-directory provider or a suspending foreign-function loader.

The witness covers scalar representations, owned buffers, explicit UTF-8 copies,
weak-anchor finalization and generated Lisp callbacks, including closure roots,
moving GC, contained errors, nonlocal exits and once-only cleanup. Retired spaces
are poisoned. All 61 rows and foreign/collection counts must equal the retained
native oracle and the Node execution. The oracle's exact Lisp input identities
and retained log digest are checked before reuse. Three directed HTTP, size and
digest refusals run in each browser before boot. Node execution checks the shared
runner refactor; unchanged lower-layer admission/mutation suites reuse their
existing identities and review records. The changed numeric admission guards
have 14 checks per engine: valid and reordered descriptors, plus missing, extra,
wrong-module, wrong-name and wrong-kind imports for each guard. Refusals preserve
all 64 TCR words. Two isolated controls restore the original guards and must fail
on reordered descriptors.

The initial WebKit refusal, original three-minute Firefox timeout and a
missing-dependency error in the isolated control harness are retained. The
longer Firefox run completes the ordinary path. Startup remains a
[blocking defect](../../../../doc/WASM/stage2/startup-blocker.md); extending the
timeout does not fix it.

The browser fixture offers real elapsed/wall clocks and synchronous captured
output. Calendar and CPU accounting capabilities are absent and retain the
product service's checked refusal; no timezone policy or CPU-time approximation
is introduced. Trace instrumentation and failure-memory file output remain Node
capabilities. Browser source modules and binary inputs are bound by hashes.
Cross-origin isolation is required. This remains one Lisp Worker and explicit
finalizer draining; it grants no multi-Worker D5, mounted-provider, stream or
full FMT/LL acceptance.

## Reproduction

Verify the two RAM volumes per `CLAUDE.md` and restore the pinned
[browser tools](../browser-tools/README.md). From the repository root:

```sh
work=/private/tmp/ccl-work/codex/foreign-browser
python3 -B tests/wasm/stage1/loader-target/build.py "$work/boot" --boot0
python3 -B tests/wasm/stage1/loader-target/build.py "$work/level1" --level1
python3 -B - <<'PY'
from pathlib import Path
paths = [Path('runtime/wasm32/foreign-api.lisp')] + [
    Path('tests/wasm/stage2')/name/'checks.lisp' for name in
    ['foreign-api', 'foreign-finalizers', 'foreign-strings', 'foreign-lisp-callbacks']]
Path('/private/tmp/ccl-work/codex/foreign-browser/source.lisp').write_text(
    '\n'.join(p.read_text() for p in paths))
PY
python3 -B tests/wasm/stage1/loader-target/build.py "$work/checks" \
  --postimage="$work/boot" --source="$work/source.lisp"
python3 -B tests/wasm/stage2/foreign-browser/run.py \
  --boot "$work/boot" --level1 "$work/level1" --checks "$work/checks" \
  --playwright /private/tmp/ccl-work/codex/stage2-browser-tools/node_modules/playwright-core/index.mjs \
  --browser-config /absolute/path/to/browser-config.json
```

The runner leases its inputs and output, writes evidence under
`/private/tmp/ccl-work/codex/foreign-browser-tests/run`, and deletes its successful
assembled foreign module. Retain compact results, source/tool/input identities
and original failures before clearing successful generated build inputs. The
compiler corpus remains deferred until the whole FFI layer is complete.
