# IDE Prototype — Technical Specification

Status: draft 4, 18 September 2026. Implements §34 of [ui-overview.md](ui-overview.md).
Companion: [ui-screens/](ui-screens/README.md).

Draft 2 follows Codex's review of draft 1 (ae61ac8f): socket-owning
Workers no longer block; rings have frame limits, chunking, an 8-byte wrap
rule and unsigned arithmetic; frames carry an activity id and the control
block is a request with a target and an acknowledgement; freshness is a
command-specific precondition, not a printed-form hash; trusted evaluation
has the native process's authority; the wire carries what the
documentation line needs at rest; drains have a budget and persistence is
asynchronous; the CLIM subset is named; the rings are a proposed transport
consistent with D5, not D5 itself; and a transport skeleton comes first.

Draft 3 follows Codex's review of draft 2 (9886496b): frames are 16-byte
aligned so a pad header always fits; the Bridge owns a completion
generation and completion is the last store; rings are never reset in a
session and reconnection is an activity epoch in the frame header; socket
receive is bounded by per-activity credits that the Host relays; and
partial operations (one form evaluated, changed definitions written) carry
per-definition state and never advance the buffer's whole revisions.

Draft 4 follows Claude's review of prototype commit 426f1c9 in `clim-web`:
epoch announcements are session frames on activity 0, sharing the Bridge's
session sequence with its errors, so the Bridge relays every Image frame
unchanged and reserves no sequence number in any activity's channels.

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
through the rings. The rings are a proposed transport consistent with the
port's architecture — an Atomics mailbox over shared memory,
`decisions.md` D5 — and are not that mailbox; D5 specifies the image's
requests to its host, and this document specifies the interface's stream
to its page. When the image runs in the Worker, both exist side by side.

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
7, 8), and the prototype's busy-image case is simulated (§8.4).

## 2. Architecture

Four components, three of them in the browser's process model:

| Component | Runs in | Owns | Talks to |
| --- | --- | --- | --- |
| **Page** | the document's main thread | rendering, the record tree, the editor, input, focus, accessibility | the Bridge, through rings |
| **Bridge** | one dedicated Worker | the rings' far ends, one WebSocket per activity, the control socket, the control block | the Page through rings; the Host through sockets |
| **Host** | a Node process on the developer's machine | static files with cross-origin isolation headers; the relay between WebSocket and TCP; later the git proxy of constraint 8 | the Bridge and the Image |
| **Image** | native CCL, one process | everything Lisp: presentations, commands, conditions, definitions, the session log, the model view | the Host over TCP, one connection per activity plus one control connection |

The Bridge is the seam. Today it relays frames between rings and sockets;
when the port is ready it is the Worker the image runs in, and the rings
become the image's own output and input streams. The Page never changes.
The Host never runs Lisp, never sees the heap and never interprets a
frame.

A fifth component, the **Harness** (§7), is a Node process that speaks the
same frames to the Image over TCP for the agent path. It does not use the
rings; it is the remote client of constraint 6.

### 2.1 What never happens

