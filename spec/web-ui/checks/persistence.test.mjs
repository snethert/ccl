/**
 * Conformance checks for: persistence
 * Contract: spec/web-ui/contracts/persistence.md
 *
 * Stub — all checks fail until implementation exists.
 */

const checks = [
  { id: 'invariant.1', desc: 'Files are authored units, not fragmented' },
  { id: 'invariant.2', desc: 'Objects are immutable and content-addressed' },
  { id: 'invariant.3', desc: 'Persistence is append-only' },
  { id: 'invariant.4', desc: 'Reference updates are crash-safe' },
  { id: 'invariant.5', desc: 'Recovery resolves each ref to one snapshot' },
  { id: 'invariant.6', desc: 'Paths are POSIX-like UTF-8 NFC-normalized' },
  { id: 'invariant.7', desc: 'No silent data loss' },
  { id: 'behavior.1', desc: 'Autosave does not overwrite user-save history' },
  { id: 'behavior.2', desc: 'Autosave triggers on idle/time/boundary' },
  { id: 'behavior.3', desc: 'Edit/save/history works offline post-bootstrap' },
  { id: 'behavior.4', desc: 'Sync moves objects, no surprise rewrites' },
  { id: 'behavior.5', desc: 'Divergence is explicit ref state' },
  { id: 'behavior.6', desc: 'Protected refs use single-writer lease' },
  { id: 'behavior.7', desc: 'Secondary writers use branch/session refs' },
  { id: 'behavior.8', desc: 'Storage pressure: autosave > artifacts > saves' },
  { id: 'anti-pattern.1', desc: 'No in-place blob mutation' },
  { id: 'anti-pattern.2', desc: 'No object-centric workflow required' },
  { id: 'anti-pattern.3', desc: 'No content replacement for indexing' },
  { id: 'anti-pattern.4', desc: 'No conflict litter filenames' },
  { id: 'anti-pattern.5', desc: 'No silent ref advancement' },
  { id: 'anti-pattern.6', desc: 'No file primacy break without policy' },
  { id: 'anti-pattern.7', desc: 'No surprise filename rewrites' },
];

export async function run() {
  let pass = 0, fail = 0, skip = 0;
  for (const check of checks) {
    console.log(`SKIP ${check.id} — ${check.desc} (not implemented)`);
    skip++;
  }
  return { pass, fail, skip };
}
