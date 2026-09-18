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
because several of the goals below only make sense in their light.

1. **Thin client, thick image.** The front end — JavaScript in a browser,
   Swift on iOS — renders presentations and captures keystrokes, pointer
   events and commands. Everything else happens in CCL running in WASM.
2. **The wire carries objects and events, never code.** No streamed value is
   ever evaluated by the client: no handler thunks, no computed layout
   expressions. Gestures identify a presentation by id and send it back; the
   image decides what that means. This keeps the client simple and keeps the
   iOS build inside App Store rule 2.5.2 without argument.
3. **The image runs inside WebKit.** In a browser that is the page; on iOS it
   is a WKWebView — offscreen when the front end is native. WebKit's content
   process holds the JIT entitlement, so dynamic compilation stays available
   and no flatten/AOT step is required. Embedding a standalone WASM runtime in
   the app process is the fallback path, and only then does ahead-of-time
   translation (wasm2c) become necessary.
4. **Crossings are expensive; frames are not.** A WKWebView round trip is
   roughly 0.5–2 ms. One crossing per keystroke or command is free. One
   crossing per animation frame is not.
5. **The client holds the output-record tree.** Repaint, scroll, pointer
   highlighting and drag feedback are local operations. Only the resulting
   command crosses.
6. **The same design serves a remote client.** CLIM's port/sheet/medium seam
   is where the transport goes; incremental redisplay is already a diff
   algorithm. The two places the classic design assumes locality — pointer-
   motion translator testing, and the input editor — are addressed in G7 and
   G8.

7. **Version storage is a repository, not a file system.** History comes from
   git, hosted on GitHub. The image holds a local clone so that editing,
   comparing and browsing history work offline and at pointer speed; network
   access is limited to fetch and push. Since the image runs in WebKit with no
   local file system, the clone is persisted in browser storage.
8. **The host proxies git traffic; the sandbox never talks to GitHub.** Page
   context cannot reach the smart-HTTP endpoints — they send no CORS headers —
   so every fetch and push goes out through the host: a custom scheme handler
   backed by the native HTTP client in an app, a server-side proxy in a pure
   browser deployment. Credentials live with the proxy, in the Keychain or on
   the server, and are never handed to the sandbox. The image asks for a
   transfer; it does not hold the means to authorise one.

**Measured risks, not design questions:** WebContent process memory and jetsam
behaviour with a realistic Lisp heap; cold-start time (page load, instantiate,
image load). Both are to be measured early with a real image, and both can
force the embedded-runtime fallback.

---

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

**G10.1. Working versions are continuous.**
Git only records history when you commit, but the Lisp Machine's value came
from every save being recoverable. Saves therefore write to a per-session
working ref — a shadow branch the user never sees in their history — which an
explicit commit promotes. "Compare with previous" always has something to
compare against, and the published history stays clean.

**G10.2. History is a graph, not a stack.**
A file's versions belong to branches. A version presentation carries its
commit, branch and author, and the listing shows the current branch's history
with the others reachable, never flattened into a single numbered sequence.

**G10.3. Git objects are presentations like any other.**
Commits, branches, tags and pull requests are presented objects with computed
verbs (show diff, check out, revert, blame, compare, merge, open review). They
enter the system through G7, not through a separate version-control tool.

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

## 11. Visual system

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

## 12. Budgets

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

## 13. Non-goals and rejected alternatives

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
- **A flatten/AOT build step for the IDE.** Unnecessary while the image runs
  inside WebKit; kept in reserve for an embedded-runtime target only.

---

## 14. Open questions

1. **Heap ceiling.** Does a realistic image survive WebContent's memory limits
   and backgrounding? This decides whether the embedded-runtime fallback is
   needed at all. Measure first.
2. **Cold start.** Page load, module instantiation and image load, on the
   slowest target device.
3. **Translator precomputation cost.** Attaching applicable-translator sets to
   every record has a size cost on the wire; measure against a large history.
4. **Client-side input editing.** How much of the input editor must move to the
   client before typing feels local, and what stays asynchronous.
5. **Multi-scene behaviour on iPad** for the tear-off path (G20).
6. **Clone persistence and sync.** Versioning is git on GitHub (G10). Open:
   where the local clone lives in each target (OPFS, IndexedDB, native file
   system), how large a repository that supports, and what happens to unpushed
   working refs when browser storage is evicted.
7. **Working-ref hygiene.** How long per-session working refs (G10.1) are kept,
   whether they sync to the remote at all, and how they are garbage collected.

---

## 15. Reference screens

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
