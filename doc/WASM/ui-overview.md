# IDE Design Goals

Status: draft. Companion to `doc/stream-spec.md`.

Revised 18 September 2026 after review against the twenty-three reference
screens and against `decisions.md` and `outline.md` on this branch. The
revision changed constraints 8 and 9, G7, G8, G20, G27, G38, G39, G60, the
§29 targets budget, and added §33. Revised again the same day after Codex's
review and the key-model decision: constraint 1, G1, G5, G7, G10.4, G16, G25,
G51, G52, G60, G62, G73, G78 and G82 changed; G9.1 and G9.2 (what a
presentation refers to, and chips in files) were added; the ring became the
shelf (§6); §20 records the editing decision; §33 lists the screen changes it
implies; §34 defines the first prototype. §35, added the same day, makes the
agent a client and defines how a model reads the stream and how its text
becomes commands; G31, G53 and G79 each gained a sentence for it.

This document records the design decisions taken for the CLIM-based IDE and
the applications built with it, and states them as goals that can be checked
against an implementation. It is written to be argued with: every goal is
phrased so that a screen either satisfies it or does not.

A set of twenty-three reference screens accompanies this document. Where a
goal names a screen, that screen is the worked example. §33 lists the places
where the screens currently disagree with the text or with each other.

---

## 1. Thesis

The Lisp Machine's reputation for discoverability did not come from its
graphics. It came from one property: **everything is a first-class object,
all the way down**, so the clipboard, the file system, the error, the
documentation and the settings are all the same kind of thing. Presentations
— objects drawn on screen that remember what they are — are a consequence of
that property, not a UI layer bolted on top.

Emacs's model (buffers, windows, rings, modes) is good and worth reusing. Its
opacity is not: the nouns are real but invisible and oddly named, learned out
of band from another person. A presentation system closes exactly that gap,
because "what is this and what can I do with it" becomes a computed answer
rather than a documented one.

The goal is therefore not a prettier Emacs. It is: **the nouns are on screen,
and the verbs are derived from them.**

Two things this design faces that the Lisp Machine did not: history lives in a
distributed repository other people push to (§5), and the interface must show
material the image cannot read (§12). Both are boundaries, and both are drawn
explicitly rather than hidden.

---

## 2. Architecture the interface assumes

The interface is designed against these constraints. They are stated here
because several of the goals below only make sense in their light. The target
is the browser; no native mobile build is in scope.

1. **Lisp semantics stay in the image; the client is not thin.** The front
   end — JavaScript in the page — renders presentations, holds the record
   tree, owns buffer text and the editor over it, finds form boundaries,
   caches indentation, and handles focus, keyboard modes and accessibility.
   Everything that gives an object its meaning — reading, evaluation,
   compilation, applicability, documentation — happens in CCL running in
   WASM. Calling the client thin understates its work; what is true is that
   nothing about Lisp is decided there.
2. **The wire carries objects and events, never code.** No streamed value is
   ever evaluated by the client: no handler thunks, no computed layout
   expressions. Gestures identify a presentation by id and send it back; the
   image decides what that means. G36 restates this for content that the
   client fetches itself.
3. **The image runs in a worker; the page renders.** Dynamic compilation stays
   available — the browser's JIT compiles the modules the Lisp compiler emits —
   so no flatten or ahead-of-time step is needed.
4. **The constraint is blocking, not latency.** Worker crossings are
   `postMessage`, not process IPC: tens of microseconds plus serialisation,
   cheap enough that per-command traffic is free. The hazard is that a Worker
   running Lisp can be unreachable for a while — inside a no-safepoint region,
   waiting out a collection rendezvous, or simply mid-computation — while the
   user is still moving the pointer. The page's own thread never runs Lisp,
   and the interface must stay live through all of it, which is why the next
   constraint exists.
5. **The client holds the output-record tree.** Repaint, scroll, pointer
   highlighting, documentation-line updates and drag feedback are local
   operations that work while the image is busy or absent. Only the resulting
   command crosses.
6. **The same design serves a remote client.** CLIM's port/sheet/medium seam
   is where the transport goes; incremental redisplay is already a diff
   algorithm. The two places the classic design assumes locality — pointer-
   motion translator testing, and the input editor — are addressed in G7 and
   G8.
7. **Published history is git, hosted on GitHub.** The image holds a local
   clone so that editing, comparing and browsing history work offline and at
   pointer speed; the network is used for fetch and push only. The clone is
   persisted in browser storage.
8. **The host proxies git traffic, and the proxy protects the credential, not
   its use.** The image evaluates whatever the user writes, so it must never
   hold a credential: a token in page context is readable by any form typed
   into the listener. Fetch and push therefore go out through a host-side
   proxy holding the credential, and the image can only ask for a transfer,
   never read the token. That is the whole of what the proxy guarantees. It
   does not stop a form typed into the listener from asking the image to push
   as the signed-in author; G79 says what the grant model does about that.
   That the smart-HTTP endpoints also send no CORS headers is a second, weaker
   reason for the same arrangement. The cost is deliberate and worth naming:
   the web deployment is not a static page — it needs a server, and that
   server is an auth surface.
9. **Shared memory is the full profile's requirement, not the interface's.**
   The Wasm port's collector rendezvous uses an atomically accessed shared
   pending word per thread, and its host crossings use an Atomics mailbox
   (`doc/WASM/decisions.md`, `doc/WASM/outline.md`, on the `wasm2` branch), so
   cross-origin isolation — COOP and COEP from the server of constraint 8 — is
   a condition of the full profile running at all. The port also defines a
   deferred single-thread profile built for unshared memory, which would not
   have it; this interface targets the full profile and inherits its
   isolation, asking for nothing further. This is what makes §13 possible: a
   Worker in a tight loop never reaches its message queue, but it does read
   that word.

**Measured risks, not design questions:**

- **Heap ceiling.** A wasm32 linear memory tops out at 4 GiB and practically
  lower in a browser tab. That is a hard bound on image size, independent of
  tuning, until memory64 is worth using.
- **Cold start.** Module instantiation plus image load, on the slowest target.
- **Save cost.** See G10.1: how expensive a recoverable save actually is.

## 3. The screen contract

**G1. Three persistent surfaces, and no others.**
A work area, one command line, one documentation line. No toolbar, no icon
rail, no global menu bar, no status bar separate from the documentation line.
Anything else is summoned and dismissed. The command line is also the visible
way in: when it is empty it offers *Commands*, *Open views* and *Activities*
as clickable words, and on first use a line of guidance, so a newcomer has
somewhere to start without a toolbar being added for them. The leader key
(§20) opens the same three lists from the keyboard.

**G2. Panes carry a name and a fact, nothing more.**
No title bars, close boxes, minimise buttons or resize grips. Panes are
separated by a one-pixel divider. A pane header may carry the pane's name, the
object it is showing, and one relevant count.

**G3. Density is budgeted.**
Adding a persistent surface is a design change requiring justification, not an
increment. Transient surfaces are free.

*Reference: screen 1 (At rest), screen 11 (Views live inline).*

---

## 4. Presentations

**G4. No chrome at rest.**
A presentation is undecorated until it is relevant. Source code looks like
source code; a directory listing looks like a list. Sensitivity costs zero
permanent pixels.

**G5. One thing is marked at a time, and what a gesture does depends on
where it lands.**
Highlighting is latent and singular. The documentation line reads that one
object: what it is, and what the click, modified-click and right-click
gestures will do to it. Three rules decide what a gesture does, and they
never overlap:

- in an editable buffer in insert mode (§20), a click places the caret and a
  drag selects text; presentations in source are reached by modified click,
  or from normal mode, where the caret already sits on a form;
- in output panes, inspectors and lists, a click activates the presentation;
- while a command is reading an argument, a click anywhere selects that
  argument and does nothing else.

The first rule is what keeps the presentation system out of the way of the
most frequent activity there is.

