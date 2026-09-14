# Development record — 14 September 2026

The exploratory scripts, native commands, logs and outputs are retained. Their
pristine source/bootstrap copies are referenced by the same pinned archives,
rather than copied into this packet.

- `prefix-r1` failed in the Lisp reader: its single command expression named
  CCL-RICH-CENSUS before the earlier subform could create that package. No
  inventory was produced. The exact script, command and native backtrace remain.
- `prefix-r2` split observer loading into its own command expression. The native
  inspection succeeded, but the complete initial inventory did not reproduce:
  the first mismatch is row 14,734, among session-created functions. That
  result is retained as a refusal of a whole-inventory identity join.
- `prefix-r3` repeated that inspection and exported the native read-only region.
  It contains exactly 14,718 function objects. An independent image-file walk
  found the same number, with 94,001 total read-only objects. The scripts,
  complete comparisons and read-only export are retained. This established
  the bounded region to check; it did not repair or normalize the dynamic suffix.
- `run-r4`, the first full producer, exported all requested read-only bytes but
  refused its inventory envelope. Using SETF to disable the observation hook
  after the inventory generated two additional macro-expansion events. Those
  original events, body bytes, source snapshots and failure are retained.
  `run-r5` uses the special operator SETQ so the stream ends at the actual
  inventory-return boundary. No body-copy or image-decoder rule was weakened.
- `run-r5` is the finalized producer. Both native exports agree; the image
  checks and 24 controls pass. A separate verifier replays the retained output
  and runs another native export from the pinned input image.

The existing installer's warning about its unbound-at-compile-time
`*XLOAD-FASL-DISPATCH-TABLE*` variable remains in every native log. This slice
does not invoke the cross-dump reader or change that reviewed installation.
