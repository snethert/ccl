## Browser CCL UI Toolkit Specification (WASM)

Status: Draft

## Scope
This document defines the UI toolkit for a browser-hosted CCL runtime running on WASM, including architecture, state model, focus and layout rules, error handling, and developer tools. It also captures implementation details implied by the current design and compares the proposed system to other windowing systems in a maintainable feature test matrix.

Out of scope for this document:
- Pixel-perfect custom rendering engines as the primary UI substrate.
- Full desktop OS window integration outside the browser page.
- A full theming marketplace or arbitrary app-defined DOM/CSS manipulation as the default.

## Goals
- Provide a Lisp-machine-like interactive environment with long-lived sessions.
- Preserve user flow under errors, interruptions, and context switches.
- Ensure deterministic, inspectable UI state and focus behavior.
- Offer a coherent application model so apps target the toolkit, not raw DOM.

## Design Principles
- Determinism over cleverness.
- User intent is authoritative; the system never rearranges or redirects without explicit commands.
- All UI-relevant state is Lisp data and inspectable.
- Errors are interactive events with recovery options, not modal interruptions.
- Applications target toolkit abstractions, not the DOM.

## Definitions
- Task: A coherent unit of work with a stable ID, label, and window set.
- Window: A view belonging to exactly one task.
- Widget: A UI component that renders from Lisp data and receives events through commands.
- Command: A first-class object with ID, docs, enablement predicate, and execution function.
- Backend: The concrete rendering and event bridge (DOM is the first backend).

## Architecture Overview
### Backend abstraction
- The toolkit targets an abstract UI backend, with DOM as the first implementation.
- The DOM is treated as an output device and event source; Lisp is the authority.
- Direct DOM access exists only for internal tooling or debugging.

### Rendering model
- UI is described as a declarative Lisp UI tree.
- Rendering uses a retained tree or immediate tree with diff/patch, with stable identity keys.
- Updates are incremental; identity is stable; performance is acceptable for devtool workloads.

### State model
- UI state is structured Lisp data:
  - tasks, windows, workspace layouts
  - focus and command routing state
  - widget models
  - background jobs and errors
- UI updates are a pure function of state plus explicit side effects (commands).

## Core Requirements
### Deterministic focus rules
- Focus changes only via user action or explicit command.
- Opening a window does not steal focus unless the open command implies focus.
- Closing a window restores focus to the previous focused window in the same task, otherwise to a defined fallback.
- Keyboard focus and active window are unambiguous and visible.
- Browser focus/blur events are treated as input signals; Lisp focus state is authoritative.

Acceptance checks:
- Focus transitions are reproducible for identical action sequences.
- No stray typing after window creation, background completion, or error events.

### User-owned layout with no drift
- The toolkit supports docking, splitting, tab groups, and optional floating panels.
- Layout actions mutate persistent layout state and are restored verbatim.
- No auto-rebalance or reflow due to content changes or background events.
- Default layouts apply only on first creation and never reapply silently.

Acceptance checks:
- Restored layouts match prior state within trivial pixel tolerances.
- No rearrangement caused by content changes, task completion, or theme changes.

### Explicit, inspectable state
- Inspectable representations exist for tasks, windows, focus history, command enablement, job queues, and recent errors.
- The UI exposes busy indicators, disabled reasons, and background job status.
- A standard command opens a System State inspector window.

Acceptance checks:
- Users can answer why something is disabled, what is running, and why a window exists without leaving the environment.

### Restart-style error handling
- Errors from UI-invoked Lisp code must not crash the UI loop.
- Errors open an interactive debugger window tied to the current task.
- The debugger shows the condition, stack, locals, and restarts.
- Alerts are modeless by default; modality is reserved for irreversible actions.

Acceptance checks:
- Errors during interaction create debugger windows, not blocking browser alerts.
- Users can select a restart and continue without losing layout or task context.

### Windows as task containers
- Every window belongs to exactly one task.
- Tasks have a stable ID, label, and window list/graph with resumable focus.
- Task navigation is first class (switch, list, close, archive).
- Debugger/inspector windows attach to the task that caused them.

Acceptance checks:
- Users can always tell the current task and why a window exists.
- Tasks can be paused and resumed without hunting for scattered windows.

### Centralized command and keybinding system
- Commands are first-class objects with IDs, docs, enablement predicates, and execution functions.
- Keybindings map to commands, not widget callbacks.
- Resolution is centralized with explicit precedence rules (global, task, context).
- The system provides a command palette and keybinding viewer.