- The Page never blocks. It never calls `Atomics.wait`.
- A Worker that owns a socket never calls `Atomics.wait` without a timeout,
  because a blocked Worker cannot run the task that delivers the socket's
  next message. The Bridge owns sockets, so the Bridge never blocks (§3.4).
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
4       4     version      static     2
8       4     capacity     static     data region size in bytes, a power of two ≥ 65536
12      4     head         producer   bytes published, monotonic u32 (mod 2^32)
16      4     tail         consumer   bytes consumed, monotonic u32 (mod 2^32)
20      4     generation   producer   set at bootstrap; never changes during a session
24      4     closed       producer   1 when no more bytes will be written
28      4     dropped      producer   frames dropped for lack of space (page→bridge ring only)
32      32    reserved
64      cap   data
```

Header words are accessed with `Atomics` on an `Int32Array` view, because
`wait` and `notify` require one. Every value read from `head` or `tail` is
converted to unsigned (`x >>> 0`) before arithmetic, and differences are
taken modulo 2^32: readable bytes are `(head − tail) >>> 0`, free bytes are
`capacity − readable`. Ordinary signed subtraction of the raw words is a
defect once either counter crosses 2^31, and a boundary test (§8.1, B4)
starts the counters at 2^31 − 64 to prove the arithmetic.

Position of byte index *i* is `i mod capacity`.

**Publication order.** The producer writes the frame's bytes, then stores
`head` with `Atomics.store`, then calls `Atomics.notify` on `head`. The
consumer reads `head`, reads the bytes up to it, then stores `tail` and
notifies on `tail`. Bytes are never read past a published `head` and never
overwritten before `tail` has passed them.

**No reset.** `head` and `tail` are continuous for the life of the
session; nothing ever sets them back. A reset would have the producer
write the consumer-owned `tail`, and a consumer mid-read could then
publish its old `tail` into the reset ring; and since the rings carry
every activity, resetting one for a replaced connection would discard the
others' unread frames. Replacing an activity's connection is therefore
not a ring event at all: it is an activity epoch (§3.3). A whole-ring
reset would require both sides quiescent, and the prototype never needs
one: a new session allocates new rings.

### 3.2 The rings and the control block

| Buffer | Direction | Capacity | Frame limit | Purpose |
| --- | --- | --- | --- | --- |
| `out` | Bridge → Page | 4 MiB | 1 MiB | presentation stream, surface state, answers |
| `in` | Page → Bridge | 1 MiB | 256 KiB | gestures, commands, queries, buffer text |
| `ctl` | both | 128 bytes | — | the pending word, the control request, the sample (§3.5, §3.6) |

The frame limit is one quarter of capacity. A payload larger than the limit
is chunked (§3.3). A payload larger than 16 MiB is refused by the sender
with a condition; nothing in the prototype approaches it.

At bootstrap the Page allocates all three, starts the Bridge Worker, and
posts them once. The Bridge acknowledges by storing `version` into `out`'s
header. From then on there is no message traffic; a debug build asserts
that `onmessage` is never invoked again on either side (M9).

### 3.3 Frames

Every frame begins on a 16-byte boundary and is padded to one, so the
header is the alignment unit:

```
u32   length      payload bytes, not counting this header
u32   activity    activity id; 0 for frames about the session itself
u8    channel     see below
u8    flags       bit 0: more chunks follow; bit 1: this is a continuation chunk
u16   sequence    per activity, channel and epoch, wraps
u16   epoch       the activity's connection epoch (below); 0 for activity 0
u16   reserved    0
bytes payload
pad   to a 16-byte boundary
```

**Chunking.** A payload larger than the ring's frame limit is sent as
chunks of at most the limit, the first with bit 0 set, the middle ones with
bits 0 and 1 set, the last with bit 1 only. Chunks of one payload carry
consecutive sequence numbers on the same activity and channel, and no other
frame on that activity and channel is interleaved. The consumer reassembles
before parsing. A payload within the limit has both bits clear.

**Wrap.** Because frames are 16-byte aligned and the data region's size
is a multiple of 16, the space left before the end of the region is either
zero or a multiple of 16 that holds at least one header. If a frame would
not fit before the end, the producer writes a pad frame (`channel 0xFF`,
length set so the frame ends exactly at the region's end, which may be a
length of zero) and continues at position 0; if the space is zero, no pad
is needed. Frames are never split across the wrap. A consumer skips pad
frames and never reads a header from fewer than 16 bytes. Boundary tests
B1–B3 (§8.1) place a frame at every remainder from 0 to 48 bytes in steps
of 16, each with a frame one unit larger than the remainder.

**Epochs.** An activity's connection can be replaced (the socket drops
and the Host reconnects, or the Image restarts the activity). Each
replacement increments the activity's epoch; the Bridge announces it on
activity **0**, channel S, with `(:activity :id a :epoch n)` before any frame
from the new connection. The announcement's header epoch is 0; its payload
identifies the activity and its new epoch. This session channel has one
Bridge-owned sequence, shared with session errors. Only these session
announcements advance the Page's connection epochs; Image metadata does not.
Every Image frame carries its own activity's epoch. Each Image channel starts
at sequence 0 per connection, including S. The Bridge relays those frames
without changing their bytes or reserving a sequence number for itself.
A consumer that sees a frame whose epoch is older than the activity's
current one drops it, and on an epoch change discards any partial
reassembly for that activity. Nothing else in the ring is touched.

Channels:

| channel | ring | content |
| --- | --- | --- |
| `0x01 P` | out | presentation stream (§4.1) |
| `0x02 S` | out | surface state (§4.2) |
| `0x03 A` | out | answers to queries (§4.4) |
| `0x11 E` | in | gestures and events (§4.3) |
| `0x12 C` | in | commands and argument acceptance (§4.3) |
| `0x13 Q` | in | queries (§4.4) |
| `0x14 T` | in | text: buffer contents with revisions (§4.3) |
| `0xFF` | both | pad |

Payloads are UTF-8 S-expressions in the restricted grammar of §4.5.

### 3.4 Waking and waiting

After publishing `head` the producer notifies on `head`; after storing
`tail` the consumer notifies on `tail`.

- The **Bridge** owns sockets, so it never blocks. It consumes `in` with
  `Atomics.waitAsync(in.head, seen)` and, when `out` is full, waits for
  space with `Atomics.waitAsync(out.tail, seen)`. Where `waitAsync` is
  unavailable, it uses `Atomics.wait` with a 4 ms timeout inside an
  `await`ed macrotask loop, so socket tasks run between waits. Socket
  messages arriving while the Bridge is inside a ring operation are queued
  by the event loop and handled on the next turn; nothing is lost.
- The **Page** consumes `out` with `Atomics.waitAsync(out.head, seen)`
  where available and otherwise reads `head` once per animation frame.
  Each drain has a budget: at most 256 KiB or 4 ms, whichever comes first,
  after which it yields and continues on the next frame, so sustained
  output cannot monopolise the thread (M1, M2 under load). It produces `in`
  without waiting: if free space is short, the frame goes into a bounded
  local queue (256 frames); pointer-motion events in the queue are
  coalesced to the newest; if the queue is full, the frame is dropped and
  `dropped` is incremented. A dropped command or query is an error the Page
  shows; a dropped pointer event is not.

**Credits.** Waiting for ring space stops the Bridge writing, but not the
browser receiving: a WebSocket has no receive-side backpressure, so
without more, a full `out` would let socket messages pile up in the
Bridge without bound while the Image kept writing. Each activity
connection is therefore credited. On connection the Bridge grants the
Image a window (1 MiB) with `(:credit :activity a :bytes n)` on that
connection; the Image's writer may send at most the granted bytes beyond
what it has already sent, and blocks in its own thread when the credit is
spent. The Bridge grants more only as it writes that activity's bytes
into `out`, so the credit follows the ring's space and bytes held by the
Bridge outside the ring never exceed the window per activity (D3, M13).
The Host relays credits unchanged and pauses its read of the Image's TCP
socket while the WebSocket's `bufferedAmount` exceeds 1 MiB, so its own
buffering is bounded too. The control connection is not credited: one
request is outstanding at a time (§3.5). In the other direction the
Bridge stops draining `in` while its send buffer exceeds 1 MiB, which
pushes back into the Page's bounded queue.

Budget (§29): the Page's per-frame cost with nothing to read is one atomic
load. Measured as M1.

### 3.5 The control block

`ctl` is a request block in the shape of the port's own (`decisions.md`,
"Mailbox and lazy-install requests"): a target, an opcode, a generation, and
a status word that is waited on.

```
offset  size  field        owner    meaning
0       4     pending      Page     bit 1 interrupt requested, bit 2 sample requested (bit 0 reserved for the port)
4       4     generation   Page     incremented for each request; the Bridge echoes it
8       4     target       Page     activity id the request is for
12      4     opcode       Page     1 interrupt, 2 sample
16      4     status       Bridge   0 idle, 1 posted, 2 acknowledged by the Image, 3 failed (reason in 20)
20      4     reason       Bridge   0 none, 1 no such activity, 2 connection lost, 3 refused
24      4     done         Bridge   generation of the last completed request; the completion itself
28      4     reserved
32      64    sample       Bridge   §3.6
96      32    reserved
```

The Page makes a request by writing `target`, `opcode` and a fresh
`generation` g, then setting the pending bit with `Atomics.or`, then
notifying on `pending`. One request is outstanding at a time: the Page
issues g + 1 only after `done` equals g, and a second request before that
is refused by the Page itself with reason 3. The Bridge waits on
`pending` with `waitAsync`, sends `(:interrupt :activity a :generation g)`
or `(:sample …)` on the control connection and stores `status` 1. When the
Image answers `(:ack :generation g)`, or the socket is lost, the Bridge
completes the request in this order: store `reason`, store `status` (2,
or 3 with reason 2), clear the pending bit with `Atomics.and`, store
`done` = g, notify on `done`. The store to `done` is the completion; the
Page waits on `done` and treats request g as complete only when `done`
equals g, then reads `status` and `reason`. `status` and `generation`
alone prove nothing, since they have different owners: after g completes
the Page can publish g + 1 while `status` still reads 2 from g. Because
the bit is cleared before `done` is published and the Page issues nothing
before it sees `done`, no new request can race the clearing.

Interrupt on the Image is `process-interrupt` on the activity's process
with a function that signals `interrupt-request` (§5). This is G38 with
native CCL's interrupt in place of the port's safepoint; the latency it
measures is the socket's, and M7 says so.

### 3.6 The heartbeat sample

The sample at offset 32 is a seqlock:

```
u32 seq            odd while the Bridge is writing, even when complete
u32 activity
u32 ms-running
u32 bytes-allocated-kb
u32 gc-count
u32 current-function   symbol id in the activity's table
u32 reserved × 10
```

The Bridge writes `seq + 1` (odd), the fields, then `seq + 2` (even),
with `Atomics.store` in that order. The Page reads `seq`, the fields, and
`seq` again, and retries if the two differ or the first was odd, so it
never combines fields from two samples. Values come from CCL's
`ccl::total-bytes-allocated`, `ccl::gccount` and the top frame of the
sampled process; they are real, and the mechanism is the one open question
11 asks the port for.

## 4. The wire

### 4.1 The presentation stream (channel P)

Output is a tree of records per activity. The Image writes the tree as it
draws it, and the Page holds it (constraint 5). Record and symbol ids are
unique within an activity; the Page keys everything by `(activity, id)`.

```
(:open :id r :parent p :kind k
       [:type t :obj o :state s :rev v
        :gestures ("edit definition" "describe" "11 commands")])
