# UI Architecture Specification

Status: draft.

This document specifies a user-interface architecture for a Lisp image: a frozen, application-independent client that renders a tree of nodes sent by Lisp and returns events; a closed node vocabulary; a command registry; a text renderer for the same tree; and a replayable log of everything that crosses between the two sides. Keywords MUST, MUST NOT, SHOULD and MAY are used in the RFC 2119 sense. Section cross-references are given as §n.

## 1. Scope and constraints

### 1.1 Design constraints

The implementation is written by a code generator that cannot see the screen. The architecture is chosen so that this author can verify its work without a display, cannot drift two codebases apart, and cannot produce unbounded styling. Three constraints follow:

1. **The client is fixed.** All application features are implemented in Lisp. The client contains one renderer per node type and a fixed set of interaction mechanisms (§14), and does not change when features are added. A feature that would require a client change indicates a missing vocabulary element, which is added through this specification (§14.3).
2. **The whole interface is expressible as text.** Every view renders to plain text through the text backend (§10) with all semantically meaningful content preserved.
3. **Every interaction is logged and replayable.** All messages between Lisp and the client are plain data and are appended to a log from which the client's state can be reconstructed (§12).

### 1.2 Deployment target

The design is optimized for the client and the Lisp image on one machine, in one process or connected by a local socket, where a round trip is negligible. A remote client is supported by the same protocol and degrades as specified in §8.7; it is not what the trade-offs are tuned for. Messages are plain data on every transport.

### 1.3 Target application

The first application is a CLIM-style development environment: source pane, transcript, examiner, debugger, file browser, settings, version comparison, object ring, and saved layouts. The vocabulary is additionally required to cover the application classes listed in Appendix A.

## 2. Protocol

### 2.1 Messages

Lisp → client:

| kind       | payload                                                              |
|------------|----------------------------------------------------------------------|
| `view`     | a complete tree for a view id, placed in a window                    |
| `patch`    | keyed operations against `(view-id, base-version → new-version)`     |
| `act`      | one of the acts in §2.4                                              |
| `error`    | a condition to display without a view                                |
| `query`    | a request for one enumerated client-owned value (§8.4)               |

Client → Lisp:

| kind       | payload                                                              |
|------------|----------------------------------------------------------------------|
| `event`    | `{window, view, key, gesture-or-command, handle, payload}`           |
| `resync`   | a request for a full `view`                                          |
| `hello`    | window id, viewport, DPR, locale, capabilities, modality, vocabulary version, measured round-trip time |
| `snapshot` | the reply to a `query`: one value, once                              |

No other message kinds exist. Messages MUST be serializable data; live objects never cross the boundary. Objects are referenced by handles (§3.3).

### 2.2 Versions and resync

Every `patch` carries `(view-id, base-version → new-version)`. A client holding a different base MUST discard the patch and send `resync`. Lisp answers `resync` with a full `view`. Resync is always legal and MUST be cheap; it is the recovery path and the test oracle.

### 2.3 Patch operations

`replace-node`, `set-attr`, `insert-child`, `remove-child`, `move-child`, `append-children`. All operations address nodes by key. `append-children` carries a scroll policy, `:stick-to-end` or `:keep`; the client applies the policy using its own scroll state and the `scrolled-away` / `scrolled-to-end` events of §8.4.

The reconciler MUST coalesce successive `set-attr` operations to the same key and attribute within one frame; the protocol may carry tens of small patches per second to a few keys (§7.6).

### 2.4 Acts

The act list is closed.

| act                | argument                                   |
|--------------------|--------------------------------------------|
| `focus`            | node key                                   |
| `scroll-into-view` | node key                                   |
| `reveal-range`     | editor key, logical range (§5)             |
| `clipboard-write`  | text                                       |
| `file-picker`      | replies with an `event`                    |
| `open-window`      | window id, initial view id, size hint (§2.6) |
| `close-window`     | window id                                  |
| `focus-window`     | window id                                  |
| `save-file`        | bytes, filename                            |
| `open-url`         | URL, opened in the platform browser        |

### 2.5 Log format

The log is part of the protocol. It is the sequence of messages in order, each with an ordinal and a direction:

```
184 IN   event  {window w1, view source-1, key form-3/runner, gesture activate, handle h:317}
185 OUT  patch  source-1 v41→v42 [(set-attr form-3/runner state :selected)]
186 OUT  act    reveal-range editor-1 (2130 . 2141)
```

A log header records the vocabulary version and, for Lisp replay (§12.3), the image identity. Every handle is logged when minted, with its `describe-handle` line (§3.3).

### 2.6 Windows

`hello` carries a window id; each window has its own viewport, DPR, modality and density. A `view` names the window it is placed in. All windows of one client share one connection and one ordered event stream. `open-window`, `close-window` and `focus-window` manage windows.

### 2.7 Transport

The transport is not part of the protocol. In-process, messages cross a function-call boundary as data; over a socket they are serialized. A socket transport binds to localhost or a Unix socket by default. Remote connections are opt-in and carry a session token in `hello` (§16).

## 3. Views

### 3.1 View functions

A view is a pure function from Lisp state to a tree of nodes:

