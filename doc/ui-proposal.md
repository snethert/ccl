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
| `open-url`           | external URL, new tab                                          |

Ten. `open-window` / `close-window` / `focus-window` are the price of the detached-transcript screen; they are cheap now and expensive to retrofit.

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
| layout    | `stack row grid split scroll spacer toolbar panel` (§24)         |
| text      | `text heading code label` — these take **inline children** (§5) |
| inline    | `span oref kbd link` — legal only inside a text-group node       |
| media     | `image icon media` (§20)                                         |
| controls  | `button toggle field number vector select checkbox radio-group slider color` (§25) |
| structure | `table tree list tabs disclosure properties` (§25); `table :tree t` (§26) |
| spatial   | `canvas item edge` (§19)                                         |
| overlay   | `dialog menu popover tooltip menubar`                            |
| menu      | `section item` — inside a `menu` (§10.1); `section prop` inside `properties` (§25) |
| feedback  | `spinner progress badge banner readout` (§27)                    |
| opaque    | `editor` (§6), `record` (§6.4), `svg`                            |

Drag-and-drop (§17), gestures (§18), virtualization (§21), hover groups (§29) and content colour (§30) are attributes and events on these nodes, not further node types.

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
| `commands`  | `(:activate cmd :modified cmd :secondary count)` — per gesture slot (§18), so the client can word the doc line for the input modality it has ("click / ⌘click / right" or "tap / long-press") |
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

Enumerated, and client-side unless subscribed: hover, focus ring, text selection, scroll offset, in-flight keystrokes, drag-in-progress (§17), gesture-in-progress (§18), canvas viewport transform (§19), force-layout positions (§28), media playback position (§20), visible range of a virtualized collection (§21), table range selection, window size, **split-divider positions**. The last is in the list because "layouts are objects" and ⌘⇧L saves the current arrangement, so Lisp must be able to subscribe to divider geometry with `local`. Every `local` subscription is throttled by the client and carries the value, never the input that produced it. Solving latency is the lesser benefit; the greater one is deleting the whole category of round-trip interaction logic that the author writes badly.

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

HTML or CSS strings in Lisp. A template language. Two-way binding. A Lisp class per DOM element. Per-feature JavaScript. An open-ended attribute bag. Editor decoration kinds added outside this document. Raw pointer or touch events crossing the wire (§18). Any API where the correct call sequence depends on what happened previously.

Also out of the initial vocabulary, with the reason: 3D viewports (three.js-style scene editing) and raw terminal emulators (a pty grid with escape sequences). Both are genuinely opaque components that would each need their own decoration protocol, as `editor` does; neither is needed for the IDE, and each is added only through this document.

## 14. Build order

The log format and the replay model come *before* the JS runtime, so that any protocol operation that cannot be represented deterministically is discovered before there is JS to protect.

1. Spec file + codegen, with the validator on both sides. Inline nodes, `oref` with `doc`/`commands`/`state`, the decoration list, `menu` structure, and roles are in the spec from the first commit.
2. Text backend + canonical serialization + log format (§12.1).
3. Golden tests + headless Lisp replay. Prove three real views in the REPL: the **source pane** (inline presentations and decorations, the hard one), the transcript (append op, inline objects, a `record` placeholder), and the debugger (restarts, backtrace with locals, current-frame decoration). Each proof is a log replayed to a golden tree.
4. JS runtime: reconciler, event queue, `act` handlers, resync, window management, editor decoration bridge, the gesture recognizer (§18), the drag-and-drop engine (§17), the canvas viewport (§19). A fourth proof in step 3 covers these headlessly: dragging a file presentation onto the Compile command replays from one logged `drop` event.
5. Browser event recording + full replay against the JS runtime.
6. **Freeze JS.** The freeze criterion is not "the feature list is done"; it is that recorded browser sessions replay headless to identical trees (§12.3), demonstrating that JS holds no accidentally authoritative state.
7. Everything after this is Lisp.

## 15. Resolved and open

Resolved while reviewing:

- `plot` is not in the initial vocabulary. `record` is the opaque seam; an actual plotting requirement must demonstrate that `record` is insufficient before the permanent vocabulary grows.
- `menu` is explicit structure (§10.1), not attributes.

