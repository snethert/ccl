/**
 * Conformance checks for: text-editing
 * Contract: spec/web-ui/contracts/text-editing.md
 *
 * Stub — all checks fail until implementation exists.
 */

const checks = [
  { id: 'invariant.1', desc: 'Selection clamped to [0, text.length]' },
  { id: 'invariant.2', desc: 'Same input produces same output' },
  { id: 'invariant.3', desc: 'Composition range separate from text state' },
  { id: 'invariant.4', desc: 'DOM and Canvas expose identical TextState' },
  { id: 'invariant.5', desc: 'Cursor matches hidden proxy caret' },
  { id: 'invariant.6', desc: 'Each edit increments revision' },
  { id: 'behavior.1', desc: 'Insert at cursor advances position' },
  { id: 'behavior.2', desc: 'Delete backward removes grapheme' },
  { id: 'behavior.3', desc: 'Delete forward removes grapheme' },
  { id: 'behavior.4', desc: 'Replace selection with new text' },
  { id: 'behavior.5', desc: 'Move by grapheme/word/line collapses selection' },
  { id: 'behavior.6', desc: 'Select all sets full range' },
  { id: 'behavior.7', desc: 'Composition start snapshots state' },
  { id: 'behavior.8', desc: 'Composition update replaces provisional range' },
  { id: 'behavior.9', desc: 'Composition commit finalizes text' },
  { id: 'behavior.10', desc: 'Composition cancel restores snapshot' },
  { id: 'behavior.11', desc: 'Canvas/WebGL uses hidden input proxy' },
  { id: 'behavior.12', desc: 'Undo/redo integration as transactions' },
  { id: 'anti-pattern.1', desc: 'No mutation during composition' },
  { id: 'anti-pattern.2', desc: 'No mixed composition/text offsets' },
  { id: 'anti-pattern.3', desc: 'No cursor drift from proxy' },
  { id: 'anti-pattern.4', desc: 'No locale/IME ignorance' },
  { id: 'anti-pattern.5', desc: 'No lost edit history' },
  { id: 'anti-pattern.6', desc: 'No out-of-bounds selection' },
];

export async function run() {
  let pass = 0, fail = 0, skip = 0;
  for (const check of checks) {
    console.log(`SKIP ${check.id} — ${check.desc} (not implemented)`);
    skip++;
  }
  return { pass, fail, skip };
}