(:text :id r :s "…")
(:close :id r)
(:erase :id r)                      ; the record and its subtree are gone
(:replace :id r)                    ; incremental redisplay: what follows until :close replaces r's subtree
(:pin :id r :on t|nil)              ; G9.1 pinned state changed
(:expire :ids (r …))                ; G9.1: these records left the window and nothing pins them
(:sym :id n :name "…" :package "…") ; interned once per activity; referred to by id thereafter
```

`kind` is `:text`, `:presentation`, `:group`, `:table`, `:row`, `:cell`,
`:code`, `:chip`. For `:presentation`, `:type` is the presentation type,
`:obj` the object id (stable across records for the same object while it
is live), `:state` one of `:live`, `:historical`, `:pinned`, `:expired`,
`:rev` the object's inspection revision (§4.4), and `:gestures` the three
strings the documentation line shows for click, modified click and right
click in the null context, computed by the Image when the record is
written. With them the Page draws the documentation line for any record
without asking (G5, M2), including while the Image is busy. What it cannot
draw offline is the applicable set under a non-null context, which is a
query (§4.4).

Geometry is not on the wire. The Page lays out; `:table` and `:group`
come from the Image's table and item-list formatting, and the Page's CSS
does the rest.

### 4.2 Surface state (channel S)

```
(:doc :left ((:b "pop-record") " — function, clim-web") :right "…")
(:cmd :state :idle|:reading|:running :verb "Trace" :args ((:arg "runner" :obj o) …)
      :prompt "function-name" :type t :context c)