Open:

- The exact scroll-anchor semantics of `append-children` when the user has scrolled up in a transcript. Note that under §12.3 the *policy* is Lisp's, but whether the user had scrolled up is browser state that affects a Lisp-visible result, so it must arrive as `local` before the policy is applied.

---

# Part II — Coverage beyond the IDE

The IDE mockups are one application. To check that the vocabulary is not secretly IDE-shaped, the design was read against screenshots of other applications **in active use, captured by other people**: developer-submitted appstream screenshots on Flathub (desktop, 42 apps) and F-Droid (Android, 5 apps), Wikimedia Commons uploads (3), and vendor documentation and blog screenshots (Magit, KiCad, Wireshark, Blender, Excel, Trello, DaVinci Resolve, Ableton). Fifty of them are in `ui-proposal-survey.jpg`. A first pass over headless-browser captures of web apps was discarded as uninformative: it mostly saw splash and sign-in screens.

Four things were missing from Part I and are added in §17–§21: drag and drop, gestures and touch, a spatial canvas, and media. The in-use screenshots then forced the further, smaller additions in Part III (§24–§30), mostly about the density and panel structure of professional desktop tools. Nothing in Part I changed shape.

## 16. What was surveyed and what it needs

| application type            | seen in                                                              | needs beyond Part I                                                   |
|-----------------------------|----------------------------------------------------------------------|-----------------------------------------------------------------------|
| spreadsheet                 | LibreOffice Calc (Commons), Excel (Computerworld)                    | virtual rows (§21), formula bar, cell-authored colour and merged cells (§30), charts floating over the grid (§19), range selection |
| CAD / EDA                   | KiCad PCB and schematic, FreeCAD, LibreCAD, Cura                     | dense docked panels (§24), property inspectors (§25), layer lists as tree-tables (§26), coordinate readouts (§27), net hover-highlight (§29), canvas with orthogonal edges (§19) |
| 3D content creation         | Blender (sculpt and layout), Godot, Cura, three.js                   | 3D viewport itself is out (§13); everything around it — outliner, properties with scrubbed numbers, workspace tabs, timeline — is §24–§28 |
| raster / vector / photo     | GIMP, Krita, Inkscape, darktable, Photopea, Method Draw              | tool palettes, layer stacks with visibility toggles (§26), colour pickers (§22), thumbnail grids with rating and colour labels (§21), brush cursor on canvas (§19) |
| audio / video / DAW         | Audacity, Ardour, LMMS, Ableton, Kdenlive, DaVinci Resolve, OBS      | timeline space with lanes, clip trimming, playhead, live meters (§28), transport controls (§20), mixer strips (§25) |
| calendar / kanban / planning| GNOME Calendar, FullCalendar, Trello, Jira                           | drag between cells and columns, resize duration (§17); labels, avatars, badges on cards |
| mail / chat / messaging     | Thunderbird, Evolution, K-9, Slack, Discord, Telegram, Signal, Element | threaded lists, reactions as chips (§25), reply quotes, composer with rich toolbar (§6), unread badges, presence dots |
| libraries / browsers        | Calibre, Zotero, darktable, Dolphin, Steam, Spotify, DaVinci projects | tree-table (§26), thumbnail grids with zoom slider (§21), hero + horizontal carousels (§20), sidebar trees |
| maps / sky                  | GNOME Maps, Organic Maps, Leaflet, KStars                            | `:geo` canvas, place cards as bottom sheets (§18), route polyline and elevation profile (§19, `svg`), object markers |
| analysis / diagnostics      | Wireshark, JupyterLab, Grafana                                       | three-pane linked selection, hex dump as `code` with spans and hover-group (§29), notebook cells as `list` of `editor`+output |
| code / text editing         | VS Code, Kate, Magit, Obsidian, LibreOffice Writer, xterm             | Part I covers editors; Magit-style transient menus need toggles in menus (§25); force-directed graph (§19); paged documents (§6); terminal out (§13) |
| block programming / games   | Scratch, Luanti                                                      | Scratch blocks are a canvas with snap-to-port drops (§17, §19); the in-game 3D view is out |
| mobile                      | Organic Maps, Loop Habits, Termux, Element, K-9, 2048, Wikipedia     | bottom sheets with drag handle, FAB, segmented transport picker, extra-keys toolbar above the keyboard, swipe navigation (§18, §22) |
| forms / setup dialogs       | KiCad Board Setup, GitHub sign-in, Cura print settings               | property lists with mixed controls and a tree nav (§25); nothing else new |

