# IDE Design Goals

Status: draft. Companion to `doc/stream-spec.md`.

This document records the design decisions taken for the CLIM-based IDE and
the applications built with it, and states them as goals that can be checked
against an implementation. It is written to be argued with: every goal is
phrased so that a screen either satisfies it or does not.

A set of twelve reference screens accompanies this document. Where a goal
names a screen, that screen is the worked example.

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

1. **Thin client, thick image.** The front end — JavaScript in the page —
   renders presentations and captures keystrokes, pointer events and commands.
   Everything else happens in CCL running in WASM.
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
   cheap enough that per-command traffic is free. The real hazard is that the
   image is single-threaded and will sit in a long compile or a collection
   while the user is still moving the pointer. The interface must stay live
   through that, which is why the next constraint exists.
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
8. **The host proxies git traffic, because the sandbox runs user code.** The
   image evaluates whatever the user writes, so it must never hold a
   credential: a token in page context is readable by any form typed into the
   listener. Fetch and push therefore go out through a host-side proxy holding
   the credential, and the image can only ask for a transfer, never authorise
   one. That the smart-HTTP endpoints also send no CORS headers is a second,
   weaker reason for the same arrangement. The cost is deliberate and worth
   naming: the web deployment is not a static page — it needs a server, and
   that server is an auth surface.
9. **Page and worker share memory, or nothing can be interrupted.** The
   interrupt flag and the heartbeat (§13) live in a `SharedArrayBuffer`,
   because a worker in a tight loop never reaches its message queue. That
   requires cross-origin isolation, so the server of constraint 8 must also
   serve the COOP and COEP headers. Without it there is no way to stop a
   running computation short of destroying the image.

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
Anything else is summoned and dismissed.

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

**G5. One thing is marked at a time, and it is the thing under the pointer.**
Highlighting is latent and singular. The documentation line reads that one
object: what it is, and what the click, modified-click and right-click
gestures will do to it.

**G6. Type-directed narrowing is the primary discovery mechanism.**
When a command wants an argument of a presentation type, every presentation of
that type on screen lights up and everything else recedes. On-screen and
in-image match counts are shown. This replaces documentation with computation
and is the single largest departure from mainstream editors.

**G7. Applicable commands are computed, never authored.**
Pointing at an object yields the commands that apply to it, grouped by where
they come from (the object, its class, its package), with counts that are real
facts about the image. There is no hand-written context menu anywhere in the
system. For a remote client, the applicable-translator set is computed when
the record is sent and attached to it, so highlighting never requires a round
trip.

**G8. Pointing and typing are the same act.**
A pending argument accepts a pointer gesture or typed text interchangeably.
The input editor runs on the client; completion is an asynchronous request,
never a synchronous one.

**G9. Selection feeds the command line.**
Multiple selected objects are an argument like any other; commands take object
sets, not just single objects.

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
| Ring entries | insert object, insert printed form, drop |
| Systems, modules, dependencies | compile, load, plan, add component, add dependency |
| Documents and citations (§12) | open at page, cite, attach to a definition, yank the text |

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
is actually bound, and how many callers it has — so resolving a conflict is
not guesswork over text.

*Reference: screens 4, 5, 6, 10, 11.*

---

## 6. The ring

**G11. The ring holds objects, not text.**
Entries are live objects with their types and a rendered view — a hash table
shows entries, a condition shows its report, a record shows itself. Each entry
records its provenance: which pane it came from and when.

**G12. Insertion preserves identity.**
`↩` inserts the object; `⇧↩` inserts its printed form. The insertion point
shows which one is about to land, as a chip rather than as text.

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

**G16. Documentation is generated from the image.**
Signature, argument types, methods, callers, source location and compilation
time are facts read out of the running system, not prose maintained beside it.

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

**G21. Ad hoc comparison is a command, not an act of window arrangement.**
`Compare Versions` takes two objects and produces a two-pane layout. Each
difference is a presentation with its own verbs.

**G22. Prefer an inline view to a new surface.**
Most historical window-need is only "somewhere to put a view of this object".
A table, a replayed record at scale, a process list — all are drawn in place
in the transcript. A new pane or window must earn itself against this.

