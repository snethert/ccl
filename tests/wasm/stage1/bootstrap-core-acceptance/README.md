# Bootstrap core acceptance: existing-target reader equivalence

Admits no additional functions and adds no target executions. This discharges
Steve's adopted R6 source-location allowance for the reviewed core proposal.

`run.py` extracts pristine pinned U1, uses the pinned macOS kernel and image,
and loads U1's architecture constants. `readers.lisp` reads the seventeen
backend declarations from their actual source, takes their declared features,
uses CCL's `setup-target-features` and TARGET package binding, and compares all
forms from each of the three changed files. No read failure is skipped.
Literal arrays compare recursively by contents and element type; strings retain
case and numbers retain their representation. Three comparator assertions cover
literal vectors, changed string case and integer/float distinction. Reader contexts are copies of the host
backend with the source-declared architecture and features; they are not foreign
machine-code compiler instances. Their complete target set must equal the
reviewed native snapshot's seventeen profiles.

All 51 comparisons pass. A PPC32-only added definition fails on DARWINPPC32,
so the check cannot be satisfied by repeating the host reader. All source forms
and the reader feature lists are retained. The existing audit-145 comparison
of 136 decoded function occurrences supplies identical native executable bytes
and non-location data. Neither this check nor the allowance claims execution of
foreign native targets. The existing native test and ABI requirements stand.

```
python3 tests/wasm/stage1/bootstrap-core-acceptance/run.py /tmp/core-reader-check
```

The accepted proposal's verifier remains reproducible from commit 6947f83b.
After integration its original generator's input pins intentionally no longer
match HEAD. Integration copies the reviewed files exactly; this runner binds
their source hashes and reuses the exact reviewed native qualification.

Development failures are retained with the acceptance evidence. Initial reader
setup needed PPC-ARCH loaded before PPC32-ARCH; reading past backend declarations
unnecessarily reached unavailable foreign-ABI packages. The final reader stops
at the declared profiles and joins their exact set with the native snapshot.
Other harness corrections were a parenthesis, the census JSON boolean spelling,
copying a non-executable archived kernel with execute permission, and parsing
the snapshot's package-qualified target names.
