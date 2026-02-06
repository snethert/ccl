## Browser CCL UI Toolkit Specification (WASM)

Status: Draft

## Scope
This document defines the UI toolkit for a browser-hosted CCL runtime running on WASM, including architecture, state model, focus and layout rules, error handling, developer tools, and multi-backend rendering (DOM + Canvas/WebGL). It captures implementation details implied by the current design and compares the proposed system to other windowing systems in a maintainable feature test matrix.

Out of scope for this document:
- Full desktop OS window integration outside the browser page.
- Emulating a full OS desktop; this toolkit provides a disciplined workspace inside a single page.
- A full theming marketplace or arbitrary app-defined DOM/CSS manipulation as the default.
- A standalone custom renderer that bypasses all browser primitives (DOM/Canvas/WebGL).

Constraints that shape the design:
- Text input/IME is delegated to native DOM inputs where necessary (composition, selection, accessibility).

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
- All authoritative UI state is Lisp data; the backend exposes only transient measurements and input signals.
- Errors are interactive events with recovery options, not modal interruptions.
- Applications target toolkit abstractions, not the DOM.
- Reentrancy is controlled: commands run to completion or yield; no implicit nested command dispatch.

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
- No command may synchronously block the UI thread; cooperative waiting MUST yield to the host.
- Backend callbacks MUST NOT mutate UI state directly; they enqueue commands.
- Every command has a stable ID and an inspectable enablement reason.
- UI state can be serialized without querying the DOM.
- Rendering is derived solely from Lisp state; DOM/Canvas/WebGL are outputs.

## Architecture Overview
### Backend abstraction
- The toolkit targets an abstract UI backend with DOM as the first implementation.
- Canvas 2D and WebGL are additional backends for high-frequency and custom rendering.
- Mixed composition is allowed (DOM chrome + Canvas/WebGL views).
- DOM owns text editing, accessibility, and selection; Canvas/WebGL owns high-frequency visuals.
- Direct DOM access exists only for internal tooling or explicit capability-gated escapes.
- Any escape hatch MUST be capability-gated and MUST register its effects in inspectable state.
- Backend implementations MAY expose native handles for tests or tooling, but those handles MUST map back to stable widget/presentation IDs before command dispatch.

### Rendering model
- UI is described as a declarative Lisp UI tree with stable identity keys.
- Stage 2 uses a retained tree with diff/patch; immediate mode MAY exist only inside Canvas/WebGL views.
- Output records (rendered subtrees + cache) support incremental redisplay.
- Canvas/WebGL backends render from a scene/paint tree derived from the UI tree.
- Hit-testing is backend-agnostic and uses stable IDs from the UI tree.
- Hit-testing MUST be stable under scrolling, transforms, and DPR changes; IDs are derived from widget identity, not backend node identity.

### State model
- UI state is structured Lisp data:
  - tasks, windows, workspace layouts
  - focus and command routing state
  - widget models and presentation trees
  - background jobs and errors
- UI updates are a pure function of state plus explicit side effects (commands).
- Commands are the only state transition boundary; the renderer is read-only over state.

## Core Requirements
### Deterministic focus rules
- Focus changes MUST occur only via user action or explicit command.
- Opening a window MUST NOT steal focus unless the open command implies focus.
- Closing a window MUST restore focus to the previous focused window in the same task, otherwise to a defined fallback.
- Keyboard focus and active window MUST be unambiguous and visible.
- Browser focus/blur events MUST be treated as input signals; Lisp focus state is authoritative.
- IME composition MUST NOT be interrupted by focus reconciliation; reconciliation defers while composing.
- Pointer lock, fullscreen, and browser-level shortcuts are treated as external constraints; focus state records these constraints.

Acceptance checks:
- Focus transitions are reproducible for identical action sequences.
- No stray typing after window creation, background completion, or error events.

