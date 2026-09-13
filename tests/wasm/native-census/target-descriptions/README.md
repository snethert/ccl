# Census target descriptions

Extends the reviewed, fixed `dumplisp.lisp` traversal with eight D1-derived
subtype descriptions and a named startup batch-mode dependency. Seven of the
twelve source definitions now yield their actual front-end bodies. Five native
boundary gaps remain. This fixture emits no Wasm implementation or acceptance
result.

```sh
python3 tests/wasm/native-census/target-descriptions/run.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --work NEW-DISPOSABLE-DIRECTORY --output NEW-OUTPUT-DIRECTORY
```

The directories must be new, separate and outside the evidence store. The runner
uses the same seven pinned inputs as the reviewed source traversal and loads the
accepted registration binaries through the actual module entries. Its extension
changes only the census architecture's subtype table, one architecture macro and
the census pass-2 callback, restoring them on ordinary and nonlocal return. The
fixture's own target constants and native refusal functions live only in the
disposable process. No shared source is patched, no native target is copied, and
no image or target FASL is written.

`descriptions.json` is the source-to-target metadata ledger and boundary worklist.
The analyzer checks the subtype declarations against U1, independently of the
Lisp constants and the evaluated target table. These are type-classification
values, not full payload layouts, GC walkers or native pointer support.

The batch-flag macro accepts exactly the quoted `batch-flag` key and produces a
call to `WASM-CENSUS-SERVICES::STARTUP-BATCH-FLAG`. That dependency is unresolved:
the fixture function raises an error if executed. No native kernel-global offset
or fabricated batch-mode value is substituted. All eight boundary obligations
remain `REPLACEMENT_REQUIRED`, with implementation absent and condition tests
not run. They are work items, not eight new gate slots.

Four load-time initializers appear while compiling `CLEAR-IOBLOCK-STREAMS`.
The pass-2 extension captures each initializer and returns a distinct native
refusal closure to the file compiler. U1's `nx1-load-time-value` puts it in a
deferred literal; the containing function can then finish front-end processing.
Its pass-2 escape occurs before dumping or installing a function. A separate
acode walk reads the actual deferred literal, matches the closure by EQ and
records its owning function, site and initializer. It refuses an unknown token,
shape or owner. The checker requires four distinct links to four distinct bodies.
This handling is qualified only for the fixed module's observed deferred forms.

Six native controls omit the types or batch macro, replace the batch read with
zero, stop at the first initializer, attempt initializer execution, or alias the
initializer guards. Twenty-six analysis controls check coverage, ownership,
retained calls, metadata, restoration and false completion claims.

```sh
python3 tests/wasm/native-census/target-descriptions/verify.py --packet RETAINED-PACKET
```

This command replays the retained data and controls without running native CCL.
Raw JSON captures are compressed without rewriting; a successful duplicate is
represented by its command, digest and equality result. Original development
failures and the identity-alias capture are retained in the compact development
archive. See the [report](../../../../doc/WASM/stage0/target-descriptions.md) for
the remaining native boundaries and macro-environment limits.