**G6. Type-directed narrowing is the primary discovery mechanism.**
When a command wants an argument of a presentation type, every presentation of
that type on screen lights up and everything else recedes. On-screen and
in-image match counts are shown. This replaces documentation with computation
and is the single largest departure from mainstream editors.

**G7. Applicability is computed, per input context; presentation is
declared.**
Pointing at an object yields the commands that apply to it, grouped by where
they come from (the object, its class, its package), with counts that are real
facts about the image. There is no hand-written context menu anywhere in the
system, but computing which commands apply does not by itself produce a
useful menu. A command's declaration carries what cannot be computed: its
label, its priority, its group, a one-line explanation, its consequence when
that is not obvious, and its key path under the leader (§20). This is what
CLIM's translators already do, and screen 3's ordering and grouping are
those declarations, not editorial afterthoughts. Which translators apply depends on the input context — what type the
command line is currently asking for — and that context changes each time a
command starts reading an argument, so a record cannot carry its answer in
advance. The client therefore asks once per input context, not once per
record: one round trip at the start of a command, inside the §29 budget,
returning the applicable set for every record on screen; G6's highlighting is
drawn from that answer. At rest, the null-context set is attached to each
record when it is sent, so pointer documentation never waits on the image.

**G8. Pointing and typing are the same act.**
A pending argument accepts a pointer gesture or typed text interchangeably.
The editing of the input line runs on the client; completion is an
asynchronous request, never a synchronous one. How much of the rest of the
input editor moves to the client is open question 4.

**G9. Selection feeds the command line.**
Multiple selected objects are an argument like any other; commands take object
sets, not just single objects.

**G9.1. A presentation refers to its object in one of four states, and says
which.**
A transcript that showed a hash table an hour ago, and a program that has
changed it since, force the question the Lisp Machine never answered well.
The answer here is a contract with four states:

- **a historical rendering** — what was drawn. Replay never recomputes it
  (G84, screen 16), so the picture is always what you saw;
- **a live reference** — the object itself, reachable through the
  presentation, with its verbs. A presentation is live while its record is
  inside the transcript's retention window (`record-history-depth`) or while
  something pins it;
- **a pinned object** — retained on purpose: on the shelf (§6), in a command
  history entry the user kept, or pinned explicitly. Pins are the only
  unbounded strong references the interface holds, and the image surface
  (G50) counts them;
- **an expired reference** — the record is older than the window and nothing
  pins it, or the object's dynamic extent has ended. The rendering stays
  readable, the documentation line says *expired*, and the only verbs left
  are *show as it was* and *re-evaluate*.

Restarts and frames expire when their dynamic extent ends, whatever the
window says. Outside the window a record holds its object weakly, so keeping
the history readable does not keep the reachable graph alive.

**G9.2. A chip is session-only.**
Inserting an object into a buffer (G12) puts a live reference into text that
may be saved as a `.lisp` file. Identity cannot survive that, so the rule is
explicit: saving a buffer that holds a chip complains on the chip, the way a
dialog complains on the argument that is wrong (G54), and offers *replace
with printed form*. Nothing is ever written as a `#.` form or as an opaque
reference the file cannot read back.

*Reference: screens 1, 2, 3, 4.*

---

## 5. Objects the system must present

Everything in this list is a presentation with its own type and verbs. The
list is a requirement, not an illustration.

| Object | Notable verbs / facts |
| --- | --- |
| Functions, classes, variables, packages | edit definition, describe, callers, methods |
| Files, directories | edit, compare with previous, compile, staleness against derived files |
| Commits, branches, tags, pull requests | show diff, check out, revert, blame, compare, merge, open review |
| Output records | inspect, replay full size, replay into a new sheet |
| Conditions and restarts | invoke, supply a value, continue |
| Stack frames and their locals | inspect, edit and resume |
| Processes | inspect, interrupt, kill, show its debugger |
| Layouts | switch, rename, save current arrangement |
| Settings and key bindings | edit value, edit declaration, revert a layer |
| Differences between versions | apply, revert |
| Shelf entries | insert object, insert printed form, drop |
| Systems, modules, dependencies | compile, load, plan, add component, add dependency |
| Documents and citations (§12) | open at page, cite, attach to a definition, copy the text |
| Forms and buffers | select, evaluate, compile, indent, transpose, wrap, raise (§20) |
| Search results and apropos matches | go to it, replace here, replace all, narrow (§21) |
| Breakpoints, traces and profiles | enable, disable, show hits, time and space by definition (§22) |
| Tests and test runs | run, run failed, open the failure in the debugger (§23) |
| Dependencies and deliverables | pin, update, show what changed, build, open the bundle (§24) |

**G10. File versions are first class, and git is where they live.**
A version is a `(path, commit)` pair, not a per-file counter. The history of a
path is read from the repository, renames followed, and `compare with
previous` is one gesture from any file. Derived files state their staleness as
"compiled from commit X, source now at Y" rather than by timestamp.

**G10.1. Two layers, and only the upper one is git.**
Git records history when you commit; the Lisp Machine's value came from every
*save* being recoverable. These are different jobs and should not share a
mechanism. Saves append to a local, per-session version log — cheap, ordered,
disposable — and an explicit commit promotes the current state into git. The
log is what "compare with previous" reads between commits; git is what
collaborators, review and CI read. Writing every save into git refs instead
was considered and rejected: it makes a tree and a commit object per
keystroke-scale event, and it puts editor autosave traffic into the artefact
other people consume.

This layering is also what covers the things that are not in any repository —
scratch buffers, the settings file, generated output. They get the log; they
do not get commits.

**G10.2. History is a graph, not a stack.**
A file's versions belong to branches. A version presentation carries its
commit, branch and author, and the listing shows the current branch's history
with the others reachable, never flattened into a single numbered sequence.

**G10.3. Git objects are presentations like any other.**
Commits, branches, tags and pull requests are presented objects with computed
verbs (show diff, check out, revert, blame, compare, merge, open review). They
enter the system through G7, not through a separate version-control tool.

**G10.4. Divergence is a state the interface designs for, not an error dialog.**
A git-backed IDE is a distributed system: branches diverge, pushes are
rejected, merges conflict, the remote moves under you. These are conditions
with restarts (rebase, merge, force with lease, keep mine, keep theirs, stop),
and conflicts are presentations with verbs, in the same debugger-shaped
surface as any other break. No modal alert, no separate "source control" mode.
The image contributes what it alone knows — which of two conflicting symbols
is bound *in this image*, and how many known callers it has here — stated as
facts about this image and never as a verdict on the other branch. A symbol
absent from this image is not wrong; it is absent. So resolving a conflict is
not guesswork over text, and it is not the image guessing either.

*Reference: screens 4, 5, 6, 10, 11.*

---

## 6. The shelf

The earlier draft called this the ring and its verb *yank*. Both are Emacs
vocabulary learned out of band, which is the opacity §1 sets out to remove,
so the surface is now the **shelf**: a place you put objects to use later.
Screen 5 still carries the old name (§33).

**G11. The shelf holds objects, not text.**
Entries are live objects with their types and a rendered view — a hash table
shows entries, a condition shows its report, a record shows itself. Each entry
records its provenance: which pane it came from and when. Shelf entries are
pinned in the sense of G9.1: they hold their objects until dropped.

**G12. Insertion preserves identity.**
`↩` inserts the object; `⇧↩` inserts its printed form. The insertion point
shows which one is about to land, as a chip rather than as text, and a chip
in a file is governed by G9.2. In a source buffer the editor's registers
(§20) are shelf slots: putting a form in a register puts it on the shelf with
its provenance, and the shelf's own commands see it there.

*Reference: screen 5.*

---

## 7. The debugger

**G13. An error is a place to stand, not a report to read.**
The condition, the restarts, the frames and their locals, and the source at
the point of failure are all on one surface, and all of them are objects.

