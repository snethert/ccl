/**
 * Conformance checks for: renderer
 * Contract: spec/web-ui/contracts/renderer.md
 *
 * Stub — all checks fail until implementation exists.
 */

const checks = [
  { id: 'invariant.1', desc: 'Conforms to at least one profile' },
  { id: 'invariant.2', desc: 'Deterministic output for same input' },
  { id: 'invariant.3', desc: 'Duplicate sibling keys fail reconciliation' },
  { id: 'invariant.4', desc: 'Child order matches next tree after reconcile' },
  { id: 'invariant.5', desc: 'Hit-test tie-break by visual stacking order' },
  { id: 'invariant.6', desc: 'Font choice is deterministic' },
  { id: 'behavior.1', desc: 'Keyed same-type children patch in place' },
  { id: 'behavior.2', desc: 'Keyed type-change children are replaced' },
  { id: 'behavior.3', desc: 'Missing keyed children are removed' },
  { id: 'behavior.4', desc: 'Unkeyed children use stable index fallback' },
  { id: 'behavior.5', desc: 'Multiple renders coalesce to latest tree' },
  { id: 'behavior.6', desc: 'flush() applies pending render synchronously' },
  { id: 'behavior.7', desc: 'captureEvents returns unsubscribe function' },
  { id: 'behavior.8', desc: 'invalidate is idempotent on cancel' },
  { id: 'behavior.9', desc: 'Dirty hints restrict redraw scope' },
  { id: 'behavior.10', desc: 'Missing font degrades to zeros' },
  { id: 'anti-pattern.1', desc: 'No non-deterministic render output' },
  { id: 'anti-pattern.2', desc: 'No duplicate sibling keys allowed' },
  { id: 'anti-pattern.3', desc: 'No cross-type patching' },
  { id: 'anti-pattern.4', desc: 'No locale-dependent measurement' },
  { id: 'anti-pattern.5', desc: 'No non-deterministic key fallback' },
  { id: 'anti-pattern.6', desc: 'No post-reconcile child reordering' },
];

export async function run() {
  let pass = 0, fail = 0, skip = 0;
  for (const check of checks) {
    console.log(`SKIP ${check.id} — ${check.desc} (not implemented)`);
    skip++;
  }
  return { pass, fail, skip };
}