**G23. Overlays are summoned and dismissed.**
The ring, the layout picker and the applicable-command list appear over the
work area and leave no residue. They are the only place shadow is used.

*Reference: screens 8, 9, 10, 11.*

---

## 10. Configuration

**G24. A setting is a variable with a declared type, a default and a
docstring.** There is no configuration schema and no configuration file
format.

**G25. Setting editors are generated from types.**
An integer range yields a range editor, a member type yields a choice, a
pathname yields a pathname reader — using the same machinery that reads a
command argument. No settings pane is hand-built.

**G26. Values show their provenance.**
Every setting displays which layer it came from (default, user, project,
session), what it overrode, and the file and line of each layer. Each layer is
revertible in place. "Why is it this?" is answered without going to look.

**G27. Two files, one of them ours.**
Defaults load first, then a machine-written settings file, then the user's own
init file. Hand-written code always wins because it loads last. The
machine-written file is never jointly owned.

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
carrying what it is, where the change came from (editor or listener), when,
and which of three states it is in:

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
the selected text — as a presented object that can be yanked into the ring,
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

**G38. Every computation can be interrupted.**
The compiler emits a safepoint poll at function entry and at every loop
back-edge. The client raises a flag in shared memory; at the next poll the
image signals an `interrupt-request` condition and enters the debugger with
the stack intact. An interrupt is an ordinary condition with restarts, not a
mode — so §7 already describes what happens next.

**G39. The poll publishes a heartbeat.**
Each safepoint also writes what is running, for how long, and the allocation
and collection counts into that shared memory. The client can therefore give a
live account of a busy image without the image answering a message: a blocked
system shows facts, not a spinner, and the time since the last safepoint says
whether it is answering at all.

**G40. A running computation is an object.**
It is presented in the command line while it runs and carries its own
applicable commands, so stopping it needs no special affordance — it is G7
applied to a process.

**G41. Three graduated actions, and the destructive one states its cost.**
*Interrupt* at the next safepoint; *abort* to unwind to this activity's
command loop; *force quit the runner*, which terminates the worker and loses
the image. The third names exactly what will be lost — the definitions that
exist in no file, the history — and when the last snapshot was taken. Only the
third works when the safepoints stop answering, which is why it exists.

**Cost to measure:** the poll is a load and a branch per back-edge. Its
overhead is an open question (§18), not a free lunch.

---

## 14. Activities

**G42. An activity is a context with its own process, panes, layout and
history.** Created on demand, switched with a keystroke, and preserved exactly
as left. Layouts (G19) rearrange panes *within* an activity; they do not give
you a second project, a second listener, or a debugger you can step away from.

**G43. Activities share one image.**
They are contexts, not sandboxes: a definition changed in one is changed for
all, which is the Lisp Machine's arrangement and the useful one. Isolation, if
it is ever wanted, means a second image, never an activity.

**G44. The activity list is where attention is claimed.**
A break, a finished run, or output written while you were elsewhere marks its
activity in the list. A process that needs you becomes visible without
stealing the screen — which is the structure §15.1 needs to hang a
notification policy on.

---

## 15. Not yet addressed

Lisp Machine properties this design wants and does not yet have. These are
gaps, not rejections: nothing here has been argued against. Two former
entries — interrupting a computation, and activities — became §13 and §14.

**15.1 Notifications and background attention.** A process that breaks,
finishes, or wants to print while its pane is not on screen. Genera posted a
notification, and output to a hidden window was a decision the window made
(permit, notify, expose), never silently lost. G15 halts one process without
stopping the system, but nothing carries that break to the user, and nothing
says what happens to output written to a pane the current layout does not
show.

**15.2 Compiler warnings as presentations.** The design never says where a
warning goes. Compilation produces conditions about specific source ranges,
and they should be presentations anchored there with verbs — go to it, explain
it, mute this one — and walkable as a set, not a log that scrolls past. This
is the natural companion to G31's changed-definition list.

**15.3 Image snapshot and resume.** The band. Save the heap, come back to it.
In a browser this is both feasible — persist the linear memory — and
load-bearing: screen 14's "in the image only, lost on restart" stops being a
hazard the moment the image survives a restart. It interacts with the wasm32
ceiling and with storage eviction (§17).