**G14. Restarts are commands.**
A restart that takes an argument reads it through the ordinary command line,
with the ordinary narrowing. Invoking it resumes the frame.

**G15. A break halts one process, not the system.**
Other processes keep running and the fact is visible in the documentation
line.

*Reference: screen 6.*

---

## 8. Documentation

**G16. Documentation is generated from the image, and says how well the
image knows.**
Signature, argument types, methods, callers, source location and compilation
time are facts read out of the running system, not prose maintained beside it.
Some of those facts are partial by nature: CCL's cross-reference is optional
and does not see calls through `funcall`, `apply` or a symbol, and a caller
list is only as complete as what was loaded with recording on. So the
Examiner says *known callers* and labels where each came from — recorded
cross-reference, observed at load, or unavailable — and never presents a
partial list as the whole.

**G17. There is no boundary between the system's code and yours.**
System sources are present. `edit definition` on anything leads somewhere,
including into CCL itself. Callers inside the implementation are shown and
labelled, not hidden.

**G18. Examples are executable.**
A documented example inserts into the transcript as a form, ready to run.

*Reference: screen 7.*

---

## 9. Windows and layout

**G19. Arrangements are named and switched, not dragged.**
A frame defines several named layouts; `⌘1`–`⌘n` switch between them and
`⌘⇧L` saves the current arrangement as a new one. Layouts are objects, so the
picker is the same type-directed narrowing as everything else.

**G20. We do not write a window manager.**
When a pane must genuinely float — ad hoc comparison, spatial memory, a size
independent of the frame, a second display — it tears off into a **host**
window. The OS draws the frame and handles z-order, focus, resize,
multi-monitor and accessibility. `⌘⇧T` re-docks it. Same image, same objects.
In the browser a host window is a popup: it needs a user gesture to open, and
it reaches the image only through the page that owns the Worker, so it lives
exactly as long as that page does. Anything longer-lived than that depends on
open question 9.

**G21. Ad hoc comparison is a command, not an act of window arrangement.**
`Compare Versions` takes two objects and produces a two-pane layout. Each
difference is a presentation with its own verbs.

**G22. Prefer an inline view to a new surface.**
Most historical window-need is only "somewhere to put a view of this object".
A table, a replayed record at scale, a process list — all are drawn in place
in the transcript. A new pane or window must earn itself against this.

**G23. Overlays are summoned and dismissed.**
The shelf, the layout picker and the applicable-command list appear over the
work area and leave no residue. They are the only place shadow is used.

*Reference: screens 8, 9, 10, 11.*

---

## 10. Configuration

**G24. A setting is a variable with a declared type, a default and a
docstring.** There is no configuration schema and no configuration file
format.

**G25. Setting editors are generated from types, and typed entry comes
first.**
An integer range yields a numeric field that reads and checks the value, a
member type yields a choice, a pathname yields a pathname reader — using the
same machinery that reads a command argument. No settings pane is hand-built.
A type alone does not say whether a slider helps: a range of one to ten
thousand needs a field you can type into, and a slider or stepper only
supplements it where the range is small enough to make dragging useful.

**G26. Values show their provenance.**
Every setting displays which layer it came from (default, user, project,
session), what it overrode, and the file and line of each layer. Each layer is
revertible in place. "Why is it this?" is answered without going to look.

**G27. Two files, one of them ours; the project layer is source.**
Defaults load first, then a machine-written user settings file, then the
project's settings file from the repository, then the user's own init file.
Hand-written code always wins because it loads last. The machine-written user
file is never jointly owned. The project file cannot be machine-owned, because
git shares it with everyone who clones the repository: it is ordinary source,
checked in and merged like any other file, and the setting editor changes it
the way G33 changes a system definition — by rewriting the one form in place
and leaving the rest of the file alone. A conflict in it is a conflict between
two settings and resolves through G10.4 like any other.

**G28. Customisation is code, and it is the same code the system is made of.**
No plugin API: `defmethod`, `defcommand`, add a translator. The affordance is
`edit definition`, which already exists.

**G29. No setting can make the system unstartable.**
A bad value surfaces as a condition with a *use the default and continue*
restart, not as a parse failure before the system exists.

*Reference: screen 12.*

---

## 11. Projects

**G30. The project is a system, not a directory.**
The primary browser shows systems: their modules in dependency order, each
module's load and compile state, and their dependencies with the versions
actually loaded. A file browser remains — directories hold plenty that is not
a module — but it is the secondary view, and neither replaces the other.

**G31. The image tracks what it has changed, and says where those changes
live.** Git knows what changed in the files; the image knows what changed in
*itself*, and the two diverge the moment a definition is evaluated in the
listener without being saved. Every changed definition is a presentation
carrying what it is, where the change came from (editor, listener, or an
agent, named — §35), when, and which of three states it is in:

- in the image only — lost on restart;
- in a file and the session log — not shared;
- committed — other people can have it.

Moving between those states is a command over a set of definitions
(*write changed definitions to files*), not a separate save ritual. Nothing
should be able to sit in the first state unnoticed.

**G32. Module state is per module, not per repository.**
Loaded, compiled, stale against its source, and the commit it was built from
are facts about a module, shown on the module. A system knows how to bring
itself up to date without the user tracking which files changed.

**G33. The system definition stays source; what is derived gets the screen.**
The `.asd` is ordinary, authoritative, hand-editable source — a
machine-owned project file would be the `custom-set-variables` mistake at
project scale (G27). The interface is built on what the definition *computes
to*:

- **the plan** — the operations `Compile System` would perform, in order, each
  with the reason it is there and each skip explained, before anything runs;
- **the dependency graph** as a presentation, with what is missing or cyclic
  drawn rather than discovered by a build failure;
- **findings only a live image can make** — a component whose file does not
  exist, a module using a symbol from a system it does not depend on, an order
  that works today by accident;
- **structural edits as commands** — add a component, add a dependency, remove
  one — which rewrite the `defsystem` form in place and leave comments and
  formatting alone.

This is what Genera actually offered around systems: a presented view of the
system object, commands taking it as an argument, and a plan you could read
before committing to it. It did not offer a form editor for `defsystem`, and
neither should this.

---

## 12. Foreign material

The image cannot read a PDF, decode a video, or lay out a web page, and should
not try. The interface still has to show them.

**G34. The client may display what the image cannot.**
A pane can hold a foreign view — a PDF, an image, a video, a rendered page —
which the client fetches (through the host proxy, or from a file the user
picked) and renders with its own machinery. The image places the view, knows
what it is and what state it is in, and never receives the bytes. A 41 MB
manual must not enter a heap with a 4 GiB ceiling (§2).

**G35. The object is presented; its interior is not.**
The document is a presentation with a type and verbs — open at page, search,
cite, attach. Its pages and words are opaque to the image, with one bridge:
when the user selects, a **citation** crosses back — document, page, range and
the selected text — as a presented object that can be put on the shelf,
attached to a definition, or written into a docstring. That bridge is what
makes a viewer part of the system rather than an embedded app beside it.

**G36. Foreign material is marked, and it is inert.**
It is drawn as visibly foreign — different surface, a stated origin — because
its provenance is not the image. It never executes in the application's
origin, nothing inside it can become a command, and a link in a document is a
request the user confirms, not an action. This is constraint 2 restated for
content: no code arrives over the wire, including inside a document. An
embedded page that could script is a hole in that rule, so arbitrary HTML is
either sandboxed with no access to the application, or not embedded at all.

**G37. References are stored, not copies.**
What persists is the citation — the resource's identity, a content hash, the
page and range — so the reference survives, can be re-opened, and can go in
the repository. The bytes stay where they came from.

---

## 13. Running and interrupting

