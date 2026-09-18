# IDE Prototype — Technical Specification

Status: draft, 18 September 2026. Implements §34 of [ui-overview.md](ui-overview.md).
Companion: [ui-screens/](ui-screens/README.md).

This document specifies the first working path of the IDE against native
CCL. It is written to be built from: every section names a component, its
contract, and how it is checked. Where the design document states a goal,
this document states the mechanism that satisfies it in the prototype, and
where the prototype cannot satisfy it, says so.

**Governing constraint.** The page and the image communicate only through
shared memory: buffered byte streams in `SharedArrayBuffer` rings, with
`Atomics` for waking. There is no `postMessage` traffic. The one exception
is structural and stated in §3.2: the browser offers no way to hand a
`SharedArrayBuffer` to a Worker except one `postMessage` at creation, so the
bootstrap sends exactly one, carrying the buffers and nothing else, and no
message is ever sent again in either direction. Every other byte moves
through the rings. This is the port's own arrangement (an Atomics mailbox
over shared memory, `decisions.md` D5) applied to the interface, so the
transport the prototype exercises is the transport the port will use.

---

## 1. Purpose

The prototype exists to decide the interaction contracts that do not depend
on WASM before the client is built around them: the gesture rule (G5),
modal editing with a leader (§20), per-context applicable sets (G7),
presentation liveness and retention (G9.1), the model view and the command
envelope (§35), and the accessibility floor (§29). It also fixes the wire,
so that when the port reaches conditions and restarts the change is
transport only.

It does not measure interrupt latency, the heap ceiling, cold start,
snapshot cost or collector behaviour. Those are the port's (§31, items 1, 2,
7, 8), and the prototype's busy-image case is simulated (§8.3).

## 2. Architecture

Four processes, three of them in the browser's process model:

| Component | Runs in | Owns | Talks to |
| --- | --- | --- | --- |
| **Page** | the document's main thread | rendering, the record tree, the editor, input, focus, accessibility | the Bridge, through rings |
| **Bridge** | a dedicated Worker | the rings' far ends, the connection to the image, the control word | the Page through rings; the Host through one WebSocket per activity plus one control socket |
| **Host** | a Node process on the developer's machine | the static files with cross-origin isolation headers, the relay between WebSocket and TCP, later the git proxy of constraint 8 | the Bridge and the Image |
| **Image** | native CCL, one process | everything Lisp: presentations, commands, conditions, definitions, the model view | the Host over TCP, one connection per activity |

The Bridge is the seam. Today it relays frames between rings and sockets;
when the port is ready it is the Worker the image runs in, and the rings
become the image's own output and input streams. The Page never changes.
The Host never runs Lisp and never sees the heap.

A fifth component, the **Harness** (§7), is a Node process that speaks the
same frames to the Image over TCP for the agent path. It does not use the
rings; it is the remote client of constraint 6.

### 2.1 What never happens

- The Page never blocks. It never calls `Atomics.wait`.
- The Bridge never receives a message after bootstrap and never posts one.
- The Host never interprets a frame; it relays bytes.
- No frame carries code, and no frame is evaluated (constraint 2, G86).

## 3. Shared-memory buffered streams

### 3.1 The ring

A ring is one `SharedArrayBuffer` holding a header and a data region. It
carries bytes in one direction between one producer and one consumer.

```
offset  size  field        owner      meaning
0       4     magic        static     0x434C494D ("CLIM")
4       4     version      static     1
8       4     capacity     static     data region size in bytes, a power of two ≥ 65536
12      4     head         producer   bytes written, monotonic u32 (mod 2^32)
16      4     tail         consumer   bytes consumed, monotonic u32 (mod 2^32)
20      4     generation   producer   incremented on reset; a consumer seeing a change discards state
24      4     closed       producer   1 when no more bytes will be written
28      4     dropped      producer   frames dropped for lack of space (page→bridge ring only)
32      32    reserved
64      cap   data
```

All header words are accessed with `Atomics` on an `Int32Array` view.
Position of byte index *i* is `i mod capacity`. Free space is
`capacity − (head − tail)`; readable bytes are `head − tail`.

