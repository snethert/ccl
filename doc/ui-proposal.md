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
| menu      | `section item` — legal only inside a `menu` (§10.1)              |
| feedback  | `spinner progress badge banner`                                  |
| opaque    | `editor` (§6), `record` (§6.4), `svg`                            |

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

### 10.1 Menus are structure, not attributes

The context menu on a presentation has sections, items with applicability counts, keybindings, and disabled state. That is a small tree, and an attribute must describe a node, not smuggle in another node tree. So `menu` takes explicit children:

```lisp
(menu :anchor "form-3/runner"
  (section "Class"
    (item :command 'show-subclasses :handle h :count 2)
    (item :command 'trace-all-methods :handle h :count 7))
  (section "Package"
    (item :command 'export-symbol :handle h)))
```

`item` carries `command`, `handle`, optional `count`, and `enabled`; its label and keybinding come from the registry. The validator, the text backend, replay, and the author can all reason about the menu structurally.

## 11. Text backend

A second renderer from the same node vocabulary to plain text, built **before** the DOM backend.

```lisp
(render-text (make-view 'inspector *foo*))
```

This gives golden-file tests, CI with no browser, and verification of a UI change in the same turn it is written. It also enforces discipline: anything that cannot render as text is pixel-goo that does not belong in the vocabulary. Inline presentations render as bracketed spans with a footnote table of handles; overlays render nested under their anchor; `editor` renders its buffer with decoration markers in a gutter; `record` renders a placeholder.

Checked against the mockups: every screen is legible as text except the two opaque things, and those are exactly where the seam is.

### 11.1 The contract

**Text rendering preserves semantic information, not visual equivalence.** The text backend never approximates columns, fonts, or positions. Its obligation is that every semantically meaningful node, state, selection, decoration, action target, and object reference remains inspectable in the output. This rule exists so that nobody later "improves" the text backend into a layout engine.

```
SOURCE presentations.lisp.14

  17 | (defun scan-buffer (runner &optional (limit [*scan-limit*]¹))
> 18 |   (loop for record = ([pop-record]² runner)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ current-frame

[1] h:311 → special variable clim-web::*scan-limit*
[2] h:317 → function clim-web::pop-record · state :matching
```

## 12. Record/replay

Every inbound event and outbound view/patch/act, appended to a log, with a headless replay that reconstructs view state deterministically. A bug report is `bug-0042.log`, reproduced in a fresh image with no browser, fonts, or timing. This is the highest-leverage item in the design for an AI collaborator: "it looks wrong on my machine" goes from five speculative rounds to one.

### 12.1 The log is part of the protocol

The log format is specified alongside the messages in §2, not treated as debugging infrastructure. A log is the sequence of protocol messages with direction and ordinal:

```
184 IN   event  {window w1, view source-1, key form-3/runner, command nil, handle h:317, payload {button :left}}
185 OUT  patch  source-1 v41→v42 [(set-attr form-3/runner state :selected)]
186 OUT  act    reveal-range editor-1 (2130 . 2141)
```

A UI failure is then a program trace. "The source pane stops highlighting the current frame after I select restart 3" becomes "replay this log; at event 184 the `current-frame` decoration disappears; find the transition that violated the protocol."

### 12.2 Replay API

```lisp
(replay-log "bug-0042.log" :until 183)        ; state just before the suspect event
(replay-log "bug-0042.log" :from 180 :until 190)
(diff-views 183 184)                          ; first divergence, as a tree diff
(dump-view 'source-1)                         ; current tree as an s-expression
(describe-handle h)                           ; what a handle denotes
```

The interesting object is almost always the first state transition where two executions diverge, not the final broken tree; `diff-views` exists for that.

### 12.3 The invariant

It is tempting to say "the log is complete because editor buffers are Lisp-owned (§6.3) and windows are in the envelope (§7)". That is an assertion; the property replay actually needs is an invariant, and it is tested:

**Browser state may affect rendering mechanics, but no unlogged browser state may affect a future Lisp-visible result.**

The JS runtime will hold ephemeral state: focus, pointer capture, scroll offsets, IME composition, pending events, measurement results. None of it needs to be authoritative. But the moment any of it determines a Lisp-visible outcome — a scroll offset deciding which source location an event names, a measured width deciding a truncation — it has become semantic state and must enter the protocol (as event payload or a `local` subscription) and therefore the log. The test is mechanical: record a session, replay it headless, and diff the final trees; any difference is a violation, and the fix is always to move state across the wire, never to special-case the replayer.

## 13. Explicitly out

HTML or CSS strings in Lisp. A template language. Two-way binding. A Lisp class per DOM element. Per-feature JavaScript. An open-ended attribute bag. Editor decoration kinds added outside this document. Any API where the correct call sequence depends on what happened previously.

## 14. Build order

The log format and the replay model come *before* the JS runtime, so that any protocol operation that cannot be represented deterministically is discovered before there is JS to protect.

1. Spec file + codegen, with the validator on both sides. Inline nodes, `oref` with `doc`/`commands`/`state`, the decoration list, `menu` structure, and roles are in the spec from the first commit.
2. Text backend + canonical serialization + log format (§12.1).
3. Golden tests + headless Lisp replay. Prove three real views in the REPL: the **source pane** (inline presentations and decorations, the hard one), the transcript (append op, inline objects, a `record` placeholder), and the debugger (restarts, backtrace with locals, current-frame decoration). Each proof is a log replayed to a golden tree.
4. JS runtime: reconciler, event queue, `act` handlers, resync, window management, editor decoration bridge.
5. Browser event recording + full replay against the JS runtime.
6. **Freeze JS.** The freeze criterion is not "the feature list is done"; it is that recorded browser sessions replay headless to identical trees (§12.3), demonstrating that JS holds no accidentally authoritative state.
7. Everything after this is Lisp.

## 15. Resolved and open

Resolved while reviewing:

- `plot` is not in the initial vocabulary. `record` is the opaque seam; an actual plotting requirement must demonstrate that `record` is insufficient before the permanent vocabulary grows.
- `menu` is explicit structure (§10.1), not attributes.

Open:

- The exact scroll-anchor semantics of `append-children` when the user has scrolled up in a transcript. Note that under §12.3 the *policy* is Lisp's, but whether the user had scrolled up is browser state that affects a Lisp-visible result, so it must arrive as `local` before the policy is applied.