**G38. Every computation can be interrupted, using the polls the port
specifies.** The Wasm backend is cooperative by design: its decisions place
polls at function entries, loop back-edges and allocation slow paths, reading
a shared pending word whose bit updates are specified to preserve unrelated
interrupt bits (`doc/WASM/decisions.md`, "Safepoints and explicit stacks").
Those polls are specified, not yet emitted: the accepted Stage 1 backend
contains none, and its unit records say so ("no safepoint or collection is
introduced"). The interface assumes they arrive with the collector work that
needs them and adds no poll site of its own. Interruption is then one more bit
in that word, set by the client. At the next safepoint the image signals an
`interrupt-request` condition and enters the debugger with the stack intact —
an ordinary condition with restarts, not a mode, so §7 already describes what
follows. Stage 0 of the port proves the underlying capability: interrupt a
computation at a cooperative safepoint, run nested code, then resume or
transfer through it.

Interruption is therefore not instantaneous and should not pretend to be.
Allocation and designated store sequences are declared no-safepoint regions,
so the delay is bounded by time-to-safepoint — a quantity the port measures
and bounds, and the only latency the interface has to account for.

**G39. The same word carries a heartbeat.**
A sample request is another bit. The client sets it on a timer; at the next
safepoint the image writes what is running, for how long, and its allocation
and collection counts into shared memory, then carries on. Nothing is added to
the fast path, and the client can give a live account of a busy image without
the image answering a message. A blocked system shows facts, not a spinner.
The age of the last sample tells the client whether the Worker is answering
at all; it is not a measurement of time-to-safepoint, which is set-to-service
and which the port measures separately.

**What this costs the port.** Less than a mechanism, more than nothing, and it
is a request against the port's decisions that must be logged there before
the interface builds on it (open question 11):

- a second bit in the pending word whose meaning is *write and continue*,
  where today a pending bit means *publish roots and stop*;
- a shared sample record with a declared schema, written at the safepoint
  slow path and read by the page;
- a way for the slow path to name the current function, which the port
  publishes today only as roots and only when a collection is pending.

The polls themselves and the interrupt bit cost nothing extra: the polls
exist for the collector, the pending word exists for the rendezvous, and the
reserved interrupt bits are named in the port's own decisions.

**G40. A running computation is an object.**
It is presented in the command line while it runs and carries its own
applicable commands, so stopping it needs no special affordance — it is G7
applied to a process.

**G41. Three graduated actions, and the destructive one states its cost.**
*Interrupt* at the next safepoint; *abort* to unwind to this activity's
command loop; *force quit*, which ends the image. The third names exactly what
will be lost — the definitions that exist in no file, the history — and when
the last snapshot was taken. It exists because it is the only one that works
when safepoints stop answering, and it ends the whole image rather than one
Worker: terminating a single Worker mid-rendezvous would leave the collector
waiting on a thread that no longer exists.

---

## 14. Activities

**G42. An activity is a context with its own process, panes, layout and
history.** Created on demand, switched with a keystroke, and preserved exactly
as left. Layouts (G19) rearrange panes *within* an activity; they do not give
you a second project, a second listener, or a debugger you can step away from.

**G43. Activities share one image.**
An activity's process is a CCL process, which the port may place on its own
Worker; they are contexts, not sandboxes: a definition changed in one is changed for
all, which is the Lisp Machine's arrangement and the useful one. Isolation, if
it is ever wanted, means a second image, never an activity.

**G44. The activity list is where attention is claimed.**
A break, a finished run, or output written while you were elsewhere marks its
activity in the list. A process that needs you becomes visible without
stealing the screen — which is what §15 hangs its policy on.

---

## 15. Attention

**G45. Background output is never lost.**
Output written to a pane the current layout does not show is retained and its
activity marked. A pane is not a place output can fall out of.

**G46. A break does not take the screen.**
A process that breaks halts, marks its activity, and waits. What you are
looking at changes when you change it, never because something else wanted
you. There is no exception for urgency.

**G47. Attention has one channel.**
The activity list (G44) and the right end of the documentation line. No toast,
no notification centre, no second queue to check.

---

## 16. Warnings

**G48. A warning is a presentation on a source range.**
Compilation produces conditions about specific places, so they are drawn
there, with verbs — go to it, explain it, define the missing thing, mute it
here. Not a log that scrolls past.

**G49. Warnings are a set you can walk.**
Per compilation, grouped by file and definition, with a position in the set
and a count. Muting is recorded where the warning applies, carries a reason,
and survives recompilation — so a mute is a statement someone made, not a
setting hidden elsewhere.

---

## 17. The image itself

**G50. The image is an object with a surface.**
Heap headroom against the wasm32 ceiling, collection rate and pause,
rendezvous health, Worker states, and the storage the clone, the session log
and the snapshots occupy. These are facts before they are failures, and the
ceiling is what makes headroom worth a permanent place.

**G51. Snapshots are objects, taken at quiescent points.**
Taken automatically before anything that can destroy the image, hourly, and on
demand; each labelled with what it contains — systems loaded, definitions that
exist in no file, history depth — and restorable, pinnable, deletable. A
snapshot is taken only when every Worker is at a safepoint with no host
request outstanding, which is the port's own save contract, and it holds
definitions and heap objects. It never holds active frames, a pending host
operation or an open debugger, and the interface does not pretend otherwise:
the verb is *restore*, not *resume*.

**G52. A snapshot is what makes the image survivable.**
It is the answer to G31's "in the image only" and the reason G41's force quit
can name what a restart would recover. It restores what the image held, not
what it was doing. Without snapshots, both are just warnings about loss.

---

## 18. History, dialogs and inspection

**G53. Commands are re-executable objects.**
A past command keeps its arguments as live objects, not printed text. Edit one
and run it again; the shelf (G11) holds values, the command history holds
invocations, and they are different lists on purpose. An agent's commands
(§35) are in the same history, marked with the agent's name, so what it did
can be read, replayed and reverted like anything a person did.

**G54. A command with more arguments than the line carries gets a dialog.**
Derived from the argument types by the same machinery as a setting's editor
(G25) — CLIM's `accepting-values` — with defaults shown, values fillable by
pointing at a presentation, and a complaint attached to the argument that is
wrong rather than to the dialog.

**G55. A dialog can hand you the form instead of running it.**
The assembled call goes into the transcript, where it is ordinary source you
can keep, edit, or put in a file. A dialog is a form-builder that happens to
be able to execute.

**G56. Inspection keeps a trail.**
Descending into a slot replaces the pane and extends a visible trail; back and
forward restore exactly what was there. It does not open a window (G22), and a
deep exploration can be retraced rather than reconstructed.

---

## 19. Undo

**G57. Undo is per substrate, and the interface says which.**
Editor text undoes. A definition compiled into the image reverts to the loaded
one (G31). A setting drops a layer (G26). A commit resets or reverts. A
deleted file comes back from the session log (G10.1). Four mechanisms, named
where they apply.

**G58. What cannot be taken back says so, before and after.**
A push others have pulled is not undoable; the honest offer is to revert
forward. The interface never presents a single undo stack, because there
isn't one — and a snapshot (G51) is the only thing that takes back everything
the image holds at once.

---

## 20. Editing

The document has said a great deal about what surrounds the editor and almost
nothing about editing. These goals close that.

**G59. The client owns the text; the image owns the meaning.**
Buffer text lives in the client, so typing, selection, scrolling and
structural motion never wait on a Worker (constraint 4). The image receives
text when asked — to compile, to evaluate, to index, to save — and never edits
a buffer behind the client's back. A refactoring the image performs (rename,
extract) comes back as a set of edits presented to the client, applied there,
and undoable there (G57).

**G60. Forms are presentations, which means the client has a reader.**
A Lisp editor is form-aware or it is a text editor with parentheses. Every
form under the caret or pointer is an object with verbs: evaluate, compile,
macroexpand, indent, transpose, wrap, raise, splice. Structural editing is
therefore G7 applied to source, not a mode you enable: in the editor of §20
a form is a text object, and the verbs are operators applied to it.
Character editing remains available underneath it, in insert mode, where G5's
first rule holds. Because G59 says structural motion never waits on the Worker,
the client must find form boundaries by itself: it carries a reader of its
own that understands strings, line and block comments, `#+` and `#-`, piped
symbols, character and string syntax and the standard dispatch characters,
and it asks the image about anything a user readtable adds. That is a second
reader, and its scope is a decision registered in §27, not an implementation
detail.