### 3.2 The rings and the control word

| Buffer | Direction | Capacity | Purpose |
| --- | --- | --- | --- |
| `out` | Bridge → Page | 4 MiB | presentation stream, documentation line, command-line state, panes, activities, answers |
| `in` | Page → Bridge | 256 KiB | gestures, commands, argument acceptance, queries, buffer text for evaluate and compile |
| `ctl` | both | 64 bytes | the control word (§3.5), the heartbeat sample (§3.6) |

At bootstrap the Page allocates all three, starts the Bridge Worker, and
posts them once. The Bridge acknowledges by writing `version` into `out`'s
header. From then on there is no message traffic; a debug build asserts
that `onmessage` is never invoked again on either side.

### 3.3 Frames

A frame is a length-prefixed payload:

```
u32   length      payload bytes, not counting this header
u8    channel     see below
u8    flags       bit 0: payload is a continuation of the previous frame (unused in v1)
u16   sequence    per-channel, wraps
bytes payload
pad   to a 4-byte boundary
```

If a frame would not fit before the end of the data region, the producer
writes a pad frame (`channel 0xFF`, payload of whatever length reaches the
end) and continues at position 0. A consumer skips pad frames. Frames are
never split across the wrap.

Channels:

| channel | ring | content |
| --- | --- | --- |
| `0x01 P` | out | presentation stream (§4.1) |
| `0x02 S` | out | surface state: documentation line, command line, panes, layouts, activities, attention (§4.2) |
| `0x03 A` | out | answers to queries (§4.4) |
| `0x11 E` | in | gestures and events (§4.3) |
| `0x12 C` | in | commands and argument acceptance (§4.3) |
| `0x13 Q` | in | queries (§4.4) |
| `0x14 T` | in | text: buffer contents for evaluate, compile, save (§4.3) |
| `0xFF` | both | pad |

Payloads are UTF-8 S-expressions in the restricted grammar of §4.5.

### 3.4 Waking and waiting

The producer, after advancing `head`, calls `Atomics.notify` on `head`. The
consumer, after advancing `tail`, calls `Atomics.notify` on `tail`.

- The **Bridge** consumes `in` by `Atomics.wait(in.head, seen)` and produces
  `out` by `Atomics.wait(out.tail, seen)` when the ring is full. It blocks;
  that is what Workers are for.
- The **Page** consumes `out` by `Atomics.waitAsync(out.head, seen)` where
  the browser provides it, and otherwise by reading `head` once per
  animation frame. Either way it drains everything readable in one pass and
  applies it before painting. It produces `in` without waiting: if free
  space is short, the frame goes into a bounded local queue (256 frames)
  and pointer-motion events in the queue are coalesced to the newest; if the
  queue is full, the frame is dropped and `dropped` is incremented. A
  dropped command is an error the Page shows; a dropped pointer event is
  not.

Budget (§29): the Page's per-frame cost with nothing to read is one atomic
load. Measured in §8.

### 3.5 The control word

`ctl` offset 0 is the pending word, with the bit layout the port reserves
(`decisions.md`, "Safepoints and explicit stacks"): bit 0 collection
pending (unused here), bit 1 interrupt requested, bit 2 sample requested.
The Page sets a bit with `Atomics.or` and notifies; the Bridge waits on the
word in a second thread of control (a `setInterval`-free loop is not
possible in one Worker, so the Bridge uses two Workers internally: one
blocked on `in`, one blocked on `ctl`, sharing the same buffers). On
interrupt the control Worker sends `(:interrupt :activity a)` over the
control socket, which the Image services with `process-interrupt` on the
activity's process, entering the debugger at the next safe point in Lisp
terms. The bit is cleared by the Image's acknowledgement frame.

This is G38 with native CCL's interrupt in place of the port's safepoint.
The latency it measures is the socket's, not the port's, and §8 says so.

### 3.6 The heartbeat sample

