# Build-flow development retention — 14 September 2026

One final packet retains the original failures, their commands/source snapshots,
focused checks and superseded-success identities. No native session ran.

- `pilot-r1` successfully read the first 100 pre-pass-2 families. It deliberately
  stopped before completion and is not a complete-build result.
- `survey-r1` refused `MATERIALIZATION_BEFORE_IR`. The first implementation
  assumed every materialized function had passed through Lisp pass 2. U1's
  `compile-named-function` explicitly skips that pass if pass 1 already supplied
  an LFUN. The correction uses the retained front-end snapshot for those cases
  and labels their assembly dependencies untraversed. The original source,
  run/input identities and traceback are retained.
- `survey-r2` completed the build extraction: 51,601 functions, 200 lexical
  bounds and 259 front-end-only families. Later revisions add direct-target
  checks, symbol descriptors, bounded garbage-collection batches in the Python
  analyzer, controls and exchange integration. Its superseded analysis payloads
  are retained by hash; its summary, command and source snapshots are kept.
- `controls-r1` successfully ran the initial 21 controls and eight callback
  probes on the retained data. The later unattached-function control brings the
  final total to 22. Its source and output remain in the development archive.
- `survey-r3` refused the full graph with `required node outside closure` for
  the assembly-only functions. It had incorrectly labeled every observed
  function an attached requirement. The correction computes attachment through
  actual existing paths, retains all 259 disconnected functions in the worklist,
  and supplies both directions of the witnessed code/compiler identity join.
  It neither adds a broad membership edge nor marks required code optional.
  Original command, source snapshots and traceback are retained.
- `projection-r2` successfully checked that corrected projection against the
  pinned full graph. All earlier graph records were preserved.
- `survey-r4` is the final complete producer: the full source/code extraction,
  attached graph, symbol identities and all controls. Its run record carries
  the executed source/tool/input identities. Finalization and the independent
  replay command have their own pinned tool sources.

The successful focused Python checks used the retained `survey-r2` facts and
the pinned wrapper graph; their source snapshots and outputs are kept. They are
development checks, not additional native executions. No original failure is
rewritten or reconstructed as success.
