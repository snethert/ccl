# UI Architecture Proposal

Status: proposal.

Written for the fact that the author of the implementation is a code generator that cannot see the screen. Every design choice below is justified by what that author gets right and wrong, not by what is elegant.

## 1. Thesis

**The JS side is a fixed-size renderer that never grows when features are added.** Every feature is Lisp-only. Two evolving codebases that must agree is the shape a code generator fails at; one evolving codebase plus a frozen interpreter is the shape it succeeds at. If a new feature requires touching the JS, the node vocabulary was wrong: fix the vocabulary, not the feature.

Everything else follows from that plus one constraint: **the entire UI must be visible as text, in a REPL, with no browser.**

The target UI (the CLIM-style IDE mockups: source pane, transcript, examiner, debugger, files, settings, compare, ring, layouts) was checked against this design screen by screen. About 80% of it falls out of the vocabulary in §4 directly. The remainder motivates §5 (inline presentations), §6 (editor decorations), §7 (windows), and §9 (roles). Those four sections are the additions that make the plan sufficient; without them the JS would not stay frozen.

## 2. Wire protocol

Four message kinds each direction. Not five.

**Lisp → client**

| kind    | payload                                                        |
|---------|----------------------------------------------------------------|
| `view`  | a complete tree for a view id, in a window                      |
| `patch` | keyed ops against `(view-id, base-version → new-version)`       |
| `act`   | one of the closed list of imperative acts (§2.2)                 |
| `error` | a condition Lisp wants the client to show without a view         |

**Client → Lisp**

| kind     | payload                                                        |
|----------|----------------------------------------------------------------|
| `event`  | `{window, view, key, command, handle, payload}`                 |
| `resync` | client asks for a full `view`                                   |
| `hello`  | window id, viewport, DPR, locale, capabilities                  |
| `local`  | client-local state Lisp explicitly subscribed to (§8)           |

### 2.1 Versions and resync

Every patch carries `(view-id, base-version → new-version)`. The client refuses a patch whose base it does not hold and sends `resync`. Full resync is always legal and always cheap: it is the recovery path, the first debugging move, and the test oracle. A design where resync is expensive will make the author paper over state bugs with incremental hacks.

### 2.2 Patch ops

Keyed ops only: `replace-node`, `set-attr`, `insert-child`, `remove-child`, `move-child`, and **`append-children`**. The last is not redundant: a transcript is an append-mostly keyed list, and without an explicit append op every REPL form re-sends the list's keys. `append-children` carries a scroll policy (`:stick-to-end` or `:keep`) so the transcript follows output without a round trip.

### 2.3 The `act` list

Closed. Adding to it is a JS change and must be argued for here first.

| act                  | notes                                                          |
|----------------------|----------------------------------------------------------------|
| `focus`              | node key                                                       |
| `scroll-into-view`   | node key                                                       |
| `reveal-range`       | editor key + range (§6)                                        |
| `clipboard-write`    | text                                                           |
| `file-picker`        | replies with an event                                          |
| `open-window`        | window id, initial view id, size hint (§7)                     |
| `close-window`       | window id                                                      |
| `focus-window`       | window id                                                      |
| `download`           | bytes + filename                                               |

Nine. `open-window` / `close-window` / `focus-window` are the price of the detached-transcript screen; they are cheap now and expensive to retrofit.

## 3. Rendering is a pure function

```lisp
(define-view (inspector obj)
  (stack :gap 3
    (heading (princ-to-string (type-of obj)))
    (table :key "slots"
           :columns '(("Slot" :text) ("Value" :object))
           :rows (loop for (name . value) in (slot-alist obj)
                       collect (trow :key name
                                     (text (string name))
                                     (oref value :on-click :inspect))))))
```

State → tree, no side effects, no retained widget objects, no `set-on-click`. A whole view function can be regenerated without reasoning about what the previous DOM mutation sequence left behind. A mutable server-side widget graph (the CLOG/Qt shape) has state that cannot be seen in a test; a pure function's output is a value to assert on.

Keys are mandatory inside any repeated structure and validated at construction. Keys are the single thing a code generator gets wrong most often; omission is an error, not a subtle reordering bug.

## 4. Node vocabulary

A closed set, defined in **one machine-readable spec file** that generates: Lisp constructors, the Lisp-side validator, the JS renderer table, the text-backend table, the JSON schema, and the theme table (§9). Generated, not hand-kept-in-sync; parallel hand-maintained lists are exactly what drifts.

| group     | types                                                            |
|-----------|------------------------------------------------------------------|
| layout    | `stack row grid split scroll spacer`                             |
| text      | `text heading code label` — these take **inline children** (§5) |
| inline    | `span oref kbd` — legal only inside a text-group node            |
| controls  | `button toggle field number select checkbox radio-group slider`  |
| structure | `table tree list tabs disclosure`                                |
| overlay   | `dialog menu popover tooltip`                                    |
| feedback  | `spinner progress badge banner`                                  |
| opaque    | `editor` (§6), `record` (§6.3), `plot`, `svg`                    |

