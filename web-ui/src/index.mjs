export { createIdGenerator, initIdCounters, allocateId } from "./ids.mjs";
export {
  createWorkspace,
  createState,
  addTask,
  addWindow,
  addWidget,
  removeWindow,
  setActiveTask,
  archiveTask,
  closeTask,
  addPresentation,
  setLayout,
  initLayout,
  splitLayout,
  wrapInTabs,
  setActiveTab,
  dockLayout,
  recordEvent,
  setCommandState,
  updateWidget,
  updateWindow,
  openInspectorWindow,
  refreshInspectorWindow,
  openDebuggerWindow,
  refreshDebuggerWindow,
  COMMAND_PALETTE_FILTER_COMMAND,
  COMMAND_PALETTE_EXECUTE_COMMAND,
  COMMAND_PALETTE_SELECT_NEXT_COMMAND,
  COMMAND_PALETTE_SELECT_PREV_COMMAND,
  COMMAND_PALETTE_EXECUTE_SELECTION_COMMAND,
  COMMAND_PALETTE_OPEN_COMMAND,
  COMMAND_PALETTE_CLOSE_COMMAND,
  KEYBINDINGS_OPEN_COMMAND,
  KEYBINDINGS_CLOSE_COMMAND,
  COMMAND_SURFACE_DISMISS_COMMAND,
  TASK_LIST_COMMAND,
  TASK_SWITCH_COMMAND,
  TASK_CLOSE_COMMAND,
  TASK_ARCHIVE_COMMAND,
  LAYOUT_SPLIT_COMMAND,
  LAYOUT_TABS_COMMAND,
  LAYOUT_DOCK_COMMAND,
  LAYOUT_SET_ACTIVE_TAB_COMMAND,
  raiseError,
  acknowledgeError,
  upsertJob,
  setSelection,
  setFocus,
  openCommandPaletteWindow,
  refreshCommandPaletteWindow,
  closeCommandPaletteWindow,
  openTaskListWindow,
  refreshTaskListWindow,
  applyCommandPaletteFilter,
  applyCommandPaletteSelection,
  resolveCommandPaletteSelection,
  registerCommandPaletteCommands,
  registerTaskCommands,
  registerLayoutCommands,
  registerCommandSurfaceCommands,
  bindCommandPaletteDefaults,
  bindCommandSurfaceDefaults,
  openKeybindingWindow,
  refreshKeybindingWindow,
  closeKeybindingWindow
} from "./state.mjs";
export {
  createRegistry,
  registerCommand,
  normalizeCommand,
  getCommand,
  bindKey,
  resolveKey,
  resolveKeyWithTrace,
  registerPresentationTranslator,
  resolvePresentationCommand,
  executePresentationCommand,
  commandEnabled,
  executeCommand
} from "./commands.mjs";
export { makeContext } from "./context.mjs";
export {
  FOCUS_REASONS,
  normalizeFocusTarget,
  sameFocusTarget,
  resolveFocusTargetFromElement,
  reconcileFocus
} from "./focus.mjs";
export { normalizeLayout, createLayout } from "./layout.mjs";
export { normalizeSelection } from "./selection.mjs";
export { createElement, createText, h, normalizeChildren } from "./vdom.mjs";
export { createRoot } from "./renderer.mjs";
export { renderWidget, renderWindow } from "./widgets.mjs";
export { createEventLog, normalizeEventLog, recordEvent as recordEventLog } from "./event-log.mjs";
export { buildScene, hitTestScene, normalizeSceneNode, flattenScene } from "../backends/canvas/scene.mjs";
export { createCanvasBackend, createCanvasRoot } from "../backends/canvas/renderer.mjs";
export { createMeasureCache } from "../backends/canvas/measure.mjs";
export { createWebGLBackend, createWebGLRoot } from "../backends/webgl/renderer.mjs";
export {
  createPersistenceManager
} from "./persistence/manager.mjs";
export {
  createSnapshot,
  restoreStateFromSnapshot,
  sanitizeState
} from "./persistence/serialize.mjs";
export {
  createMemoryStore,
  createIndexedDBStore
} from "./persistence/storage.mjs";
export { SCHEMA_VERSION as PERSISTENCE_SCHEMA_VERSION } from "./persistence/schema.mjs";
