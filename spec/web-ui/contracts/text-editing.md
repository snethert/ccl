# Text Editing

## Status
⏸️ Not started

## Purpose

Canonical text state model with IME composition lifecycle. Both DOM and
Canvas/WebGL backends expose the same state shape. Canvas/WebGL uses a
hidden-input proxy for IME support. Integrates with undo/redo as
reversible transactions.

## Depends On
- [renderer](renderer.md) — text is rendered by a backend
- [command-system](command-system.md) — editing commands route through the command system

## Interface

```
TextState {
  text:               string
  selectionStart:     integer     // UTF-16 code-unit offset
  selectionEnd:       integer     // UTF-16 code-unit offset
  selectionDirection: "forward" | "backward" | "none"
  composing:          boolean
  revision:           integer     // monotonically increasing
}
```

Selection range clamped to `[0, text.length]`. Single cursor = start equals end.

**Edit operations:** insert, delete (backward/forward), replace selection,
move by grapheme/word/line, select all, set explicit range.

**IME composition lifecycle:**
- Start → `composing=true`
- Update → replace provisional range
- Commit → write committed text, `composing=false`
- Cancel → restore pre-composition snapshot, `composing=false`

## Invariants

1. Selection bounds are always clamped to [0, text.length]
2. Same (prior state, operation) produces same output (deterministic)
3. Composition range is separate from text state — no interference
4. DOM and Canvas/WebGL backends expose identical TextState shape
5. Rendered cursor position matches hidden proxy caret (Canvas/WebGL)
6. Each edit increments revision (monotonic, for undo/redo coalescing)

## Behavior

1. Insert at cursor: text spliced at selectionStart, cursor advances by inserted length
2. Delete backward: remove grapheme before cursor; no-op at position 0
3. Delete forward: remove grapheme after cursor; no-op at end
4. Replace selection: selected range replaced with new text, cursor at end of replacement
5. Move by grapheme/word/line: cursor repositions, selection collapses
6. Select all: selectionStart=0, selectionEnd=text.length, direction=forward
7. IME composition start: snapshot current state, set composing=true
8. IME composition update: replace provisional range with composition text
9. IME composition commit: finalize text, composing=false, increment revision
10. IME composition cancel: restore snapshot, composing=false, no revision change
11. Canvas/WebGL: one focus-coupled hidden DOM input with mirrored selection and composition
12. Text operations integrate with undo/redo as reversible transactions with coalescing windows

## Anti-Patterns

1. Never mutate text during composition — preserve pre-composition snapshot
2. Never mix composition range with normal text offsets
3. Never allow Canvas/WebGL cursor to drift from hidden proxy state
4. Never ignore locale/IME requirements — all locales work identically
5. Never lose edit history in undo/redo integration
6. Never allow selection to exceed text bounds

## Out of Scope

- Rich text formatting (not part of MVP)
- Syntax highlighting (renderer concern, not editing model)
- File save/load (see [persistence](persistence.md))

## Conformance Check
Run: `node spec/web-ui/checks/text-editing.test.mjs`