### User-owned layout with no drift
- The toolkit MUST support docking, splitting, tab groups, and optional floating panels.
- Layout actions MUST mutate persistent layout state and be restored verbatim.
- The system MUST NOT auto-rebalance or reflow due to content changes or background events.
- Content size changes MUST introduce scrollbars, not layout mutation.
- Default layouts MUST apply only on first creation and MUST NOT reapply silently.

Acceptance checks:
- Restored layouts match prior state within <= 1 CSS pixel (or <= 1 device pixel converted to CSS pixels).
- No rearrangement caused by content changes, task completion, or theme changes.

### Explicit, inspectable state
- Inspectable representations MUST exist for tasks, windows, focus history, command enablement, job queues, and recent errors.
- The UI MUST expose busy indicators, disabled reasons, and background job status.
- A standard command MUST open a System State inspector window.
- All "why" questions have a first-class object: FocusReason, DisableReason, WindowCause, JobCause.
- A deterministic event log (ring buffer) records command dispatch, focus transitions, and backend signals for replay.

Acceptance checks:
- Users can answer why something is disabled, what is running, and why a window exists without leaving the environment.

### Restart-style error handling
- Errors from UI-invoked Lisp code MUST NOT crash the UI loop.
- Errors MUST open an interactive debugger window tied to the current task.
- The debugger MUST show the condition, stack, locals, and restarts.
- Alerts SHOULD be modeless; modality is reserved for irreversible actions.
- Debugger windows MUST be rate-limited/coalesced per task to prevent error storms.
- Errors in background jobs produce a job-error object and MAY open a debugger window by policy; they MUST NOT spam-focus.

Acceptance checks:
- Errors during interaction create debugger windows, not blocking browser alerts.
- Users can select a restart and continue without losing layout or task context.

### Windows as task containers
- Every window MUST belong to exactly one task.
- Tasks MUST have a stable ID, label, and window list/graph with resumable focus.
- Task navigation MUST be first class (switch, list, close, archive).
- Task list UI MUST surface these actions and make task switching deterministic and inspectable.
- Debugger/inspector windows MUST attach to the task that caused them.

Acceptance checks:
- Users can always tell the current task and why a window exists.
- Tasks can be paused and resumed without hunting for scattered windows.

### Centralized command and keybinding system
- Commands MUST be first-class objects with IDs, docs, enablement predicates, and execution functions.
- Keybindings MUST map to commands, not widget callbacks.
- Resolution MUST be centralized with explicit precedence rules (global, task, context, widget).
- The system MUST provide a command palette and keybinding viewer.
- Default keybinding resolution is inspectable as a trace (matched scopes, rejected scopes, final command).
- Text fields have an explicit "text editing mode" command layer so editor shortcuts do not leak into global bindings.

Acceptance checks:
- Shortcuts either work consistently or are explicitly disabled with an inspectable reason.

### Presentation and semantic interaction
- Widgets MAY declare presentations for the objects they render.
- Presentation translators MUST map (presentation type, gesture) to commands.
- Presentation trees MUST be inspectable; "what did I click" resolves to a typed object.
- Presentation translators MUST be deterministic and side-effect-free during enablement checks.
- Presentations include a stable object reference strategy (object-id + epoch) so persisted UI doesn’t resurrect stale pointers.
- Presentation resolution MUST return a command id (or null) without mutating state.

Acceptance checks:
- A user can invoke context-appropriate commands based on the object they selected, not just the widget they clicked.

### Canvas/WebGL integration
- Canvas/WebGL views MUST support hit-testing, focus, and command routing via stable IDs.
- Text measurement and font metrics MUST be provided through backend interfaces.
- Canvas/WebGL views MUST integrate with layout, focus, and persistence like any other widget.
- `measureText` MUST be cached per font key; the backend reports cache misses.
- Canvas/WebGL views MUST provide an accessibility proxy strategy (focusable regions + label/role mapping) or explicitly declare themselves non-accessible.
- Canvas/WebGL views default to non-accessible; accessibility proxies are enabled only when explicitly configured (label/role/tabIndex).
- Text editing uses DOM inputs for composition, selection, and accessibility; Canvas/WebGL text editing is not the baseline.

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
- Task/window/widget structure MUST persist with stable IDs.
- Focus and selection persistence is best-effort; invalid targets MUST be dropped on restore.
- Presentations are NOT persisted; they are regenerated from restored state.
- Persistent data MUST be versioned; schema migrations are supported.
- Schema migrations MUST be reversible or explicitly marked as destructive and recorded in a migration log.