`ctl` offset 16 holds the sample record G39 asks for: `u32 sequence`,
`u32 activity`, `u32 ms-running`, `u32 bytes-allocated-kb`, `u32 gc-count`,
`u32 current-function-id` (a symbol id from the P channel's symbol table).
When bit 2 is set the Image writes a sample frame on the control socket,
the control Worker copies it into `ctl` and clears the bit. The Page reads
`ctl` when it wants to draw screen 17's panel and never waits for it. In
the prototype the values come from CCL's `ccl::total-bytes-allocated`,
`ccl::gccount` and the interrupted process's top frame; they are real, and
the mechanism is the one open question 11 asks the port for.

## 4. The wire

### 4.1 The presentation stream (channel P)

Output is a tree of records. The Image writes the tree as it draws it, and
the Page holds it (constraint 5). Every record has an id unique for the
activity's lifetime.

```
(:open :id r :parent p :kind k [:type t :obj o :state s :rev v :verbs n])
(:text :id r :s "…")
(:close :id r)
(:erase :id r)                      ; the record and its subtree are gone
(:replace :id r)                    ; incremental redisplay: what follows until :close replaces r's subtree
(:pin :id r :on t|nil)              ; G9.1 pinned state changed
(:expire :ids (r …))                ; G9.1: these records left the window and nothing pins them
```

`kind` is `:text`, `:presentation`, `:group`, `:table`, `:row`, `:cell`,
`:code` (a source form; the Page renders it in the code face), `:chip`.
For `:presentation`: `:type` is the presentation type name, `:obj` is the
object id (stable across records for the same object while it is live),
`:state` is `:live`, `:historical`, `:pinned` or `:expired`, `:rev` is the
inspection revision (§4.4), `:verbs` is the count of applicable commands in
the null context. Symbols are interned once per activity by
`(:sym :id n :name "…" :package "…")` and referred to by id thereafter, so
a frame never repeats a package prefix.

Geometry is not on the wire. The Page lays out records; the Image's
`formatting-table` and `formatting-item-list` become `:table` and `:group`
records, and the Page's CSS does the rest. The port will draw to a canvas
one day; the prototype does not, and the wire does not care.

### 4.2 Surface state (channel S)

```
(:doc :left ((:b "pop-record") " — function, clim-web") :right "…")
(:cmd :state :idle|:reading|:running :verb "Trace" :args ((:arg "runner" :obj o) …)
      :prompt "function-name" :type t :context c)
(:pane :id p :name "presentations.lisp" :chips ("clim-web") :fact "edited 4 m ago" :editable t)
(:layout :current "three-up" :available ("single" …))
(:activity :id a :name "clim-web" :status "editing presentations.lisp" :wants-you nil)
(:attention :activity a :reason :break|:finished|:output)
(:mode-hint :pane p :insert t)      ; the Image asks the Page to open in insert mode (input lines, dialogs)
(:grant :activity a :may (:evaluate :compile "clim-web" :files "/lisp/clim-web/") :tier :trusted)
```

The command line's `:context` is the input-context id the Page must quote
when it answers with a gesture or queries applicability (G7).

### 4.3 Events, commands and text (channels E, C, T)

```
(:gesture :record r :obj o :gesture :click|:alt-click|:right|:activate :context c)
(:pointer :record r)                ; the pointer's record changed; coalesced; drives the documentation line locally and asks nothing
(:key :pane p :key "…")             ; only for keys the Page does not own: none in v1
(:command :name "trace" :args ((:obj o) (:string "…") (:integer 500)) :context c :rev v :seq n)
(:accept :context c :arg (:obj o)|(:string "…"))
(:cancel :context c)
(:text :buffer b :range (from to) :s "…")   ; for :evaluate, :compile-buffer, :save
(:leader :path ("l" "3"))           ; a leader sequence the Page could not resolve locally
```

`:rev` on a command that edits an object is the revision the Page or
Harness last inspected it at (G86). The Image re-inspects before running
and answers `(:stale …)` if the state differs.

### 4.4 Queries and answers (channels Q, A)

```
(:query :id q :applicable :context c)            → (:answer :id q :applicable ((r (v1 v2 …)) …))
(:query :id q :verbs :obj o :context c)           → (:answer :id q :verbs ((:name "edit-definition" :key "e" :label "Edit Definition"
                                                       :why "opens …" :consequence nil|"rewrites two files" :group :object|:class|:package) …))
(:query :id q :inspect :obj o)                    → (:answer :id q :inspect :obj o :rev v :printed "…" :type t :slots ((name (:obj o2) …)))
(:query :id q :complete :context c :prefix "…")   → (:answer :id q :complete ("…" …))
(:query :id q :indent :form "(defmacro …)")       → (:answer :id q :indent ((name kind depth) …))
(:query :id q :view :activity a :window n)        → (:answer :id q :view :rev v :items (…))       ; the model view, §7
(:query :id q :callers :obj o)                    → (:answer :id q :callers ((o2 :source :xref|:load) …) :complete nil)
```

Every answer may instead be `(:error :id q :condition "…" :restarts (…))`,
which the Page shows as a condition and the Harness receives as one (G86).
Applicability is asked once per context change, never per record (G7);
the Page caches the answer until `:cmd` announces a new context.

### 4.5 The grammar

Payloads are read on both sides by a hand-written reader that accepts
exactly: lists, symbols (`[A-Za-z0-9*+!?<>=/_-]+`, case preserved, keywords
with a leading colon), strings with `\"` and `\\` escapes, integers,
decimal floats, `t` and `nil`. Nothing else: no `#`, no `'`, no `|`, no
backquote, no packages on the wire (symbols are ids, §4.1). The Lisp side
does not use `read`; it uses this reader, which cannot evaluate (G86). A
payload that fails to parse is dropped and counted; a debug build logs it.

Frame size limit 1 MiB. Text larger than that (a buffer to compile) is sent
as several `:text` frames with ranges.

## 5. The Image (native CCL)

A system `clim-web` loaded into a stock CCL 1.13 on macOS, the project's
reference host. It uses what CCL has and adds no kernel change.

| Concern | Mechanism |
| --- | --- |
| Activities | one CCL process each, created by `(:command :name "new-activity")`; the listener activity exists at start |
| Connection | one TCP connection per activity to the Host (`ccl:make-socket`), a reader thread and a writer thread per connection; frames as §3.3 without the pad rule |
| Output | a `presentation-stream` class whose `stream-write-string` and `with-output-as-presentation` emit P frames; `formatting-table` emits `:table`; every form the listener prints is a `:code` record |
| Presentations | `define-presentation-type` and `define-presentation-to-command-translator` as in CLIM II, over the image's own objects; the null-context translator set is computed when a record is written and its count sent as `:verbs` |
| Applicability | the input-context stack per activity; `(:query :applicable)` walks the visible records the Page named and tests translators against the context; declared `:why`, `:consequence`, `:key` and `:group` come from the command's `define-command` options |
| Objects | an `eq` weak hash table from object to id and a bounded strong table for the retention window (`record-history-depth` records) plus pins (G9.1); an object outside both is `:expired` and its id still names its last printed form |
| Revisions | `(:query :inspect)` records `(obj . printed-form-hash)` under a monotonic revision; an editing command compares before running (G86) |
| Conditions | `handler-bind` around every command and evaluation; the debugger surface is `compute-restarts`, `ccl::map-call-frames` for frames, `ccl::frame-named-variables` for locals; a `:condition` presentation, `:restart` presentations with `:state :live` until the dynamic extent ends, then `:expired` |
| Interrupt | `process-interrupt` on the activity's process with a function that signals `interrupt-request`, from the control connection (§3.5) |
| Definitions | `ccl:*record-source-file*` and `ccl::xref` on for the loaded systems; G31's three states from the image's definition record, the session log (§6.3) and `git status` |
| Callers | `ccl::who-calls` when recorded, labelled `:xref`; observed callers from load, labelled `:load`; `:complete nil` always in the prototype |
| Evaluation | `(:command :name "evaluate" :args ((:string "…")))` reads with the standard reader in the activity's package and `*read-eval*` bound to nil, in the activity's process; only for a `:trusted` activity (G89) |
| Model view | §7 |
| Grants | per activity, set at creation, enforced for files by wrapping `open` and `probe-file` in the activity's dynamic extent; the socket and the git proxy are the Host's to enforce |

The Image has no knowledge of rings, Workers or the page. It reads and
writes frames on sockets.

## 6. The Page

### 6.1 Components

| Component | Contract |
| --- | --- |
| Ring client | §3; exposes `drain(handler)` and `send(channel, sexp)`; asserts no `onmessage` |
| Record tree | a map from id to node with parent, kind, state and DOM element; applies P frames incrementally; `:replace` swaps a subtree without re-creating siblings |
| Renderer | DOM elements per record; `:code` in the monospace face with the screens' tokens (`ui-screens/src/screens.css` is the stylesheet); presentations are real buttons or links with the accessible name "type, printed form, n commands" (G82) |
| Editor | CodeMirror 6 with the vim extension for the prototype, chosen to be replaced (§27); modal, leader on space in normal mode, ⌥Space in the insert-only set; forms as text objects from the client reader |
| Client reader | form boundaries for strings, comments, `#+`/`#-`, piped symbols, character and string syntax; asks `(:query :indent)` for indentation and caches by symbol id |
| Input line | the command line as a real `<input>`; reads typed text or a gesture; the pending argument's type from `:cmd` |
| Leader menu | the applicable list from `(:query :verbs)` filtered by prefix, drawn as screen 3; every row a button with the letter |
| Documentation line | computed locally from the record under the pointer or caret and the cached applicable set; asks nothing |
| Activities and layouts | from S frames; switching is a command; layouts are CSS grid templates |
| Persistence | editor text to `localStorage` on every change, keyed by buffer id, restored on load (G78's client half) |
| Keyboard reach | `j`/`k` move sensitivity between presentations in non-editable panes, `↩` activates, Escape by the §20 order |

### 6.2 Gestures

The Page resolves gestures by G5 before sending anything: in an editable
pane in insert mode a click places the caret and sends nothing; ⌥click and
normal-mode `↩` send `(:gesture :activate)`; in output panes a click sends
`:click`; while `:cmd` says `:reading`, any click on a record of the wanted
type sends `(:accept …)` and other clicks do nothing.

### 6.3 What the Page keeps that the Image does not

The session log of G10.1 lives on the Host in the prototype: every save
appends `(path, time, sha256, bytes)` to `~/.clim-web/log/` and the Image
reads it over a `:query`. The Page never writes files.

## 7. The Harness and the model view

The Harness is a Node process: it connects to the Host as a client of one
activity, issues `(:query :view)`, formats the answer and the `(:query
:verbs)` manifest for the model, sends the person's prompt with them, parses
the reply, validates each command against the manifest and the grammar,
and sends it as `(:command …)` with the view's `:rev`. Messages that are
not commands go to the activity's transcript as `(:command :name "say"
:args ((:string "…")))`, which the Image prints with the agent's name.

The model view answer is:

```
(:view :rev v :activity a :window n
  :items (((:id r :kind :code :s "(scan-buffer *runner*)")
           (:id r :kind :presentation :type hash-table :obj o :printed "#<HASH-TABLE eql, 14 entries>" :state :live :rev v2 :verbs 8 :from "Transcript 2 min ago")
           (:id r :kind :text :s "14") …)
  :cmd (:state :idle) :doc "…" :activities (…) :grants (…))
```

It is generated by the same walk that writes P frames, restricted to the
window, with interiors omitted; the Harness descends with `(:query
:inspect)`. Two harnesses are built in that order: first an MCP server that
exposes the view as resources and the manifest as tools to the vendors'
harnesses, with their file and shell tools disabled for the session; second
a direct API loop under the Harness's own control (§35).

Tiers (G89): the activity's `:tier` is set at creation; a `:restricted`
activity's manifest never contains `evaluate` or `compile`, and the Image
refuses them if asked anyway.

## 8. The path, and what is measured

### 8.1 The path

1. Open `presentations.lisp` in the clim-web activity. Edit `scan-buffer`
   in normal mode using form text objects.
2. Evaluate the definition from the editor (`SPC e v`). See it appear in
   *Changed since load* as "in the image only".
3. Inspect the result in the transcript; descend one slot; step back.
4. Call it with input that fails the `check-type`. Land in the debugger
   with the three restarts the fixture establishes.
5. Choose *Skip this record and continue the loop*. See the process resume
   and the debugger record expire.
6. Write changed definitions to files. See the state move to "in a file and
   the session log".
7. Repeat 1–6 keyboard-only; with a screen reader at 200% text; from the
   Harness with Fable and with Codex; and with the image busy (§8.3).

### 8.2 Measurements

| # | What | How | Pass |
| --- | --- | --- | --- |
| M1 | Page idle cost | `performance.measure` around the per-frame drain with nothing to read, 10 000 frames | median < 50 µs |
| M2 | Gesture to documentation line | pointer moves onto a record → text updated, no ring traffic | median < 1 frame; zero frames sent |
| M3 | Command round trip | `:command` sent → first P frame received, 1 000 commands | median < 20 ms on localhost |
| M4 | Applicability answer size | bytes of `(:answer :applicable)` for a 2 000-record transcript | < 64 KiB; time < 30 ms |
| M5 | Retention | heap held by the object table after 10 000 forms with window 2 000 | bounded: grows with pins only |
| M6 | Model view budget | tokens of `(:view)` at window 200 and 2 000; commands failing validation per 100 turns, per model | recorded; no pass value yet (§31, item 13) |
| M7 | Interrupt bite | bit set → `interrupt-request` signalled, native CCL over the socket | recorded; not the port's number |
| M8 | Dropped frames | `dropped` after the path with pointer motion at 120 Hz | 0 commands dropped |
| M9 | No messages | debug assertion that `onmessage` fires once | holds for the whole session |
| M10 | Accessibility | the path completed with VoiceOver at 200% text | completed, with the list of what was announced wrong |

### 8.3 The busy image

The Bridge can be told to hold `out` closed for *n* milliseconds while the
Image keeps writing, which fills the socket buffer and then the Image's
writer thread blocks. During the hold the Page must keep scrolling,
highlighting and updating the documentation line (M2 under hold), and the
command line must accept a command that is delivered when the hold ends.
This simulates constraint 4; it does not simulate a Worker in a no-safepoint
region, and the number it produces is not a port number.

## 9. Repository and build

The prototype is a separate system, not part of the port's tree:
`clim-web` as a sibling repository, with `image/` (the CCL system),
`page/` (the client), `host/` (the Node server and relay), `harness/` and
`spec/` holding a copy of this document at the revision built. The port
repository keeps this specification and the screens; the prototype
references them by commit. The Host serves `page/` with
`Cross-Origin-Opener-Policy: same-origin` and
`Cross-Origin-Embedder-Policy: require-corp`, without which
`SharedArrayBuffer` does not exist in the page.

Build: `node host/serve.js` starts the Host and launches CCL with
`--load image/start.lisp`; the page opens at `http://localhost:8080/`. No
bundler; ES modules; CodeMirror from a pinned copy under `page/vendor/`.
Tests: `node host/test.js` runs M1, M3, M4, M5, M8 and M9 headless with the
same Chrome the screens are rendered with, and writes `results.json` the
design document's §31 can cite.

## 10. Out of scope

Canvas rendering, tear-off windows (G20), snapshots and image checkpoints
(G51), git through the proxy (constraint 8; the Host has the seam and no
credential), foreign material (§12), delivery (§24), a light theme, and
anything that needs the port.

## 11. Decisions this specification makes

- Rings, not messages, for everything but the one bootstrap post.
- Two Workers inside the Bridge so a blocked data wait never delays an
  interrupt.
- S-expressions in a restricted grammar with a hand-written reader on both
  sides.
- Symbols interned per activity and sent by id.
- Geometry off the wire; the Page lays out.
- CodeMirror 6 with vim for the editor, as a trial.
- The session log on the Host, not in the Image.
- Native CCL's `process-interrupt` as the interrupt, and the socket's
  latency as a number that is labelled as such.