Acceptance checks:
- Shortcuts either work consistently or are explicitly disabled with an inspectable reason.

## Toolkit Surface Requirements
### Core widgets (minimum viable)
- Layout: split panes (H/V), tab groups, scroll containers, docking manager.
- Controls: buttons, toggles, checkboxes, radio groups.
- Inputs: single-line and multiline text inputs.
- Lists: list, tree, table (virtualized rows recommended).
- Menus: menubar, dropdown, context menu.
- Status: status bar and notifications.
- Developer tools: REPL, inspector, debugger, editor integration via CodeMirror or Monaco backend.

### Standard model protocols
- List model: count, item retrieval, stable key, selection, activation.
- Tree model: children, label, expanded state, selection, lazy loading.
- Command model: IDs, enablement, execution.
- Document model: buffer ops, selection, markers, change events.

## Persistence and Versioning
- Layout state persists per session/workspace and restores exactly.
- Task state persists open windows, navigation context, and focus target.
- Persistent data is versioned; schema migrations are supported.

## Performance and Responsiveness
- UI event handling remains responsive under large inspector trees, logs, and compilation.
- Rendering is incremental; avoid full-tree rerenders on small changes.
- Long operations are background tasks with inspectable progress and no UI-thread blocking.

## Safety and Isolation
- UI actions are restart-safe; errors cannot corrupt global UI state.
- Apps interact via toolkit APIs, not raw DOM.
- Privileged operations require explicit capabilities and policy mediation.

## Developer Experience
- All UI state is debuggable from within the environment.
- A UI developer mode provides optional overlays and event/command routing traces.

## Implementation Details (Design-Consistent)
### Object graph and identity
- The app is a graph of Lisp objects: workspace -> tasks -> windows -> widget tree + models.
- Each object has stable identity and explicit IDs for diffing and persistence.

### Rendering pipeline
- Windows expose a view function that returns a UI tree.
- The renderer diffs UI trees and patches the DOM with stable keys.
- DOM nodes are never the source of truth; they mirror Lisp state.

### Command system
- Commands include ID, docstring, enablement predicate, and execution function.
- Enablement predicates return (enabled, reason) for inspectability.
- Keybindings resolve to commands in a deterministic, centralized resolver.

### Focus manager
- Maintain authoritative focus state in Lisp: active task, active window, focused widget.
- DOM focus/blur is treated as a signal; mismatches trigger reconciliation.
- Focus changes carry a reason code, inspired by Qt focus reasons, to support debugging.

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

## External System Lessons (Research-Grounded)
These are the recurring difficulties and constraints observed in other windowing systems and the browser, and how they motivate the design:

- Focus cannot be freely stolen. Windows restricts which processes may set the foreground window. The browser similarly treats window focus as a best-effort request. This motivates explicit focus authority in Lisp and deterministic focus restoration. References: SetForegroundWindow restrictions, Window.focus behavior.
- Focus models vary by platform. GTK maintains a single focus widget per window, with explicit keyboard navigation rules. Qt exposes focus reason codes. This motivates explicit focus state, focus reasons, and deterministic routing. References: GTK input handling, Qt FocusReason.
- Event routing is chain-based in mature systems. Cocoa/AppKit uses a responder chain to cooperatively resolve events and actions. This supports a centralized command routing layer rather than ad hoc widget handlers. References: AppKit responder chain.
- UI toolkits are thread-constrained. GTK objects must be used on the main thread; Qt GUI classes are main-thread only. This motivates strict separation between UI updates and background jobs. References: GTK threading, Qt threads/QObject rules.
- Compositors, not clients, own focus on Wayland. Focus is delivered by enter/leave events for surfaces, not taken by clients. This reinforces the idea that focus is an external signal reconciled with internal state. References: Wayland keyboard focus events.
- X11 ICCCM requires clients to follow focus conventions and WM_TAKE_FOCUS handshakes. This reinforces the need for explicit, protocol-like focus transitions. References: ICCCM Input Focus.

## Common Failure Modes and Countermeasures
- Focus stealing and random focus changes: Prevented by explicit focus state and command-only focus transitions.
- Event routing chaos from widget-level handlers: Prevented by centralized command routing and responder-like propagation.
- UI freezes from long tasks on the UI thread: Prevented by background jobs and explicit progress tracking.
- Layout drift and auto-reflow surprises: Prevented by user-owned layout state and no implicit rebalance.
- Uninspectable state and "mystery disabled" controls: Prevented by command enablement reasons and System State inspector.

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