**15.4 Command history as re-executable objects.** The ring holds objects
(G11); commands are not in it. Past commands should be presentations you can
edit and re-run, with their arguments still live objects rather than printed
text.

**15.5 Generated dialogs for whole argument sets.** G25 derives an editor for
one setting from its type. CLIM's `accepting-values` does the same for a set
of typed values at once, which is the right answer for commands with more
arguments than a single command line carries comfortably. Stated for settings,
not yet for commands.

**15.6 The inspector as a place with history.** Inspection verbs exist and
views render inline, but there is no navigable inspector: descend into a slot,
go back, keep the trail. Deep exploration without a trail loses its way.

**15.7 Undo, and its honest limits.** No goal addresses it. Three substrates
behave differently: editor text is undoable; image state largely is not,
though G31's record of changed definitions supports *revert to loaded*; git
has revert. The design should say plainly which is which rather than implying
a single undo stack.

**15.8 Live system health.** Peek showed processes, storage and network,
updating continuously. With a hard heap ceiling and a single worker, headroom,
collection activity and worker liveness are facts the user needs before they
become failures.

---

## 16. Visual system

- **Two typefaces.** One for interface text, one monospace for code and data.
- **One ground, one panel, one divider.** Separation is a single pixel line;
  panels do not get borders, gradients or fills to distinguish them.
- **Two accents with fixed meaning.** Warm: *the object you are pointing at or
  have chosen*. Cool: *candidates matching the type being asked for*, and
  healthy status. A third hue appears only for error state, and only as a thin
  bar and a label.
- **De-emphasis is a colour, not an opacity.** Recessed text is recoloured to
  stay above the contrast floor; it is never faded below it.
- **Shadow marks transience.** Only summoned surfaces cast one.
- **Motion is not decoration.** Nothing animates that does not correspond to a
  state change the user caused.

---

## 17. Budgets

- **Interaction:** no interaction may require a client↔image round trip per
  animation frame. Highlighting, scrolling, pointer documentation and drag
  feedback are client-local.
- **Latency:** one round trip per command or keystroke is the design target;
  batch the presentation stream rather than sending per-presentation messages.
- **Contrast:** body text at 4.5:1 or better against its ground, including
  de-emphasised text; large text at 3:1.
- **Targets:** interactive elements at least 44 px on their smaller axis.
- **Semantics:** real buttons, links, inputs and labels, including in static
  mock-ups. Never a click handler on a `div`.

---

## 18. Non-goals and rejected alternatives

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

---

## 19. Open questions

1. **Heap ceiling.** Does a realistic image survive WebContent's memory limits
   and backgrounding? This decides whether the embedded-runtime fallback is
   needed at all. Measure first.
2. **Cold start.** Page load, module instantiation and image load, on the
   slowest target device.
3. **Translator precomputation cost.** Attaching applicable-translator sets to
   every record has a size cost on the wire; measure against a large history.
4. **Client-side input editing.** How much of the input editor must move to the
   client before typing feels local, and what stays asynchronous.
5. **Version-log storage and retention** (G10.1): what the log costs per save
   on a large file, how long it is kept, and what survives a browser storage
   eviction with unpushed work in it.
6. **Clone persistence.** Where the local clone lives (OPFS or IndexedDB), how
   large a repository that supports, and how the working copy is reconstructed
   after an eviction.
7. **Safepoint overhead.** What a poll per function entry and loop back-edge
   actually costs on representative Lisp code (G38).
8. **Definition-level history.** Git versions text; the system presents
   definitions. Mapping commits onto "this function last changed here" needs a
   source-range-to-definition mapping, and it is not free. Whether the
   Examiner earns it is undecided.

---

## 20. Reference screens

1. At rest — the three surfaces; nothing marked but the pointer's object.
2. Type-directed narrowing — `Trace` wants a function name.
3. Verbs from nouns — applicable commands for a class.
4. Files as objects — versions, staleness, multi-selection into a command.
5. The ring — objects with provenance; inserting keeps identity.
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