**G61. Indentation is the image's, not a table's.**
Indentation rules come from the definitions the image actually has — a macro's
lambda list decides how its body indents — so a new macro indents correctly
the moment it is defined. The client caches what the image tells it and asks
when it does not know.

**G62. A buffer's state is visible where the buffer is.**
Unsaved, uncompiled, compiled-but-not-saved, saved-but-uncommitted (G31): the
pane header carries which, in words. So does the editor's mode (§20), beside
it, because a mode is state and state is shown. There is no modified-star
convention to learn.

**Decision (18 September 2026): modal editing with vi's grammar, and a leader
key.** The earlier draft assumed the Emacs bindings as the obvious
inheritance. They are not; they are the vocabulary §1 rejects, and the
browser reserves the modifier chords both inherited sets depend on. The
editor is modal, in the shape Spacemacs gave vi, for four reasons that are
about this design rather than habit:

- **Forms are text objects.** An operator applied to a text object is a verb
  applied to a noun, which is this document's thesis in editing form. `d`,
  `y`, `c` and `>` apply to *a form*, *inner form*, *top-level form* and *the
  string under the caret* exactly as they apply to a word. Spacemacs's lisp
  state, vim-sexp and evil-cleverparens are the precedents, including the
  rule that operators keep parentheses balanced.
- **It settles G5.** Insert mode is ordinary text editing, so a click places
  the caret and a drag selects. Normal mode puts the caret on a form, and the
  documentation line reads that form as a presentation.
- **The leader menu is the discovery route.** After the leader, a popup
  lists the commands under that prefix with their letters — the applicable
  command list of screen 3, filtered by prefix — so G1's way in exists from
  the keyboard and no persistent surface is added. Every command declares
  its key path (G7).
- **It sidesteps the browser.** Every collision found in the screens uses a
  modifier: Chrome and Firefox reserve ⌘1 to ⌘8 for tabs and Safari can be
  set to; ⌘⇧T reopens a closed tab in all three; ⌘. stops loading in Safari;
  ⌘T, ⌘N, ⌘W and ⌘L cannot be captured by a page at all. Normal mode uses
  unmodified keys and the leader, all of which a page may take. Modifier
  chords survive only inside insert mode, where few are needed.

The decision has these parts:

- **Where modes apply.** Source buffers are modal. The transcript's input
  line and dialog fields open in insert mode, because a modal listener is the
  mistake modal-editor users spend the most time undoing. Non-editable panes
  — transcript output, the inspector, every list — have only normal mode:
  `j` and `k` move sensitivity between presentations, `↩` activates, and the
  leader is always the leader. That is G81's keyboard reach.
- **The leader.** Space in normal mode by default; a setting (G24) makes it
  another key. In insert mode space types a space. The leader tree is
  mnemonic and shallow, and its first level is the three lists of G1 plus
  the object under the caret.
- **Escape.** Insert to normal is one use; cancelling a pending command or
  dismissing an overlay is another. In normal mode with nothing pending,
  Escape does nothing. The command line's *Esc cancel* chips stay.
- **How much of vi.** The grammar, not the program: operators, motions, text
  objects, counts, marks and registers. No ex commands and no scripting
  language; `:` opens the command line, which is what ex was for.
- **Registers are shelf slots.** vi's `y` is kept as a key, not as a word:
  copying in a source buffer copies text, as a form with its printed form;
  copying in an output pane copies the object. Both land on the shelf (§6)
  with their provenance.
- **A non-modal alternative is a setting.** Bindings are settings, so an
  insert-only set with familiar chords exists for people who want it, the
  way Spacemacs keeps its holy mode. It gets the same leader and the same
  command line.
- **The screens rebind.** Every ⌘-chord on the screens becomes a leader
  sequence (§33). Interrupt moves under the leader too, and stays
  client-local so it works while the Worker is busy.

Two things the decision does not fix, and says so: modal editing is also
learned out of band, which is why the leader menu and the mode indicator
exist; and the vi layer is client work (G59). A modal layer over a browser
editor component is a known quantity rather than research, but it is not
free, and the component is registered in §27.

---

## 21. Search, navigation and completion

**G63. One search, several substrates.**
Text in the open buffer, text across the repository, and `apropos` over the
image are one command with a scope argument, not three tools. Results are
presentations grouped by where they came from, and a result from the image
knows whether it is a function, a variable or a class before you open it.

**G64. Replacement is a set of edits you can see.**
Replace-all produces the edits as presentations first and applies them on
confirmation; each is revertible on its own. Replace-here is the same thing
one at a time.

**G65. Navigation keeps a trail, like inspection.**
Every jump — edit definition, go to a caller, open a search result, follow a
citation — pushes onto one trail per activity, and back returns exactly.
This is G56's trail extended to the whole activity, and it is the answer to
"how did I get here" that Emacs's mark ring only half gives.

**G66. Completion is typed and asynchronous.**
What completes depends on what is being read: symbols in code, pathnames in a
pathname argument, commands in the command line, members of a member type,
anything of the presentation type currently wanted (G6). Completion is a
request to the image that may arrive late or not at all; the client never
blocks on it (G8).

**G67. Where is this open?**
The set of buffers and views an activity holds is a presented list, with each
entry's state (G62), reachable from the command line by name. It is not a tab
strip (G22) and it is not persistent chrome (G1).

---

## 22. Debugging beyond the break

The debugger (§7) covers what happens once execution has stopped. These cover
getting it to stop, and watching it while it runs.

**G68. Breakpoints are set on definitions, not lines.**
A breakpoint is an object attached to a function, a method, or a form within
one, and it survives recompilation because it follows the definition. Line
numbers are how a text editor thinks; the image has better nouns.

**G69. Stepping happens in the debugger you already have.**
Step into, over and out are restarts on the current frame, so §7's surface is
the stepping surface. Locals stay live objects while stepping; there is no
separate watch window because the inspector (G56) is already open beside it.

**G70. Trace output is presentations, not text.**
A traced call shows its arguments and values as objects, nested by call depth,
in the transcript. A trace is itself an object with verbs — untrace, show the
last twenty, trace callers too — and the screen-2 command `Trace` that reads a
function name is the front of this.

**G71. Profiles attribute time and space to definitions.**
A profile run is an object; its result is a presentation of definitions with
their share of time or allocation, each one clickable to its source, callers
and callees. Sampling uses the safepoint mechanism the port already has
(§13), so profiling does not need its own instrumentation.

---

## 23. Tests

**G72. Tests are definitions, and runs are objects.**
A test is presented like any other definition — edit, run, show its last
result — and a test run is a presentation carrying what passed, what failed,
and how long it took. Screen 14's `84 of 84, 2 h ago` is this object shown in
the system list.

**G73. A failing test is a break you can stand in.**
Running a test interactively does not swallow its condition into a report. A
failure lands in the debugger (§7) with the test's frame, its fixtures as
locals, and the assertion as the condition, so fixing it is the same act as
fixing anything else. Reporting is what happens when you choose to run the
whole suite non-interactively. A completed failure is then a report: always
inspectable, never resumable, because its execution state is gone. Its verb
is *rerun under debugger*, which runs the test again with the break enabled,
and the label says exactly that.

**G74. Tests know what they cover.**
The image can record which definitions a test exercised, so a changed
definition (G31) can name the tests that touch it and *run affected tests* is
one command.

---

## 24. Delivery and dependencies

This is where the conversation began: applications built with the thing.