(:pane :id p :name "presentations.lisp" :chips ("clim-web") :fact "edited 4 m ago"
       :editable t :buffer b :rev v :saved-rev v2 :compiled-rev v3)
(:layout :current "three-up" :available ("single" …))
(:activity :id a :name "clim-web" :status "…" :wants-you nil :tier :trusted|:restricted
           :version "…")             ; the Image's own metadata; carries no epoch authority
(:activity :id a :epoch n)           ; session announcement from the Bridge, activity 0 only (§3.3)
(:definition :name scan-buffer :buffer b :rev v :range (from to)
             :compiled t|nil :written t|nil :state :in-image-only|…)   ; per-definition state (G31)
(:attention :activity a :reason :break|:finished|:output)
(:mode-hint :pane p :insert t)
(:grant :activity a :may (…))
(:ack :generation g)                ; control request acknowledged (§3.5), also echoed here for the transcript
```

A `:pane` that is editable names its buffer and three revisions, which is
how G62 is drawn: unsaved when `:rev` > `:saved-rev`, uncompiled when
`:rev` > `:compiled-rev`. The Page is the source of `:rev` (§4.3); the
Image is the source of the other two, and advances them only for
whole-buffer operations: `:compiled-rev` when `compile-buffer` completes
a transfer of the whole buffer at that revision, `:saved-rev` when
`save-buffer` does. Evaluating one form or writing changed definitions
is partial and never moves either: the Image answers with a
`:definition` record naming the buffer, revision and range the definition
came from, and the Page draws that as a per-definition mark in the gutter
and in the *Changed since load* pane. A buffer with two edited
definitions and one evaluated therefore shows as uncompiled with one
definition marked current, which is the truth.

### 4.3 Events, commands and text (channels E, C, T)

```
(:gesture :record r :obj o :gesture :click|:alt-click|:right|:activate :context c)
(:pointer :record r)                ; coalesced; local only in v1, sent for the busy-image measurement
(:command :name "…" :args (…) :context c :seq n [:pre (…)])
(:accept :context c :arg (:obj o)|(:string "…")|(:integer n))
(:cancel :context c)
(:text :buffer b :rev v :kind :buffer :range (from to) :s "…" :complete t|nil)
(:text :buffer b :rev v :kind :range :range (from to) :s "…")
(:leader :path ("l" "3"))
```

`:pre` is the command's precondition (§5, "Freshness"): what the sender
believes about the state it is about to change. The Image checks it in the
activity's process immediately before applying the change; a mismatch
answers `(:stale …)` with the current value and applies nothing.

`:text` carries the buffer's revision and a kind. A `:kind :buffer`
sequence, ranges with `:complete nil` followed by one with `:complete t`,
transfers the whole buffer at one revision; the Image discards a partial
transfer whose revision changes midway, and `:complete` is defined only
for this kind. A `:kind :range` frame is one form's text at a revision
and carries no completion flag; it feeds `evaluate-form` and nothing
else. `compile-buffer` and `save-buffer` act on a completed buffer
transfer, name its revision, and cite it in their answers, which is what
updates `:compiled-rev` and `:saved-rev` in the next `:pane` frame (§4.2).

### 4.4 Queries and answers (channels Q, A)

```
(:query :id q :applicable :context c :records (r …))
   → (:answer :id q :applicable ((r (v …)) …))
