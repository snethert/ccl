## Browser CCL UI Toolkit Specification (WASM)

Status: Draft

## Scope
This document defines the UI toolkit for a browser-hosted CCL runtime running on WASM, including architecture, state model, focus and layout rules, error handling, developer tools, and multi-backend rendering (DOM + Canvas/WebGL). It captures implementation details implied by the current design and compares the proposed system to other windowing systems in a maintainable feature test matrix.

Out of scope for this document:
- Full desktop OS window integration outside the browser page.
- A full theming marketplace or arbitrary app-defined DOM/CSS manipulation as the default.
- A standalone custom renderer that bypasses all browser primitives (DOM/Canvas/WebGL).

## Normative Language
The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted as described in RFC 2119.

## Goals
- Provide a Lisp-machine-like interactive environment with long-lived sessions.
- Preserve user flow under errors, interruptions, and context switches.
- Ensure deterministic, inspectable UI state and focus behavior.
- Offer a coherent application model so apps target the toolkit, not raw DOM.
- Support both standard widgets and high-frequency custom visuals via Canvas/WebGL.

## Design Principles
- Determinism over cleverness.
- User intent is authoritative; the system never rearranges or redirects without explicit commands.
- All UI-relevant state is Lisp data and inspectable.
- Errors are interactive events with recovery options, not modal interruptions.
- Applications target toolkit abstractions, not the DOM.

## Design Synthesis (Best of Both Worlds)
The system intentionally combines three layers:
- CLIM-like semantics: presentations, output records, and command tables to make UI object-aware and incrementally redisplayable.
- CLOG-like pragmatism: REPL-first development, rapid UI construction, and a builder that emits real tasks/windows/widgets.
- This spec's trust model: deterministic focus/layout, centralized commands, restart-driven errors, and inspectability by default.

## Definitions
- Task: A coherent unit of work with a stable ID, label, and window set.
- Window: A view belonging to exactly one task.
- Widget: A UI component that renders from Lisp data and receives events through commands.
- Command: A first-class object with ID, docs, enablement predicate, and execution function.
- Presentation: A typed visual representation of an underlying object, used for semantic interaction.
- Backend: The concrete rendering and event bridge (DOM, Canvas 2D, WebGL).

## Architectural Invariants
The following invariants MUST hold at all times:
- All windows belong to exactly one task.
- There is a single authoritative focus target at any time.
- UI state changes occur only via commands.
- Every command has a stable ID and an inspectable enablement reason.
- UI state can be serialized without querying the DOM.
- Rendering is derived solely from Lisp state; DOM/Canvas/WebGL are outputs.

## Architecture Overview
### Backend abstraction
- The toolkit targets an abstract UI backend with DOM as the first implementation.
- Canvas 2D and WebGL are additional backends for high-frequency and custom rendering.
- Mixed composition is allowed (DOM chrome + Canvas/WebGL views).
- Direct DOM access exists only for internal tooling or explicit capability-gated escapes.
- Backend implementations MAY expose native handles for tests or tooling, but those handles MUST map back to stable widget/presentation IDs before command dispatch.

### Rendering model
- UI is described as a declarative Lisp UI tree with stable identity keys.
- Rendering uses a retained tree or immediate tree with diff/patch.
- Output records (rendered subtrees + cache) support incremental redisplay.
- Canvas/WebGL backends render from a scene/paint tree derived from the UI tree.
- Hit-testing is backend-agnostic and uses stable IDs from the UI tree.

### State model
- UI state is structured Lisp data:
  - tasks, windows, workspace layouts
  - focus and command routing state
  - widget models and presentation trees
  - background jobs and errors
- UI updates are a pure function of state plus explicit side effects (commands).

## Core Requirements
### Deterministic focus rules
- Focus changes MUST occur only via user action or explicit command.
- Opening a window MUST NOT steal focus unless the open command implies focus.
- Closing a window MUST restore focus to the previous focused window in the same task, otherwise to a defined fallback.
- Keyboard focus and active window MUST be unambiguous and visible.
- Browser focus/blur events MUST be treated as input signals; Lisp focus state is authoritative.

Acceptance checks:
- Focus transitions are reproducible for identical action sequences.
- No stray typing after window creation, background completion, or error events.

### User-owned layout with no drift
- The toolkit MUST support docking, splitting, tab groups, and optional floating panels.
- Layout actions MUST mutate persistent layout state and be restored verbatim.
- The system MUST NOT auto-rebalance or reflow due to content changes or background events.
- Default layouts MUST apply only on first creation and MUST NOT reapply silently.