**G75. Delivery is a snapshot plus a shell.**
A delivered application is an image snapshot (G51) — with the systems it needs
loaded and nothing else — wrapped in the client shell, minus the listener, the
compiler and the editor unless the application asks for them. No flattening or
ahead-of-time step is involved (§2); the browser compiles what the image ships.
`Deliver` is a command over a system, and its result is an object you can open,
size, and diff against the last delivery.

**G76. A delivered application keeps the debugger.**
An error in a delivered application is still a condition with restarts; what
changes is who is expected to answer. The application decides which restarts
its users see. The developer, connected to it (constraint 6), sees all of
them.

**G77. Dependencies are objects with provenance, like settings.**
Each dependency shows the version loaded, where it was pinned, and what
changed since — as screen 14 already shows `alexandria 1.4.0 · pinned`.
Updating one is a command whose result is a plan (G33) before it is a change.

**Decision needed:** the source of dependencies — a Quicklisp dist, an
Ultralisp feed, git submodules, or a lockfile of commits — and whether the pin
lives in the `.asd` or beside it. G77 holds whichever is chosen.

---

## 25. Session, host and identity

**G78. A page reload does not lose work, and unload is not how.**
The image runs in a Worker that dies with the page. Browsers do not reliably
deliver `unload`, so nothing here depends on it. Instead: editor text
persists continuously on the client as it changes; the image is checkpointed
at quiescent points (G51) on a timer and before any destructive command; and
the image surface (G50) shows what the latest checkpoint recovers and how old
it is. `pagehide` and `unload` are extra opportunities to checkpoint, never
the guarantee. A reload restores data — buffers, and the last checkpoint's
definitions and heap — not a computation that was running and not an open
debugger; it should feel like waking the machine with the desk as you left
it, and it does not pretend the machine never stopped. Whether a
`SharedWorker` can keep the image alive across a reload is worth measuring
(§31); the checkpoint path is required regardless.

**G79. The image has no ambient authority over the host.**
Every capability the image uses — a file on the user's disk, a network
request, the clipboard — is granted by a user gesture and visible while it
holds. The host proxy holds credentials (constraint 8); the image holds
grants it can show you. A push is the case that matters: constraint 8 keeps
the token out of the image but not out of its reach, so a push is granted by
a gesture the client makes and the image cannot synthesise — the user runs
the push command, or confirms one the image asked for — and the image's
request names what it would send. Fetch needs no such gesture, because it
writes nothing anyone else reads. An agent (§35) is a client under the same
rule: it holds grants the human can see, never a credential, and cannot
supply the gesture a push needs. This is constraint 2 and G36 from the other
direction: code never comes in over the wire, and the image never reaches out
on its own.

**G80. Identity is stated, once, where it applies.**
Commits carry the author the proxy is signed in as, and the status line says
who that is. Switching identity is a command; there is no account panel.

---

## 26. Reach

**G81. Every presentation is reachable without a pointer.**
Sensitivity moves with the keyboard as well as the mouse: next and previous
presentation, next of the wanted type during narrowing (G6), activate, and the
applicable-commands list (G7). G8 says pointing and typing are the same act;
this says pointing itself does not require a pointer.

**G82. A presentation announces what it is.**
Because every object on screen has a type and a set of verbs, a screen reader
can be told exactly that — "function, pop-record, 11 commands" — rather than
"text". That is what the model makes computable, which mainstream editors
cannot say; it is a prerequisite, not a delivery. Usable keyboard navigation,
focus order and screen-reader behaviour are tested in the prototype (§34),
including at increased text size, and the budget in §29 is the floor, not the
design.

**G83. A presentation can be dragged.**
Dragging one onto a pending argument, a pane, or another presentation is
pointing with a destination, and resolves through the same translators as a
click. CLIM defines this; the design should not lose it.

**G84. Output records export as drawings.**
A record replays to SVG or PDF as readily as to a sheet (G10.3's model of
replay), so a transcript, a diff, or a diagram can be handed to someone who
has no image. What leaves is a picture, never a live object.

---

## 27. Still undecided

Registered, with the question stated rather than a guess recorded.

- **Dependency source and pinning** (§24).
- **The client editor component** that carries the modal layer, the reader
  and the record tree (§20, G59). A decision about a dependency, made once,
  after the prototype (§34) has tried one.
- **Which agent harness comes first** (§35): the IDE as a server the
  vendors' own harnesses connect to, or a harness of our own that calls the
  model directly. The section recommends an order; the prototype decides.
- **Scope of the client-side reader** (G60): which of the standard reader
  syntax the client understands by itself, what it does with a reader macro
  it does not know, and whether it ever asks the image for a boundary.
- **A light variant of the visual system.** The screens are dark and the
  `theme` setting exists; the tokens have not been drawn for light.
- **Connecting to a remote image.** Constraint 6 makes it possible and G76
  needs it; the connection, its authentication and what the client shows
  about which image it is on are undesigned.
- **History depth and transcript growth.** `record-history-depth` exists as a
  setting; what happens at the limit, and how a long-running listener stays
  fast, does not.

---

## 28. Visual system

- **Two typefaces.** One for interface text, one monospace for code and data.
- **One ground, one panel, one divider.** Separation is a single pixel line;
  panels do not get borders, gradients or fills to distinguish them.
- **Two accents with fixed meaning.** Warm: *the object you are pointing at or
  have chosen*. Cool: *candidates matching the type being asked for*, and
  healthy status. A third hue appears only for error state, and only as a thin
  bar and a label.
- **De-emphasis is a colour, not an opacity.** Recessed text is recoloured to
  stay above the contrast floor; it is never faded below it. The current
  screens do fade below it in places (§33).
- **Shadow marks transience.** Only summoned surfaces cast one.
- **Motion is not decoration.** Nothing animates that does not correspond to a
  state change the user caused.

---

## 29. Budgets

- **Interaction:** no interaction may require a client↔image round trip per
  animation frame. Highlighting, scrolling, pointer documentation and drag
  feedback are client-local.
- **Latency:** one round trip per command or keystroke is the design target;
  batch the presentation stream rather than sending per-presentation messages.
  G7's per-context applicable set is one such round trip, at command start.
- **Contrast:** body text at 4.5:1 or better against its ground, including
  de-emphasised text; large text at 3:1.
- **Targets:** controls — buttons, chips, rows in a summoned list, the command
  line — at least 44 px on their smaller axis. Inline presentations are the
  size of the text they are: a symbol in a source pane is a target at text
  height, and that is the design, not an exception. The keyboard path (G81)
  is what makes those reachable without precision.
- **Semantics:** real buttons, links, inputs and labels, including in static
  mock-ups. Never a click handler on a `div`.

---

## 30. Non-goals and rejected alternatives

- **Emacs compatibility.** The model is borrowed; the vocabulary's opacity and
  the elisp ecosystem are not.
- **Per-window command loops.** Genera gave every window its own command area
  and paid for it in visual noise. One retargeting command line instead.
- **Tool windows you must already know about.** The LispWorks failure: the
  capability exists but there is no path from an object to it. Every verb is
  reachable from a noun.
- **An in-app window manager.** See G20.
- **Toolbars, ribbons, and authored context menus.** See G7.
- **A settings schema.** See G24.
- **A plugin API.** See G28.
- **A native mobile build.** Out of scope. With it go the ahead-of-time
  flattening of the compiler's output, the embedded-runtime fallback and the
  App Store questions that went with them.
- **Autosave as commits.** See G10.1.
- **Real-time collaboration.** Two people in one image at once is not a goal;
  git is the collaboration mechanism (§5), and G76's developer connection is
  one developer at a time.
- **Localisation.** The interface is English for now; the presentation model
  does not preclude it, and nothing here should be built to.

---

## 31. Open questions

1. **Heap ceiling.** Does a realistic image survive WebContent's memory limits
   and backgrounding? This decides whether the embedded-runtime fallback is
   needed at all. Measure first.
2. **Cold start.** Page load, module instantiation and image load, on the
   slowest target device.