(:query :id q :verbs :obj o :context c)
   → (:answer :id q :verbs ((:name "edit-definition" :key "e" :label "Edit Definition"
        :why "opens …" :consequence nil|"rewrites two files" :group :object|:class|:package) …))
(:query :id q :inspect :obj o)
   → (:answer :id q :inspect :obj o :rev v :printed "…" :type t
        :slots ((name :value (:obj o2)|(:string …)|… :rev v2) …))
(:query :id q :complete :context c :prefix "…")   → (:answer :id q :complete ("…" …))
(:query :id q :indent :symbols (n …))            → (:answer :id q :indent ((n kind depth) …))
(:query :id q :view :activity a :window n)        → (:answer :id q :view …)         ; §7
(:query :id q :callers :obj o)                    → (:answer :id q :callers ((o2 :source :xref|:load) …) :complete nil)
(:query :id q :log :path "…")                     → (:answer :id q :log ((time sha256 bytes) …))
```

Every answer may instead be `(:error :id q :condition "…" :restarts (…))`
or `(:stale :id q :current …)`. Applicability is asked once per context
change for the records the Page has on screen, never per record (G7); the
Page caches the answer until `:cmd` announces a new context.

### 4.5 The grammar

Payloads are read on both sides by a hand-written reader that accepts
exactly: lists, symbols (`[A-Za-z0-9*+!?<>=/_-]+`, case preserved, keywords
with a leading colon), strings with `\"` and `\\` escapes, integers,
decimal floats, `t` and `nil`. Nothing else: no `#`, no `'`, no `|`, no
backquote, no packages on the wire. The Lisp side does not use `read`; it
uses this reader, which cannot evaluate (G86). A payload that fails to
parse is dropped and counted; a debug build logs it.

## 5. The Image (native CCL)

A system `clim-web` loaded into stock CCL 1.13 on macOS, the project's
reference host. Stock CCL has no CLIM. The prototype implements the subset
it needs and nothing more, in `image/present.lisp`:

- presentation types: `define-presentation-type` with `:inherit-from` and
  `presentation-subtypep` over a single-inheritance lattice; no type
  parameters in v1;
- presentations: `with-output-as-presentation` binding an object to a
  record id, and the object table below;
- translators: `define-presentation-to-command-translator` with `:gesture`
  (`:click`, `:alt-click`, `:right`), `:tester`, `:documentation`, and the
  declared `:why`, `:consequence`, `:key` and `:group` of G7;
- commands: `define-command` with typed arguments, into a per-activity
  command table; `accept` that reads a typed argument from a gesture or a
  string;
- input contexts: a per-activity stack with ids, pushed by `accept`.

McCLIM is not used: its value is in backends that draw, and the prototype
draws nothing on the Image side. If a later stage adopts it, the wire does
not change.

| Concern | Mechanism |
| --- | --- |
| Activities | one CCL process each, created by the `new-activity` command; the listener activity exists at start; each has an id, a tier, a package, a command table, an object table and a symbol table |
| Connections | one TCP connection per activity to the Host (`ccl:make-socket`), a reader thread and a writer thread per connection; the control connection carries only `:interrupt`, `:sample` and `:ack` |
| Output | a `presentation-stream` class whose `stream-write-string` and `with-output-as-presentation` emit P frames; every form the listener prints is a `:code` record |
| Gestures at rest | when a `:presentation` record is written, the null-context translators for the three gestures are computed and their documentation strings sent as `:gestures` |
| Applicability | `(:query :applicable)` tests each named record's object against the context's translators |
| Objects | an `eq` weak table from object to id plus a bounded strong table for the retention window (`record-history-depth` records) and pins (G9.1); an object outside both is `:expired` and its id still names its last printed form |
| Freshness | preconditions, per command: `edit-buffer` and `save-buffer` carry `(:buffer b :rev v)`; `redefine` carries `(:definition name :identity h)` where `h` hashes the current source form recorded for the name; `set-slot` carries `(:obj o :slot s :was (…))`; `store-value` and restart invocation carry the restart's id and are refused once its extent has ended. The check and the change run in the activity's process, so within an activity there is no interleaving. For an arbitrary mutable object touched from another activity there is no strong guarantee, and `(:inspect)` says so with `:rev` only |
| Conditions | `handler-bind` around every command and evaluation; the debugger surface is `compute-restarts`, `ccl::map-call-frames`, `ccl::frame-named-variables`; a `:condition` presentation and `:restart` presentations `:live` until the dynamic extent ends, then `:expired` |
| Interrupt | `process-interrupt` on the activity's process with a function that signals `interrupt-request`; `(:ack)` on the control connection |
| Flow | each activity connection's writer holds a credit (§3.4); `(:credit)` frames add to it; the writer blocks in its own thread when it is spent, and the activity's process blocks with it |
| Definitions | `ccl:*record-source-file*` and `ccl::xref` on for the loaded systems; G31's states from the definition record, the session log and `git status` run by the Image |
| Session log | owned by the Image: every `save-buffer` appends `(path time sha256 bytes)` under `~/.clim-web/log/` and copies the bytes; `(:query :log)` reads it |
| Callers | `ccl::who-calls` when recorded, labelled `:xref`; observed callers from load, `:load`; `:complete nil` always |
| Evaluation | `evaluate` reads with the standard reader in the activity's package with `*read-eval*` nil, in the activity's process; only in a `:trusted` activity |
| Authority | a `:trusted` activity has the native process's authority: everything CCL can do, it can do. The prototype therefore runs the Image in a disposable environment — a throwaway user account or container with only the project checkout — and says so on the image surface. A `:restricted` activity has its permitted commands and nothing else; `evaluate`, `compile-buffer`, `save-buffer` and `redefine` are absent from its table. Anything stronger is an external boundary and out of scope |