Attributes are enumerated per type. Unknown attribute or unknown type → a Lisp condition at construction time, printing the offending node. The JS side never guesses, never falls back, never "does its best": silent visual degradation is the failure mode the author cannot detect and the human has to catch by eye.

**No CSS authoring, ever.** No style dicts, no class strings. Spacing is an integer on a fixed scale; color is intent; emphasis is `:weak :normal :strong`. Given free-form CSS the author will produce four thousand lines of inconsistent bespoke styling and visual coherence will never arrive. Constrained, the UI looks like one system by construction.

Overlays (`menu`, `popover`, `tooltip`) take `:anchor <node-key>`. The client owns the geometry; the text backend renders an anchored overlay nested under its anchor.

## 5. Inline presentations (the addition that matters)

Every pane in the target UI is text whose *substrings are typed objects*: `runner` in a `defclass` is a presentation, `#<HASH-TABLE eql, 14 entries>` in the transcript is one, the examiner states "every symbol below is the object itself", and while a command gathers a `function-name` argument, every matching presentation on screen highlights. A vocabulary whose text nodes take a string cannot express any of that. This is not an edge case; it is the product.

Therefore `text`, `heading`, `code`, and `label` take a sequence of inline children: strings and inline nodes.

```lisp
(code :key "form-3"
  "(defclass " (oref *runner-class* :label "runner" :type 'class) " ()")
```

An `oref` carries:

| attribute   | meaning                                                            |
|-------------|--------------------------------------------------------------------|
| `handle`    | an opaque id into the Lisp-side handle table                       |
| `label`     | the text to draw                                                   |
| `type`      | presentation type, for command applicability                       |
| `doc`       | the one-line pointer documentation (§5.1)                          |
| `commands`  | `(default-command modified-command count)` for the doc line        |
| `state`     | `:normal :matching :selected` — set by Lisp during argument gathering |

Handles are minted by Lisp, never by the client; `(describe-handle h)` prints what one denotes. Handles are the only thing that crosses the wire in place of an object.

### 5.1 Pointer documentation stays local

The bottom line of every screen ("`pop-record` — function, clim-web · click **edit definition** · ⌘click **describe** · right **11 commands**") depends on server knowledge that changes per object *and* per active command context. If it required a round trip on hover, the design would have the chatty hover channel it set out to avoid.

Decision: the `doc` and `commands` attributes ship *with* the `oref`, so hover is entirely client-local. When the command context changes (a command starts gathering an argument), Lisp patches the affected `oref` nodes' `state`, `doc`, and `commands` — a keyed patch, not a hover protocol.

### 5.2 Events from inline nodes

An inline node's click, modified-click, and context-menu events carry `handle` and `type`. The client sends them; one generic Lisp dispatcher looks up the command registry (§10). No closures cross the boundary.

## 6. The editor is not opaque

The source pane needs presentation spans over buffer tokens, hover documentation from Lisp, a context menu on a symbol, "highlight everything that could satisfy this argument", diff-hunk gutters, and a highlighted erroring form in the debugger. A dropped-in third-party editor does none of that. The choice is between rendering source with §5 and implementing editing in-house (expensive), or keeping a real editor component and giving it a **decoration protocol** that is frozen and enumerated like everything else. This proposal takes the second route.

### 6.1 Decorations (Lisp → editor)

An `editor` node has a `:decorations` attribute: a keyed list of

```
(range kind handle doc commands state)
```

where `kind` is a closed set: `:presentation :hunk-added :hunk-removed :hunk-changed :error-form :current-frame :match :selection-hint`. `handle`, `doc`, `commands`, and `state` mean exactly what they mean on an `oref` (§5), so the same client code renders the doc line whether the pointer is over transcript text or source text. New decoration kinds are a JS change and go through this document.

### 6.2 Buffer events (editor → Lisp)

`hover`, `click`, `context-menu`, and `selection` events carry a buffer range and, when over a decoration, its key and handle. Keystrokes are client-local (§8) and reach Lisp as buffer text patches, not per key.

### 6.3 Buffer text is Lisp-owned

The editor's text is state Lisp owns, shipped as a `view` and updated by text patches in both directions, so that record/replay (§12) captures it. An editor whose buffer lives only in the browser breaks replay determinism.

### 6.4 Output records are SVG with tagged groups