3. **Per-context applicable sets.** G7 answers once per input context for
   every record on screen. Measure the size and latency of that answer
   against a large transcript history, and whether the at-rest set attached
   to each record is worth its wire cost.
4. **Client-side input editing.** How much of the input editor must move to the
   client before typing feels local, and what stays asynchronous.
5. **Version-log storage and retention** (G10.1): what the log costs per save
   on a large file, how long it is kept, and what survives a browser storage
   eviction with unpushed work in it.
6. **Clone persistence.** Where the local clone lives (OPFS or IndexedDB), how
   large a repository that supports, and how the working copy is reconstructed
   after an eviction.
7. **Felt interrupt latency.** Time-to-safepoint is bounded and measured by
   the port; what matters here is how long `⌘.` takes to bite in practice,
   and what the interface shows in the meantime.
8. **Interrupting a blocked thread.** A Worker waiting on host I/O through the
   Atomics mailbox or JSPI is not running Lisp and will not reach a poll. The
   port has a completion/cancellation path for that case; the interface needs
   to know which of its three actions applies to a thread that is waiting
   rather than computing.
9. **Reload persistence.** Whether a `SharedWorker` keeps the image alive
   across a page reload on the target browsers, and at what cost; the
   snapshot-on-unload path (G78) is required either way. G20's torn-off
   windows depend on the same answer.
10. **Definition-level history.** Git versions text; the system presents
   definitions. Mapping commits onto "this function last changed here" needs a
   source-range-to-definition mapping, and it is not free. Whether the
   Examiner earns it is undecided.
11. **The sample bit.** G39 asks the port for a pending bit that does not
   stop the thread, a shared sample record, and a current-function name at
   the safepoint slow path. Whether the port accepts that request, and in
   which stage, is the port's decision to record; until it does, G39 is a
   design and the heartbeat on screen 17 is a mock.
12. **Retention cost.** G9.1 bounds strong references to the transcript's
   window plus pins. Measure what a long listener session holds under that
   rule, and whether weak records outside the window cost more than they
   save.
13. **Model decoding.** How much of the model view (§35) a model needs per
   turn to act correctly, how often its commands fail validation, and
   whether the manifest alone is enough documentation or the protocol note
   has to be in context too. Measured with Fable and Codex on the §34 path.

---

## 32. Reference screens

The screens are committed in [ui-screens/](ui-screens/README.md), one PNG
per screen, numbered as below, rendered from the HTML source beside them.

1. At rest — the three surfaces; nothing marked but the pointer's object.
2. Type-directed narrowing — `Trace` wants a function name.
3. Verbs from nouns — applicable commands for a class.
4. Files as objects — versions, staleness, multi-selection into a command.
5. The shelf — objects with provenance; inserting keeps identity.
6. Break, fix, resume — condition, restarts, frames, locals, source.
7. The image explains itself — generated documentation, system sources.
8. Named layouts — arrangements as objects.
9. Tear off to the host — the only window frames in the system are the OS's.
10. Compare without windows — comparison as a command.
11. Views live inline — tables, replayed records, process lists in place.
12. Settings with provenance — generated editors, layered values.
13. Divergence as a break — a rejected push as a condition with restarts.
14. Systems, not directories — modules in dependency order, and what only the
    image knows it has changed.
15. The definition and its plan — the .asd as source, beside the graph, the
    ordered plan and the findings derived from it.
16. Foreign material — a PDF manual in a pane, and a citation crossing back
    into the image.
17. Interrupting a computation — the running computation as an object, with a
    heartbeat and three graduated ways to stop it.
18. Activities — six contexts, one image, and where a process claims attention.
19. Warnings as presentations — anchored, walkable, mutable with a reason.
20. The inspector keeps a trail — descend in place, step back.
21. A dialog from the argument types — six arguments, generated editors.
22. The image, and its snapshots — headroom, Workers, and what a restart
    recovers.
23. Undo, honestly — four substrates, four reversals, one with none.

---

## 33. Corrections owed to the screens

The screens are worked examples, so where they disagree with the text or
with each other the disagreement is a defect in the example. These are the
ones found in the 18 September review. The text above is already corrected;
the screens are not.

**One fixture, one story.** The screens share a fixture (the `clim-web`
system, the `runner` class, the scan-limit setting) and should tell one
consistent story about it.

- Screens 12 and 23 put the change to `*scan-limit*` in the project settings
  file. Screen 14 marks the same variable "in no file, set in the listener".
  These are two of G31's three states, and the screen that exists to show the
  distinction is the one that gets it wrong. Pick one; screen 14 is the one to
  change.
- Screen 4 names `7b20e14` "Validate records before replay" and shows the
  branch two ahead. Screen 13 gives that title to `9c1e77a`, makes `7b20e14`
  the common ancestor, and shows four ahead. Screen 22 pins a snapshot
  labelled "clean load, a3f1c9d" from yesterday evening while screen 4 dates
  that commit two hours ago.
- Screen 6 offers "Abort — kill process runner-2". G41 defines abort as
  unwinding to the activity's command loop; killing the process is a
  different verb and should be listed as one.
- Screen 17 titles the third action "Force quit the runner" and its body
  says it terminates the Worker and loses the image. G41 says force quit ends
  the whole image, and a runner is one Worker, not the image. Retitle it
  "Force quit the image", and change "restart would resume from it" to
  "restore", per G51.
- Screen 17's heartbeat panel shows the port supplying what G39 asks for. It
  is a mock until open question 11 is answered.

**Changes the second revision implies.** These follow from Codex's review
and the §20 decision, and they touch most screens. They have been applied:
the screens in `ui-screens/` are the redrawn set, kept as HTML source and
rendered from it, and every item below and every fixture discrepancy above
is fixed in them. The list stays as the record of what changed.

- Every ⌘-chord becomes a leader sequence: screen 3's ⌘E and ⌘D; screen 8's
  ⌘1 to ⌘5 and ⌘⇧L; screen 9's ⌘⇧T; screen 12's ⌘E and ⌥Y; screen 17's ⌘.
  and ⌘⇧.; screen 18's ⌘E, ⌘D, ⌘B, ⌘L, ⌘T, ⌘K and ⌘N, and its footer "⌘ and
  a letter" becomes "space and a letter". ⌘Z on screen 23 may stay for
  insert mode; normal mode has `u`.
- Screen 1's documentation line says "click edit definition" over an
  editable buffer. Under G5 a click places the caret; the line should read
  the modified-click and the normal-mode verb instead.
- Every screen with an editable pane (1, 2, 3, 9, 10, 15, 19) shows the editor's
  mode in the pane header, beside the buffer state (G62).
- Screen 3 gains the declared explanation and consequence lines for each
  command (G7), which the menu now has room for.
- Screen 5 is retitled *Shelf*, its footer verbs lose *yank*, and its "⌥Y
  cycles" becomes a leader sequence. Screen 16's "yank the text" becomes
  "copy the text".
- Screen 6 lists only restarts the program established. The fixture's loop
  establishes none of *Skip this record and continue the loop*, so either
  the fixture gains a `with-simple-restart` or the row goes. "Abort — kill
  process" is not G41's abort and is relabelled *Kill process runner-2*.
- Screen 7's *callers* heading becomes *known callers*, with the source of
  each row (G16).
- Screens 12 and 21 make the numeric field primary and the slider a
  supplement (G25).
- Screen 13's "What the image knows" gains "in this image" and loses any
  reading that the other branch's symbol is wrong (G10.4).
- Screen 22's snapshot labels use *restore*, not *resume* (G51), and the
  surface gains a row for pinned objects (G9.1) and for the age of the last
  checkpoint (G78).
- Any presentation older than the retention window, on any screen, shows
  the expired state of G9.1; screen 11's transcript is the natural place to
  show one.

**Contrast.** §29 requires 4.5:1 for de-emphasised text. Measured against
the rendered screens, taking the brightest pixel of each run of text so the
figure is an upper bound:

