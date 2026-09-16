# On-demand native census

One entry point answers questions from a retained build or observes a selected
call in a fresh, disposable native U1 session. It does not compile Wasm or infer
an exhaustive callee bound. No upstream source is edited or definition installed
by the probe. The instrumentation is a temporary forwarding pass-2 hook over one
private compilation; both the hook and changed IR operands are restored.

Run from the repository root with Python 3.12 or later. Retained queries are
portable; native probes require the macOS x86-64 reference host and the pinned
archives/kernel in the evidence repository. Choose fresh output directories.

## Query an existing capture

```sh
mkdir -p "$HOME/ccl-census-queries"
cat > "$HOME/ccl-census-queries/question.json" <<'JSON'
{"kind":"find-function","name":"CCL::GETF-TEST"}
JSON
python3 tests/wasm/native-census/query/run.py query \
  --capture ../ccl-evidence/2026-09-15-correlated-query-base-r1/packet.json \
  --question "$HOME/ccl-census-queries/question.json" \
  --cache "$HOME/ccl-census-queries/capture.sqlite" \
  --output "$HOME/ccl-census-queries/find-getf"
```

The first query builds a derived SQLite index. Later queries reuse it after
checking the capture and cache identities. Only that capture's three input
files are checked, not the evidence catalog. The cache can be deleted and
rebuilt. It is not evidence or an accepted result. A changed tool/input requires
a fresh cache path; a damaged cache is refused.

Supported JSON questions:

| Question | Answer |
| --- | --- |
| `{"kind":"summary"}` | Indexed populations |
| `{"kind":"find-function","name":"CCL::GETF-TEST"}` | Exact printed-name search, possibly several compiler identities |
| `{"kind":"function","id":N}` | Compiler function and recorded calls |
| `{"kind":"calls","id":N}` | Calls owned by compiler function N |
| `{"kind":"call-site","function":N,"site":S}` | One compiler function/site pair |
| `{"kind":"materialization","id":N}` | Compiler identity to emitted native function |
| `{"kind":"body","id":N}` | Native function descriptor, payload and literals |
| `{"kind":"binding","id":N}` | Exact symbol's observed binding history |
| `{"kind":"binding-event","id":N}` | An event, including an unkeyed NIL binding event |
| `{"kind":"registry","id":N}` | Generic function's checkpoints and mutation observations |

Replace N/S with JSON integers from an earlier answer. IDs belong only to the
answer's capture namespace. Name search finds candidates; it never joins
identities between runs. Removal records are **intent before the store**, not
completed removals. `NOT_OBSERVED` means absence from this capture, not an
unsupported operation. Every answer retains `exhaustive: false` and its input
hashes. The correlated capture has 51,341 compiler functions and 103,392 calls;
these are not the older rich build's 51,601 functions and 103,393 calls.

## Observe a native call site

First list the ordinary call sites in an actual U1 definition:

```sh
python3 tests/wasm/native-census/query/run.py sites \
  --work "$HOME/ccl-census-queries/native-work" \
  --source level-1/l1-utils.lisp --function CCL::GETF-TEST \
  --output "$HOME/ccl-census-queries/getf-sites"
```

The tool creates a disposable pristine U1 copy from the retained source and
bootstrap archives. `--source-archive` can specify the same pinned archive at a
different location; `--evidence` before the subcommand relocates the evidence
repository. The requested source is checked against U1 on every invocation.
Select one complete object from `answer.json`'s `selections` array:

```sh
python3 - <<'PY'
import json
from pathlib import Path
base = Path.home() / 'ccl-census-queries'
answer = json.loads((base / 'getf-sites/answer.json').read_text())
(base / 'selection.json').write_text(json.dumps(answer['selections'][0]))
(base / 'scenario.lisp').write_text(
    '(lambda (fn) (funcall fn (list :a 10 :b 20) :b (function eq)))\n')
PY
python3 tests/wasm/native-census/query/run.py probe \
  --work "$HOME/ccl-census-queries/native-work" \
  --source level-1/l1-utils.lisp --function CCL::GETF-TEST \
  --selection "$HOME/ccl-census-queries/selection.json" \
  --scenario "$HOME/ccl-census-queries/scenario.lisp" \
  --output "$HOME/ccl-census-queries/getf-witness"
```

This example returns 20 and observes two calls through the supplied predicate.
The selection binds source bytes, function name, nested-function path and IR
path. It is a new private compilation, not an identity claim about a resident
image function or an earlier build's site number. To investigate a Stage 1
site, map it explicitly to this source selection and supply its native scenario.

The scenario is a Lisp lambda receiving the recompiled function. It runs against
reference, observed and restored versions in one fresh process. It must set up
and reset any relevant state itself and return/check the effects that matter.
All returned values are compared using `EQUALP`; uncaught errors are compared
by condition type. This is not a comparison of every side effect or condition
message. The reference/restored native code must be byte-identical.

The logger observes the resolved target after argument evaluation, just before
dispatch. It preserves spread arguments, all values and nonlocal exits. A record
does not assert successful entry or return: arity checks or the callee may fail.
Function IDs are local to this invocation. A late symbol redefinition is read
at dispatch, not before its argument effects. Events are capped by
`--event-limit`; dropped events are counted. `NOT_REACHED` and `TRUNCATED` exit 2
and cannot supply a complete positive witness. Failures retain logs and exact
tool sources; output directories are never overwritten.

The current source reader supports uniquely named top-level `DEFUN` forms and
top-level package changes. It refuses missing/ambiguous definitions and unreadable
source rather than guessing a nested definition, method environment or call site.
The disposable baseline is an observation environment, never the port's starting
image. A scenario runs native Lisp with native capabilities; use a controlled
scenario, not untrusted input.

## Verification

`test_native.py` exercises a real U1 function plus explicitly synthetic semantic
controls, corrupted selections and four source mutants. `test_capture.py` compares
answers with original native events and checks missing/reordered streams, member
identity, namespace/query shape and damaged caches. Tests use fresh output
directories. Their results qualify this tool's stated scope; formal LL15-b/c
publication, independent review and project acceptance are separate steps.
