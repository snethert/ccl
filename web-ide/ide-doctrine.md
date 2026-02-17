# The Definitive Browser-First CL IDE: A Concrete Vision

## Doctrine Scope and Precedence
This document defines interaction, capability, and system behavior for the IDE.
Visual presentation, motion, typography, and spatial rules are governed by `web-ui/ui-doctrine.md`.
If the two documents appear to conflict:
- IDE Doctrine wins for interaction semantics and tool behavior.
- UI Doctrine wins for visual form, motion, and spatial presentation.

## Rendering Model (Hybrid, Deliberate)
This IDE uses a hybrid rendering model:
- Text-heavy surfaces (Editor, REPL input, documentation panes) use the DOM backend for IME, selection, clipboard, and accessibility.
- High-density visuals and custom instruments use canvas/WebGL (graphs, inspectors, timelines, visualizations).
- All backends must consume the same theme tokens and spacing metrics to preserve a single visual language.
- DOM usage does not imply OS-native appearance; the UI Doctrine still governs visual form.
- Clipboard UX includes required multi-item history with deterministic history-paste behavior.

## Core Principles

### 1. One Mental Model: Workspaces Contain Live Instruments
A workspace is a small number of panels: Editor, REPL, Inspector, Problems (compile/runtime), Debugger (appears only when needed).
Everything else is a mode or lens inside these, not new windows.
Outcome: less clutter than Allegro/LispWorks, while preserving power by nesting capability instead of spawning chrome.

### 2. Presentation-Based UI, Modernized
Take the Genera idea ("things on screen are typed objects") and render it with contemporary presentation rules.
Every value in REPL output is clickable/hoverable. Click opens the Inspector focused on that value.
Lists, hash-tables, objects, conditions, restarts render with progressive disclosure: summary first, expand on demand.
Actions are attached to objects (inspect, trace, describe, find callers, jump to source, pin, watch).
This directly inherits the best part of Dynamic Windows without inheriting the dated surface.

### 2.1 UI Doctrine Alignment (Visual System Requirements)
All IDE surfaces MUST conform to the UI Doctrine, specifically:
- Shallow physicality with a small number of planes and restrained shadows.
- Motion that explains state changes and can be suppressed.
- Typography-first hierarchy (text carries meaning before icons).
- Density with disciplined whitespace, avoiding gallery-style layouts.
- Dark mode as a primary design target, not a post-process.
- OS neutrality: the UI belongs to itself, not the host OS.

These constraints apply to every instrument: Editor, REPL, Inspector, Debugger, Problems, and Search/Command Palette.

### 3. Progressive Disclosure as Law
Commercial IDEs lead with tool inventories. Lisp scares people because it looks like an aircraft maintenance hangar.
Rules:
- The default workspace shows only the four core instruments.
- Advanced instruments appear only via search/command palette, context menus, or "More..." drawers.
- New users are never shown the full tool universe at once.
This is how you beat LispWorks' "podium of everything" problem.

### 4. Two Interaction Tracks: Mouse-Safe and Keyboard-Fast
You can fully embrace Emacs bindings in chosen panes, without making Emacs mandatory.

Mouse-safe track (non-expert friendly):
- Big obvious "Run Form", "Run Defun", and "Compile File" affordances.
- Right-click context menus on symbols/values: "Go to definition", "Find references", "Macroexpand", "Inspect result".
- Breadcrumb navigation everywhere: "You are here: package -> file -> defun -> local binding".

Keyboard-fast track (expert):
- A keybinding layer per pane: Editor can be Emacs/Spacemacs-like; REPL can be readline-like; Debugger can be single-key.
- A command palette that exposes the same commands as keybindings, so mouse users can learn by searching verbs.
Result: keyboard users remain lethal, mouse users remain safe.

### 5. The Debugger Is the Product
Genera's "restart menu" safety is the emotional core you want: productive, happy, safe.
Design it as:
- A calm Debugger panel that slides in (does not spawn a new universe of windows).
- Clear top line: condition summary plus "what was attempted".
- Restart buttons are primary UI, not buried.
- Stack frames are navigable: click to view locals, click to jump to source, click to inspect any local value.
- "Time travel" basics: keep the last N evaluations, their results, and their warnings, so users can backtrack mentally.