### Snapshot Envelope (Normative)
Each snapshot MUST be a versioned envelope:
- `schemaVersion` (string or number)
- `createdAt` (ms since epoch or ISO string)
- `workspaceId`
- `metadata` (implementation-defined, JSON-serializable)
- `state` (see below)

### Persisted State Subset (Normative)
The persisted `state` MUST include:
- `workspace`, `tasks`, `windows`, `widgets`
- `layout`
- `selection` (best-effort)
- `focus` (best-effort)
- `idCounters` (to avoid ID reuse)

The persisted `state` MUST NOT include:
- command registry or executable handlers
- DOM references or backend-specific caches
- presentation trees (recomputed on restore)

### Restore Rules (Normative)
- Missing referenced IDs (task/window/widget) MUST be dropped and replaced with safe defaults.
- `rootWidgetId` MUST be repaired if missing by selecting the first widget for the window.
- If layout is missing or invalid, a minimal layout MUST be synthesized.

### Migration Policy (Normative)
- Unknown schema versions MUST fail safe (restore minimal empty state, not crash).
- Forward-only migrations are allowed; destructive migrations MUST be labeled.
- Implementations SHOULD keep a backup snapshot before applying destructive migrations.

### Persistence Policy (Guidance)
- A single latest snapshot per workspace is sufficient by default.
- Writes SHOULD be debounced/coalesced and MUST NOT block the UI thread.

## Performance and Responsiveness
### Budgets
- Command dispatch latency SHOULD be <= 2 ms in the common case.
- UI update to visible response SHOULD be <= 16 ms for single-frame updates.
- Large list/table views SHOULD remain interactive at 10k+ rows with virtualization.
- Canvas/WebGL views SHOULD support 60 FPS for typical diagram/timeline workloads.

### Requirements
- UI event handling MUST remain responsive under large inspector trees, logs, and compilation.
- Rendering MUST be incremental; avoid full-tree rerenders on small changes.
- Renderer must support incremental commits; long diffs are chunked over frames with visible progress.
- Canvas/WebGL views SHOULD use dirty-rect or region invalidation.
- Long operations MUST be background tasks with inspectable progress and no UI-thread blocking.
- All expensive inspectors (10k+ nodes) MUST be virtualized; no recursive pretty-print on the UI thread.

## Safety and Isolation
- UI actions MUST be restart-safe; errors cannot corrupt global UI state.
- Apps MUST interact via toolkit APIs, not raw DOM.
- Privileged operations MUST require explicit capabilities and policy mediation.
- Capability mediation is a command, not an API call (so it is logged, inspectable, and restartable).
- A "safe mode" can disable all capability-granted escapes and still bring up REPL/inspector/debugger.

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

### Event loop boundary
Define a single UI turn:
- Backend signals enqueue input events.
- Input events are resolved to commands.
- Commands run to completion or yield, producing state deltas.
- Renderer commits are scheduled (rAF/microtask policy).
- Backend updates complete and may enqueue further signals.
Lisp code runs only within command execution boundaries and explicit yields.

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
- The command palette is a task-scoped window that lists commands deterministically and supports filtering.
- The keybinding viewer is a task-scoped window that lists bindings across scopes with stable formatting.
- Keybinding resolution exposes a trace: an ordered list of scope checks with scope id, key, match flag, and resolved command.

