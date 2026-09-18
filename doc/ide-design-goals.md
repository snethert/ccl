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
   image decides what that means.
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

**G32. Module state is per module, not per repository.**
Loaded, compiled, stale against its source, and the commit it was built from
are facts about a module, shown on the module. A system knows how to bring
itself up to date without the user tracking which files changed.

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

## 13. Visual system

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

## 14. Budgets

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

## 15. Non-goals and rejected alternatives

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

## 16. Open questions

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
7. **Definition-level history.** Git versions text; the system presents
   definitions. Mapping commits onto "this function last changed here" needs a
   source-range-to-definition mapping, and it is not free. Whether the
   Examiner earns it is undecided.

---

## 17. Reference screens

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
