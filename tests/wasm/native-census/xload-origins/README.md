# Cold initializer origins

This fixture observes U1's existing cross-loader while it reads the exact 164-FASL set used by the reviewed boot observation. It identifies the source module for all 133 cold initializers. Of these, 131 retain a compiler source context; entries 65 and 106 retain only their module and exact FASL initializer offsets.

There is no new shared-source patch or native recompilation. Three process-local replacements surround the existing lfuncall reader, `xload-fasload` and `xload-dump-image`. Each successful reader invocation must add exactly one cons to the queue, with its former list as the tail. Immediately before image writing, the recorded insertion order must agree with the host list and the list actually stored in the target image. U1's single reversal makes insertion order equal boot execution order. A fresh boot of that image must reproduce the complete reviewed boot stream after the declared archive-root relocation.

`unwind-protect` restores all three original function objects. The injected abort checks restoration before any image is written; the omission control suppresses one recording while leaving the actual queue unchanged. Twenty analysis controls reject corrupted counts, identities, orders, module joins, source notes, ranges and extra fields.

The source-note reader validates U1's four-slot structure and SOURCE-NOTE class-cell identity, reads its filename and range, and retains the raw words as well as decoded offsets. Python independently decodes the tagged packed/pair range. The offsets are byte positions in the exact source bytes corresponding to the FASL, and are compiler contexts: several expanded forms can share a context. The reviewed boot patch is materialized into a separate data directory solely to recover the source bytes for its changed FASLs; those copies are never loaded or compiled.

Run from the repository root on macOS x86-64, using fresh work and output directories:

```sh
python3 tests/wasm/native-census/xload-origins/run.py \
  --store /Users/buildsomething/Source/ccl-evidence \
  --work /tmp/ccl-xload-origin-work --output /tmp/ccl-xload-origin-result
```

This extracts pristine U1 and the pinned bootstrap into an owned archive, reuses retained FASLs and the kernel, writes a plain and an observed boot image, boots and exports the observed image, binds source contexts, runs controls, and checks that all 164 FASLs and the source files used for materialization remain unchanged. Image byte identity is recorded separately; neither image is used as an implementation baseline. Source and kernel in the project checkout are untouched.

Reproduce just the retained joins and twenty controls without native execution:

```sh
python3 tests/wasm/native-census/xload-origins/verify.py \
  --packet /path/to/origin-packet \
  --store /Users/buildsomething/Source/ccl-evidence \
  --output /tmp/ccl-xload-origin-verification
```

The positional rule requires identical input bytes and loader order, the insertion and saved-queue witnesses, and the corresponding boot execution. Queue length alone is insufficient. The two missing source ranges remain null; neighboring locations are never substituted. This supplies source provenance for later census integration, not complete static dependencies or LL15 acceptance.
