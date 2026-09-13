# Macro and special-operator wrapper contents

This post-boot exporter describes the 1,059 two-element function-cell vectors
previously labeled opaque: 1,028 macro wrappers and 31 special-operator wrappers.
It records both slots, macro expansion functions, special-operator symbols and
their current `*nx1-alphatizers*` handler identities. No wrapper is invoked and no
captured object or compiler source is changed.

The existing boot exporter has one optional `after-export` callback, invoked
only after its legacy stream is closed. The callback shares the completed ID
map and allocates further identities without renumbering old objects. A disabled
export and two extended exports must reproduce every byte of the reviewed
legacy stream; the two wrapper exports must also match exactly.

Prepare the reviewed base graph if it is not already available:

```sh
python3 tests/wasm/native-census/startup-closure/materialize_boot.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --packet /Users/buildsomething/Source/ccl-evidence/2026-09-13-boot-integration-r1 \
  --output /tmp/ccl-wrapper-base-new
```

Then run from the repository root on the macOS x86-64 reference host, with new,
separate work and output directories:

```sh
python3 tests/wasm/native-census/boot-wrappers/run.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --base-graph /tmp/ccl-wrapper-base-new/census.json.gz \
  --work /tmp/ccl-wrapper-work-new --output /tmp/ccl-wrapper-result-new
```

The runner uses a disposable copy of the retained image and kernel. It writes no
FASL or saved image and adds no startup observation hook. The work directory
contains the unpacked input and reproducible full graph; the output is a compact
wrapper description, bounded graph update, checks and run record. The original
image is never an implementation baseline. All direct inputs and executed
source identities are bound; unchanged archive payloads are not scanned.

The exporter derives wrapper rows from old opaque descriptors. A second native
reading walks the original binding events and inspects literal array slots,
checking payload and handler IDs independently of those rows. Native controls
reject wrong layouts, dispatch values and payload types. Twenty-six analysis
controls cover omissions, wrong identities, graph insertions, false
classification and changes to seeds, initializers or trace modules.

`join.py` classifies the wrapper nodes and adds dependencies. `check.py` derives
full expected records from the literal-slot witness, including edge multiplicity
and exact replacement preconditions. Existing functions are reused only when
their complete same-image descriptor agrees. Macro expansion edges have phase
`macroexpand`; special handlers have phase `compile`; the bad-application trap
has phase `run`. This is native identity coverage, not Wasm implementation or
complete function-body closure.

The xloader stores `#xc9cd0000000000` as the raw macro-application word. Lisp
reads those bits as a fixnum, shifted right by three. The export retains both the
Lisp value and reconstructed raw word, and the checker verifies both against U1.
Special handler observations describe the saved image, not historical handler
executions during the recorded boot.

To reproduce a retained graph update without another native export:

```sh
python3 tests/wasm/native-census/boot-wrappers/verify.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --base-graph /tmp/ccl-wrapper-base-new/census.json.gz \
  --packet /absolute/path/to/wrapper-packet \
  --output /tmp/ccl-wrapper-verification-new
```

This validates the bound descriptions, reproduces the update, applies it to the
base and compares the full graph identity with the producer's result. Retain the
verification record; full graphs need not be duplicated in evidence. See the
[scope report](../../../../doc/WASM/stage0/boot-wrappers.md).