The transcript replays a CLIM output record at 1:3 scale, with "⌘click **replay full size**", and records contain presentations. A canvas with server-side hit testing would mean round trips and JS. Decision: a `record` node is server-rendered SVG in which presentation regions are `<g>` elements tagged with handle and type. The client's inline-node event path handles them unchanged. The text backend prints a placeholder line (`[record text-2193, 840×276, 3 presentations]`).

## 7. Windows

The target UI detaches a pane into its own OS-level window sharing the same image ("same image, same objects · ⌘⇧T to re-dock"). The protocol therefore has windows, not just views:

- `hello` carries a window id; each window has its own viewport and DPR.
- `view` names the window it is placed in.
- `open-window`, `close-window`, `focus-window` are acts (§2.2).
- All windows share one socket and one event queue.

## 8. Client-local state

Enumerated, and client-side unless subscribed: hover, focus ring, text selection, scroll offset, in-flight keystrokes, drag-in-progress, **split-divider positions**. The last is in the list because "layouts are objects" and ⌘⇧L saves the current arrangement, so Lisp must be able to subscribe to divider geometry with `local`. Solving latency is the lesser benefit; the greater one is deleting the whole category of round-trip interaction logic that the author writes badly.

## 9. Roles, not colors

Five global intents (`:neutral :accent :ok :warn :danger`) are the right *shape* but too coarse for the target screens, which lean on subtle role-specific tints: the diff-hunk gutter, the "in progress" restart row, the uncommitted file row, the selected setting layer, the argument chip in the command line. Given only five intents the author will either misuse them or ask for CSS.

Decision: nodes that need it take a per-node enumerated `:role` (`trow :role :changed`, `restart :role :active`, `layer :role :in-effect`), declared in the same spec file, and the theme table mapping (node, role, theme) → tokens is generated alongside the renderers. Same discipline as intents, enough resolution. Typography is two families (mono, UI grotesk) and a fixed type scale, also in the spec file, never chosen per node.

## 10. Commands

```lisp
(define-command (inspect-object :label "Inspect" :key "C-c I")
    ((obj object))
  (open-view 'inspector obj))
```

A node names a command and carries a handle; the client sends `{window, view, key, command, handle, payload}`; one generic dispatches. Buttons, menu items, keybindings, the command palette, the context menu on a presentation, and the bottom-line partial-command prompt with its argument chips are all *views over the registry*, generated. Adding a feature is one registry entry plus one method: a shape the author executes identically a hundred times.

## 11. Text backend

A second renderer from the same node vocabulary to plain text, built **before** the DOM backend.

```lisp
(render-text (make-view 'inspector *foo*))
```

This gives golden-file tests, CI with no browser, and verification of a UI change in the same turn it is written. It also enforces discipline: anything that cannot render as text is pixel-goo that does not belong in the vocabulary. Inline presentations render as bracketed spans with a footnote table of handles; overlays render nested under their anchor; `editor` renders its buffer with decoration markers in a gutter; `record` renders a placeholder.

Checked against the mockups: every screen is legible as text except the two opaque things, and those are exactly where the seam is.

## 12. Record/replay

Every inbound event and outbound view/patch/act, appended to a log, with a headless replay that reconstructs view state deterministically. A bug report is `bug-0042.log`, reproduced in a fresh image with no browser, fonts, or timing. This is the highest-leverage item in the design for an AI collaborator: "it looks wrong on my machine" goes from five speculative rounds to one.

Because editor buffers are Lisp-owned (§6.3) and windows are in the envelope (§7), the log is complete without any browser-side state.

`(dump-view id)` prints the current tree as an s-expression; `(describe-handle h)` says what a handle denotes. The debugging loop is entirely textual.

## 13. Explicitly out

HTML or CSS strings in Lisp. A template language. Two-way binding. A Lisp class per DOM element. Per-feature JavaScript. An open-ended attribute bag. Editor decoration kinds added outside this document. Any API where the correct call sequence depends on what happened previously.

## 14. Build order

1. Spec file + codegen, with the validator on both sides. Inline nodes, `oref` with `doc`/`commands`/`state`, the decoration list, and roles are in the spec from the first commit.
2. Text backend + golden tests. Prove three real views in the REPL: the **source pane** (inline presentations and decorations, the hard one), the transcript (append op, inline objects, a `record` placeholder), and the debugger (restarts, backtrace with locals, current-frame decoration).
3. JS runtime: reconciler, event queue, `act` handlers, resync, window management, editor decoration bridge. **Frozen after this.**
4. Record/replay.
5. Everything after this is Lisp.

## 15. Open questions

- Whether `plot` is needed at all, or is a special case of `record`.
- Whether `menu` sections and counts (the context-menu mockup shows grouped items with applicability counts) are `menu` attributes or a `tree`-shaped child list. Leaning attributes: it keeps `menu` a view over the registry.
- The exact scroll-anchor semantics of `append-children` when the user has scrolled up in a transcript.
