/**
 * Conformance checks for: bridge-envelope
 * Contract: spec/web-ui/contracts/bridge-envelope.md
 *
 * Stub — all checks fail until implementation exists.
 */

const checks = [
  { id: 'invariant.1', desc: 'Envelope version field is 1' },
  { id: 'invariant.2', desc: 'Empty string fields normalize to null' },
  { id: 'invariant.3', desc: 'Non-string error normalizes to Unknown error' },
  { id: 'invariant.4', desc: 'Normalization is deterministic' },
  { id: 'invariant.5', desc: 'Sequence numbers are monotonic per streamId' },
  { id: 'invariant.6', desc: 'All envelope fields present after normalization' },
  { id: 'behavior.1', desc: 'Strict mode rejects unknown kinds' },
  { id: 'behavior.2', desc: 'Non-strict mode preserves unknown kinds' },
  { id: 'behavior.3', desc: 'Validation occurs before state application' },
  { id: 'behavior.4', desc: 'Sequence monotonicity enforced for microkernel messages' },
  { id: 'behavior.5', desc: 'Invalid timestamps are rejected' },
  { id: 'anti-pattern.1', desc: 'No code execution during decode' },
  { id: 'anti-pattern.2', desc: 'No state application without validation' },
  { id: 'anti-pattern.3', desc: 'No locale-dependent validation' },
  { id: 'anti-pattern.4', desc: 'No trusted envelope inputs' },
  { id: 'anti-pattern.5', desc: 'No silent drop of malformed envelopes' },
];

export async function run() {
  let pass = 0, fail = 0, skip = 0;
  for (const check of checks) {
    // TODO: Replace with real assertions against implementation
    console.log(`SKIP ${check.id} — ${check.desc} (not implemented)`);
    skip++;
  }
  return { pass, fail, skip };
}