Acceptance checks:
- Restored layouts match prior state within trivial pixel tolerances.
- No rearrangement caused by content changes, task completion, or theme changes.

### Explicit, inspectable state
- Inspectable representations MUST exist for tasks, windows, focus history, command enablement, job queues, and recent errors.
- The UI MUST expose busy indicators, disabled reasons, and background job status.
- A standard command MUST open a System State inspector window.

Acceptance checks:
- Users can answer why something is disabled, what is running, and why a window exists without leaving the environment.

### Restart-style error handling
- Errors from UI-invoked Lisp code MUST NOT crash the UI loop.
- Errors MUST open an interactive debugger window tied to the current task.
- The debugger MUST show the condition, stack, locals, and restarts.
- Alerts SHOULD be modeless; modality is reserved for irreversible actions.

Acceptance checks:
- Errors during interaction create debugger windows, not blocking browser alerts.
- Users can select a restart and continue without losing layout or task context.

### Windows as task containers
- Every window MUST belong to exactly one task.
- Tasks MUST have a stable ID, label, and window list/graph with resumable focus.
- Task navigation MUST be first class (switch, list, close, archive).
- Debugger/inspector windows MUST attach to the task that caused them.

Acceptance checks:
- Users can always tell the current task and why a window exists.
- Tasks can be paused and resumed without hunting for scattered windows.

### Centralized command and keybinding system
- Commands MUST be first-class objects with IDs, docs, enablement predicates, and execution functions.
- Keybindings MUST map to commands, not widget callbacks.
- Resolution MUST be centralized with explicit precedence rules (global, task, context).
- The system MUST provide a command palette and keybinding viewer.

Acceptance checks:
- Shortcuts either work consistently or are explicitly disabled with an inspectable reason.

### Presentation and semantic interaction
- Widgets MAY declare presentations for the objects they render.
- Presentation translators MUST map (presentation type, gesture) to commands.
- Presentation trees MUST be inspectable; "what did I click" resolves to a typed object.

Acceptance checks:
- A user can invoke context-appropriate commands based on the object they selected, not just the widget they clicked.

### Canvas/WebGL integration
- Canvas/WebGL views MUST support hit-testing, focus, and command routing via stable IDs.
- Text measurement and font metrics MUST be provided through backend interfaces.
- Canvas/WebGL views MUST integrate with layout, focus, and persistence like any other widget.

Acceptance checks:
- Canvas/WebGL views participate in focus and command routing without bypassing the system.

## Toolkit Surface Requirements
### Core widgets (minimum viable)
Bring-up baseline (Phase 2): button, label, text input, list.

- Layout: split panes (H/V), tab groups, scroll containers, docking manager.
- Controls: buttons, toggles, checkboxes, radio groups.
- Inputs: single-line and multiline text inputs.
- Lists: list, tree, table (virtualized rows recommended).
- Menus: menubar, dropdown, context menu.
- Status: status bar and notifications.
- Developer tools: REPL, inspector, debugger, editor integration via CodeMirror or Monaco backend.
- Rendering: canvas view, WebGL view, and a mixed DOM + canvas compositor widget.

### Standard model protocols
- List model: count, item retrieval, stable key, selection, activation.
- Tree model: children, label, expanded state, selection, lazy loading.
- Command model: IDs, enablement, execution.
- Document model: buffer ops, selection, markers, change events.
- Presentation model: type, object, bounds, and translators.

## Persistence and Versioning
- Layout state MUST persist per session/workspace and restore exactly.
- Task state MUST persist open windows, navigation context, and focus target.
- Persistent data MUST be versioned; schema migrations are supported.
- Schema migrations MUST be reversible or explicitly marked as destructive.

## Performance and Responsiveness
### Budgets
- Command dispatch latency SHOULD be <= 2 ms in the common case.
- UI update to visible response SHOULD be <= 16 ms for single-frame updates.
- Large list/table views SHOULD remain interactive at 10k+ rows with virtualization.
- Canvas/WebGL views SHOULD support 60 FPS for typical diagram/timeline workloads.

### Requirements
- UI event handling MUST remain responsive under large inspector trees, logs, and compilation.
- Rendering MUST be incremental; avoid full-tree rerenders on small changes.
- Canvas/WebGL views SHOULD use dirty-rect or region invalidation.
- Long operations MUST be background tasks with inspectable progress and no UI-thread blocking.

## Safety and Isolation
- UI actions MUST be restart-safe; errors cannot corrupt global UI state.
- Apps MUST interact via toolkit APIs, not raw DOM.
- Privileged operations MUST require explicit capabilities and policy mediation.

