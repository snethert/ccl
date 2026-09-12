# Reversible census backend registration

This is S0-LL08-a's observation-only loading and target-state fixture. It uses the real U1 reader/front end and a capture-only pass-2 entry. It emits no Wasm or target FASL. Its fourteen source forms are a bounded registration proof, not the full bootstrap census.

Run from the repository root on the macOS x86-64 reference host:

```sh
python3 tests/wasm/native-census/stub-backend/run.py \
  --inputs /Users/buildsomething/Source/ccl-evidence/macos-u1-inputs \
  --kernel /tmp/ccl-native-census-r7/ccl/dx86cl64 \
  --work NEW-DISPOSABLE-DIRECTORY \
  --output NEW-EVIDENCE-DIRECTORY
python3 tests/wasm/native-census/stub-backend/test_registration.py \
  --output NEW-EVIDENCE-DIRECTORY/unit-controls.json
python3 tests/wasm/native-census/stub-backend/test_record.py \
  --run NEW-EVIDENCE-DIRECTORY
python3 tests/wasm/native-census/stub-backend/record.py \
  --run NEW-EVIDENCE-DIRECTORY \
  --inventory doc/WASM/stage0/inventory.json
```

Use the reviewed native kernel identified by the retained run. All directories must be new; producers refuse to overwrite results. `--failures DIRECTORY` can retain an earlier development failure with the final packet. Inspect `results.json` and native logs if a command fails. Only one final packet is needed; unchanged prerequisites and complete baseline trees are not copied per iteration.

`registration.patch` adds two module records to `lib/systems.lisp`. `registration.py` applies that patch and the two `payload/` sources as one owned unit in a pristine U1 archive. It verifies source identities, preserves recovery data and removes the entire unit on success or failure. It refuses unexplained external edits rather than overwriting them. `run.py` performs the clean/registered/restored native builds, full native suites, snapshots, probe comparison and fresh target sessions. On a later failure it also restores the saved clean output files. Normal removal is followed by a fresh bootstrap rebuild, never by retaining an observed image as an implementation baseline.

For recovery after an interrupted process, use the same fixture revision and owned work directory:

```python
from pathlib import Path
import sys
sys.path.insert(0, "tests/wasm/native-census/stub-backend")
from registration import Registration
Registration(Path("OWNED-WORK-DIRECTORY"),
             Path("tests/wasm/native-census/stub-backend")).restore()
```

This restores source only. If the runner did not complete its output recovery, keep that disposable tree quarantined; start subsequent work from pristine U1 and the pinned bootstrap. There is no reason to use a development tree as the port's baseline.

`session.lisp` compiles the registered module sources in a fresh host session. The loading recipe establishes target backend/features/FASL target/foreign data and package nicknames before reading the corpus or target-dependent macro source. The shared U1 compiler is untouched. `check.py` checks literal target values, actual acode widths and argument partitions, and dependency identities. A cached-host-macro control really compiles a native macro FASL before entering the target context. Context restoration is checked on return and nonlocal escape. The fixture assumes one compiler thread in each fresh process.

Native FASLs are stored once in `baseline-fasls.tar.gz`; later manifests compare against that baseline, with only the intentional shared difference stored separately. `sources.tar.gz` retains exact executed source inputs and producer/unit tooling. Producer controls alter semantic data in memory. The LL08-a envelope covers only this new packet; historical accepted records are reused separately rather than repacked or rehashed.

See the [qualification and limits](../../../../doc/WASM/stage0/stub-registration.md). The descriptor is a small D1/B observation subset: it supplies neither complete data layouts nor foreign/callback/LAP/lowering implementations. Further census work must qualify those dependencies. Functional compiler implementation still needs separate authorization under the standing rules.