```lisp
(define-view (inspector obj)
  (stack :gap 3
    (heading (princ-to-string (type-of obj)))
    (table :key "slots"
           :columns '(("Slot" :text) ("Value" :object))
           :rows (loop for (name . value) in (slot-alist obj)
                       collect (trow :key name
                                     (text (string name))
                                     (oref value))))))
```

View functions MUST NOT have side effects, retain widget objects, or depend on client-owned state (§8.4). Every child of a repeated structure MUST carry a `:key`; a missing key is a construction-time error.

### 3.2 Incremental rendering

- `define-view` memoizes its result on its arguments and on each argument's **version**, a modification counter on observed Lisp objects (an observer mixin, or explicit `(touch object)` at mutation sites). A re-render re-evaluates only sub-views whose inputs changed; unchanged subtrees are shared by identity and skipped in O(1) by the differ.
- The differ computes keyed patches (§2.3) from the previous and new trees, walking only regenerated subtrees.
- A view MAY return a patch instead of a tree — `(append-children …)` for a transcript, `(set-attr …)` for a meter. Such patches are validated against the node model exactly as a tree is.

### 3.3 Handles

Lisp mints an opaque handle for each object referenced from a tree; the client never mints handles. `(describe-handle h)` prints what a handle denotes. Lisp MUST validate every `{command, handle}` it receives against the handle's presentation type (§9.2) before dispatch.

## 4. Node vocabulary

### 4.1 Types

The vocabulary is closed and is defined in one machine-readable specification file from which the following are generated: Lisp constructors, the Lisp-side validator, the client renderer table, the text-backend table, the message schema, the theme table (§4.3), the translator-table schema (§9.2), the keymap schema (§8.6) and the mechanism registry (§14.2).

| group     | types                                                                  |
|-----------|------------------------------------------------------------------------|
| layout    | `stack row grid split scroll spacer toolbar panel`                     |
| text      | `text heading code label` (take inline children, §4.4)                 |
| inline    | `span oref kbd link` (legal only inside a text-group node)             |
| media     | `image icon media`                                                     |
| controls  | `button toggle field number vector select checkbox radio-group slider color` |
| structure | `table tree list tabs disclosure properties`                           |
| spatial   | `canvas item edge`                                                     |
| overlay   | `dialog menu popover tooltip menubar`                                  |
| children  | `section item` inside `menu`; `section prop` inside `properties`; `trow cell` inside `table` |
| feedback  | `spinner progress badge banner readout`                                |
| opaque    | `editor` (§5), `record` (§6)                                           |

### 4.2 Attributes and validation

Attributes are enumerated per type in the specification file. An unknown type or attribute is a Lisp condition at construction time that prints the offending node. The client MUST refuse a tree it cannot validate and MUST NOT render a best effort.

Common attributes:

| attribute       | on                          | meaning                                                   |
|-----------------|-----------------------------|-----------------------------------------------------------|
| `:key`          | any node                    | identity for patches; mandatory in repeated structures     |
| `:role`         | per type, enumerated        | semantic variant selecting theme tokens (§4.3)             |
| `:label`, `:description` | any node           | accessible name and description (§15)                      |
| `:anchor`       | `menu popover tooltip`      | key of the node the overlay is positioned against          |
| `:placement`    | `toolbar dialog tabs`       | `toolbar`: `:top :bottom :floating :around`; `dialog`: `:center :sheet :side`; `tabs`: `:top :bottom :side` |
| `:drag :accepts :sortable :sort-group :resizable :port` | §8.2 |                                       |
| `:hover-group`  | any node                    | §8.3                                                       |
| `:track-focus`  | any focusable node          | §8.5                                                       |
| `:color`        | `cell item span trow`       | content colour, a colour value (§4.3.4)                    |
| `:pad`          | `item edge`                 | name of a pad (§9.2)                                       |

### 4.3 Styling

#### 4.3.1 No authored styling

Nodes carry no style. There are no style dictionaries, class strings, or markup strings. Spacing is an integer on a fixed scale; colour is an intent or a role; emphasis is `:weak :normal :strong`.

#### 4.3.2 Intents and roles

Five intents: `:neutral :accent :ok :warn :danger`. Where a type needs finer distinction it declares an enumerated `:role` in the specification file (for example `trow :role :changed`, `restart :role :active`, `layer :role :in-effect`, `progress :role :meter`).

#### 4.3.3 Theme table

The theme table maps `(type, role, state, density, pointer)` to tokens and is generated from the specification file for each backend (CSS for the web client; a stylesheet or palette for a native one). Typography is two families (monospace, UI sans) and a fixed type scale. Density is `:comfortable` or `:dense`, chosen per window in `hello`. Pointer is `:fine` or `:coarse` (§8.8). The initial token values are measured from the reference mockups. A `theme-gallery` view renders every type × role × state × density × pointer on one screen and is the theme's review surface and the box oracle's largest golden (§11).

#### 4.3.4 Content colour

