# WASM Startup Regression Reference Map

This file locks the reference and authority contract used by the `WASM-SR-*`
startup-regression tickets.

## Fixed Refs

- Startup hardening baseline: `9a2bda2a`
- Regression source range includes: `b46646c3`
- Working tip observed at lock time: `9462beba`
- Semantic/root reference: `origin/master` (no `root` ref available)
- Comparison head: `HEAD`

## Baseline Commands (Required)

Run these commands before and after each startup-regression ticket:

```bash
cd ccl
git show --no-patch --oneline 9a2bda2a b46646c3 origin/master HEAD
git merge-base b46646c3 HEAD
git merge-base origin/master HEAD
```

## Per-File Authority Matrix

| Path | Governing Ref | Authority Notes |
| --- | --- | --- |
| `lisp-kernel/wasm-kernel-stubs.c` | `9a2bda2a` + explicit policy constraints | File does not exist on `origin/master`; startup behavior authority for this file is baseline commit plus ticket constraints. |
| `level-0/l0-pred.lisp` | `origin/master` | Semantic authority is root-style `typep` path. |
| `level-1/l1-readloop-lds.lisp` | `9a2bda2a` (startup-flow sections) | Startup/debug flow in scoped sections must align to baseline behavior unless explicitly re-aligned by a ticket. |

## Validation Range Contract

- Use `9a2bda2a..HEAD` for startup hardening drift checks.
- Use ranges that include `b46646c3` to verify known-regression detection behavior.
- Use `origin/master..HEAD` only for semantic/root comparisons and `level-0`
  authority checks.
- For `level-0/` and `level-1/`, do not introduce semantic changes outside
  explicit semantic re-alignment tickets.

## Notes

- `origin/master` lacks `lisp-kernel/wasm-kernel-stubs.c`; this is intentional
  and is the reason that startup authority for that file is pinned to
  `9a2bda2a` and policy constraints.