### Command palette and keybinding viewer
- The palette filter is explicit state (e.g., a text input) and re-renders the command list deterministically.
- Palette list items SHOULD carry the resolved command id for dispatch (e.g., as a target command id).
- The palette maintains an explicit selected item; navigation updates selection without mutating command order.
- Executing the selected item MUST use the target command id.
- Palette navigation and execution MUST be exposed as commands (e.g., select-next, select-prev, execute-selected).
- Opening/closing the command palette and keybinding viewer MUST be exposed as commands.
- Palette implementations MAY hide internal commands from the listing.
- Palette bindings SHOULD map ArrowUp/ArrowDown/Enter to selection and execution commands for the palette scope.
- Default keybindings SHOULD include `Ctrl+Shift+P` (open palette), `Ctrl+Shift+K` (open keybindings), and `Escape` (dismiss active command surface).
- Keybinding viewer entries SHOULD encode scope, scope id (if any), key, and command id in a human-readable label.
- The keybinding viewer SHOULD expose a trace panel for a selected key showing scope decisions in order.
- Trace entries SHOULD include explicit reasons when a scope is skipped after a match or missing its scope id.

### Focus manager
- Maintain authoritative focus state in Lisp: active task, active window, focused widget.
- DOM focus/blur is treated as a signal; mismatches trigger reconciliation.
- Focus changes carry a reason code for debugging and replay.
- Reconciliation is best-effort and never destructive; if the browser refuses focus, record refusal reason and leave Lisp focus unchanged.

### Layout manager
- Layout operations mutate a persistent layout tree (splits, tabs, docks).
- No automatic rebalancing; layout changes are explicit commands.
- Layout mutations MUST be exposed as commands (split, wrap-in-tabs, set-active-tab, dock).

### Error handling and debugger integration
- All command execution is wrapped in restart-friendly error handling.
- Errors create a debugger window attached to the current task.
- Provide standard restarts (abort, retry, use default, inspect state).
- The debugger itself is restart-safe; debugger rendering errors fall back to a minimal textual condition viewer.

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
- Provide command palette and keybinding viewer tests that validate listing and filtering.
- Provide keybinding resolution trace tests for deterministic scope evaluation.
- Provide a rendering diff test suite for output record stability.
- Provide a Canvas/WebGL hit-test test suite with fixed fixtures.
- Provide IME and text editing tests: composition, dead keys, mobile virtual keyboard, selection persistence.
- Deterministic replay: record backend signals + command log; assert resulting focus/layout hashes.

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

## Feature Test Matrix
The feature test matrix is maintained in Appendix A to keep normative sections free of comparative content.

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

## Appendix A: Feature Test Matrix
This appendix tracks design-intent coverage for the CCL Browser UI. Comparative columns are deferred until each row has explicit sources.

| ID | Feature | Status | Notes |
| --- | --- | --- | --- |
| F-01 | Focus changes are explicitly reasoned and inspectable | Design intent | Focus reasons are first-class. |
| F-02 | Focus cannot be stolen arbitrarily | Design intent | Best-effort; browser constraints are recorded. |
| F-03 | Single focus target per window/surface | Design intent | Authoritative focus state in Lisp. |
| F-04 | Centralized event routing / responder chain | Design intent | Commands and resolver precedence. |
| F-05 | UI toolkits are main-thread constrained | Design intent | No blocking commands; yield when needed. |
| F-06 | Layout persistence is first-class | Design intent | Layout is serialized and restored. |
| F-07 | Restart-based error recovery in UI | Design intent | Debugger windows with restarts. |
| F-08 | Focus events delivered as enter/leave signals | Design intent | Backend signals enqueue commands. |
| F-09 | Typed presentations and semantic interaction | Design intent | Object-id + epoch strategy. |
| F-10 | Incremental redisplay/output records | Design intent | Retained tree + diff. |
| F-11 | GUI builder / rapid UI construction | Design intent | Builder output remains inspectable. |
| F-12 | Canvas/WebGL as first-class render backend | Design intent | DOM for text editing. |
| F-13 | Mixed DOM + custom rendering composition | Design intent | DOM owns text editing and accessibility. |
