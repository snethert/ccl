# Artifact retention

User direction, 28 September 2026. This policy supersedes older instructions
to retain complete compiled outputs or a new workspace for every attempt.
It changes storage, not acceptance criteria or the identity of historical
evidence. Tooling must conform to this policy; recording it does not establish
that existing writers or packs already conform.

1. **Compiler state is shared.** Do not dump or copy `compiler.image` into
   each run. Cache one image per compiler build hash, including the source,
   bootstrap, toolchain and configuration identities needed to distinguish
   builds. Runs reference that entry. A live host process can avoid the image.
   Cache the native oracle once per exact set of inputs and environment too;
   do not copy the full `native.json` into each run or evidence pack.
2. **Generated assembly is temporary.** Assemble and discard successful
   `.wat` files. Retain or regenerate the particular WAT needed to reproduce
   a failure. Remove successful `.wasm` files after execution; keep failing
   inputs and the hashes that bind results to the executed bytes. Tracked
   WAT source files remain source inputs.
3. **Records are temporary.** Consume full `*.records.json` during the build
   or a diagnostic that needs them, then retain a digest and counts per file.
   Record the pinned regeneration recipe before removing records required
   by later tooling. A summary cannot be passed off as the original records.
4. **Reuse workspaces.** Use one run directory per purpose, overwritten for
   subsequent attempts under an exclusive lease. First retain necessary
   results and original failures. Do not overwrite an active run. Compilation
   and validation storage stays on the two verified RAM-backed volumes;
   their shared 16 GiB is a hard cap, with no SSD spill directory.
5. **Evidence is small.** Aim for tens of megabytes; the user clarified that
   50 MB is a guideline, not a hard cap. A finalized pack contains sources
   or source identities, toolchain/input hashes, results
   JSON, review records and specific failing inputs. No compiled-artifact
   tarballs, complete successful build trees, or duplicate `development/`
   and `rejected/` copies. Record a rejected experiment's source hash and
   results file, plus any unique failing input needed for reproduction.
   Required shared bootstrap inputs and native baselines have one persistent
   home referenced by identity; do not duplicate them into deliverables.
6. **Compact existing packs.** Apply the same policy to the existing evidence
   archive. Remove compiled artifacts only when pinned sources, required
   inputs and a regeneration recipe account for them. Preserve original
   manifests and review verdicts; record removed artifact hashes and the
   replacement references in a compaction manifest. Update readers that
   require the removed files before removing them. Retain unique failures.
   Rewriting Git history is not part of routine pack compaction.

The SSD directories set aside when the RAM disk was created on 26 September
are obsolete scratch/cache copies, distinct from the evidence archive and
the active RAM volumes:

- `/private/tmp/ccl-work.ssd-before-ramdisk-20260926-200255`
- `/Users/buildsomething/Library/Caches/ccl-wasm-validation.ssd-before-ramdisk-20260926-200255`

Both copies were deleted on 28 September 2026 at the user's direction.
`ccl-evidence/2026-09-28-artifact-retention/ssd-cleanup.json` records measured
free-space change. The evidence archive and active RAM volumes were preserved.

The shared validation driver references cached compiler/oracle inputs and
discards generated assembly. Its `finish` operation retains a checked,
snapshot, compressing large text/results and preserving declared
`failure-inputs.json` files. Original failure directories are also retained.
The target loader defaults to fixed purpose paths and record summaries.
`--diagnostic-records` keeps records temporarily for a batch of record-based
diagnostics; finalize that output after the diagnostics. Individual record
readers can regenerate them from the checked source recipe on the RAM disk.

`doc/WASM/tools/compact-evidence.py` defaults to a plan; `--apply` compacts
eligible pinned packs. It reports unresolved source pins, required inputs and
retained excess explicitly. It does not remove unique failures to meet a cap.
`read-compacted-evidence.py PACK` verifies retained original bytes;
`--extract ORIGINAL_ARCHIVE --output RAM_PATH` recovers the retained sources,
results and failing inputs at their original relative names. The output lists
elided compiled products and is not presented as an executable restore.