## Developer Experience
- All UI state MUST be debuggable from within the environment.
- A UI developer mode SHOULD provide optional overlays and event/command routing traces.
- Rapid UI construction is supported (REPL-first helpers and a builder), but all generated UI MUST be inspectable and task/window-based.

## Implementation Details (Design-Consistent)
### Object graph and identity
- The app is a graph of Lisp objects: workspace -> tasks -> windows -> widget tree + models.
- Each object MUST have stable identity and explicit IDs for diffing and persistence.

### Presentation system
- A presentation binds an object to a visual representation and a type.
- Presentation translators map object types and gestures to commands.
- Presentation trees are cached as output records for incremental redisplay.

### Rendering pipeline
- Windows expose a view function that returns a UI tree.
- The renderer diffs UI trees and patches the DOM or issues draw commands to Canvas/WebGL.
- DOM nodes are never the source of truth; they mirror Lisp state.

### Backend interface (minimal, Stage 2 baseline)
- `render(tree)` renders a UI tree to the backend. Diff/patch MAY be internal.
- `measureText(text, options)` returns font metrics (width/height/ascent/descent) with deterministic defaults.
- `hitTest(point, options)` returns a backend handle; the handle MUST be resolvable to stable widget/presentation IDs.
- `invalidate(callback|ids)` coalesces updates. DOM backends MAY schedule a callback (e.g., rAF); Canvas/WebGL SHOULD support id/region invalidation.
- `captureEvents(target, handlers, options)` attaches listeners and returns a disposer. Events MUST be resolved to stable IDs before command routing.

### DOM backend pragmatics (Stage 2)
- DOM nodes SHOULD carry stable IDs via data attributes (e.g., `data-widget-id`, `data-command-id`) to support hit-testing and instrumentation.
- `hitTest` MAY use `elementFromPoint` as long as mapping to stable IDs is deterministic.

### Command system
- Commands include ID, docstring, enablement predicate, and execution function.
- Enablement predicates return (enabled, reason) for inspectability.
- Keybindings resolve to commands in a deterministic, centralized resolver.

### Focus manager
- Maintain authoritative focus state in Lisp: active task, active window, focused widget.
- DOM focus/blur is treated as a signal; mismatches trigger reconciliation.
- Focus changes carry a reason code for debugging and replay.

### Layout manager
- Layout operations mutate a persistent layout tree (splits, tabs, docks).
- No automatic rebalancing; layout changes are explicit commands.

### Error handling and debugger integration
- All command execution is wrapped in restart-friendly error handling.
- Errors create a debugger window attached to the current task.
- Provide standard restarts (abort, retry, use default, inspect state).

### Background tasks and progress
- Background jobs are first-class objects in the task state.
- UI exposes queue depth, active job count, and per-job progress.

### System state inspector
- A built-in inspector lists tasks, windows, focus history, command registry, and job queues.
- The inspector is the canonical answer to why controls are disabled or windows exist.

### Browser integration
- Browser focus is not fully controllable; treat focus APIs as best-effort signals.
- Use explicit focus state and reconcile with `document.activeElement` and window focus signals.

### Rapid UI construction path
- Provide high-level constructors that emit real tasks/windows/widgets.
- A builder may generate UI trees, but the result MUST be inspectable, persisted, and command-driven.
- Direct DOM access is allowed only under explicit capabilities and MUST be tagged for inspector visibility.

## Validation and Testing
- Provide a deterministic focus test suite that replays action sequences and compares focus history.
- Provide a layout drift test suite that serializes layout before/after actions.
- Provide a command routing test suite that verifies scope precedence and disabled reasons.
- Provide a rendering diff test suite for output record stability.
- Provide a Canvas/WebGL hit-test test suite with fixed fixtures.

## External System Lessons (Research-Grounded)
These are the recurring difficulties and constraints observed in other windowing systems and the browser, and how they motivate the design:

- Focus cannot be freely stolen. Windows restricts which processes may set the foreground window. The browser similarly treats window focus as a best-effort request. This motivates explicit focus authority in Lisp and deterministic focus restoration.
- Focus models vary by platform. GTK maintains a single focus widget per window, with explicit keyboard navigation rules. Qt exposes focus reason codes. This motivates explicit focus state, focus reasons, and deterministic routing.
- Event routing is chain-based in mature systems. Cocoa/AppKit uses a responder chain to cooperatively resolve events and actions. This supports a centralized command routing layer rather than ad hoc widget handlers.
- UI toolkits are thread-constrained. GTK objects must be used on the main thread; Qt GUI classes are main-thread only. This motivates strict separation between UI updates and background jobs.
- Compositors, not clients, own focus on Wayland. Focus is delivered by enter/leave events for surfaces, not taken by clients. This reinforces the idea that focus is an external signal reconciled with internal state.
- X11 ICCCM requires clients to follow focus conventions and WM_TAKE_FOCUS handshakes. This reinforces the need for explicit, protocol-like focus transitions.