A colour that is part of the document (a cell fill, a calendar event's colour, a label colour) is data, not theme. `cell`, `item`, `span` and `trow` accept `:color` holding a colour value; the validator rejects `:color` on any other node. `cell :span (rows cols)` merges cells.

### 4.4 Inline presentations

`text`, `heading`, `code` and `label` take a sequence of inline children: strings and inline nodes.

```lisp
(code :key "form-3"
  "(defclass " (oref *runner-class* :label "runner" :type 'class) " ()")
```

`oref` attributes:

| attribute  | meaning                                                                  |
|------------|--------------------------------------------------------------------------|
| `handle`   | the object's handle (§3.3)                                               |
| `type`     | presentation type                                                        |
| `label`    | the text drawn                                                           |
| `state`    | `:normal :matching :selected`                                            |
| `doc`      | optional override of the type's pointer documentation (§9.2)             |
| `commands` | optional override of the type's gesture-slot commands (§9.2)             |

Pointer documentation and gesture-slot commands are properties of the presentation type, shipped once in the type's translator table (§9.2); the client looks them up, so hover never crosses the wire. Lisp changes `state` by patch when a command begins or ends gathering an argument of that type (§9.3).

Gestures on an inline node (§8.1) produce events carrying `handle` and `type`.

`code :numbered t` numbers logical lines (§5.4). `label :editable t` commits in-place edits as one `change` event.

### 4.5 Overlays and menus

`menu`, `popover` and `tooltip` are positioned by the client against `:anchor`. `menu` has explicit structure:

```lisp
(menu :anchor "form-3/runner"
  (section "Class"
    (item :command 'show-subclasses :handle h :count 2)
    (item :command 'trace-all-methods :handle h :count 7))
  (section "Package"
    (item :command 'export-symbol :handle h)))
```

`item` carries `command`, `handle`, optional `count`, `enabled`, and `:kind (:command | :toggle)`; label and keybinding come from the registry (§9.1). `menubar` is a row of menus. `button :menu (menu …)` is a split button. `dialog :placement :center | :sheet | :side`; a dialog traps focus until dismissed.

### 4.6 Layout, panels and workspaces

`stack`, `row`, `grid`, `split` and `scroll` are containers with integer gaps on the spacing scale. `split` regions are `:resizable`; divider positions are client-owned (§8.4). `scroll :axis (:x | :y | :both)`.

`panel` is a `stack` with a title, an optional header `toolbar`, and a state from `:expanded :collapsed :floating`. A **workspace** is a named layout object holding a tree of `split`, `tabs` and `panel`; switching workspace is a `view` of another layout. A panel's title is a `:drag (panel)` source and a `split` region `:accepts ((panel dock-panel))`, so docking, floating and re-docking are drag-and-drop (§8.2) answered by a patched layout. `toolbar :placement` positions toolbars at a window edge, floating, or `:around` an anchor (§9.2).

### 4.7 Properties and controls

`properties` holds collapsible `section`s of `prop` rows, each a label and one control; `prop :leading` / `:trailing` hold `icon`, `toggle` or `color` slots.

```lisp
(properties :key "transform"
  (section "Transform" :collapsed nil
    (prop "Location" (vector :unit :m :scrub t :live t :keys (x y z)))
    (prop "Rotation Mode" (select :options *rotation-modes*))
    (prop "Suppressed" (toggle))))
```

Control attributes:

| control        | attributes                                                                 |
|----------------|----------------------------------------------------------------------------|
| `number`       | `:unit :min :max :step`; `:scrub t` (horizontal drag adjusts); `:live t` (throttled `change` events while scrubbing, otherwise one on release) |
| `vector`       | `:keys (x y z)`, per-component slots; otherwise as `number`                |
| `select`       | `:options`; `:editable t` (combo box)                                      |
| `field`        | `:live t` (throttled `change` while typing); `:input-mode (:text :numeric :decimal :email :url :search)` |
| `toggle`       | `:appearance (:switch :chip)`                                              |
| `radio-group`  | `:appearance (:list :segmented :toolbar :rating)`                          |
| `slider`       | `:min :max :step`; `:track (:gradient from to)`                            |
| `button`       | `:icon`; `:menu`                                                           |
| `color`        | a colour value                                                             |

### 4.8 Tables, trees and collections

`table` rows are `trow`s of `cell`s; cells hold any node. `trow` MAY contain `trow` children and carries `:expanded`; `table :tree t` renders as a tree-table. `tree` is the column-less case. `list`, `stack`, `row`, `grid`, `tabs` and `tree` accept `:sortable`/`:sort-group` (§8.2); `table` accepts them on rows and columns, and `:resizable` on columns.

`table`, `list` and `tree` accept `:virtual t :count N`. Lisp ships a window of keyed rows; the client raises `need-rows {from to}` when its visible range leaves the window; Lisp patches the window with `replace-node`. Row keys are stable across windows. Column sort, filter, pin, resize and reorder are events carrying the column key. Range selection is client-owned and queried as `(r1 c1 r2 c2)` (§8.4).

### 4.9 Media, images and links

- `image :src :alt :fit (:cover | :contain) :shape (:rect | :circle)`.
- `icon :name`, from the enumerated icon set in the specification file.
- `media :kind (:audio | :video) :src :state (:playing | :paused) :position :volume`. Controls are client-owned; Lisp drives playback by patching `state` and `position` and MAY query `position`.
- `link :href`, inline. Activation opens the URL client-side and is not an event.

### 4.10 Readouts

`readout :of value :format f` displays one client-owned value continuously without any message. `value` is one of `:pointer` (in a named canvas's coordinate space), `:zoom`, `:scroll`, `:selection-range`, `:media-position`, `:drag-delta`, `:pending-keys`. `:format` is from a closed set (unit, precision). A readout cannot reach Lisp state and is not a binding. The text backend renders it as `⟨pointer canvas-1⟩`.

## 5. Editor

`editor` is the one component with an internal model. It is governed by the contract in this section and by nothing else; each backend supplies a component satisfying it (§13). `editor :mode (:code | :rich)`; a rich document is a Lisp-owned structure of paragraphs and marks synchronized by the same buffer model as code, and `:paged t` renders page boundaries.

### 5.1 Decorations

`editor :decorations` is a keyed list of `(range kind handle state)` in logical coordinates (§5.4). `kind` is closed: `:presentation :hunk-added :hunk-removed :hunk-changed :error-form :current-frame :match :selection-hint :foldable`. A `:presentation` decoration behaves as an `oref` (§4.4) for gestures, documentation and pads, using the type's translator table. Adding a decoration kind is a change to this specification.

### 5.2 Buffer events

`hover`, `activate`, `secondary`, `selection` and gutter-mark gestures carry a logical range and, when over a decoration, its key and handle. Typing does not produce per-key events; it produces edit events under §5.3.

### 5.3 Buffer ownership

A buffer with an `editor` on it is client-authoritative. The client holds the text and a version counter that only it increments. Each user edit is sent as `event {buffer, version, ops}` with insert/delete operations at offsets; Lisp applies them to a mirror.

Lisp MUST NOT edit such a buffer directly. It sends a **proposal** `{buffer, base-version, ops}`. If the client's version equals `base-version` the client applies the ops. Otherwise it rebases the proposal's offsets through its own edits made since `base-version` (one-sided transformation: two writers, the proposer yields), applies the result, and reports the applied ops back as an ordinary edit event, so the mirror converges. A focused buffer is never resynced; an unfocused buffer MAY be replaced by a `view`.

Text under IME composition is not in the buffer until committed; proposals arriving during composition are queued until commit. The buffer's undo stack is the client's, at typing granularity; an applied proposal enters it as one step (§9.4).

Edit events and proposals are both logged in order; the rebase is deterministic, so replay reproduces the buffer.

### 5.4 Line coordinates and gutters

Logical lines are a property of the text. Visual lines are a product of wrapping, which depends on client-side width and font metrics. Every position in the protocol — decoration ranges, buffer events, `reveal-range`, `readout :of :cursor` — is logical (offset, or line and column). `editor :wrap (:none | :word | (:column n))` sets the wrapping policy; Lisp never learns where wraps fall.

The client draws the gutter from the text it holds: a number on the first visual line of each logical line, none on continuation lines. `editor :gutter` selects columns from `:line-numbers :relative-numbers :folds :marks`. Marks are the decorations of §5.1, attached to the first visual line of their range; a gesture on a mark carries the logical line. Fold markers are `:foldable` decorations from Lisp; fold state is client-owned (§8.4).

### 5.5 Paragraph ruler

In `:rich` mode the paragraph ruler (margins, indents, tab stops) is an editor decoration whose markers are `:resizable`, reporting positions in document units. It uses the tick policy of §7.3.

## 6. Records

`record :svg svg :regions ((handle type (x y w h)) …) :scale s` displays Lisp-drawn output. The SVG is generated by Lisp from an output record; view functions never author it. The client draws the SVG with the backend's SVG renderer and hit-tests the region list itself in record coordinates through `:scale`; a region behaves as an `oref` (§4.4). The text backend prints the region list: `[record text-2193, 840×276: h:41 runner @(12,8 120×20), …]`.

A raw SVG or markup node does not exist in the vocabulary.

## 7. Canvas

### 7.1 Nodes

```lisp
(canvas :key "board" :space :pixels :unit :mm :snap 8 :rulers t :guides t :tool :select
  (item :key "n1" :at (120 80) :size (160 60) :handle h1 :drag (node) :resizable :both
        :ports ((:out "value" number)) :pad task-pad
    (stack (heading "Source") (text "…")))
  (item :key "n2" :at (420 80) :size (160 60) :handle h2 :ports ((:in "x" number))
    (stack (heading "Sink")))
  (edge :key "e1" :from ("n1" "value") :to ("n2" "x") :route :curve :handle h3))
```

`canvas` attributes:

| attribute    | values                                                                              |
|--------------|-------------------------------------------------------------------------------------|
| `:space`     | `:pixels`; `(:grid cols rows)` (positions snap to cells); `(:time start end)` (x is time); `:geo` (positions are lat/lng) |
| `:tiles`     | tile URL template; `:geo` only                                                      |
| `:unit`      | `:px :mm :in :pt` for pixels; `:frames :seconds` for time; degrees for geo; `:auto` |
| `:origin`    | ruler origin in space coordinates                                                   |
| `:rulers`, `:guides` | rulers on both edges (§7.3); guides make rulers drag sources                 |
| `:lanes`, `:lane-axis` | §7.4                                                                       |
| `:tool`      | the effect of a drag on empty space: `:select` (marquee), `:pan`, `(:create type)`  |
| `:layout`    | `:manual` (default) or `:force` (§7.6)                                              |
| `:cursor`    | a client-owned value drawn as a line, e.g. `:media-position` (§7.6)                 |
| `:snap`      | snapping distance                                                                   |

`item :at :size :lane :handle :ports :pad :kind`. An item contains any node. `edge :from :to :route (:straight :orthogonal :curve) :label :waypoints :handle :pad`; edges route client-side. A `popover :anchor item-key` is positioned against an item.

### 7.2 Events

`move {key at lane}`, `resize {key size}`, `connect {from to}`, `select {keys}`, `create {type at size | points | axis}`, and `move` on an edge with a waypoint index. A freehand stroke is one `create` with its points. The viewport transform is client-owned; `pan` and `pinch` on a canvas never produce events.

### 7.3 Rulers and guides

A ruler is a function of the canvas's `:unit` and `:origin`, the client-owned viewport transform, and the client's tick policy. The tick policy is one algorithm parameterized by unit family: decimal (1, 2, 5 × 10ⁿ), imperial (halves, quarters, eighths), time (sexagesimal), geographic (degrees, minutes, seconds). Rulers read the same transform as the content: they pan with it on both axes and rescale with it, and produce no messages. Tick spacing and label unit are chosen from the zoom level; with `:unit :auto` the label unit steps through the unit's family. The pointer position is marked on both rulers from the client-owned pointer value.

With `:guides t` each ruler is a `:drag (guide)` source and the canvas `:accepts ((guide create-guide))`; dragging out of a ruler ends in one `create {type :guide, axis, at}` and the guide is an `item :kind :guide`.

### 7.4 Lanes

`canvas :lanes ((:key k :label l :lanes (…)) …) :lane-axis (:x | :y)` partitions the space into lanes, nested at most one level. Items carry `:lane`; `move` reports the destination lane. Lane headers are `:sortable` and `:resizable`; a drop on a lane header targets the lane. On a `(:time …)` space, lanes are tracks.

### 7.5 Ports, connections and pads

Connecting is a drag from a `:port` or from a pad button of command `connect-to` to another item, ending in `connect {from to}`; the same drag onto empty space ends in a `drop` with a point, which Lisp answers by creating the target and the edge in one patch.

A pad is a set of command buttons the client shows around an item or edge on hover or selection. Pads are defined once against the registry (§9.2) and referenced by name with `:pad`; per-item applicability arrives as a `:pad-state` patch. The client positions a pad with `toolbar :placement :around`.

### 7.6 Timelines, meters and force layout

On a `(:time start end)` space with lanes, an item's `:at`/`:size` are a time extent; trimming is `:resizable :x`. `canvas :cursor :media-position` draws the playhead from the client-owned media position. Meters are `progress :role :meter` updated by `set-attr` patches under the coalescing rule of §2.3.

`canvas :layout :force` makes the client compute item positions by force-directed layout; positions are then client-owned, queryable (§8.4), and pinnable by a `move`.

### 7.7 Text rendering

```
CANVAS board (pixels, unit mm, tool select)
  lane sales
    n1 @120,80 160×60  h1 ⇄node  ports: value→number  pad task-pad
  lane ops
    n2 @420,80 160×60  h2        ports: number→x
  e1 n1.value → n2.x  (curve)
RULER x 0–1440 px step 100 (zoom 1.0)
```

Rulers and other zoom-dependent output are rendered for a viewport stated by the test.

## 8. Interaction

### 8.1 Gestures

Input modality never crosses the wire. The client recognizes a closed gesture set from mouse, touch, pen and keyboard; Lisp receives gesture names. Which gestures a type can emit is declared in the specification file.

| gesture     | mouse                        | touch                        | keyboard           |
|-------------|------------------------------|------------------------------|--------------------|
| `activate`  | click                        | tap                          | Enter / Space      |
| `modified`  | ⌘/Ctrl-click                 | two-finger tap               | ⌘/Ctrl-Enter       |
| `secondary` | right-click                  | long-press                   | Menu / ⇧F10        |
| `double`    | double-click                 | double-tap                   | —                  |
| `select`    | ⇧/⌘-click, marquee           | tap in selection mode        | ⇧-arrows           |
| `swipe`     | —                            | swipe with direction         | arrows             |
| `pan`       | drag on empty space, scroll  | one-finger drag              | arrows             |
| `pinch`     | modified wheel               | two-finger pinch             | ⌘+/−               |
| `refresh`   | —                            | pull past top                | —                  |
| `dismiss`   | Escape, click outside        | swipe down a sheet, tap outside | Escape          |
| `drag`      | press and move               | long-press and move          | —                  |

`pan` and `pinch` on `canvas`, `record`, `scroll` and `media` are absorbed into the client-owned viewport transform. Elsewhere a gesture is an `event`.

### 8.2 Drag and drop

A drag has a source, a target, a client-owned feedback phase, and exactly one terminal event; a cancelled drag sends nothing. Lisp never receives pointer motion.

| attribute                       | meaning                                                                       |
|---------------------------------|-------------------------------------------------------------------------------|
| `:drag (type &key handle)`      | the node is a drag source presenting `handle` as `type`                        |
| `:accepts ((type command) …)`   | the node is a drop target; a drop of `type` dispatches `command` with `(source-handle target-handle placement)` |
| `:sortable t`                   | children reorder by drag                                                       |
| `:sort-group name`              | children move between containers sharing the group                             |
| `:resizable (:x :y :both)`      | edge drag resizes                                                              |
| `:port (:in | :out type)`       | connection endpoint on a canvas item                                           |
| `:accepts ((:files command))`   | drop zone for OS files; the event carries names, sizes, types and a handle per file for reading bytes |

Terminal events: `drop {source-handle type target-key placement}`, `reorder {key from to}`, `move {key from-container to-container index}`, `resize {key size}`, `connect {from to}`. `placement` is an index, a cell, a canvas point (with lane), a port, or `:into`.

Target validity, drag image, insertion indicator, autoscroll and spring-loading are client-side; validity is computed from the `:drag` and `:accepts` types in the tree. On touch, a drag begins with a long-press.

The text backend renders sources as `⇄type`, targets as `⇐(types)`, sortable containers as `⇅`.

### 8.3 Hover groups

`:hover-group id` on any nodes makes them highlight together when any one is hovered, without a message. Selection remains an event.

### 8.4 Client-owned state, queries and events

The client owns: hover, focus, text selection, scroll offsets, the focused buffer's text (§5.3), drag and gesture in progress, canvas viewport transforms, force-layout positions, media position, visible ranges of virtualized collections, range selections, window size, split-divider positions, fold state.

Lisp never holds a live copy of client-owned state. It obtains a value by `query {window, view, value}` and receives one `snapshot`; the value is used and not retained. The client raises events when its state requires action from Lisp: `need-rows {from to}`, `resized {window size}`, `scrolled-away` / `scrolled-to-end` (per scroll container), `focus-changed {key}` for nodes with `:track-focus t`. Continuous display of a client-owned value is a `readout` (§4.10).

### 8.5 Focus and keyboard navigation

Focus is client-owned. Each container type's traversal is defined in the specification file: `tabs` and `radio-group` by arrows; `list`, `tree` and `table` by arrows with type-ahead; `menu` by arrows and mnemonics; `split` by a fixed chord between regions; `dialog` traps focus until dismissed. The `focus` act moves focus. The text backend marks the focused node.

### 8.6 Keymaps and key routing

Keymaps are tables sent once: the global keymap from the registry (§9.1), a per-view keymap, and the focused editor's own bindings, which declare a reserved set (movement, insertion). The client resolves chords locally, including prefix keys, echoing pending keys through `readout :of :pending-keys`, and sends `{command, handle}`. Priority: reserved editor bindings, then the view keymap, then the global keymap; unresolved keys go to the focused editor or field. The registry validator rejects a global binding that collides with a reserved editor binding.

### 8.7 Pending feedback and latency

Client-owned interactions (§8.4) never wait on Lisp. All other interactions are one round trip. When an event has been sent and no patch or `error` has arrived after 150 ms, the client shows the originating node in a pending state until one arrives; the client never applies an optimistic update. `hello` carries a measured round-trip time; above a threshold the client lengthens the throttles of `:live` controls and the interactor (§9.3) and shows pending state sooner. Nothing else varies with transport.

### 8.8 Modality and touch

`hello` carries `pointer (:fine | :coarse)`, `hover`, `touch`, viewport, safe-area insets and density. With `pointer :coarse` the theme selects larger targets. Without hover, the pointer-documentation line follows the most recently touched presentation, and the doc line is worded per modality from the gesture slots (§9.2). Mobile idioms are placements: `tabs :placement :bottom`, `toolbar :placement :floating`, `dialog :placement :sheet | :side`; `list` rows accept `:swipe-commands` revealed by a horizontal swipe; a sheet or drawer is closed by `dismiss`.

## 9. Commands

### 9.1 Registry

```lisp
(define-command (inspect-object :label "Inspect" :key "C-c I")
    ((obj object))
  (open-view 'inspector obj))
```

A command has a name, label, optional key, typed arguments, a body, and optionally an `:undo` method (§9.4). The client sends `{window, view, key, command, handle, payload}` and one generic dispatcher invokes the command. Buttons, menu items, keybindings, the palette, context menus, pads and the interactor are views over the registry.

### 9.2 Translator tables and pads

For each presentation type the registry generates a **translator table**: the one-line pointer documentation, the commands in each gesture slot (`:activate`, `:modified`, `:secondary` with count), and the applicable command list. Tables are sent once per session and looked up by the client; `oref` and decoration nodes carry only the type. Pads are defined against the registry and sent with the tables:

```lisp
(define-pad task-pad
  (:east  connect-to     :icon :arrow)
  (:south add-annotation :icon :note)
  (:north change-type    :icon :wrench)
  (:west  delete-item    :icon :trash))
```

The client words the documentation line per modality ("click / ⌘click / right" or "tap / long-press"). Per-node applicability changes arrive as patches to `state` or `:pad-state`.

### 9.3 The interactor

A command in progress is an `interaction` object: the command, the arguments accepted, the argument being gathered with its presentation type, and the partial text. The command line is a view of that object; accepted arguments render as chips. Input reaches it as events: `activate` on a presentation of the current argument's type, `change` on the command-line `field :live t`, `Escape` (cancel), `Enter` (default or commit). When gathering starts, Lisp patches `state :matching` on visible presentations of that type; when it ends, it clears them. Completion is a patched list returned for each change event.

### 9.4 Undo

Uncommitted client state (the focused buffer, an uncommitted `field`) is undone by the client (§5.3). Committed changes are undone by the registry's `undo` command over the command history; a command that changes image state and has no `:undo` method is not undoable, and the palette shows it as such. A commit is the boundary between the two stacks.

## 10. Text backend

The text backend renders any tree to plain text:

```lisp
(render-text (make-view 'inspector *foo*))
```

Contract: **text rendering preserves semantic information, not visual appearance.** Every semantically meaningful node, state, selection, decoration, action target and object reference MUST appear in the output; columns, fonts and positions MUST NOT be approximated. A node type that has no semantic text rendering does not belong in the vocabulary.

```
SOURCE presentations.lisp.14

  17 | (defun scan-buffer (runner &optional (limit [*scan-limit*]¹))
> 18 |   (loop for record = ([pop-record]² runner)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ current-frame

[1] h:311 → special variable clim-web::*scan-limit*
[2] h:317 → function clim-web::pop-record · state :matching
```

Inline presentations render as bracketed spans with a footnote table of handles; overlays render nested under their anchor; `editor` renders logical lines with decoration markers in a gutter and ignores wrapping; `record` renders its region list; canvases render as item and edge tables (§7.7); drag attributes, gesture slots, pads and the focused node are marked. Zoom- or width-dependent output is rendered for a viewport or column width stated by the test.

## 11. Box oracle

Each backend supplies `dump-boxes`, which runs the client headless and prints, for every keyed node in text-backend order, its computed rectangle, whether it is clipped, whether it overflows its parent, and whether it is visible. Box dumps are golden files at fixed viewports. Standing assertions: no keyed node is clipped except inside a `scroll`; no overlay lies outside its window; no `split` region is below its minimum; no `label` is truncated unless `:truncate t`. A screenshot is stored beside each box golden for human review and is not an oracle.

## 12. Record and replay

### 12.1 Log

Every message is appended to the log in the format of §2.5.

### 12.2 API

```lisp
(replay-log "bug-0042.log" :mode :client :until 183)
(replay-log "bug-0042.log" :mode :lisp :from 180 :until 190)
(diff-views 183 184)          ; first divergence, as a tree diff
(dump-view 'source-1)         ; current tree as an s-expression
(describe-handle h)
```

### 12.3 Modes

- **Client replay** feeds the logged Lisp→client messages to the runtime or the text backend and reproduces what the client showed. It requires no Lisp state; handle descriptions come from the log.
- **Lisp replay** feeds the logged client→Lisp messages to the image and compares the messages Lisp produces with the log. It requires the image identified in the log header (path, build, checksum) or a scripted fixture.

### 12.4 Invariant

**No unlogged client state may affect a future Lisp-visible result.** Client-owned state may affect rendering only. Any client state that determines an event's content enters the event payload; any that Lisp needs enters a `snapshot`. The invariant is tested by recording a session, replaying it, and diffing final trees; a difference is fixed by moving state across the wire, never by special-casing the replayer. The same test, run against two backends, is the cross-backend conformance test (§13).

## 13. Backends

A backend supplies the following; everything else is shared.

| supplied by each backend                  | web client                      | native client                          |
|-------------------------------------------|---------------------------------|----------------------------------------|
| one renderer per type (§14.1)             | DOM elements                    | widgets or a custom-drawn surface      |
| the generated theme (§4.3.3)              | CSS                             | stylesheet or palette                  |
| the delegated dispatcher and gesture recognizer (§8.1) | pointer, touch, key events | toolkit events                    |
| the mechanisms of §14.2                   | one implementation each         | one implementation each                |
| an `editor` satisfying §5                 | a CodeMirror-class component    | Scintilla, KTextEditor, NSTextView, …  |
| a `record` painter (§6)                   | inline SVG                      | the toolkit's SVG rasterizer           |
| a `media` element (§4.9)                  | HTML media                      | the platform player                    |
| `:geo` tiles (§7.1)                       | a tile layer                    | a tile layer                           |
| windows (§2.6)                            | tabs or `window.open`           | native windows                         |
| `dump-boxes` (§11)                        | headless browser                | headless toolkit                       |

The text backend is a backend of the same tree. A log recorded against one backend MUST replay to the same trees against another.

## 14. Client architecture

### 14.1 Per-type renderers, generated theme, delegated dispatch

The renderer table has one entry per node type. A node becomes elements or widgets; no code or closure is created per node. Per-node data written to the rendered element is limited to key, type, enumerated attributes, and geometry that is itself data. Styling is by generated class or token (§4.3.3); nothing emits style at runtime. The client installs a fixed set of input listeners at the window root, resolves the nearest keyed node, and interprets the event from that node's attributes; adding nodes adds no listeners. Data shared by all nodes of a type lives in per-type tables (§9.2, §8.6) and nodes carry references.

### 14.2 Mechanism registry

The client's interaction mechanisms are enumerated in the specification file. Each has a conformance test, a text-backend rendering and an implementation in every backend:

1. keyed reconciliation and patch coalescing (§2.3)
2. gesture recognition (§8.1)
3. drag and drop (§8.2)
4. hover groups (§8.3)
5. focus traversal (§8.5)
6. keymap resolution (§8.6)
7. pending feedback (§8.7)
8. canvas viewport: pan, zoom, rulers, tick policy, guides, cursor (§7.3)
9. lanes (§7.4)
10. edge routing and ports (§7.5)
11. pads and anchored overlays (§7.5, §4.5)
12. force layout (§7.6)
13. readouts (§4.10)
14. virtualization windows (§4.8)
15. editor bridge: decorations, buffer operations, gutters (§5)
16. record painting and region hit-testing (§6)
17. media element (§4.9)
18. box dump (§11)

### 14.3 Changing the client

A change to the vocabulary or the mechanism registry requires: an amendment to this specification, the generated artifacts of §4.1, a conformance test, a text-backend rendering, and an implementation in every backend. Before adding a mechanism, the alternatives are, in order: composition from existing nodes; a `record`; exclusion (§17). The client states its vocabulary version in `hello`, and the Lisp validator checks views against it.

## 15. Accessibility

Roles derive from node types in every backend. Names derive from content, or from `:label`; `:description` supplies a description. `banner` is a live region. Focus traversal is §8.5.

## 16. Security

A handle and a command constitute execution in the image. In-process there is no boundary. A socket transport binds to localhost or a Unix socket by default; a remote connection is opt-in and carries a session token in `hello` over TLS. Lisp validates every `{command, handle}` against the translator table before dispatch (§3.3). Multi-user isolation is out of scope.

## 17. Exclusions

The following are not part of the architecture: HTML, CSS or SVG authored in view code; a template language; two-way binding; a Lisp class per rendered element; application-specific client code; open-ended attribute bags; raw pointer or touch events crossing the wire; any API whose correct call sequence depends on prior calls.

Not in the vocabulary, and added only through §14.3: a 3D viewport; a terminal emulator; a `plot` node (a plot is a `record`).

## 18. Build order

1. Specification file and code generation with the validator on both sides; the vocabulary of §4, the buffer model of §5.3, keymap tables, translator tables and the mechanism registry are in the file from the first commit.
2. Text backend, canonical serialization, log format.
3. Golden tests and Lisp replay for four views: source pane, transcript, debugger, and a file-to-command drop.
4. Web client: all mechanisms of §14.2, the theme gallery, the box oracle.
5. Client event recording and full replay against the web client.
6. Freeze of the web client. The criterion is that recorded sessions replay to identical trees (§12.4).
7. Application work in Lisp. A native client, if built, starts after step 6 and is validated by cross-backend replay (§13).

## Appendix A. Coverage

The vocabulary is required to express the following application classes. Each entry names the sections that cover it.

| class                          | covered by                                                        |
|--------------------------------|-------------------------------------------------------------------|
| spreadsheet                    | §4.8 (virtual rows, range selection), §4.3.4 (cell colour, spans), §7 (charts over a grid) |
| CAD / EDA                      | §4.6 (panels), §4.7 (inspectors), §4.8 (tree-tables), §4.10 (coordinate readouts), §8.3 (net highlight), §7 (orthogonal edges) |
| raster / vector / photo editing| §4.6, §4.7, §4.8 (layer stacks), §4.9, §7.3 (rulers, guides), §4.7 (`color`) |
| audio / video / DAW            | §7.6 (timeline lanes, playhead, meters), §4.9 (`media`), §4.7 (mixer controls) |
| calendar / kanban / planning   | §8.2 (drag between cells and columns, resize), §4.8              |
| mail / chat / messaging        | §4.8 (threaded lists), §4.7 (chips), §5 (`:rich` composer), §4.4  |
| libraries / media browsers     | §4.8 (tree-table, virtual grids), §4.9                             |
| maps / sky                     | §7.1 (`:geo`), §4.5 (`dialog :placement :sheet`), §6              |
| network / data analysis        | §4.4 (`code` with spans), §8.3, §4.8                              |
| code and text editing          | §5, §4.5 (`item :kind :toggle`), §7.6 (force layout)               |
| block programming              | §7.5 (ports), §8.2                                                 |
| mobile                         | §8.8, §4.2 (placements), §4.7 (`:input-mode`)                      |
| forms and setup dialogs        | §4.7, §4.5                                                          |

Excluded classes: 3D viewports, terminal emulators (§17).

## Appendix B. Open questions

- Spreadsheet fill handle: `:resizable` on the selection rectangle producing a `fill` event, or a distinct gesture.
- Whether `select` on a canvas requires a lasso variant.
- Whether `:geo` is in the first frozen client or deferred; the cost is the tile layer's size.
- Formula entry with cell-reference picking: a gesture or an interactor mode.
- Whether `readout :format` admits Lisp-defined formatters compiled to the client, or only the closed set.
- Block snapping: `:port` drops or a canvas snap policy.