### 5.1 Stepper and Breakpoint Contract
Stepping is part of the debugger experience, not a separate product surface.

The stepper should combine the strongest patterns from LispWorks, Genera/Open Genera, and Franz/Allegro:
- Expression-level breakpoints in source views, including explicit entry/exit semantics.
- Closing-paren placement maps to "break on return" and surfaces return values prominently.
- A dual-lane stepping model:
  - Source lane for form-level `into`/`over`/`out`.
  - Low-level lane for runtime-level stepping with explicit handoff.
- A slide-point model for ambiguous stopping points, so users can move to the nearest valid source-correlated stop without losing context.
- Restart-frame stepping from debugger frames, preserving restart-first recovery.
- In-step REPL access with lexical context, auditable actions, and clear safety affordances for value overrides.

This doctrine defines interaction and UX requirements only.
The exact compiler/runtime source-mapping representation is intentionally deferred to a follow-up design step.

### 6. The Inspector Is the Universal Pivot
Make the Inspector the place where "Lisp feels like a system" instead of a terminal.
Capabilities:
- Structured views per type (arrays, hash tables, CLOS objects, conditions).
- Pinned watches: values that update after each evaluation.
- Safe edit-in-place: you can modify slots/entries, but changes are clearly staged and undoable.
This preserves the "integrated tool invocation on objects" that Allegro emphasizes, but without a zoo of separate tools.

### 7. Browser Capabilities to Exploit (Instead of Pretending You're a Desktop IDE)
- Hyperlink navigation: every symbol, definition, doc reference, and file is a linkable address.
- Instant search-as-navigation: fuzzy symbol search across loaded image and project.
- Persistent sessions: workspace layout, REPL history, and pinned watches saved as "worldlets".
- Rich rendering: charts for profiler output, collapsible trees for objects, inline diffs for recompilations.
- Sandboxed processes: background compilation, linting, indexing without blocking interaction.

### 8. Opinionated Defaults, Escape Hatches for Experts
Defaults that reduce fear:
- One command to "Start a Project": create package, ASDF, tests, run config, and open the right panels.
- One command to "Make a Function": template, docstring, tests stub, and quick-run hook.
- A "Safe Mode" toggle that disables dangerous operations (redefining core, nuking packages) unless explicitly unlocked.

Experts still get:
- Full REPL power, full macroexpansion, full tracing, full compilation knobs, accessed through context or command palette.

## A Small, Canonical Toolset
If you keep the surface minimal, the IDE can still be definitive if these are flawless:
- Editor (structural awareness, eval hooks, navigation)
- REPL (live, history, object links)
- Inspector (pivot for everything)
- Debugger (restart-first, source-first, with integrated stepper lane)
- Problems (warnings/errors as a navigable queue)
- Search/Command palette (the gateway to everything else)
Everything beyond this must justify itself by removing friction, not adding "capability presence".

## What "Happy and Safe" Means in Practice
- Errors never destroy flow: they offer a next action immediately (restart, edit, retry).
- The UI never shouts: minimal chrome, strong typography, calm motion.
- Users always know where they are (breadcrumbs, back/forward, history).
- The system is forgiving: undoable edits, recoverable sessions, visible evaluation history.
This is the modern version of what the Lisp Machine experience got right: not nostalgia, but confidence under live change.

## Legacy Ideas Worth Explicitly Adding (Without Copying the Old Surface)
Yes. There are a handful of old Lisp-environment ideas that remain unmatched and are worth explicitly adding. None require copying the old surface.

### 1. Output Recording as a Real Subsystem, Not "We Rendered Some Spans"
Old win: Dynamic Windows recorded the structure of output (what was printed, where, with what identity), so later operations could reliably target it.
Add to your design:
- A formal output-recording layer in the REPL host: every run (text, presentation, system) is stored with stable anchors and provenance (job-id, seq range, stream-id).
- Operations act on recordings, not DOM nodes, so selection, copying, folding, and replay are deterministic even after re-render.
- "Copy as form", "copy with context", and "re-run this output as input" act on the recording model.
Net effect: the transcript becomes a manipulable artifact, not just a log.