Every entry in the third column resolves to §17–§30. No application required a new opaque node beyond those already declared out.

## 17. Drag and drop

Every drag seen in the survey reduces to the same four parts: a **source** (an object handle presented as a type, or a child being reordered), a **target** (a node that declares what it accepts and how it positions a drop), a **feedback phase** that is entirely client-local, and **one terminal event**. Lisp never sees pointer motion. This is CLIM's drag-and-drop translator table, expressed as data on the tree.

### 17.1 Attributes

| attribute        | on                                   | meaning                                                                 |
|------------------|--------------------------------------|-------------------------------------------------------------------------|
| `:drag (type &key handle)` | any node                   | the node is a drag source presenting `handle` as `type`                  |
| `:accepts ((type command) ...)` | any node              | the node is a drop target; a source of `type` dropped here dispatches `command` with `(source-handle target-handle placement)` |
| `:sortable t`    | `list stack row grid tabs tree`, `table` rows and columns | children reorder by drag                              |
| `:sort-group name` | the same                           | children move between containers sharing the group                       |
| `:resizable (:x :y :both)` | any node                   | edge-drag resizes; also `split` dividers and `table` columns             |
| `:port (:in\|:out type)` | `item` inside a `canvas`      | a connection endpoint; connecting is a drag whose source type is `port`  |

A shape palette (draw.io, "drag these onto the calendar") is a `list` whose children carry `:drag`; the canvas or calendar cell carries `:accepts`. A kanban board is three `list`s with one `:sort-group`. The AG Grid "drag here to set row groups" bar is a `row` with `:accepts ((column group-by-column))`. Docking a pane is `:drag (pane)` on a tab and `:accepts ((pane dock-pane))` on each `split` region.

### 17.2 Events

Exactly one event ends a drag; a cancelled drag sends nothing.

| event     | payload                                                        |
|-----------|----------------------------------------------------------------|
| `drop`    | `source-handle type target-key placement`                       |
| `reorder` | `key from-index to-index` (within a `:sortable`)                |
| `move`    | `key from-container to-container to-index` (across a `:sort-group`) |
| `resize`  | `key size`                                                      |

`placement` is what the target can compute locally and depends on the target's kind: an index in a list, a cell in a grid or calendar, a point in canvas coordinates (§19), a port for connections, or `:into` for a tree node. The terminal event is the only thing logged, so a drag replays (§12) from one line with no pointer trace.

### 17.3 Client-local feedback

Drag image, valid-target highlighting, insertion indicator, autoscroll near edges, and spring-loading a collapsed tree node are all client-side. Target validity needs no round trip: `:drag` types and `:accepts` types are both in the tree, so the client computes applicability the way it computes the doc line. Spring-loading sends the ordinary `expand` event. On touch, a drag begins with a long-press and the same engine runs (§18).

### 17.4 OS file drop