## Common Failure Modes and Countermeasures
- Focus stealing and random focus changes: Prevented by explicit focus state and command-only focus transitions.
- Event routing chaos from widget-level handlers: Prevented by centralized command routing and responder-like propagation.
- UI freezes from long tasks on the UI thread: Prevented by background jobs and explicit progress tracking.
- Layout drift and auto-reflow surprises: Prevented by user-owned layout state and no implicit rebalance.
- Uninspectable state and "mystery disabled" controls: Prevented by command enablement reasons and System State inspector.
- Gesture/hit-test mismatches in Canvas/WebGL: Prevented by backend-agnostic hit-testing with stable IDs.

## Feature Test Matrix (Maintainable)
Legend:
- Y = supported by design
- P = partial support or depends on configuration
- V = varies by platform or toolkit
- N = not supported

Note: The matrix includes only features with publicly documented behavior in the referenced systems. Rows are intended to be expanded as more verified data is added.

| ID | Feature | CCL Browser UI | Win32 | AppKit | GTK | Qt | X11/ICCCM | Wayland | Browser DOM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F-01 | Focus changes are explicitly reasoned and inspectable | Y | V | V | P | Y | P | P | P |
| F-02 | Focus cannot be stolen arbitrarily | Y | Y | V | V | V | P | Y | P |
| F-03 | Single focus target per window/surface | Y | V | Y | Y | Y | P | Y | Y |
| F-04 | Centralized event routing / responder chain | Y | V | Y | V | V | V | V | V |
| F-05 | UI toolkits are main-thread constrained | Y | V | Y | Y | Y | V | V | Y |
| F-06 | Layout persistence is first-class | Y | V | V | V | V | V | V | V |
| F-07 | Restart-based error recovery in UI | Y | N | N | N | N | N | N | N |
| F-08 | Focus events delivered as enter/leave signals | P | V | V | V | V | V | Y | P |
| F-09 | Typed presentations and semantic interaction | Y | V | V | V | V | V | V | N |
| F-10 | Incremental redisplay/output records | Y | V | V | V | V | V | V | P |
| F-11 | GUI builder / rapid UI construction | P | V | V | V | V | V | V | V |
| F-12 | Canvas/WebGL as first-class render backend | Y | P | P | P | P | P | V | P |
| F-13 | Mixed DOM + custom rendering composition | Y | V | V | V | V | V | V | P |

Matrix maintenance notes:
- Add new rows only when a feature can be verified with a stable source.
- Prefer explicit references for each feature in the References section.
- Avoid assuming parity between toolkits; use V when behavior is toolkit- or platform-specific.

## Acceptance Checklist (High-Leverage)
- Focus behavior is repeatable and never surprising.
- Layout restored on reload matches prior session without drift.
- Users can inspect why actions are disabled and what is running.
- Errors open debugger windows with restarts and do not block with modal alerts.
- Windows are grouped by task; task switching is first class.
- Keybindings are consistent, centrally resolved, and discoverable.
- Canvas/WebGL views participate in focus and command routing without bypassing the system.

## References
- Microsoft SetForegroundWindow restrictions and focus rules: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow
- GTK input and focus handling: https://docs.gtk.org/gtk4/input-handling.html
- GTK threading requirements: https://docs.gtk.org/gtk4/section-threading.html
- Qt FocusReason enumeration: https://doc.qt.io/qt-6/qt.html#FocusReason-enum
- Qt GUI classes main-thread constraints: https://doc.qt.io/qt-6/threads-qobject.html
- AppKit responder chain documentation: https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/EventOverview/EventArchitecture/EventArchitecture.html
- Wayland keyboard focus enter/leave events: https://wayland-book.com/seat/keyboard.html
- X11 ICCCM input focus conventions: https://www.x.org/releases/X11R7.7/doc/xorg-docs/icccm/icccm.html
- MDN Window.focus behavior: https://developer.mozilla.org/en-US/docs/Web/API/Window/focus
- MDN Document.activeElement behavior: https://developer.mozilla.org/en-US/docs/Web/API/Document/activeElement