### 2. Presentation Types Richer Than v0: Command, Frame, Location
Old win: the system treated commands, stack frames, and places as first-class things you could click.
Add types early:
- Command (the submission itself as an object; lets you re-run with variants).
- Frame (backtrace frames as click targets even outside the debugger).
- Binding (locals/specials as click targets).
- Place (generalized setf place/slot/array cell, enabling "edit here" workflows).
- Definition (function/macro/class generic "go to definition" target).
- Condition-report sections (so parts of an error are actionable).
These are the presentations that make the environment feel alive faster than adding more widgets.

### 3. A Real Command Processor (Verbs Over Objects), Not Just a Right-Click Menu
Old win: Genera was built around commands with typed arguments, completion, defaults, and history.
Add:
- A single command system whose arguments can be satisfied by clicking a presentation, typing in the command palette (with completion), or pasting text (fallback).
- Commands are serializable and replayable ("do again", "do again with different args").
- Command history stores structured arguments, not strings.
This becomes your unifying layer between mouse-first and Emacs-first operation.

### 4. "Do What I Mean" Argument Acquisition
Old win: you rarely had to specify context explicitly; the system used the current selection, window, and last result as implicit defaults.
Add:
- Default target equals current selection or last presentation under cursor.
- Default package equals transcript entry context capsule.
- Default source location equals most recent definition touched.
- Every command shows its inferred defaults before execution.
This is the single biggest friendliness multiplier for mouse users.

### 5. A First-Class "World State" Concept, Even Without Full Image Snapshots
Old win: Lisp Machines felt safe because the environment persisted and resumed.
Add:
- Workspace snapshots of UI state: open inspectors, pinned objects, transcript, history, watches, layout.
- Session restore that brings back that workspace even if object references are stale.
- A revalidate mechanism: stale presentations become live again when possible, otherwise remain readable.
This delivers psychological safety without claiming full Genera-style world saving.

### 6. Integrated Documentation as an Interactive Object, Not a Webpage
Old win: documentation was part of navigation and inspection.
Add:
- Documentation is a presentation type.
- Symbol docs expand inline (summary) and open in a doc pane (full).
- Cross references are presentations (clickable symbols, packages, classes).
- "Why am I seeing this?" links for conditions and warnings explain in plain terms, then link to formal doc.
This is crucial for non-expert friendliness.

### 7. Restarts Deserve a Richer UI Contract Than "Buttons With Optional Args"
Old win: restart-driven recovery was the main loop.
Add:
- Restart presentations include a short label, longer explanation, safety level (safe/destructive/irreversible), and argument schema (types, defaults, validation).
- The UI supports preview effects when possible (for example, "Retry compilation of X" shows what will be retried).
- A recommended restart can be suggested by runtime, but must be transparent.
This keeps flow and reduces fear.

### 8. Inspectable Places and Safe Edit-in-Place
Old win: the inspector was not passive; it could change the running system in controlled ways.
Add:
- Inspector fields can optionally represent a setf-able place.
- Edits are staged with apply/undo per edit group.
- Changes produce transcript events (auditable history of mutations).
This makes the environment feel powerful while remaining safe.

### 9. A "Select-and-Operate" Interaction, Not Just Click-to-Inspect
Old win: you could select an object on screen and then choose operations that understood its type.
Add:
- A selection model for presentations (single, multi-select).
- A context-aware action bar that changes based on selection type.
- Multi-object operations: "inspect all", "describe all", "trace these", "compare", "diff slots".
This is how you get power without tool sprawl.

### 10. A Deliberate Beginner Mode That Is Still the Same System
Old win: old systems assumed expertise; you should not.
Add:
- Same commands, fewer exposed verbs by default.
- Explanations attached to actions ("Inspect shows structure; it does not evaluate").
- A reversible training-wheels layer, not a separate product.
This aligns with new wins while keeping the old model's depth.

If you add only three things from the old world: (1) output recording as a formal subsystem, (2) command objects plus a typed command processor, and (3) restart-first recovery with rich restart metadata. Everything else can iterate.