The Image has no knowledge of rings, Workers or the page. It reads and
writes frames on sockets.

## 6. The Page

### 6.1 Components

| Component | Contract |
| --- | --- |
| Ring client | §3; `drain(handler, budget)` and `send(activity, channel, sexp)`; chunking and reassembly; asserts no `onmessage` |
| Record tree | per activity, a map from id to node with parent, kind, state, gestures and DOM element; applies P frames incrementally; `:replace` swaps a subtree without re-creating siblings |
| Renderer | DOM elements per record; the screens' stylesheet (`ui-screens/src/screens.css`); presentations are real buttons or links whose accessible name is "type, printed form, n commands" (G82) |
| Editor | CodeMirror 6 with the vim extension for the prototype, chosen to be replaced (§27); modal; leader on space in normal mode, ⌥Space in the insert-only set; forms as text objects from the client reader; the buffer revision `:rev` increments on every change |
| Client reader | form boundaries for strings, comments, `#+`/`#-`, piped symbols, character and string syntax; asks `(:query :indent)` for unknown symbols and caches by id |
| Input line | a real `<input>`; reads typed text or a gesture; the pending argument's type from `:cmd` |
| Leader menu | the applicable list from `(:query :verbs)` filtered by prefix, drawn as screen 3; every row a button with its letter |
| Documentation line | from the record under the pointer or caret: its `:gestures` at rest, or the cached applicable answer while reading; asks nothing |
| Activities and layouts | from S frames; switching is a command; layouts are CSS grid templates |
| Persistence | an asynchronous journal in IndexedDB: each buffer change appends `(buffer rev delta)`; a compaction every 200 entries; the pane header shows the persisted revision beside G62's states; a quota failure is shown as a condition with *keep going without persistence* as the restart, never a silent stop |
| Keyboard reach | `j`/`k` move sensitivity between presentations in non-editable panes, `↩` activates, Escape by the §20 order |

### 6.2 Gestures

The Page resolves gestures by G5 before sending anything: in an editable
pane in insert mode a click places the caret and sends nothing; ⌥click and
normal-mode `↩` send `(:gesture :activate)`; in output panes a click sends
`:click`; while `:cmd` says `:reading`, a click on a record of the wanted
type sends `(:accept …)` and other clicks do nothing.

## 7. The Harness and the model view

The Harness is a Node process: it connects to the Host as a client of one
activity, issues `(:query :view)`, formats the answer and the `(:query
:verbs)` manifest for the model, sends the person's prompt with them, parses
the reply, validates each command against the manifest and the grammar,
and sends it as `(:command …)` with the precondition the view supplied.
Messages that are not commands go to the activity's transcript as `say`,
which the Image prints with the agent's name.

The model view answer is:

```
(:view :rev v :activity a :window n
  :items (((:id r :kind :code :s "(scan-buffer *runner*)")
           (:id r :kind :presentation :type hash-table :obj o
            :printed "#<HASH-TABLE eql, 14 entries>" :state :live :rev v2 :verbs 8
            :from "Transcript 2 min ago")
           (:id r :kind :text :s "14") …)
  :cmd (:state :idle) :doc "…" :activities (…) :grants (…))
```

It is generated by the same walk that writes P frames, restricted to the
window, with interiors omitted; the Harness descends with `(:query
:inspect)`. Two harnesses are built in that order: first an MCP server that
exposes the view as resources and the manifest as tools to the vendors'
harnesses, with their file and shell tools disabled for the session; second
a direct API loop under the Harness's own control (§35). A `:restricted`
activity's manifest never contains `evaluate`, `compile-buffer`,
`save-buffer` or `redefine`, and the Image refuses them if asked anyway.

## 8. Milestones, the path, and what is measured

### 8.1 Milestone 0: the transport skeleton

Before any editor exists, a skeleton of Page, Bridge, Host and a stub Image
that echoes commands as records demonstrates, with tests that fail before
and pass after:

| # | Demonstration | Passes when |
| --- | --- | --- |
| D1 | One request and response with idle input | a `:command` is answered while `in` is otherwise empty and the Page's drain cost stays at one atomic load per frame |
| D2 | Two simultaneous activities | records with the same id in two activities render in the right panes; commands route to the right socket; closing one activity leaves the other's frames intact |
| D3 | Full-ring backpressure | with the Page not draining and the stub Image writing at full speed for 10 s, the Bridge waits for space without blocking its sockets, a control request during the wait is acknowledged, the bytes the Bridge holds outside the ring never exceed the credit window per activity, and the Image's writer is observed blocked; when draining resumes no frame is lost or duplicated |
| D4 | Wrap boundaries | frames placed to leave every remainder from 0 to 48 bytes in steps of 16 before the wrap, each with a frame one unit larger than the remainder, chunked payloads at the limit, an epoch change mid-payload, and counters started at 2^31 − 64, all read back byte-identical or dropped as the epoch rule says |
| D5 | Interrupt during congestion | with `out` full and the stub Image looping, a control request reaches the Image and is acknowledged within the socket's round trip |

Boundary tests B1–B4 are D4's four cases run under `node host/test.js`
without a browser, against the ring library alone.

### 8.2 The path, frame by frame

The six steps of §34, with every frame that crosses. `A` is the clim-web
activity, `L` the listener activity.

1. **Edit `scan-buffer`.** The Page opens the buffer: `(:command :name
   "open-buffer" :args ((:string "presentations.lisp")))` → the Image
   answers with `:pane` (buffer `b`, `:rev 0`, `:saved-rev 0`,
   `:compiled-rev 0`) and `:text` frames on channel S carrying the file.
   Every keystroke increments `:rev` locally and appends to the journal;
   nothing crosses. Normal-mode `daf` on a form is local.
2. **Evaluate the definition.** `SPC e v` sends `(:text :buffer b :rev 17
   :kind :range :range (from to) :s "(defun scan-buffer …)")` then
   `(:command :name "evaluate-form" :args ((:buffer b :rev 17 :range (from
   to))) :context c)`. The Image reads the form, compiles it in A's process,
   records the definition as changed from the editor at revision 17, and
   answers on P with a `:code` record of the form and a `:presentation` of
   the function (`:gestures ("edit definition" "describe" "9 commands")`),
   and on S with `(:definition :name scan-buffer :buffer b :rev 17 :range
   (from to) :compiled t :state :in-image-only)` and the *Changed since
   load* pane's records. The `:pane` frame does not change: `:compiled-rev`
   stays 0, the header still says uncompiled, and the gutter marks this
   one definition as current at 17 (§4.2).
3. **Inspect.** A click on the function's record in the transcript sends
   `(:gesture :record r :obj o :gesture :click :context c0)`; the Image
   answers with the inspector pane's records. `↩` on the `pending-forms`
   slot sends `(:query :inspect :obj o2)`; the answer carries the slots
   with `:rev`s; the Page replaces the pane and extends the trail locally.
   `h` restores the previous records from the Page's own tree; nothing
   crosses.
4. **Fail the check-type.** `(scan-buffer *runner*)` typed in A's input
   line is `(:command :name "evaluate" :args ((:string "(scan-buffer
   *runner*)")))`. The Image's handler catches the `type-error`, computes
   the restarts, and sends the debugger pane: the condition presentation,
   three `:restart` presentations (`:live`), the frames, the locals as
   presentations, and `:attention :reason :break` on S. The `:cmd` frame
   announces context `c1` reading a restart.
5. **Choose a restart.** `↩` on the second restart sends `(:command :name
   "invoke-restart" :args ((:obj restart-1)) :context c1 :pre (:restart
   restart-1 :extent-live t))`. The Image checks the extent is live,
   invokes it, the process resumes, and it sends `(:expire :ids (…))` for
   the debugger's records and `:cmd :state :idle`.
6. **Write to files.** `(:command :name "write-changed-definitions" :args
   ((:definitions (scan-buffer))))`: the Image rewrites the form in
   `presentations.lisp` in place, appends to the session log, runs `git
   status`, and answers with `(:definition :name scan-buffer … :written
   t :state :in-file-and-log)` and the *Changed since load* records now
   "in a file and the session log". `:saved-rev` does not move, because
   writing one definition is not saving the buffer; the header keeps
   saying unsaved until `save-buffer`, and the definition's own mark says
   written. The Page's journal notes the persisted revision.

Any step's answer may be `:stale` or `:error`, and the Page shows both as
conditions on the command that asked.

### 8.3 Measurements