`:accepts ((:files command))` makes a node a drop zone for files from the OS (Photopea's "Drop any files here"). The `drop` event carries names, sizes and types and a handle per file through which Lisp reads the bytes; the bytes themselves never sit in the event.

### 17.5 Text backend

Sources render as `⇄type`, targets as `⇐(types)`, sortable containers as `⇅`. A drop is exercised in a test by constructing the `drop` event directly, which is also how the golden replay for step 3 of §14 is written.

## 18. Gestures and touch

**Input modality never crosses the wire.** Lisp sees gestures from a closed set; the client recognizes them from mouse, touch, pen, or keyboard. Which gestures a node can emit is declared per type in the spec file. Raw pointer or touch events are explicitly out (§13).

### 18.1 The gesture set

| gesture           | mouse                 | touch                    | keyboard          |
|-------------------|-----------------------|--------------------------|-------------------|
| `activate`        | click                 | tap                      | Enter / Space     |
| `modified`        | ⌘/Ctrl-click          | two-finger tap           | ⌘/Ctrl-Enter      |
| `secondary`       | right-click           | long-press               | Menu / ⇧F10       |
| `double`          | double-click          | double-tap               | —                 |
| `select`          | shift/⌘-click, marquee | tap in selection mode   | ⇧-arrows          |
| `swipe`           | —                     | swipe, with direction    | arrows on the node |
| `pan`             | drag on empty space / scroll | one-finger drag    | arrows            |
| `pinch`           | wheel with modifier   | two-finger pinch         | ⌘+/−              |
| `refresh`         | —                     | pull down past top       | —                 |
| `dismiss`         | Escape / click outside | swipe down on a sheet, tap outside | Escape |
| `drag`            | press and move        | long-press and move      | —                 |

`pan` and `pinch` on a `canvas`, `record`, `scroll` or `media` node are absorbed client-side into the viewport transform (§8, §19) and reach Lisp only as a throttled `local` value when subscribed. Everywhere else a gesture is an ordinary `event` with the gesture name in it; a slide deck is a `stack` of keyed pages that emits `swipe :left`, and the 2048 board is a `grid` that emits `swipe` with a direction and gets keyed `move-child` patches back, which the client animates.

### 18.2 What touch changes

- **No hover.** The pointer-documentation line follows the most recently touched presentation, and `oref`'s `commands` attribute names gesture slots, not buttons (§5), so the client can word it as "tap **edit definition** · long-press 11 commands".
- **Modality in `hello`.** `pointer :fine|:coarse`, `hover t|nil`, `touch t|nil`, plus the viewport and safe-area insets. Window resize is a `local` value. Choosing a one-pane layout below a width, moving `tabs` to the bottom, or turning a `split` into a drawer is a pure function of `hello` and that value; the vocabulary does not change.
- **Hit targets.** With `pointer :coarse` the theme table (§9) selects larger spacing and target sizes. Lisp does not know or care.
- **Mobile idioms as placements**, not new nodes: `tabs :placement :bottom` (YouTube's bar), `toolbar :placement :floating` (Excalidraw's tool strip), `dialog :placement :sheet|:side` (bottom sheets, navigation drawers; swiping one away is `dismiss`), `list` rows with `:swipe-commands` revealed by a horizontal swipe.
- **Virtual keyboard.** `field :input-mode` from a closed set (`:text :numeric :decimal :email :url :search`).

### 18.3 Text backend and replay

Gestures are already abstract, so the text backend lists each node's gesture slots and replay logs the gesture, never the modality. A bug that appears only on touch is by construction a bug in the recognizer (JS, frozen, tested against fixture pointer streams) or a bug in Lisp's handling of a gesture, which replays on a desktop image.

## 19. Spatial canvas

Whiteboards, diagram editors, node editors, dashboards, gantt charts and maps all put nodes at coordinates in a space that the user pans and zooms. `record` (§6.4) covers read-only replay of Lisp-drawn output; it cannot cover editing, because re-rendering SVG per pointer move is a round trip per frame. So there is one interactive spatial node family.

### 19.1 Nodes

```lisp
(canvas :key "board" :space :pixels :snap 8 :rulers t :tool :select
  (item :key "n1" :at (120 80) :size (160 60) :handle h1 :drag (node) :resizable :both
        :ports ((:out "value" number))
    (stack (heading "Source") (text "…")))
  (item :key "n2" :at (420 80) :size (160 60) :handle h2 :ports ((:in "x" number))
    (stack (heading "Sink")))
  (edge :key "e1" :from ("n1" "value") :to ("n2" "x") :route :curve :handle h3))
```

| attribute on `canvas` | values                                                                 |
|-----------------------|------------------------------------------------------------------------|
| `:space`              | `:pixels`, `(:grid cols rows)` (dashboards; positions snap to cells), `(:time start end)` (gantt; x is a time), `:geo` (maps; positions are lat/lng) |
| `:tiles`              | a tile URL template, `:geo` only                                       |
| `:tool`               | what a drag on empty space does: `:select` (marquee), `:pan`, or `(:create type)` |
| `:snap`, `:rulers`    | client-side conveniences                                               |

An `item` contains any node, including a `record`, so a Lisp-drawn shape sits on an editable canvas. `edge` routes between ports client-side. A popup anchored to a marker is a `popover :anchor "n1"`; anchors already exist (§4).

### 19.2 Events

`move {key at}`, `resize {key size}`, `connect {from to}` (a port-to-port drag, per §17), `select {keys}` (marquee or multi-select), and `create {type at size|points}` for drawing tools, where a freehand stroke arrives as one event with its points, never as motion. Every one is a terminal event; the viewport transform is `local` (§8). A gantt bar's resize is a duration change; a dependency is an `edge`; a dashboard panel move is a `move` in grid coordinates; a map marker drag is a `move` in lat/lng.

### 19.3 Text backend

```
CANVAS board (pixels, tool select)
  n1 @120,80 160×60  h1 ⇄node  ports: value→number
  n2 @420,80 160×60  h2        ports: number→x
  e1 n1.value → n2.x  (curve)
```

Editable canvases render as a table of items and edges. This is enough to assert a golden state after a replayed `move` or `connect`, which is the whole point.

## 20. Media, images and links

- `image :src :alt :fit (:cover|:contain) :shape (:rect|:circle)`. Avatars, album art, thumbnails.
- `icon :name` from an enumerated set in the spec file. Activity bars and tool palettes are `toolbar`s of `button :icon`.
- `media :kind (:audio|:video) :src :state (:playing|:paused) :position :volume`. The controls are client-local; Lisp drives playback by patching `state` and `position` (declarative, no `act`), and subscribes to `position` as a throttled `local` value if it needs it. A sticky player bar is a `toolbar :placement :bottom` holding a `media`.
- `link :href`, inline. Activation opens the URL client-side and is not Lisp-visible, which is why it is not an event; Lisp-initiated navigation is the `open-url` act (§2.3).
- Horizontal carousels (Spotify) are `scroll :axis :x` around a `row`.

## 21. Large collections

A 100 000-row grid cannot ship as a tree. `table`, `list` and `tree` take `:virtual t :count N`, Lisp ships only a window of keyed rows, the client reports the visible range as a subscribed `local` value, and Lisp patches the window with `replace-node`. The row keys keep selection and patches stable across windows. Paged document viewers are the same mechanism with pages as rows.

Column sort, filter, pin, resize and reorder are ordinary events carrying the column key (reorder via `:sortable` on the columns, resize via `:resizable`). Cells hold any node, so a progress bar, a star rating (`radio-group :appearance :rating`), a badge or a checkbox in a cell is nothing new. Range selection is a `local` value `(r1 c1 r2 c2)`; in-cell editing is a `field` in the cell.

## 22. Small additions the survey forced

| addition                                   | seen in                       |
|--------------------------------------------|-------------------------------|
| `menubar` — a row of `menu`s                | Photopea, draw.io, three.js   |
| `toolbar :placement (:top :bottom :floating)` | every editor, mobile bars  |
| `radio-group :appearance (:list :segmented :toolbar :rating)` | Handsontable, tool palettes |
| `color` control                            | Method Draw, draw.io          |
| `dialog :placement (:center :sheet :side)` | mobile                        |
| `tabs :placement (:top :bottom :side)`     | YouTube, VS Code activity bar |
| `button :icon`                             | everywhere                    |
| `editor :mode (:code :rich)`               | tiptap                        |
| `field :input-mode`                        | mobile                        |

All are attributes on existing nodes except `menubar`, `toolbar` and `color`, which are in the §4 table. None of them is styling: each is a semantic choice the text backend renders differently.

---

# Part III — What applications in use added

Professional desktop tools (Blender, KiCad, Kdenlive, GIMP, Inkscape, FreeCAD, Godot, OBS, Ardour) share a shape that neither the IDE mockups nor the web apps have: a dense workspace of dockable panels, each with its own header toolbar, wrapped around one large canvas, with an inspector of label/value rows on one side and a status bar of live readouts along the bottom. Part I and Part II already contain the pieces; what follows makes the shape expressible without inventing it per application.

## 24. Panels and workspaces

`panel` is a layout node: a `stack` with a title, an optional header `toolbar`, and a closed set of states (`:expanded :collapsed :floating`). `split` and `tabs` compose panels; a **workspace** is a named layout object (§8 already makes layouts objects) holding that tree. Blender's Layout/Modeling/Sculpting tabs, Kdenlive's Logging/Editing/Audio, Cura's Prepare/Preview/Monitor and Godot's 2D/3D/Script are all `tabs` over workspaces, and switching one is a `view` of a different layout, not a rebuild.

Docking is §17: a panel's title is a `:drag (panel)` source and every `split` region `:accepts ((panel dock-panel))`; Lisp answers a `drop` with a patched layout. Float and re-dock are the same drop onto a window (§7). Collapsing is a `disclosure` gesture on the panel header. None of this is new mechanism, which is the point of having built §17 first.

## 25. Property inspectors and dense controls

Blender's properties, FreeCAD's data table, Godot's inspector, Inkscape's fill and stroke, Cura's print settings and KiCad's board setup are the same widget: collapsible sections of label/control rows. `properties` is a structure node whose children are `section`s (the same `section` as in `menu`) of `prop` rows:

```lisp
(properties :key "transform"
  (section "Transform" :collapsed nil
    (prop "Location" (vector :unit :m :scrub t :live t :keys (x y z)))
    (prop "Rotation Mode" (select :options *rotation-modes*))
    (prop "Suppressed" (toggle))))
```

Controls that the survey forced, all attributes on existing nodes:

| addition                                | seen in                                             |
|-----------------------------------------|-----------------------------------------------------|
| `number :scrub t` — horizontal drag adjusts the value; click still types | Blender, Godot, Inkscape, Kdenlive |
| `number :live t` — while scrubbing, throttled `change` events stream so the viewport follows; without it, one `change` on release | Blender radius/strength |
| `number :unit :min :max :step`          | everywhere                                          |
| `vector :keys (x y z)` — grouped numbers with per-component lock/keyframe slots | Blender, Godot, FreeCAD |
| `select :editable t` — a combo box      | KiCad track width, Blender brush size units          |
| `button :menu (menu …)` — a split button| LibreOffice, Kdenlive, GIMP toolbars                 |
| `toggle :appearance :chip` — reactions, filter chips, tags | Discord, Slack, Thunderbird tags, darktable colour labels |
| `item :kind :toggle` inside `menu`      | Magit transients: switches shown with their keys     |
| `slider :track (:gradient from to)`     | Inkscape RGBA sliders, Krita                          |

Per-row icon slots (Blender's lock and keyframe dots, KiCad's layer colour swatch and visibility eye) are `prop :leading` / `:trailing` children holding `icon`, `toggle` or `color`; nothing per-application.

## 26. Tree-tables

An outliner (Blender), an accounts ledger (GnuCash), a layer list (KiCad, GIMP), a reference library (Zotero) and a threaded inbox (Thunderbird) are all a tree whose rows have columns. `table` rows may nest: a `trow` may contain `trow` children and carries `:expanded`. That makes `table :tree t` the tree-table, keyed like any table, virtualized like any table (§21), and rendered by the text backend as an indented table. `tree` remains for the column-less case.

## 27. Readouts

Every professional tool has a status bar of values that change with the pointer: cursor position in canvas coordinates (KiCad's X/Y/dx/dy, Blender, Inkscape, QGIS), zoom percentage, timecode under the playhead, selection counts, RA/Dec under the cursor in KStars. A round trip per pointer move is not acceptable and never was. These are pure functions of client-local state that §8 already enumerates.

`readout` is a feedback node bound to **one enumerated client-local value**: `:pointer` (in the coordinate space of a named canvas), `:zoom`, `:scroll`, `:selection-range`, `:media-position`, `:drag-delta`. It takes a `:format` from a closed set (units, precision). This is a one-way display of a value the client already owns; it is not the two-way binding §13 prohibits, and it cannot reach Lisp state. The text backend renders it as `⟨pointer canvas-1⟩`. Anything not on that list goes through `local` subscription and an ordinary patched `label`, which is fine for values that change on the order of once a second.

## 28. Timelines and live meters

Kdenlive, DaVinci Resolve, Audacity, Ardour, LMMS, Ableton and Blender's timeline all put clips on lanes against a time axis. `canvas :space (:time start end :lanes n)` is the §19 time space with rows; an `item` on it has a lane and a time extent, clip trimming is `:resizable :x` (both edges), moving between lanes is `move`, and snapping is a canvas attribute. Waveforms and thumbnails inside clips are `image` or `record` children.

The playhead is `canvas :cursor :media-position` — the same client-local value a `readout` shows, drawn as a line, so scrubbing never round-trips. Transport buttons are commands; `media :state`/`:position` (§20) drive playback.

Audio meters (OBS, Kdenlive, Ardour) update at frame rate. `progress :role :meter` is the node; its value arrives as ordinary `set-attr` patches. The protocol has to tolerate a few dozen small patches per second on a handful of keys, and the reconciler should coalesce patches to the same attribute within a frame. That is a runtime requirement, stated here so it is in the frozen JS from step 4 of §14, not a vocabulary change.

Obsidian's graph view is a `canvas :layout :force`: the client runs the layout, positions are `local` (subscribable, pinnable by a `move`), and Lisp owns only the nodes and edges. It is the one case where item positions are not Lisp-owned, and it is opt-in per canvas.

## 29. Hover groups

Wireshark highlights the hex bytes of the field under the pointer; KiCad highlights every segment of the net under the pointer; Blender's outliner and viewport highlight together. Hover is client-local by rule (§8), so linked hover cannot round-trip. `:hover-group id` on any node makes all nodes sharing the id highlight together, locally. Selection (a click) remains a Lisp event and patches the other panes, which is the right cost for selection and the wrong one for hover.

## 30. Content colour, spans and density

Three things the "no styling" rule (§4, §9) has to be precise about after seeing real documents:

- **Content colour is data.** A spreadsheet cell's fill, a calendar event's colour, a darktable colour label, a Trello label, a Blender collection colour are chosen by the user and stored with the document. They are not theme decisions. `cell`, `item`, `span` and `trow` take `:color` holding a colour *value* (the same datum a `color` control produces), rendered as-is; the theme still owns everything else. The validator allows `:color` only on content nodes, never on chrome.
- **Spans.** `cell :span (rows cols)` for merged cells; nothing else is needed for the Calc screenshot.
- **Density is a window setting.** Blender and KiCad are roughly twice as dense as the IDE mockups. The theme table (§9) is generated for two densities, `:comfortable` and `:dense`, and the choice is per window in `hello`/`local`, never per node. Combined with `pointer :coarse` (§18) that gives four generated tables and no per-node sizing.

One observation rather than an addition: five of the surveyed desktop tools are built around a 3D viewport. It stays out of the vocabulary (§13), but it is the single largest class the design declines, and if CAD or 3D ever becomes a target it will need an opaque node with its own decoration protocol, designed the way `editor` was.

## 31. Still open after the survey

- Spreadsheet fill-handle drag (extend a selection by dragging its corner): probably `:resizable` on the selection rectangle producing a `fill` event, but unproven.
- Whether `select` in a `canvas` needs a lasso variant or marquee is enough.
- Whether `:geo` earns its place in the initial vocabulary or waits, as `plot` does, for a real requirement. It is cheap only if the tile layer is a fixed dependency of the frozen runtime; that is a size decision for step 4.
- Spreadsheet formula bar and name box: a `field` bound to the selected cell is a round trip per selection change, which is acceptable; whether formula *entry* with cell-reference picking (click a cell while typing) is a gesture or a command mode.
- Whether `readout` (§27) should accept a Lisp-supplied pure formatter compiled to the client, or only the closed `:format` set. The closed set is the thesis; the survey shows KStars and QGIS wanting domain formats (RA/Dec, mm at page scale).
- Whether Scratch-style block snapping is `:port` drops (§17) or a canvas `:snap` policy; the former keeps it data.

