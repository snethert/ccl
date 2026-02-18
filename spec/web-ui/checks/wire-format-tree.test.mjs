/**
 * Conformance checks for: wire-format-tree
 * Contract: spec/web-ui/contracts/wire-format-tree.md
 *
 * Stub — all checks fail until implementation exists.
 */

const checks = [
  { id: 'invariant.1', desc: 'Magic equals 0x55494231 and version equals 1' },
  { id: 'invariant.2', desc: 'All reads are bounds-checked' },
  { id: 'invariant.3', desc: 'root_index < node_count when node_count > 0' },
  { id: 'invariant.4', desc: 'Incomplete payload fails atomically' },
  { id: 'invariant.5', desc: 'Composite graph is acyclic' },
  { id: 'invariant.6', desc: 'Identical bytes produce identical tree' },
  { id: 'invariant.7', desc: 'Child order matches encoded index order' },
  { id: 'behavior.1', desc: 'Writers deduplicate string table entries' },
  { id: 'behavior.2', desc: 'Missing string indices decode to fallback' },
  { id: 'behavior.3', desc: 'Object composite key order preserved' },
  { id: 'behavior.4', desc: 'Duplicate object keys: last-write-wins' },
  { id: 'behavior.5', desc: 'Invalid child indices are dropped' },
  { id: 'behavior.6', desc: 'Composite types not emitted without capability' },
  { id: 'behavior.7', desc: 'Missing capability fails on composite types' },
  { id: 'anti-pattern.1', desc: 'No trusted payload bounds' },
  { id: 'anti-pattern.2', desc: 'No code execution from property values' },
  { id: 'anti-pattern.3', desc: 'No circular composite references' },
  { id: 'anti-pattern.4', desc: 'No reordering during decode' },
  { id: 'anti-pattern.5', desc: 'No skipped magic/version validation' },
  { id: 'anti-pattern.6', desc: 'No composite values without negotiation' },
];

export async function run() {
  let pass = 0, fail = 0, skip = 0;
  for (const check of checks) {
    console.log(`SKIP ${check.id} — ${check.desc} (not implemented)`);
    skip++;
  }
  return { pass, fail, skip };
}
