/**
 * Conformance checks for: command-system
 * Contract: spec/web-ui/contracts/command-system.md
 *
 * Stub — all checks fail until implementation exists.
 */

const checks = [
  { id: 'invariant.1', desc: 'Precedence is a total order with no ties' },
  { id: 'invariant.2', desc: 'Same inputs resolve to same command' },
  { id: 'invariant.3', desc: 'Enablement gates in fixed order' },
  { id: 'invariant.4', desc: 'Safe mode blocks all capability-gated commands' },
  { id: 'invariant.5', desc: 'Runtime commands return pending with requestId' },
  { id: 'invariant.6', desc: 'Trace reasons are a closed set' },
  { id: 'behavior.1', desc: 'Iterate scopes in precedence order' },
  { id: 'behavior.2', desc: 'Global scope checks keymaps.global' },
  { id: 'behavior.3', desc: 'Missing scope ID skips scope' },
  { id: 'behavior.4', desc: 'First match wins, no match returns null' },
  { id: 'behavior.5', desc: 'Trace entries for each visited scope' },
  { id: 'behavior.6', desc: 'Conflict analysis sorts deterministically' },
  { id: 'behavior.7', desc: 'Winner is first sorted candidate' },
  { id: 'behavior.8', desc: 'Unknown command is disabled' },
  { id: 'behavior.9', desc: 'Beginner-hidden command is disabled' },
  { id: 'behavior.10', desc: 'Safe mode disables capability-gated' },
  { id: 'behavior.11', desc: 'Missing capability disables command' },
  { id: 'behavior.12', desc: 'Missing args disables typed command' },
  { id: 'behavior.13', desc: 'Disabled commands fail with reason' },
  { id: 'behavior.14', desc: 'Beginner confirmation gate' },
  { id: 'behavior.15', desc: 'Runtime dispatch via runtime client' },
  { id: 'behavior.16', desc: 'No-exec command succeeds with null' },
  { id: 'behavior.17', desc: 'Exec command succeeds with result' },
  { id: 'anti-pattern.1', desc: 'No gate reordering' },
  { id: 'anti-pattern.2', desc: 'No scope skipping in resolution' },
  { id: 'anti-pattern.3', desc: 'No late-precedence override' },
  { id: 'anti-pattern.4', desc: 'No implicit runtime context' },
  { id: 'anti-pattern.5', desc: 'No silent runtime downgrade' },
  { id: 'anti-pattern.6', desc: 'No capability bypass in safe mode' },
];

export async function run() {
  let pass = 0, fail = 0, skip = 0;
  for (const check of checks) {
    console.log(`SKIP ${check.id} — ${check.desc} (not implemented)`);
    skip++;
  }
  return { pass, fail, skip };
}