| Screen | Text | Measured |
| --- | --- | --- |
| 5, the shelf | provenance line "from Transcript · 2 min ago" | 4.1 |
| 12, settings | layer column "default" | 4.1 |
| 4, files | "19 earlier commits" | 4.3 |
| 17, interrupt | footnote under the actions | 5.0 |
| 1, documentation line | "— function, clim-web" | 5.2 |

The recessed grey used for provenance, layer names and collapsed history
measures about `#747783`, which gives 4.1 on the panel ground `#131419` and
3.2 on the highlighted ring row. Lifting it to about `#8e939d` gives 6.0 on
the panel and 4.6 on the highlighted row, clearing the floor everywhere it is
used. The three rows under 4.5 are the same token; one change fixes all
three.

---

## 34. The first prototype

Static screens have said what they can. The next evidence comes from one
working path, built before any second screen is drawn, and used to decide
which of this document's absolute rules improve daily work and which are
only preferences:

> edit a definition → evaluate it → inspect its result → hit a condition →
> choose a restart the program really established → save the changed
> definition and see it move between G31's states.

The path is walked three ways: with the pointer, keyboard-only in normal
mode and through the leader, and with a screen reader at twice the text
size. It is walked with the image busy, so the client's liveness under
constraint 4 is felt rather than asserted.

The prototype does not wait for the port. The wire carries objects and events
only (constraint 2), and constraint 6 already says the same design serves a
remote image, so the client is built against native CCL over a socket, with
the same presentation stream and the same event stream, and moves to the
Worker transport when the port has conditions and restarts. Until then the
busy-Worker case is simulated on the socket, and the prototype says so. What
it measures is discoverability, comfort, the retention rule of G9.1 in a long
session (§31, item 12), and the accessibility floor of §29.

The same path is walked a fourth way, by a model (§35): given the model view
of the activity and the command manifest, and nothing else, it edits the
definition, evaluates it, meets the condition, chooses the restart and
writes the file, with a person watching from another activity. What that
measures is §31, item 13.

---

## 35. The agent as a client

An agent — Fable, Codex, or whatever comes next — is a second client of the
image. It is not a plugin, a chat panel, or a feature. Constraint 2 says the
wire carries objects and events and never code; constraint 6 says the same
design serves a remote client. An agent is that remote client without a
renderer, and every rule in this document already applies to it. What this
section adds is the four things an agent needs that a page does not: a view
of the stream it can read, a way for its text to become commands, a place
to live, and the limits on what it may do.

**G85. The agent reads the model view, not the pixels and not the records.**
The output-record tree is for drawing. A model does not need geometry; it
needs the objects. So the stream has a second projection beside the one the
page renders: the **model view**, a textual rendering of an activity in
which every presentation appears once, as its id, its presentation type, its
printed form, and — where it has one — its provenance and state (G9.1). The
transcript's text appears as text. Nothing is summarised by a person and
nothing is described in prose: the view is generated from the same records
the page draws, so it is never stale and never editorialised. It is written
in S-expressions, because the reader is a model that reads Lisp and the
objects are Lisp objects, and because a person can read it too. Two rules
keep it inside a context window: the view is windowed like the transcript
(G9.1), and an object's interior is not in it. Descending into an object is
a command (*inspect* by id, G56), so the inspector's trail is the model's
pagination.

**G86. Text becomes action through the command table, and nowhere else.**
A model answers in text. Only one kind of text acts: a structured command,
in the shape the command line already reads — the command's name and its
arguments, where an argument is a presentation id or a typed literal. The
harness (G87) validates every such command against the command table as the
command line would validate a typed one: the command must be applicable in
the current context (G7), each id must name a live presentation (G9.1), each
literal must read as its declared type. A command that fails validation is
not executed; the failure goes back to the model as a condition, with the
reason, and the model tries again. Everything else the model says is a
message, shown in the activity's transcript to whoever is watching. No text
from a model is ever evaluated as code. When the model wants to evaluate a
form, it invokes *evaluate* with the form as a string argument; the image
reads it, compiles it and runs it in the agent's own process, under the same
interrupt (G38), conditions (G13) and restarts (G14) as anything a person
types. A condition the model raises lands in the model's debugger, and its
restarts arrive in the next model view as commands it may invoke.

**G87. The harness is a program, not a chat loop.**
Between the model and the image sits a small program that does five things
in order, every turn: project the model view of the agent's activity;
attach the applicable-command manifest, generated by G7 for that view, with
each command's declared explanation and consequence; send both to the model
with the person's prompt if there is one; parse the reply into commands and
messages; execute the commands through the command line, one at a time,
returning each result's presentations into the next view. The manifest is
the tool list, regenerated each turn, so documentation stays short: a
one-page protocol note says what a model view is and what a command looks
like, and the manifest says what can be done right now. The consequence
field gates execution: a command whose declaration names a consequence in
G58's list of what cannot be taken back is not executed until the person
confirms it, and a snapshot (G51) is taken before any command that can
destroy the image.

**G88. The person talks to the agent in an activity, with objects.**
An agent lives in its own activity (G42): its own process, panes, layout
and history. Its transcript is the conversation. The activity's input line
takes a prompt the way a listener takes a form, and a prompt is a message
to the model with the current model view attached. Pointing while typing
works as it does for any argument (G8, G9): a presentation the person points
at or has selected goes into the prompt as the object, by id, not as pasted
text, so "fix this" carries the frame, and "these three" carries the three
files. From any other activity, *Ask agent* is a command that takes a string
and an optional object set and switches nothing: the answer arrives in the
agent's activity and claims attention through the activity list (G44),
never by taking the screen (G46). A person can also run the agent's commands
by hand: every command the model issued is in the history (G53), with its
arguments as live objects, and can be edited and re-run.

**G89. What the agent may do is what the person granted, shown while it
holds it.**
An agent is a client that can evaluate anything, so constraint 8 and G79
apply without exception: no credential, no push without a person's gesture,
and every capability it holds — which files, which systems, whether it may
compile into the image or only propose — is a grant the person made and can
see and revoke in the image surface (G50). Its changes carry its name in
G31's three states, its commits carry its name as author (G80), and the
things it changed in the image only are visible in the same list as anyone
else's, so nothing it did can sit unnoticed.

**Can Fable and Codex decode this?** Yes, and the shape is not speculative:
it is how those models already work in their own harnesses, which feed them
tool results as text and read commands back as structured calls. The model
view is easier to read than a shell transcript, because every object in it
is typed, addressed and provenanced, and the manifest is easier than a tool
schema written by hand, because it is generated from the image and cannot
drift. The failure modes are known and the design meets each one: an
invented id is rejected by validation and reported; an ambiguous printed
form is never the address, the id is; a too-large view is windowed and
descended into rather than dumped; a runaway evaluation is interrupted at
the next safepoint; a wrong command is one command in the history, reverted
per substrate (G57). What is not known is the budget — how much view a model
needs per turn, and how often it fails validation — and §31, item 13,
measures it.

**Two ways to build it, in order.** First, the IDE as a server the vendors'
harnesses connect to: the model view as resources, the manifest as tools,
G86's validation and G87's gates enforced on the server side. This gets
Fable and Codex working with the harnesses they already have, at the cost
that those harnesses also carry their own file and shell tools, which bypass
the object model and must be disabled or sandboxed for the session. Second,
a harness of our own that calls the model directly, which owns the whole
loop and can hold the model to the command table alone. The first proves the
model view; the second is the product. The order is registered in §27.

**What not to do.** No screenshot or DOM agents: the model view exists so
nobody needs them. No agent API beside the command table: a verb a model can
invoke that a person cannot discover breaks G7 in both directions. No
autonomy over the irreversible: G58's list is the list of what an agent
asks about. And no prose documentation of the objects: the manifest and the
model view are generated, and a document about them would be the stale
documentation §8 was written to abolish.

