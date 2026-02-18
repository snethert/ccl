/**
 * Conformance checks for: security
 * Contract: spec/web-ui/contracts/security.md
 *
 * Stub — all checks fail until implementation exists.
 */

const checks = [
  { id: 'invariant.1', desc: 'Startup gate is strict with no fallback' },
  { id: 'invariant.2', desc: 'Check execution stops at first failure' },
  { id: 'invariant.3', desc: 'load-image terminates on gate failure' },
  { id: 'invariant.4', desc: 'granted[] is deduped and lexically sorted' },
  { id: 'invariant.5', desc: 'Capability log is append-only' },
  { id: 'invariant.6', desc: 'Safe mode blocks all capability-gated commands' },
  { id: 'invariant.7', desc: 'Policy evaluation is deterministic' },
  { id: 'invariant.8', desc: 'Disabling safe mode does not auto-grant' },
  { id: 'behavior.1', desc: 'Startup applies to full-runtime-v1 only' },
  { id: 'behavior.2', desc: 'All 12 checks run in SRG sequence' },
  { id: 'behavior.3', desc: 'Summary records matching results_digest' },
  { id: 'behavior.4', desc: 'hasCapability returns false in safe mode' },
  { id: 'behavior.5', desc: 'Policy first-match: explicit > wildcard > default' },
  { id: 'behavior.6', desc: 'Grant/revoke logged with action and reason' },
  { id: 'behavior.7', desc: 'setSafeMode(true) disables escapes immediately' },
  { id: 'behavior.8', desc: 'Pending requests process in stable order' },
  { id: 'behavior.9', desc: 'dom.escape is always capability-gated' },
  { id: 'anti-pattern.1', desc: 'No silent transport downgrade' },
  { id: 'anti-pattern.2', desc: 'No skipped/reordered startup checks' },
  { id: 'anti-pattern.3', desc: 'No silent capability degradation' },
  { id: 'anti-pattern.4', desc: 'No auto-grant on safe mode disable' },
  { id: 'anti-pattern.5', desc: 'No capability log mutation' },
  { id: 'anti-pattern.6', desc: 'No mismatched results_digest' },
  { id: 'anti-pattern.7', desc: 'No non-deterministic policy evaluation' },
];

export async function run() {
  let pass = 0, fail = 0, skip = 0;
  for (const check of checks) {
    console.log(`SKIP ${check.id} — ${check.desc} (not implemented)`);
    skip++;
  }
  return { pass, fail, skip };
}