| # | What | How | Pass |
| --- | --- | --- | --- |
| M1 | Page idle cost | `performance.measure` around the per-frame drain with nothing to read, 10 000 frames | median < 50 µs |
| M2 | Gesture to documentation line | pointer moves onto a record → text updated from `:gestures`, no ring traffic; repeated with the Image held (§8.4) | median < 1 frame; zero frames sent |
| M3 | Command round trip | `:command` sent → first P frame received, 1 000 commands | median < 20 ms on localhost |
| M4 | Applicability answer size | bytes and time of `(:answer :applicable)` for 2 000 named records | < 64 KiB; < 30 ms |
| M5 | Retention | heap held by the object table after 10 000 forms with window 2 000 | bounded: grows with pins only |
| M6 | Model view budget | tokens of `(:view)` at window 200 and 2 000; commands failing validation per 100 turns, per model | recorded; no pass value yet (§31, item 13) |
| M7 | Interrupt bite | pending bit set → `interrupt-request` signalled, native CCL over the socket | recorded; not the port's number |
| M8 | Dropped frames | `dropped` after the path with pointer motion at 120 Hz | 0 commands or queries dropped |
| M9 | No messages | debug assertion that `onmessage` fires once per side | holds for the whole session |
| M10 | Drain budget | longest single drain during sustained 4 MB/s output | < 4 ms |
| M11 | Typing latency under persistence | keystroke to paint with a 2 MB buffer and the journal on | median < 1 frame |
| M12 | Accessibility | the path completed with VoiceOver at 200% text | completed, with the list of what was announced wrong |
| M13 | Bounded socket buffering | bytes held by the Bridge outside `out`, and by the Host outside its sockets, during a 10 s hold with the Image writing at full speed | ≤ credit window per activity; ≤ 1 MiB in the Host |

### 8.4 The busy image

The Bridge can be told to hold `out` closed for *n* milliseconds while the
Image keeps writing. The Bridge stops granting credit because it writes
nothing into the ring, the Image spends its window and its writer thread
blocks, and the Host pauses its read once its send buffer is high; nothing
between them grows (M13). During the hold the Page must keep scrolling,
highlighting and drawing the documentation line from `:gestures` (M2 under
hold), and the command line must accept a command that is delivered when
the hold ends. This simulates constraint 4; it does not simulate a Worker
in a no-safepoint region, and its number is not a port number.

## 9. Repository and build

The prototype is a separate system, not part of the port's tree:
`clim-web` as a sibling repository, with `image/` (the CCL system,
including `present.lisp`), `page/` (the client), `host/` (the Node server
and relay), `harness/` and `spec/` holding a copy of this document at the
revision built. The port repository keeps this specification and the
screens; the prototype references them by commit. The Host serves `page/`
with `Cross-Origin-Opener-Policy: same-origin` and
`Cross-Origin-Embedder-Policy: require-corp`, without which
`SharedArrayBuffer` does not exist in the page.

Build: `node host/serve.js` starts the Host and launches CCL with
`--load image/start.lisp` in the disposable environment; the page opens at
`http://localhost:8080/`. No bundler; ES modules; CodeMirror from a pinned
copy under `page/vendor/`. Tests: `node host/test.js` runs B1–B4, D1–D5,
M1, M3, M4, M5, M8, M9, M10 and M13 headless with the same Chrome the screens
are rendered with, and writes `results.json` the design document's §31 can
cite.

## 10. Out of scope

Canvas rendering, tear-off windows (G20), snapshots and image checkpoints
(G51), git through the proxy (constraint 8; the Host has the seam and no
credential), foreign material (§12), delivery (§24), a light theme,
confinement stronger than a disposable environment, and anything that
needs the port.

## 11. Decisions this specification makes

- Rings, not messages, for everything but the one bootstrap post; the
  rings are a proposed transport consistent with D5, not D5.
- No Worker that owns a socket ever blocks; `waitAsync` with a timed
  fallback.
- 16-byte frame alignment, so a pad header always fits; a frame limit of
  a quarter of capacity, chunking with two flag bits, unsigned modular
  counters, a stated publication order.
- No in-session ring reset; reconnection is an activity epoch carried in
  every frame header.
- An activity id in every frame header; a control request block with
  target, generation, a Bridge-owned completion generation stored last,
  and acknowledgement; a seqlock on the sample.
- Per-activity credits from the Bridge to the Image's writer, relayed by
  the Host, so socket receive is bounded when a ring is full.
- Whole-buffer revisions advance only on whole-buffer operations; partial
  operations answer with per-definition state.
- Freshness as command-specific preconditions checked in the activity's
  process; no guarantee for arbitrary objects across activities, said so.
- Trusted evaluation has the native process's authority in a disposable
  environment; restricted activities have permitted commands only.
- Gesture meanings on every presentation at rest; buffer revisions on text
  and cited by compile and save; the session log in the Image.
- Drains budgeted; persistence as an asynchronous journal with a visible
  persisted revision.
- A named CLIM subset of our own; McCLIM not used.
- S-expressions in a restricted grammar with a hand-written reader on both
  sides; symbols interned per activity and sent by id; geometry off the
  wire.
- CodeMirror 6 with vim for the editor, as a trial.
- Milestone 0 is the transport skeleton, with its five demonstrations,
  before any editor.
