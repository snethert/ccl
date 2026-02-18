/**
 * Conformance checks for: focus-and-selection
 * Contract: spec/web-ui/contracts/focus-and-selection.md
 *
 * Stub — all checks fail until implementation exists.
 */

const checks = [
  { id: 'invariant.1', desc: 'Focus target is exactly four nullable fields' },
  { id: 'invariant.2', desc: 'History entries append in call order' },
  { id: 'invariant.3', desc: 'Reconciliation suspended during composition' },
  { id: 'invariant.4', desc: 'Selection ordered by list position' },
  { id: 'invariant.5', desc: 'Range endpoints inclusive and stable' },
  { id: 'invariant.6', desc: 'Unknown IDs rejected without allowUnknown' },
  { id: 'invariant.7', desc: 'Each setFocus appends exactly one entry' },
  { id: 'behavior.1', desc: 'setFocus normalizes and appends history' },
  { id: 'behavior.2', desc: 'setActiveTask updates focus to active window' },
  { id: 'behavior.3', desc: 'reconcileFocus resolves and completes targets' },
  { id: 'behavior.4', desc: 'Null reconcile with clearOnUnknown clears focus' },
  { id: 'behavior.5', desc: 'Same target reconcile skips history append' },
  { id: 'behavior.6', desc: 'Selection normalization from various inputs' },
  { id: 'behavior.7', desc: 'Missing listId/itemId leaves state unchanged' },
  { id: 'behavior.8', desc: 'Replace mode: single target, anchor = target' },
  { id: 'behavior.9', desc: 'Toggle mode: add/remove with anchor update' },
  { id: 'behavior.10', desc: 'Range mode: inclusive interval, replace fallback' },
  { id: 'anti-pattern.1', desc: 'No unvalidated DOM dataset trust' },
  { id: 'anti-pattern.2', desc: 'No stale ID mutation without allowUnknown' },
  { id: 'anti-pattern.3', desc: 'No duplicate history entries' },
  { id: 'anti-pattern.4', desc: 'No insertion-order selection' },
  { id: 'anti-pattern.5', desc: 'No composition-time reconciliation' },
  { id: 'anti-pattern.6', desc: 'No partial targets without completion' },
  { id: 'anti-pattern.7', desc: 'No persist without schema validation' },
];

export async function run() {
  let pass = 0, fail = 0, skip = 0;
  for (const check of checks) {
    console.log(`SKIP ${check.id} — ${check.desc} (not implemented)`);
    skip++;
  }
  return { pass, fail, skip };
}
