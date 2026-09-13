# Target numeric and layout helper paths

This isolated census extension rebuilds selected helper bodies from pinned U1
source. Private EQL, BASIC-STREAM-P and VECTORP compiler macros use those bodies
while CCL's actual front end traverses `lib/dumplisp.lisp`. Numeric probes expose
two unsafe host assumptions: the native helper treats single floats as immediate
and uses the native fixnum range. The target version reads the 32-bit branch and
uses U1's target-range predicate through a lexical binding.

Run on the macOS x86-64 reference host with fresh paths:

```sh
python3 tests/wasm/native-census/target-helpers/run.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --work /private/tmp/ccl-target-helper-work-review \
  --output /private/tmp/ccl-target-helper-review
```

Replay the retained packet and its direct bindings:

```sh
python3 tests/wasm/native-census/target-helpers/run.py \
  --verify /Users/buildsomething/Source/ccl-evidence/2026-09-13-target-helpers-r1
```

Six native sessions cover normal/repeat execution, the inherited helper and
three mutations: host source reading, host fixnum range and host subtag lookup.
Normal/repeat captures must be byte-identical; all six file traversals must be
byte-identical. Eight numeric probes check both expansion and actual front-end
call records. Five descriptor probes cover changed values, changed range,
missing-description refusal and restoration. Four native controls and fifteen
checker controls must reject with their specified reasons.

Private functions compile only in memory. The existing owner-only pass-2 observer
joins their actual compiler records to the returned functions and is restored.
No global helper binding is replaced. Source, on-disk FASLs and the existing
fixtures remain unchanged; no Wasm or implementation image is produced.

Qualification covers these observed paths and probes. Nonconstant type inference,
other helper dependencies and native object materialization remain open. No
graph widening or gate obligation is removed. See the
[scope report](../../../../doc/WASM/stage0/target-helpers.md).
