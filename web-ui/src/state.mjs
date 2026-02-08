import { allocateId, initIdCounters } from "./ids.mjs";
import {
  normalizeRecordingStore,
  appendRecording as appendRecordingCore,
  appendEntry as appendEntryCore,
  attachAnchor as attachAnchorCore,
  setEntryFolded as setEntryFoldedCore,
  setRecordingCollapsed as setRecordingCollapsedCore,
  copyAsForm as copyAsFormRecording,
  copyWithContext as copyWithContextRecording,
  replayAsInput as replayAsInputRecording,
  reRunRecording as reRunRecordingInput
} from "./recordings.mjs";
import { normalizeEventLog, recordEvent as recordEventLog } from "./event-log.mjs";
import { normalizeSelection } from "./selection.mjs";
import {
  normalizeLayout,
  createLayout,
  splitLayoutNode,
  wrapInTabsNode,
  setActiveTabNode,
  dockLayoutNode
} from "./layout.mjs";
import { normalizeFocusTarget, normalizeFocusHistory, setFocus as setFocusCore } from "./focus.mjs";
import { registerCommand, executeCommand, executePresentationCommand, bindKey, resolveKeyWithTrace } from "./commands.mjs";
import {
  normalizeCommandSpec,
  normalizeInvocation,
  validateInvocation,
  materializeInvocation
} from "./typed-commands.mjs";
import {
  normalizePresentationType,
  applyPresentationDefaults,
  validatePresentationMetadata
} from "./presentation-taxonomy.mjs";
import { normalizeThemeTokens } from "./theme.mjs";
import {
  KEYMAP_PANES,
  KEYMAP_SCOPE_KINDS,
  normalizeCustomizationEnvelope,
  patchCustomizationLayer,
  exportCustomizationProfile,
  importCustomizationProfile,
  validateCustomizationProfile
} from "./customization.mjs";
import { normalizeRestart, normalizeConditionReport } from "./conditions.mjs";
import { revalidatePresentations as revalidatePresentationsCore } from "./world-state.mjs";

const ID_KINDS = ["workspace", "task", "window", "widget", "presentation", "layout", "reason", "error", "job", "session"];
const UI_TURN_PHASES = ["signals", "commands", "render", "backend", "idle"];
const UI_TURN_HISTORY_LIMIT = 8;
const DOM_ESCAPE_HISTORY_LIMIT = 32;
const CAPABILITY_POLICY_DECISIONS = ["ask", "grant", "deny"];
const CAPABILITY_REQUEST_STATUSES = ["pending", "granted", "denied"];
const PROBLEM_STATUSES = ["new", "active", "resolved", "suppressed"];
const EDIT_GROUP_STATUSES = ["staged", "applied", "undone", "failed"];
export const COMMAND_PALETTE_FILTER_COMMAND = "ui.command-palette.filter";
export const COMMAND_PALETTE_EXECUTE_COMMAND = "ui.command-palette.execute";
export const COMMAND_PALETTE_SELECT_NEXT_COMMAND = "ui.command-palette.select-next";
export const COMMAND_PALETTE_SELECT_PREV_COMMAND = "ui.command-palette.select-prev";
export const COMMAND_PALETTE_EXECUTE_SELECTION_COMMAND = "ui.command-palette.execute-selected";
export const COMMAND_PALETTE_OPEN_COMMAND = "ui.command-palette.open";
export const COMMAND_PALETTE_CLOSE_COMMAND = "ui.command-palette.close";
export const KEYBINDINGS_OPEN_COMMAND = "ui.keybindings.open";
export const KEYBINDINGS_CLOSE_COMMAND = "ui.keybindings.close";
export const COMMAND_SURFACE_DISMISS_COMMAND = "ui.command-surface.dismiss";
export const RECORDING_APPEND_COMMAND = "repl.recording.append";
export const RECORDING_ENTRY_APPEND_COMMAND = "repl.recording.entry.append";
export const RECORDING_ANCHOR_ATTACH_COMMAND = "repl.recording.anchor.attach";
export const RECORDING_ENTRY_FOLD_COMMAND = "repl.recording.entry.fold";
export const RECORDING_TOGGLE_COMMAND = "repl.recording.toggle";
export const RECORDING_COPY_AS_FORM_COMMAND = "repl.recording.copy-as-form";
export const RECORDING_COPY_WITH_CONTEXT_COMMAND = "repl.recording.copy-with-context";
export const RECORDING_REPLAY_AS_INPUT_COMMAND = "repl.recording.replay-as-input";
export const RECORDING_RERUN_COMMAND = "repl.recording.rerun";
export const COMMAND_HISTORY_APPEND_COMMAND = "ui.command-history.append";
export const COMMAND_HISTORY_OPEN_COMMAND = "ui.command-history.open";
export const COMMAND_HISTORY_REFRESH_COMMAND = "ui.command-history.refresh";
export const COMMAND_HISTORY_EXECUTE_COMMAND = "ui.command-history.execute";
export const PROBLEMS_OPEN_COMMAND = "ui.problems.open";
export const PROBLEMS_REFRESH_COMMAND = "ui.problems.refresh";
export const PROBLEMS_ITEM_OPEN_COMMAND = "ui.problems.item.open";
export const DEBUGGER_RESTART_INVOKE_COMMAND = "ui.debugger.restart.invoke";
export const INSPECTOR_WATCH_PIN_COMMAND = "ui.inspector.watch.pin";
export const INSPECTOR_WATCH_UNPIN_COMMAND = "ui.inspector.watch.unpin";
export const INSPECTOR_EDIT_STAGE_COMMAND = "ui.inspector.edit.stage";
export const INSPECTOR_EDIT_APPLY_COMMAND = "ui.inspector.edit.apply";
export const INSPECTOR_EDIT_UNDO_COMMAND = "ui.inspector.edit.undo";
export const LIST_SELECTION_UPDATE_COMMAND = "ui.list.selection.update";
export const TRANSCRIPT_OPEN_COMMAND = "ui.transcript.open";
export const TRANSCRIPT_REFRESH_COMMAND = "ui.transcript.refresh";
export const TRANSCRIPT_ITEM_OPEN_COMMAND = "ui.transcript.item.open";
export const TASK_LIST_COMMAND = "ui.task.list";
export const TASK_SWITCH_COMMAND = "ui.task.switch";
export const TASK_CLOSE_COMMAND = "ui.task.close";
export const TASK_ARCHIVE_COMMAND = "ui.task.archive";
export const SESSION_LIST_COMMAND = "ui.session.list";
export const SESSION_REFRESH_COMMAND = "ui.session.refresh";
export const SESSION_CREATE_COMMAND = "ui.session.create";
export const SESSION_OPEN_COMMAND = "ui.session.open";
export const SESSION_SAVE_COMMAND = "ui.session.save";
export const SESSION_RENAME_COMMAND = "ui.session.rename";
export const SESSION_DELETE_COMMAND = "ui.session.delete";
export const LAYOUT_SPLIT_COMMAND = "ui.layout.split";
export const LAYOUT_TABS_COMMAND = "ui.layout.tabs";
export const LAYOUT_DOCK_COMMAND = "ui.layout.dock";
export const LAYOUT_SET_ACTIVE_TAB_COMMAND = "ui.layout.set-active-tab";
export const CAPABILITY_REQUEST_COMMAND = "ui.capability.request";
export const CAPABILITY_GRANT_COMMAND = "ui.capability.grant";
export const CAPABILITY_REVOKE_COMMAND = "ui.capability.revoke";
export const CAPABILITY_OPEN_PANEL_COMMAND = "ui.capability.open-panel";
export const CAPABILITY_SELECT_COMMAND = "ui.capability.select";
export const CAPABILITY_APPROVE_COMMAND = "ui.capability.approve";
export const CAPABILITY_DENY_COMMAND = "ui.capability.deny";
export const CAPABILITY_AUTO_RUN_COMMAND = "ui.capability.auto-run";
export const SAFE_MODE_ENABLE_COMMAND = "ui.safe-mode.enable";
export const SAFE_MODE_DISABLE_COMMAND = "ui.safe-mode.disable";
export const DOM_ESCAPE_COMMAND = "ui.dom.escape";
export const CUSTOMIZATION_THEME_PRESET_COMMAND = "ui.customization.theme.preset";
export const CUSTOMIZATION_THEME_OVERRIDES_COMMAND = "ui.customization.theme.overrides";
export const CUSTOMIZATION_THEME_OVERRIDES_RESET_COMMAND = "ui.customization.theme.overrides.reset";
export const CUSTOMIZATION_KEYMAP_PROFILE_COMMAND = "ui.customization.keymap.profile";
export const CUSTOMIZATION_BEGINNER_MODE_ENABLE_COMMAND = "ui.customization.beginner.enable";
export const CUSTOMIZATION_BEGINNER_MODE_DISABLE_COMMAND = "ui.customization.beginner.disable";
export const CUSTOMIZATION_GUIDANCE_DISMISS_COMMAND = "ui.customization.guidance.dismiss";
export const CUSTOMIZATION_PROFILE_EXPORT_COMMAND = "ui.customization.profile.export";
export const CUSTOMIZATION_PROFILE_IMPORT_COMMAND = "ui.customization.profile.import";

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === "[object Object]";
}

function ensureCounters(counters) {
  if (counters) {
    const next = { ...counters };
    for (const kind of ID_KINDS) {
      if (!Number.isInteger(next[kind])) {
        next[kind] = 0;
      }
    }
    return next;
  }
  return initIdCounters(ID_KINDS);
}

function ensureWorkspace(state) {
  if (state.workspace) {
    return state;
  }
  const alloc = allocateId(state.idCounters, "workspace");
  const workspace = createWorkspace({ id: alloc.id });
  return {
    ...state,
    idCounters: alloc.counters,
    workspace
  };
}

function normalizeTask(task) {
  return {
    id: task.id,
    title: task.title ?? "Untitled",
    windowIds: Array.isArray(task.windowIds) ? [...task.windowIds] : [],
    activeWindowId: task.activeWindowId ?? null,
    metadata: task.metadata ?? {}
  };
}

function normalizeWindow(window) {
  return {
    id: window.id,
    taskId: window.taskId,
    title: window.title ?? "Window",
    kind: window.kind ?? "document",
    rootWidgetId: window.rootWidgetId ?? null,
    metadata: window.metadata ?? {}
  };
}

function normalizeWidget(widget) {
  return {
    id: widget.id,
    kind: widget.kind ?? "container",
    parentId: widget.parentId ?? null,
    windowId: widget.windowId ?? null,
    childIds: Array.isArray(widget.childIds) ? [...widget.childIds] : [],
    props: widget.props ?? {},
    model: widget.model ?? {}
  };
}

function normalizeSession(session) {
  if (!session || typeof session !== "object") return null;
  return {
    id: session.id,
    name: session.name ?? "Session",
    notes: session.notes ?? "",
    createdAt: Number.isInteger(session.createdAt) ? session.createdAt : null,
    lastOpenedAt: Number.isInteger(session.lastOpenedAt) ? session.lastOpenedAt : null,
    lastSavedAt: Number.isInteger(session.lastSavedAt) ? session.lastSavedAt : null,
    metadata: session.metadata ?? {}
  };
}

function normalizeSessions(sessions) {
  if (!sessions || typeof sessions !== "object") return {};
  const out = {};
  for (const [id, session] of Object.entries(sessions)) {
    const normalized = normalizeSession({ ...session, id: session.id ?? id });
    if (normalized && normalized.id) {
      out[normalized.id] = normalized;
    }
  }
  return out;
}

function normalizeSessionOrder(sessions, order) {
  const ids = Object.keys(sessions ?? {});
  const seen = new Set();
  const next = [];
  if (Array.isArray(order)) {
    for (const id of order) {
      if (typeof id !== "string") continue;
      if (!sessions[id] || seen.has(id)) continue;
      seen.add(id);
      next.push(id);
    }
  }
  for (const id of ids) {
    if (seen.has(id)) continue;
    next.push(id);
  }
  return next;
}

function normalizeActiveSessionId(sessions, activeId, order) {
  if (activeId && sessions?.[activeId]) return activeId;
  const ordered = Array.isArray(order) ? order : [];
  for (const id of ordered) {
    if (sessions?.[id]) return id;
  }
  const first = Object.keys(sessions ?? {})[0];
  return first ?? null;
}

function normalizePresentation(presentation) {
  const base = applyPresentationDefaults({
    id: presentation.id,
    type: normalizePresentationType(presentation.type ?? presentation.presentationType ?? "value"),
    objectId: presentation.objectId ?? null,
    entryId: presentation.entryId ?? null,
    widgetId: presentation.widgetId ?? null,
    bounds: presentation.bounds ?? null,
    label: presentation.label ?? null,
    actions: Array.isArray(presentation.actions) ? [...presentation.actions] : [],
    metadata: presentation.metadata ?? {}
  });
  const validation = validatePresentationMetadata(base);
  if (validation.ok) {
    return base;
  }
  const fallbackSummary =
    (typeof base.metadata?.summary === "string" && base.metadata.summary.length > 0
      ? base.metadata.summary
      : typeof base.label === "string" && base.label.length > 0
        ? base.label
        : `${base.id ?? "presentation"} (${validation.type})`);
  return {
    ...base,
    type: "value",
    metadata: {
      ...base.metadata,
      summary: fallbackSummary,
      degradedFromType: validation.type,
      missingMetadata: validation.missing,
      validation: "degraded"
    }
  };
}

function buildPresentationForEntry(state, entry) {
  if (!entry || typeof entry !== "object") return null;
  const existing = entry.presentationId ? state.presentations?.[entry.presentationId] ?? null : null;
  if (existing) return existing;
  const kind = entry.kind ?? "text";
  if (kind === "error") {
    return normalizePresentation({
      id: entry.presentationId ?? `entry-${entry.id ?? "unknown"}`,
      type: "condition-section",
      entryId: entry.id ?? null,
      label: entry.text ?? "Condition",
      metadata: {
        errorId: entry.metadata?.errorId ?? entry.recordingId ?? null,
        sectionKey: entry.metadata?.sectionKey ?? "summary",
        text: entry.text ?? ""
      }
    });
  }
  if (kind === "system") {
    return normalizePresentation({
      id: entry.presentationId ?? `entry-${entry.id ?? "unknown"}`,
      type: "command",
      entryId: entry.id ?? null,
      label: entry.text ?? "Command",
      metadata: {
        commandId: entry.metadata?.commandId ?? "repl.eval",
        args: entry.metadata?.args ?? {},
        title: entry.text ?? "Command"
      }
    });
  }
  return normalizePresentation({
    id: entry.presentationId ?? `entry-${entry.id ?? "unknown"}`,
    type: "value",
    entryId: entry.id ?? null,
    label: entry.text ?? null,
    metadata: {
      summary: entry.text ?? ""
    }
  });
}

function sanitizeDomEscapeDetail(detail) {
  if (detail === null || detail === undefined) return {};
  const type = typeof detail;
  if (type === "string" || type === "number" || type === "boolean") {
    return { value: detail };
  }
  if (Array.isArray(detail) || type === "object") {
    try {
      return JSON.parse(JSON.stringify(detail));
    } catch (err) {
      return {};
    }
  }
  return {};
}

function normalizeDomEscape(entry, index) {
  if (!entry || typeof entry !== "object") {
    return {
      id: `dom-escape-${index + 1}`,
      kind: "dom.escape",
      target: null,
      detail: {},
      capability: "dom.escape",
      taskId: null,
      windowId: null,
      commandId: DOM_ESCAPE_COMMAND,
      ts: null
    };
  }
  return {
    id: entry.id ?? `dom-escape-${index + 1}`,
    kind: entry.kind ?? "dom.escape",
    target: entry.target ?? null,
    detail: sanitizeDomEscapeDetail(entry.detail ?? null),
    capability: entry.capability ?? "dom.escape",
    taskId: entry.taskId ?? null,
    windowId: entry.windowId ?? null,
    commandId: entry.commandId ?? DOM_ESCAPE_COMMAND,
    ts: Number.isInteger(entry.ts) ? entry.ts : null
  };
}

function normalizeDomEscapes(entries) {
  if (!Array.isArray(entries)) return [];
  return entries.map((entry, index) => normalizeDomEscape(entry, index));
}

function normalizeUiSignal(signal, index) {
  if (!signal || typeof signal !== "object") {
    return { id: `signal-${index + 1}`, type: "signal", payload: {} };
  }
  return {
    id: signal.id ?? `signal-${index + 1}`,
    type: signal.type ?? "signal",
    payload: signal.payload ?? {}
  };
}

function normalizeUiTurn(turn) {
  if (!turn || typeof turn !== "object") {
    return null;
  }
  const phase = UI_TURN_PHASES.includes(turn.phase) || turn.phase === "yielded" ? turn.phase : "signals";
  const signals = Array.isArray(turn.signals) ? turn.signals.map(normalizeUiSignal) : [];
  return {
    id: turn.id ?? "turn-0",
    phase,
    signals,
    commitPolicy: turn.commitPolicy ?? "rAF",
    yielded: Boolean(turn.yielded),
    yieldReason: turn.yieldReason ?? null,
    startedAt: Number.isFinite(turn.startedAt) ? Number(turn.startedAt) : null
  };
}

function normalizeUiState(ui) {
  if (!ui || typeof ui !== "object") {
    return {
      queue: [],
      turn: null,
      history: [],
      nextTurnId: 1
    };
  }
  const queue = Array.isArray(ui.queue) ? ui.queue.map(normalizeUiSignal) : [];
  const history = Array.isArray(ui.history)
    ? ui.history.map((entry) => ({
        id: entry?.id ?? "turn-0",
        phase: entry?.phase ?? "idle",
        yielded: Boolean(entry?.yielded),
        commitPolicy: entry?.commitPolicy ?? "rAF"
      }))
    : [];
  const nextTurnId = Number.isInteger(ui.nextTurnId) && ui.nextTurnId > 0 ? ui.nextTurnId : 1;
  return {
    queue,
    turn: normalizeUiTurn(ui.turn),
    history,
    nextTurnId
  };
}

function normalizeCapabilityEntry(entry, index) {
  if (!entry || typeof entry !== "object") {
    return {
      id: `capability-${index + 1}`,
      action: "unknown",
      capability: null,
      reason: null,
      taskId: null,
      windowId: null,
      commandId: null
    };
  }
  return {
    id: entry.id ?? `capability-${index + 1}`,
    action: entry.action ?? "unknown",
    capability: entry.capability ?? null,
    reason: entry.reason ?? null,
    taskId: entry.taskId ?? null,
    windowId: entry.windowId ?? null,
    commandId: entry.commandId ?? null
  };
}

function normalizeCapabilityRequest(entry, index) {
  if (!entry || typeof entry !== "object") {
    return {
      id: `capability-request-${index + 1}`,
      capability: null,
      reason: null,
      status: "pending",
      decisionReason: null,
      decidedBy: null,
      taskId: null,
      windowId: null,
      commandId: null
    };
  }
  const status = CAPABILITY_REQUEST_STATUSES.includes(entry.status) ? entry.status : "pending";
  return {
    id: entry.id ?? `capability-request-${index + 1}`,
    capability: entry.capability ?? null,
    reason: entry.reason ?? null,
    status,
    decisionReason: entry.decisionReason ?? null,
    decidedBy: entry.decidedBy ?? null,
    taskId: entry.taskId ?? null,
    windowId: entry.windowId ?? null,
    commandId: entry.commandId ?? null
  };
}

function normalizeCapabilityRequests(requests) {
  if (!Array.isArray(requests)) return [];
  return requests.map((entry, index) => normalizeCapabilityRequest(entry, index));
}

function normalizeCapabilityPolicyRule(rule, index) {
  if (!rule || typeof rule !== "object") {
    return {
      id: `capability-rule-${index + 1}`,
      capability: null,
      decision: "ask",
      reason: null
    };
  }
  const decision = CAPABILITY_POLICY_DECISIONS.includes(rule.decision) ? rule.decision : "ask";
  const capability = typeof rule.capability === "string" ? rule.capability : null;
  return {
    id: rule.id ?? `capability-rule-${index + 1}`,
    capability,
    decision,
    reason: rule.reason ?? null
  };
}

function normalizeCapabilityPolicy(policy) {
  if (!policy || typeof policy !== "object") {
    return { defaultDecision: "ask", rules: [] };
  }
  const defaultDecision = CAPABILITY_POLICY_DECISIONS.includes(policy.defaultDecision)
    ? policy.defaultDecision
    : "ask";
  const rules = Array.isArray(policy.rules) ? policy.rules.map(normalizeCapabilityPolicyRule) : [];
  return {
    defaultDecision,
    rules
  };
}

function normalizeCapabilityRequestSeq(seq, requests) {
  let maxId = 0;
  for (const request of requests ?? []) {
    if (typeof request?.id !== "string") continue;
    const match = request.id.match(/^capability-request-(\d+)$/);
    if (!match) continue;
    const value = Number.parseInt(match[1], 10);
    if (Number.isFinite(value) && value > maxId) {
      maxId = value;
    }
  }
  const candidate = Number.isInteger(seq) && seq > 0 ? seq : 0;
  return Math.max(candidate, maxId + 1);
}

function normalizeCapabilities(capabilities) {
  const granted = Array.isArray(capabilities?.granted)
    ? [...new Set(capabilities.granted.filter((cap) => typeof cap === "string"))].sort()
    : [];
  const log = Array.isArray(capabilities?.log)
    ? capabilities.log.map((entry, index) => normalizeCapabilityEntry(entry, index))
    : [];
  return {
    safeMode: Boolean(capabilities?.safeMode),
    granted,
    log
  };
}

function appendCapabilityLog(capabilities, entry) {
  const log = Array.isArray(capabilities?.log) ? capabilities.log : [];
  const normalizedEntry = normalizeCapabilityEntry(entry, log.length);
  return { ...capabilities, log: [...log, normalizedEntry] };
}

function allocateCapabilityRequestId(state) {
  const seq = normalizeCapabilityRequestSeq(
    state.capabilityRequestSeq ?? null,
    normalizeCapabilityRequests(state.capabilityRequests ?? null)
  );
  return { id: `capability-request-${seq}`, nextSeq: seq + 1 };
}

function normalizeWatch(watch, index = 0) {
  const fallbackId = `watch-${index + 1}`;
  const id = typeof watch?.id === "string" && watch.id.length > 0 ? watch.id : fallbackId;
  const kind = typeof watch?.kind === "string" && watch.kind.length > 0 ? watch.kind : "entry";
  return {
    id,
    kind,
    label:
      (typeof watch?.label === "string" && watch.label.length > 0
        ? watch.label
        : watch?.entryId ?? watch?.presentationId ?? watch?.recordingId ?? id),
    entryId: typeof watch?.entryId === "string" && watch.entryId.length > 0 ? watch.entryId : null,
    presentationId:
      typeof watch?.presentationId === "string" && watch.presentationId.length > 0
        ? watch.presentationId
        : null,
    recordingId:
      typeof watch?.recordingId === "string" && watch.recordingId.length > 0 ? watch.recordingId : null,
    valueSummary: typeof watch?.valueSummary === "string" ? watch.valueSummary : "",
    pinned: watch?.pinned !== false,
    updatedAt: Number.isInteger(watch?.updatedAt) ? watch.updatedAt : null,
    metadata: isPlainObject(watch?.metadata) ? { ...watch.metadata } : {}
  };
}

function normalizeWatches(watches) {
  if (!Array.isArray(watches)) return [];
  return watches.map((watch, index) => normalizeWatch(watch, index));
}

function normalizeWatchSeq(seq, watches) {
  const maxFromList = normalizeWatches(watches).reduce((max, watch) => {
    const match = watch.id.match(/^watch-(\d+)$/);
    if (!match) return max;
    const value = Number.parseInt(match[1], 10);
    return Number.isFinite(value) && value > max ? value : max;
  }, 0);
  const candidate = Number.isInteger(seq) && seq > 0 ? seq : 0;
  return Math.max(candidate, maxFromList + 1);
}

function normalizeEditEntry(edit, index = 0) {
  const fallbackId = `edit-${index + 1}`;
  const id = typeof edit?.id === "string" && edit.id.length > 0 ? edit.id : fallbackId;
  const placeId = typeof edit?.placeId === "string" && edit.placeId.length > 0 ? edit.placeId : null;
  const label =
    (typeof edit?.label === "string" && edit.label.length > 0
      ? edit.label
      : typeof edit?.description === "string" && edit.description.length > 0
        ? edit.description
        : placeId ?? id);
  return {
    id,
    placeId,
    label,
    before: edit?.before ?? null,
    after: edit?.after ?? edit?.value ?? null,
    metadata: isPlainObject(edit?.metadata) ? { ...edit.metadata } : {}
  };
}

function normalizeEditGroup(group, index = 0) {
  const fallbackId = `edit-group-${index + 1}`;
  const id = typeof group?.id === "string" && group.id.length > 0 ? group.id : fallbackId;
  const status = EDIT_GROUP_STATUSES.includes(group?.status) ? group.status : "staged";
  const edits = Array.isArray(group?.edits) ? group.edits.map((edit, editIndex) => normalizeEditEntry(edit, editIndex)) : [];
  const label =
    (typeof group?.label === "string" && group.label.length > 0
      ? group.label
      : edits[0]?.label ?? id);
  return {
    id,
    label,
    status,
    edits,
    createdAt: Number.isInteger(group?.createdAt) ? group.createdAt : null,
    appliedAt: Number.isInteger(group?.appliedAt) ? group.appliedAt : null,
    undoneAt: Number.isInteger(group?.undoneAt) ? group.undoneAt : null,
    failedAt: Number.isInteger(group?.failedAt) ? group.failedAt : null,
    metadata: isPlainObject(group?.metadata) ? { ...group.metadata } : {}
  };
}

function normalizeEditGroups(groups) {
  if (!Array.isArray(groups)) return [];
  return groups.map((group, index) => normalizeEditGroup(group, index));
}

function normalizeEditSeq(seq, groups) {
  const maxFromList = normalizeEditGroups(groups).reduce((max, group) => {
    const match = group.id.match(/^edit-group-(\d+)$/);
    if (!match) return max;
    const value = Number.parseInt(match[1], 10);
    return Number.isFinite(value) && value > max ? value : max;
  }, 0);
  const candidate = Number.isInteger(seq) && seq > 0 ? seq : 0;
  return Math.max(candidate, maxFromList + 1);
}

function normalizeRuntimeInspectorState(runtimeInspector) {
  if (!isPlainObject(runtimeInspector)) {
    return {
      targetId: null,
      targetType: null,
      stale: false,
      view: null,
      lastUpdatedAt: null
    };
  }
  return {
    targetId:
      typeof runtimeInspector.targetId === "string" && runtimeInspector.targetId.length > 0
        ? runtimeInspector.targetId
        : null,
    targetType:
      typeof runtimeInspector.targetType === "string" && runtimeInspector.targetType.length > 0
        ? runtimeInspector.targetType
        : null,
    stale: Boolean(runtimeInspector.stale),
    view: isPlainObject(runtimeInspector.view) ? { ...runtimeInspector.view } : null,
    lastUpdatedAt: Number.isInteger(runtimeInspector.lastUpdatedAt) ? runtimeInspector.lastUpdatedAt : null
  };
}

function resolveCapabilityPolicyDecision(policy, capability) {
  const normalizedPolicy = normalizeCapabilityPolicy(policy ?? null);
  for (const rule of normalizedPolicy.rules) {
    if (!rule.capability) continue;
    if (rule.capability !== "*" && rule.capability !== capability) continue;
    return { decision: rule.decision, reason: rule.reason ?? null };
  }
  return { decision: normalizedPolicy.defaultDecision, reason: null };
}

function normalizeCustomization(customization) {
  return normalizeCustomizationEnvelope(customization ?? null);
}

function resolveThemeFromCustomization(customization, fallbackTheme = null) {
  const normalized = normalizeCustomization(customization);
  if (fallbackTheme && typeof fallbackTheme === "object") {
    return normalizeThemeTokens(fallbackTheme);
  }
  return normalizeThemeTokens(normalized.effective?.theme?.tokens ?? null);
}

function resolveEffectiveBeginnerMode(state) {
  return state?.customization?.effective?.beginnerMode ?? {
    enabled: false,
    showExplanations: true,
    confirmAdvanced: true,
    hiddenCommandIds: [],
    forceVisibleCommandIds: []
  };
}

function resolveGuidanceDismissed(state) {
  return new Set(state?.customization?.effective?.guidance?.dismissed ?? []);
}

function normalizeCustomizationLayerName(layer) {
  if (layer === "defaults" || layer === "user" || layer === "project" || layer === "session") {
    return layer;
  }
  return "session";
}

export function createWorkspace({ id, title, taskIds, activeTaskId, metadata } = {}) {
  return {
    id,
    title: title ?? "Workspace",
    taskIds: Array.isArray(taskIds) ? [...taskIds] : [],
    activeTaskId: activeTaskId ?? null,
    metadata: metadata ?? {}
  };
}

export function createState(options = {}) {
  const idCounters = ensureCounters(options.idCounters);
  const watches = normalizeWatches(options.watches ?? null);
  const watchSeq = normalizeWatchSeq(options.watchSeq ?? null, watches);
  const editGroups = normalizeEditGroups(options.editGroups ?? options.stagedEdits ?? null);
  const editSeq = normalizeEditSeq(options.editSeq ?? null, editGroups);
  const capabilityRequests = normalizeCapabilityRequests(options.capabilityRequests ?? null);
  const capabilityPolicy = normalizeCapabilityPolicy(options.capabilityPolicy ?? null);
  const capabilityRequestSeq = normalizeCapabilityRequestSeq(options.capabilityRequestSeq ?? null, capabilityRequests);
  const sessions = normalizeSessions(options.sessions ?? null);
  const sessionOrder = normalizeSessionOrder(sessions, options.sessionOrder ?? null);
  const activeSessionId = normalizeActiveSessionId(sessions, options.activeSessionId ?? null, sessionOrder);
  const customization = normalizeCustomization(options.customization ?? null);
  const theme = resolveThemeFromCustomization(customization, options.theme ?? null);
  let state = {
    ...options,
    workspace: options.workspace ?? null,
    tasks: options.tasks ?? {},
    windows: options.windows ?? {},
    widgets: options.widgets ?? {},
    presentations: options.presentations ?? {},
    recordingStore: normalizeRecordingStore(options.recordingStore ?? options.recordings ?? null),
    commandHistory: Array.isArray(options.commandHistory) ? [...options.commandHistory] : [],
    runtimeInspector: normalizeRuntimeInspectorState(options.runtimeInspector ?? null),
    watches,
    watchSeq,
    editGroups,
    editSeq,
    domEscapes: normalizeDomEscapes(options.domEscapes ?? null),
    ui: normalizeUiState(options.ui ?? null),
    capabilities: normalizeCapabilities(options.capabilities ?? null),
    capabilityRequests,
    capabilityPolicy,
    capabilityRequestSeq,
    sessions,
    sessionOrder,
    activeSessionId,
    customization,
    theme,
    focus: normalizeFocusTarget(options.focus ?? null),
    focusHistory: normalizeFocusHistory(options.focusHistory ?? []),
    selection: normalizeSelection(options.selection ?? null),
    commands: options.commands ?? {},
    layout: options.layout ?? null,
    focusReasons: options.focusReasons ?? {},
    disableReasons: options.disableReasons ?? {},
    windowCauses: options.windowCauses ?? {},
    jobCauses: options.jobCauses ?? {},
    eventLog: normalizeEventLog(options.eventLog ?? null),
    errors: Array.isArray(options.errors) ? [...options.errors] : [],
    jobs: Array.isArray(options.jobs) ? [...options.jobs] : [],
    idCounters
  };
  state = ensureWorkspace(state);
  const normalized = normalizeLayout(state.layout, state.idCounters);
  state = { ...state, layout: normalized.layout, idCounters: normalized.counters };
  return state;
}

export function addTask(state, task) {
  if (!task) {
    throw new Error("Task is required");
  }
  const alloc = task.id ? { id: task.id, counters: state.idCounters } : allocateId(state.idCounters, "task");
  const normalized = normalizeTask({ ...task, id: alloc.id });
  const tasks = { ...state.tasks, [normalized.id]: normalized };
  const workspace = state.workspace ?? createWorkspace({ id: "workspace-0" });
  const existingTaskIds = Array.isArray(workspace.taskIds) ? workspace.taskIds : [];
  const taskIds = existingTaskIds.includes(normalized.id)
    ? existingTaskIds
    : [...existingTaskIds, normalized.id];
  const activeTaskId = workspace.activeTaskId ?? normalized.id;
  return {
    ...state,
    idCounters: alloc.counters,
    tasks,
    workspace: { ...workspace, taskIds, activeTaskId }
  };
}

function taskIsArchived(task) {
  return Boolean(task?.metadata?.archived);
}

export function setActiveTask(state, taskId, options = {}) {
  if (!taskId) {
    return state;
  }
  const tasks = state.tasks ?? {};
  const task = tasks[taskId];
  if (!task) {
    return state;
  }
  const workspace = state.workspace ?? createWorkspace({ id: "workspace-0" });
  const taskIds = Array.isArray(workspace.taskIds) ? [...workspace.taskIds] : [];
  if (!taskIds.includes(taskId) && !taskIsArchived(task)) {
    taskIds.push(taskId);
  }
  let activeWindowId = task.activeWindowId ?? null;
  let updatedTask = task;
  if (!activeWindowId && Array.isArray(task.windowIds) && task.windowIds.length > 0) {
    activeWindowId = task.windowIds[0];
    updatedTask = { ...task, activeWindowId };
  }
  let nextState = {
    ...state,
    workspace: { ...workspace, activeTaskId: taskId, taskIds },
    tasks: updatedTask === task ? tasks : { ...tasks, [taskId]: updatedTask }
  };
  if (options.updateFocus !== false) {
    const target = { taskId, windowId: activeWindowId ?? null, widgetId: null, presentationId: null };
    nextState = setFocusCore(nextState, target, options.reason ?? "command", options.seq ?? null);
  }
  return nextState;
}

export function archiveTask(state, taskId, options = {}) {
  if (!taskId) {
    return state;
  }
  const task = state.tasks?.[taskId];
  if (!task) {
    return state;
  }
  const metadata = { ...(task.metadata ?? {}), archived: true, archivedAt: options.archivedAt ?? null };
  const tasks = { ...(state.tasks ?? {}), [taskId]: { ...task, metadata } };
  const workspace = state.workspace ?? createWorkspace({ id: "workspace-0" });
  const taskIds = Array.isArray(workspace.taskIds)
    ? workspace.taskIds.filter((id) => id !== taskId)
    : [];
  const wasActive = workspace.activeTaskId === taskId;
  let nextState = {
    ...state,
    tasks,
    workspace: { ...workspace, taskIds, activeTaskId: wasActive ? (taskIds[0] ?? null) : workspace.activeTaskId }
  };
  if (wasActive) {
    if (nextState.workspace.activeTaskId) {
      nextState = setActiveTask(nextState, nextState.workspace.activeTaskId, { reason: options.reason });
    } else {
      nextState = setFocusCore(nextState, null, options.reason ?? "command");
    }
  }
  return nextState;
}

export function closeTask(state, taskId, options = {}) {
  if (!taskId) {
    return state;
  }
  const task = state.tasks?.[taskId];
  if (!task) {
    return state;
  }
  let nextState = state;
  const windowIds = Array.isArray(task.windowIds) ? [...task.windowIds] : [];
  for (const windowId of windowIds) {
    if (nextState.windows?.[windowId]) {
      nextState = removeWindow(nextState, windowId, { reason: options.reason });
    }
  }
  for (const [windowId, window] of Object.entries(nextState.windows ?? {})) {
    if (window.taskId === taskId) {
      nextState = removeWindow(nextState, windowId, { reason: options.reason });
    }
  }

  const tasks = { ...(nextState.tasks ?? {}) };
  delete tasks[taskId];
  const workspace = nextState.workspace ?? createWorkspace({ id: "workspace-0" });
  const taskIds = Array.isArray(workspace.taskIds)
    ? workspace.taskIds.filter((id) => id !== taskId)
    : [];
  const wasActive = workspace.activeTaskId === taskId;
  let activeTaskId = wasActive ? (taskIds[0] ?? null) : workspace.activeTaskId;
  nextState = {
    ...nextState,
    tasks,
    workspace: { ...workspace, taskIds, activeTaskId }
  };
  if (wasActive) {
    if (activeTaskId) {
      nextState = setActiveTask(nextState, activeTaskId, { reason: options.reason });
    } else {
      nextState = setFocusCore(nextState, null, options.reason ?? "command");
    }
  }
  return nextState;
}

export function createSession(state, options = {}) {
  const alloc = allocateId(state.idCounters, "session", "session");
  const now = Number.isInteger(options.now) ? options.now : null;
  const name =
    options.name ??
    (alloc.id ? `Session ${alloc.id.replace("session-", "")}` : "Session");
  const session = normalizeSession({
    id: alloc.id,
    name,
    notes: options.notes ?? "",
    createdAt: now,
    lastOpenedAt: now,
    lastSavedAt: null,
    metadata: options.metadata ?? {}
  });
  const sessions = { ...(state.sessions ?? {}), [session.id]: session };
  const sessionOrder = normalizeSessionOrder(sessions, [...(state.sessionOrder ?? []), session.id]);
  return {
    ...state,
    idCounters: alloc.counters,
    sessions,
    sessionOrder,
    activeSessionId: session.id
  };
}

export function renameSession(state, sessionId, name, options = {}) {
  if (!sessionId) return state;
  const session = state.sessions?.[sessionId];
  if (!session) return state;
  const next = {
    ...session,
    name: name ?? session.name,
    notes: options.notes ?? session.notes
  };
  return {
    ...state,
    sessions: { ...(state.sessions ?? {}), [sessionId]: next }
  };
}

export function openSession(state, sessionId, options = {}) {
  if (!sessionId) return state;
  const session = state.sessions?.[sessionId];
  if (!session) return state;
  const now = Number.isInteger(options.now) ? options.now : null;
  const nextSession = {
    ...session,
    lastOpenedAt: now ?? session.lastOpenedAt
  };
  return {
    ...state,
    sessions: { ...(state.sessions ?? {}), [sessionId]: nextSession },
    activeSessionId: sessionId
  };
}

export function saveSession(state, sessionId, options = {}) {
  if (!sessionId) return state;
  const session = state.sessions?.[sessionId];
  if (!session) return state;
  const now = Number.isInteger(options.now) ? options.now : null;
  const nextSession = {
    ...session,
    lastSavedAt: now ?? session.lastSavedAt
  };
  return {
    ...state,
    sessions: { ...(state.sessions ?? {}), [sessionId]: nextSession }
  };
}

export function deleteSession(state, sessionId) {
  if (!sessionId || !state.sessions?.[sessionId]) return state;
  const sessions = { ...(state.sessions ?? {}) };
  delete sessions[sessionId];
  const sessionOrder = normalizeSessionOrder(sessions, (state.sessionOrder ?? []).filter((id) => id !== sessionId));
  const nextActive =
    state.activeSessionId === sessionId
      ? normalizeActiveSessionId(sessions, null, sessionOrder)
      : state.activeSessionId;
  return {
    ...state,
    sessions,
    sessionOrder,
    activeSessionId: nextActive
  };
}

export function addWindow(state, window) {
  if (!window) {
    throw new Error("Window is required");
  }
  const taskId = window.taskId ?? state.workspace?.activeTaskId ?? null;
  if (!taskId || !state.tasks[taskId]) {
    throw new Error("Window must reference an existing task");
  }
  const alloc = window.id ? { id: window.id, counters: state.idCounters } : allocateId(state.idCounters, "window");
  const normalized = normalizeWindow({ ...window, id: alloc.id, taskId });
  const windows = { ...state.windows, [normalized.id]: normalized };
  const task = state.tasks[taskId];
  const existingWindowIds = Array.isArray(task.windowIds) ? task.windowIds : [];
  const windowIds = existingWindowIds.includes(normalized.id)
    ? existingWindowIds
    : [...existingWindowIds, normalized.id];
  const activeWindowId = task.activeWindowId ?? normalized.id;
  return {
    ...state,
    idCounters: alloc.counters,
    windows,
    tasks: {
      ...state.tasks,
      [taskId]: { ...task, windowIds, activeWindowId }
    }
  };
}

export function addWidget(state, widget) {
  if (!widget) {
    throw new Error("Widget is required");
  }
  const alloc = widget.id ? { id: widget.id, counters: state.idCounters } : allocateId(state.idCounters, "widget");
  const normalized = normalizeWidget({ ...widget, id: alloc.id });
  const widgets = { ...state.widgets, [normalized.id]: normalized };
  if (normalized.parentId) {
    const parent = widgets[normalized.parentId];
    if (!parent) {
      throw new Error(`Unknown parent widget: ${normalized.parentId}`);
    }
    const parentChildIds = Array.isArray(parent.childIds) ? parent.childIds : [];
    if (!parentChildIds.includes(normalized.id)) {
      widgets[normalized.parentId] = {
        ...parent,
        childIds: [...parentChildIds, normalized.id]
      };
    }
  }
  let windows = state.windows;
  if (normalized.windowId) {
    const window = windows[normalized.windowId];
    if (window && !window.rootWidgetId) {
      windows = {
        ...windows,
        [normalized.windowId]: { ...window, rootWidgetId: normalized.id }
      };
    }
  }
  return {
    ...state,
    idCounters: alloc.counters,
    widgets,
    windows
  };
}

function collectWidgetSubtreeIds(widgets, rootIds) {
  const childrenByParent = new Map();
  for (const [id, widget] of Object.entries(widgets ?? {})) {
    const parentId = widget.parentId;
    if (!parentId) continue;
    let list = childrenByParent.get(parentId);
    if (!list) {
      list = [];
      childrenByParent.set(parentId, list);
    }
    list.push(id);
  }
  const pending = [...new Set(rootIds.filter(Boolean))];
  const toRemove = new Set();
  while (pending.length > 0) {
    const current = pending.pop();
    if (!current || toRemove.has(current)) continue;
    toRemove.add(current);
    const children = childrenByParent.get(current);
    if (children) {
      pending.push(...children);
    }
  }
  return toRemove;
}

export function removeWindow(state, windowId, options = {}) {
  const window = state.windows?.[windowId];
  if (!window) {
    return state;
  }
  const widgets = state.widgets ?? {};
  const rootIds = [];
  if (window.rootWidgetId) {
    rootIds.push(window.rootWidgetId);
  }
  for (const [id, widget] of Object.entries(widgets)) {
    if (widget.windowId === windowId) {
      rootIds.push(id);
    }
  }
  const toRemove = collectWidgetSubtreeIds(widgets, rootIds);

  let nextWidgets = widgets;
  if (toRemove.size > 0) {
    nextWidgets = {};
    for (const [id, widget] of Object.entries(widgets)) {
      if (!toRemove.has(id)) {
        nextWidgets[id] = widget;
      }
    }
  } else {
    nextWidgets = { ...widgets };
  }

  let nextState = { ...state, widgets: nextWidgets };

  if (toRemove.size > 0 && nextState.presentations) {
    const nextPresentations = {};
    for (const [id, presentation] of Object.entries(nextState.presentations)) {
      if (presentation.widgetId && toRemove.has(presentation.widgetId)) {
        continue;
      }
      nextPresentations[id] = presentation;
    }
    nextState = { ...nextState, presentations: nextPresentations };
  }

  const nextWindows = { ...nextState.windows };
  delete nextWindows[windowId];
  nextState = { ...nextState, windows: nextWindows };

  const tasks = { ...nextState.tasks };
  const task = tasks[window.taskId];
  if (task) {
    const windowIds = task.windowIds.filter((id) => id !== windowId);
    const activeWindowId = task.activeWindowId === windowId ? (windowIds[0] ?? null) : task.activeWindowId;
    tasks[window.taskId] = { ...task, windowIds, activeWindowId };
  }
  nextState = { ...nextState, tasks };

  if (nextState.windowCauses && nextState.windowCauses[windowId]) {
    const nextCauses = { ...nextState.windowCauses };
    delete nextCauses[windowId];
    nextState = { ...nextState, windowCauses: nextCauses };
  }

  if (nextState.layout?.nodes) {
    const layout = nextState.layout;
    let changed = false;
    const nodes = {};
    for (const [id, node] of Object.entries(layout.nodes)) {
      if (node?.kind === "leaf" && node.props?.windowId === windowId) {
        nodes[id] = { ...node, props: { ...(node.props ?? {}), windowId: null } };
        changed = true;
      } else {
        nodes[id] = node;
      }
    }
    if (changed) {
      nextState = { ...nextState, layout: { ...layout, nodes } };
    }
  }

  const focus = nextState.focus;
  if (focus && (focus.windowId === windowId || (focus.widgetId && toRemove.has(focus.widgetId)))) {
    nextState = setFocusCore(nextState, null, options.reason ?? "command");
  }

  return nextState;
}

export function addPresentation(state, presentation) {
  if (!presentation) {
    throw new Error("Presentation is required");
  }
  const alloc = presentation.id
    ? { id: presentation.id, counters: state.idCounters }
    : allocateId(state.idCounters, "presentation");
  const normalized = normalizePresentation({ ...presentation, id: alloc.id });
  const presentations = { ...state.presentations, [normalized.id]: normalized };
  return { ...state, idCounters: alloc.counters, presentations };
}

export function appendRecording(state, recording) {
  const recordingStore = appendRecordingCore(state.recordingStore ?? null, recording);
  return { ...state, recordingStore };
}

function updateWatchesFromEntry(state, entry) {
  if (!entry || typeof entry !== "object" || !Array.isArray(state.watches) || state.watches.length === 0) {
    return state;
  }
  let changed = false;
  const nextWatches = state.watches.map((watch) => {
    const matchByEntry = Boolean(watch.entryId && watch.entryId === entry.id);
    const matchByPresentation = Boolean(
      watch.presentationId && entry.presentationId && watch.presentationId === entry.presentationId
    );
    if (!matchByEntry && !matchByPresentation) {
      return watch;
    }
    const valueSummary = typeof entry.text === "string" ? entry.text : watch.valueSummary ?? "";
    changed = true;
    return {
      ...watch,
      entryId: entry.id ?? watch.entryId,
      recordingId: entry.recordingId ?? watch.recordingId,
      valueSummary,
      updatedAt: Number.isInteger(entry.ts) ? entry.ts : watch.updatedAt ?? null
    };
  });
  return changed ? { ...state, watches: nextWatches } : state;
}

export function appendRecordingEntry(state, entry) {
  const recordingStore = appendEntryCore(state.recordingStore ?? null, entry);
  const normalizedEntry = recordingStore.entries?.[entry?.id] ?? null;
  const nextState = { ...state, recordingStore };
  return updateWatchesFromEntry(nextState, normalizedEntry);
}

export function attachRecordingAnchor(state, anchor) {
  const recordingStore = attachAnchorCore(state.recordingStore ?? null, anchor);
  return { ...state, recordingStore };
}

export function setRecordingEntryFolded(state, entryId, folded) {
  const recordingStore = setEntryFoldedCore(state.recordingStore ?? null, entryId, folded);
  return { ...state, recordingStore };
}

export function setRecordingCollapsed(state, recordingId, collapsed) {
  const recordingStore = setRecordingCollapsedCore(state.recordingStore ?? null, recordingId, collapsed);
  return { ...state, recordingStore };
}

function resolveWatchSource(state, options = {}) {
  const item = options.item ?? null;
  const entryId = options.entryId ?? item?.entryId ?? null;
  const presentationId = options.presentationId ?? item?.presentationId ?? null;
  const store = state.recordingStore ?? null;
  const resolvedEntryId =
    entryId ??
    (presentationId ? store?.byPresentation?.[presentationId] ?? null : null);
  const entry = resolvedEntryId ? store?.entries?.[resolvedEntryId] ?? null : null;
  const recordingId = options.recordingId ?? item?.recordingId ?? entry?.recordingId ?? null;
  const presentation = presentationId ? state.presentations?.[presentationId] ?? null : null;
  const label =
    options.label ??
    item?.label ??
    presentation?.label ??
    (typeof entry?.text === "string" && entry.text.length > 0 ? truncateTranscriptText(entry.text, 72) : null) ??
    resolvedEntryId ??
    presentationId ??
    recordingId ??
    "watch";
  const valueSummary =
    options.valueSummary ??
    (typeof entry?.text === "string" ? entry.text : null) ??
    (typeof presentation?.metadata?.summary === "string" ? presentation.metadata.summary : null) ??
    "";
  return {
    entryId: resolvedEntryId,
    presentationId,
    recordingId,
    label,
    valueSummary
  };
}

export function pinWatch(state, options = {}) {
  const source = resolveWatchSource(state, options);
  if (!source.entryId && !source.presentationId && !source.recordingId) {
    return state;
  }
  const existing = (state.watches ?? []).find((watch) => {
    if (source.entryId && watch.entryId && watch.entryId === source.entryId) return true;
    if (source.presentationId && watch.presentationId && watch.presentationId === source.presentationId) return true;
    return false;
  });
  if (existing) {
    const nextWatches = (state.watches ?? []).map((watch) =>
      watch.id === existing.id
        ? {
            ...watch,
            label: source.label ?? watch.label,
            recordingId: source.recordingId ?? watch.recordingId,
            valueSummary: source.valueSummary ?? watch.valueSummary
          }
        : watch
    );
    return { ...state, watches: nextWatches };
  }
  const id = typeof options.id === "string" && options.id.length > 0 ? options.id : `watch-${state.watchSeq ?? 1}`;
  const watch = normalizeWatch(
    {
      id,
      kind: options.kind ?? "entry",
      label: source.label,
      entryId: source.entryId,
      presentationId: source.presentationId,
      recordingId: source.recordingId,
      valueSummary: source.valueSummary,
      pinned: true,
      updatedAt: Number.isInteger(options.ts) ? options.ts : null,
      metadata: options.metadata ?? {}
    },
    (state.watches ?? []).length
  );
  return {
    ...state,
    watches: [...(state.watches ?? []), watch],
    watchSeq: (state.watchSeq ?? 1) + 1
  };
}

export function unpinWatch(state, watchId) {
  if (typeof watchId !== "string" || watchId.length === 0) return state;
  const existing = Array.isArray(state.watches) ? state.watches : [];
  if (!existing.some((watch) => watch.id === watchId)) {
    return state;
  }
  return {
    ...state,
    watches: existing.filter((watch) => watch.id !== watchId)
  };
}

function resolveEditList(options = {}) {
  if (Array.isArray(options.edits) && options.edits.length > 0) {
    return options.edits;
  }
  if (options.edit && typeof options.edit === "object") {
    return [options.edit];
  }
  if (options.placeId || options.before !== undefined || options.after !== undefined || options.value !== undefined) {
    return [
      {
        placeId: options.placeId ?? null,
        label: options.label ?? null,
        before: options.before ?? null,
        after: options.after ?? options.value ?? null,
        metadata: options.metadata ?? {}
      }
    ];
  }
  return [];
}

export function stageEdit(state, options = {}) {
  const edits = resolveEditList(options);
  if (edits.length === 0) return state;
  const id = typeof options.id === "string" && options.id.length > 0 ? options.id : `edit-group-${state.editSeq ?? 1}`;
  const label =
    options.label ??
    edits[0]?.label ??
    edits[0]?.placeId ??
    id;
  const group = normalizeEditGroup(
    {
      id,
      label,
      status: "staged",
      edits,
      createdAt: Number.isInteger(options.ts) ? options.ts : null,
      metadata: options.metadata ?? {}
    },
    (state.editGroups ?? []).length
  );
  return {
    ...state,
    editGroups: [...(state.editGroups ?? []), group],
    editSeq: (state.editSeq ?? 1) + 1
  };
}

export function applyEditGroup(state, editGroupId, options = {}) {
  if (typeof editGroupId !== "string" || editGroupId.length === 0) return state;
  const groups = Array.isArray(state.editGroups) ? state.editGroups : [];
  let changed = false;
  const nextGroups = groups.map((group) => {
    if (group.id !== editGroupId) return group;
    changed = true;
    return {
      ...group,
      status: "applied",
      appliedAt: Number.isInteger(options.ts) ? options.ts : group.appliedAt ?? null
    };
  });
  return changed ? { ...state, editGroups: nextGroups } : state;
}

export function undoEditGroup(state, editGroupId, options = {}) {
  if (typeof editGroupId !== "string" || editGroupId.length === 0) return state;
  const groups = Array.isArray(state.editGroups) ? state.editGroups : [];
  let changed = false;
  const nextGroups = groups.map((group) => {
    if (group.id !== editGroupId) return group;
    changed = true;
    return {
      ...group,
      status: "undone",
      undoneAt: Number.isInteger(options.ts) ? options.ts : group.undoneAt ?? null
    };
  });
  return changed ? { ...state, editGroups: nextGroups } : state;
}

function resolveInvocationId(state, requestedId = null) {
  const history = Array.isArray(state.commandHistory) ? state.commandHistory : [];
  const used = new Set(
    history
      .map((entry) => entry?.id)
      .filter((id) => typeof id === "string" && id.length > 0)
  );
  if (typeof requestedId === "string" && requestedId.length > 0) {
    if (!used.has(requestedId)) return requestedId;
    let suffix = 2;
    while (used.has(`${requestedId}-${suffix}`)) {
      suffix += 1;
    }
    return `${requestedId}-${suffix}`;
  }
  let next = history.length + 1;
  while (used.has(`inv-${next}`)) {
    next += 1;
  }
  return `inv-${next}`;
}

export function recordCommandInvocation(state, invocation) {
  const normalized = normalizeInvocation(invocation);
  const nextInvocation = {
    ...normalized,
    id: resolveInvocationId(state, normalized.id)
  };
  return { ...state, commandHistory: [...(state.commandHistory ?? []), nextInvocation] };
}

export function patchCommandInvocation(state, invocationId, patch = {}) {
  if (typeof invocationId !== "string" || invocationId.length === 0) {
    return state;
  }
  const history = Array.isArray(state.commandHistory) ? state.commandHistory : [];
  let changed = false;
  const nextHistory = history.map((entry) => {
    if (entry?.id !== invocationId) return entry;
    changed = true;
    return {
      ...entry,
      ...(patch && typeof patch === "object" ? patch : {}),
      id: invocationId
    };
  });
  return changed ? { ...state, commandHistory: nextHistory } : state;
}

export function upsertCommandInvocation(state, invocation) {
  const normalized = normalizeInvocation(invocation);
  const id = normalized.id ?? resolveInvocationId(state, null);
  const history = Array.isArray(state.commandHistory) ? state.commandHistory : [];
  const index = history.findIndex((entry) => entry?.id === id);
  if (index < 0) {
    return {
      ...state,
      commandHistory: [...history, { ...normalized, id }]
    };
  }
  const nextHistory = [...history];
  nextHistory[index] = {
    ...nextHistory[index],
    ...normalized,
    id
  };
  return {
    ...state,
    commandHistory: nextHistory
  };
}

export function requestCapability(state, capability, options = {}) {
  if (!capability) return state;
  const capabilities = normalizeCapabilities(state.capabilities ?? null);
  const requests = normalizeCapabilityRequests(state.capabilityRequests ?? null);
  const allocation = allocateCapabilityRequestId(state);
  const request = normalizeCapabilityRequest(
    {
      id: allocation.id,
      capability,
      reason: options.reason ?? null,
      status: "pending",
      decisionReason: null,
      decidedBy: null,
      taskId: options.taskId ?? null,
      windowId: options.windowId ?? null,
      commandId: options.commandId ?? null
    },
    requests.length
  );
  const nextCaps = appendCapabilityLog(capabilities, {
    action: "request",
    capability,
    reason: options.reason ?? null,
    taskId: options.taskId ?? null,
    windowId: options.windowId ?? null,
    commandId: options.commandId ?? null
  });
  return {
    ...state,
    capabilities: nextCaps,
    capabilityRequests: [...requests, request],
    capabilityRequestSeq: allocation.nextSeq
  };
}

export function grantCapability(state, capability, options = {}) {
  if (!capability) return state;
  const capabilities = normalizeCapabilities(state.capabilities ?? null);
  if (capabilities.granted.includes(capability)) {
    return state;
  }
  const granted = [...capabilities.granted, capability].sort();
  const nextCaps = appendCapabilityLog({ ...capabilities, granted }, {
    action: "grant",
    capability,
    reason: options.reason ?? null,
    taskId: options.taskId ?? null,
    windowId: options.windowId ?? null,
    commandId: options.commandId ?? null
  });
  return { ...state, capabilities: nextCaps };
}

export function revokeCapability(state, capability, options = {}) {
  if (!capability) return state;
  const capabilities = normalizeCapabilities(state.capabilities ?? null);
  if (!capabilities.granted.includes(capability)) {
    return state;
  }
  const granted = capabilities.granted.filter((entry) => entry !== capability);
  const nextCaps = appendCapabilityLog({ ...capabilities, granted }, {
    action: "revoke",
    capability,
    reason: options.reason ?? null,
    taskId: options.taskId ?? null,
    windowId: options.windowId ?? null,
    commandId: options.commandId ?? null
  });
  return { ...state, capabilities: nextCaps };
}

export function setSafeMode(state, enabled, options = {}) {
  const capabilities = normalizeCapabilities(state.capabilities ?? null);
  const nextEnabled = Boolean(enabled);
  if (capabilities.safeMode === nextEnabled) {
    return state;
  }
  const nextCaps = appendCapabilityLog({ ...capabilities, safeMode: nextEnabled }, {
    action: nextEnabled ? "safe-mode-enabled" : "safe-mode-disabled",
    reason: options.reason ?? null,
    taskId: options.taskId ?? null,
    windowId: options.windowId ?? null,
    commandId: options.commandId ?? null
  });
  return { ...state, capabilities: nextCaps };
}

export function hasCapability(state, capability) {
  if (!capability) return true;
  const capabilities = state.capabilities ?? {};
  if (capabilities.safeMode) return false;
  return Array.isArray(capabilities.granted) && capabilities.granted.includes(capability);
}

export function evaluateCapabilityRequest(state, request, policyOverride = null) {
  if (!request || typeof request !== "object") {
    return { decision: "ask", reason: "Missing request" };
  }
  if (!request.capability) {
    return { decision: "ask", reason: "Missing capability" };
  }
  const capabilities = normalizeCapabilities(state.capabilities ?? null);
  if (capabilities.safeMode) {
    return { decision: "deny", reason: "Safe mode" };
  }
  if (capabilities.granted.includes(request.capability)) {
    return { decision: "grant", reason: "Already granted" };
  }
  return resolveCapabilityPolicyDecision(policyOverride ?? state.capabilityPolicy ?? null, request.capability ?? null);
}

export function applyCapabilityDecision(state, requestId, decision, options = {}) {
  if (!requestId) return state;
  const requests = normalizeCapabilityRequests(state.capabilityRequests ?? null);
  const index = requests.findIndex((request) => request.id === requestId);
  if (index === -1) return state;
  const normalizedDecision = CAPABILITY_POLICY_DECISIONS.includes(decision) ? decision : "ask";
  if (normalizedDecision === "ask") return state;
  const request = requests[index];
  if (request.status !== "pending" && options.force !== true) {
    return state;
  }

  const nextStatus = normalizedDecision === "grant" ? "granted" : "denied";
  const updatedRequest = {
    ...request,
    status: nextStatus,
    decisionReason: options.reason ?? request.decisionReason ?? null,
    decidedBy: options.decidedBy ?? request.decidedBy ?? null
  };
  const nextRequests = [...requests];
  nextRequests[index] = updatedRequest;

  let nextState = { ...state, capabilityRequests: nextRequests };
  if (normalizedDecision === "grant") {
    nextState = grantCapability(nextState, request.capability, {
      reason: options.reason ?? null,
      taskId: request.taskId ?? null,
      windowId: request.windowId ?? null,
      commandId: options.commandId ?? null
    });
  } else {
    const capabilities = normalizeCapabilities(nextState.capabilities ?? null);
    nextState = {
      ...nextState,
      capabilities: appendCapabilityLog(capabilities, {
        action: "deny",
        capability: request.capability ?? null,
        reason: options.reason ?? null,
        taskId: request.taskId ?? null,
        windowId: request.windowId ?? null,
        commandId: options.commandId ?? null
      })
    };
  }
  return nextState;
}

export function autoRunCapabilityPolicy(state, options = {}) {
  const requests = normalizeCapabilityRequests(state.capabilityRequests ?? null);
  let nextState = state;
  for (const request of requests) {
    if (request.status !== "pending") continue;
    const evaluation = evaluateCapabilityRequest(nextState, request, options.policy ?? null);
    if (evaluation.decision === "ask") continue;
    nextState = applyCapabilityDecision(nextState, request.id, evaluation.decision, {
      reason: evaluation.reason ?? null,
      decidedBy: options.decidedBy ?? "policy",
      commandId: options.commandId ?? null
    });
  }
  return nextState;
}

export function setLayout(state, layout) {
  const normalized = normalizeLayout(layout, state.idCounters);
  return { ...state, layout: normalized.layout, idCounters: normalized.counters };
}

export function setCustomization(state, customization) {
  const normalized = normalizeCustomization(customization);
  return {
    ...state,
    customization: normalized,
    theme: normalizeThemeTokens(normalized.effective?.theme?.tokens ?? null)
  };
}

export function patchCustomization(state, layer, patch) {
  const nextCustomization = patchCustomizationLayer(
    state.customization ?? null,
    normalizeCustomizationLayerName(layer),
    patch ?? {}
  );
  return setCustomization(state, nextCustomization);
}

export function setThemePreset(state, presetId, options = {}) {
  if (typeof presetId !== "string" || presetId.length === 0) return state;
  const layer = normalizeCustomizationLayerName(options.layer ?? "session");
  const patch = {
    theme: {
      presetId,
      mode: options.mode ?? null
    }
  };
  return patchCustomization(state, layer, patch);
}

export function setThemeOverrides(state, overrides, options = {}) {
  const layer = normalizeCustomizationLayerName(options.layer ?? "session");
  return patchCustomization(state, layer, {
    theme: {
      overrides: overrides ?? {}
    }
  });
}

export function resetThemeOverrides(state, options = {}) {
  const layer = normalizeCustomizationLayerName(options.layer ?? "session");
  return patchCustomization(state, layer, {
    theme: {
      overrides: {}
    }
  });
}

export function setPaneKeymapProfile(state, pane, profileId, options = {}) {
  if (!KEYMAP_PANES.includes(pane)) return state;
  if (typeof profileId !== "string" || profileId.length === 0) return state;
  const layer = normalizeCustomizationLayerName(options.layer ?? "session");
  return patchCustomization(state, layer, {
    keymaps: {
      paneProfiles: {
        [pane]: profileId
      }
    }
  });
}

export function setBeginnerMode(state, enabled, options = {}) {
  const layer = normalizeCustomizationLayerName(options.layer ?? "session");
  return patchCustomization(state, layer, {
    beginnerMode: {
      enabled: Boolean(enabled)
    }
  });
}

export function dismissGuidance(state, guidanceId, options = {}) {
  if (typeof guidanceId !== "string" || guidanceId.length === 0) return state;
  const layer = normalizeCustomizationLayerName(options.layer ?? "session");
  const current = state.customization?.layers?.[layer]?.guidance?.dismissed ?? [];
  return patchCustomization(state, layer, {
    guidance: {
      dismissed: [...current, guidanceId]
    }
  });
}

export function setTheme(state, theme) {
  const normalizedTheme = normalizeThemeTokens(theme);
  const nextCustomization = patchCustomizationLayer(state.customization ?? null, "session", {
    theme: {
      mode: normalizedTheme.mode,
      overrides: normalizedTheme
    }
  });
  return {
    ...state,
    customization: nextCustomization,
    theme: normalizedTheme
  };
}

export function setThemeMode(state, mode) {
  const nextCustomization = patchCustomizationLayer(state.customization ?? null, "session", {
    theme: {
      mode
    }
  });
  return setCustomization(state, nextCustomization);
}

export function recordDomEscape(state, entry, options = {}) {
  const escapes = normalizeDomEscapes(state.domEscapes ?? null);
  const normalized = normalizeDomEscape(
    { ...entry, ts: entry?.ts ?? options.ts ?? null },
    escapes.length
  );
  const nextEscapes = [...escapes, normalized];
  const trimmed =
    nextEscapes.length > DOM_ESCAPE_HISTORY_LIMIT
      ? nextEscapes.slice(nextEscapes.length - DOM_ESCAPE_HISTORY_LIMIT)
      : nextEscapes;
  return { ...state, domEscapes: trimmed };
}

export function recordEvent(state, entry) {
  if (!entry || typeof entry !== "object") {
    throw new Error("Event entry must be an object");
  }
  const eventLog = recordEventLog(state.eventLog ?? null, entry);
  return { ...state, eventLog };
}

function buildUiEvent(options, type, payload) {
  if (!options?.recordEvent) return null;
  if (!Number.isInteger(options.seq)) {
    throw new Error("UI event requires integer seq when recording");
  }
  const entry = {
    seq: options.seq,
    type,
    payload: payload ?? {}
  };
  if (Number.isInteger(options.ts)) {
    entry.ts = options.ts;
  }
  if (typeof options.target === "string") {
    entry.target = options.target;
  }
  return entry;
}

function resolveUiMetricNow(options = {}) {
  if (Number.isFinite(options.ts)) {
    return Number(options.ts);
  }
  if (typeof options.now === "function") {
    const value = Number(options.now());
    if (Number.isFinite(value)) {
      return value;
    }
  }
  return null;
}

function recordUiQualityMetric(options = {}, payload = null) {
  const collector = options?.qualityCollector ?? null;
  if (!collector || typeof collector.recordUiTurn !== "function" || !payload || typeof payload !== "object") {
    return;
  }
  collector.recordUiTurn(payload);
}

export function enqueueUiSignal(state, signal, options = {}) {
  const ui = normalizeUiState(state.ui ?? null);
  const normalized = normalizeUiSignal(signal, ui.queue.length);
  const nextQueue = [...ui.queue, normalized];
  let nextState = { ...state, ui: { ...ui, queue: nextQueue } };
  const event = buildUiEvent(options, "ui:signal.enqueue", {
    signal: normalized,
    queueLength: nextQueue.length
  });
  if (event) {
    nextState = recordEvent(nextState, event);
  }
  return nextState;
}

export function beginUiTurn(state, options = {}) {
  const ui = normalizeUiState(state.ui ?? null);
  if (ui.turn) {
    throw new Error("UI turn already active");
  }
  const turnId = `turn-${ui.nextTurnId}`;
  const drainSignals = options.drainSignals !== false;
  const signals = drainSignals ? ui.queue : [];
  const queue = drainSignals ? [] : ui.queue;
  const turn = {
    id: turnId,
    phase: "signals",
    signals,
    commitPolicy: options.commitPolicy ?? "rAF",
    yielded: false,
    yieldReason: null,
    startedAt: resolveUiMetricNow(options)
  };
  let nextState = {
    ...state,
    ui: {
      ...ui,
      queue,
      turn,
      nextTurnId: ui.nextTurnId + 1
    }
  };
  const event = buildUiEvent(options, "ui:turn.begin", {
    turnId,
    commitPolicy: turn.commitPolicy,
    signalCount: signals.length,
    drainedSignals: drainSignals
  });
  if (event) {
    nextState = recordEvent(nextState, event);
  }
  recordUiQualityMetric(options, {
    turnId,
    phase: "signals",
    commitPolicy: turn.commitPolicy,
    signalCount: signals.length,
    yielded: false,
    ts: turn.startedAt
  });
  return nextState;
}

export function advanceUiTurn(state, phase, options = {}) {
  const ui = normalizeUiState(state.ui ?? null);
  if (!ui.turn) {
    throw new Error("UI turn not active");
  }
  const nextPhase = phase ?? ui.turn.phase;
  if (!UI_TURN_PHASES.includes(nextPhase) && nextPhase !== "yielded") {
    throw new Error(`Unknown UI turn phase: ${nextPhase}`);
  }
  if (UI_TURN_PHASES.includes(nextPhase) && UI_TURN_PHASES.includes(ui.turn.phase)) {
    const currentIndex = UI_TURN_PHASES.indexOf(ui.turn.phase);
    const nextIndex = UI_TURN_PHASES.indexOf(nextPhase);
    if (nextIndex < currentIndex) {
      throw new Error("UI turn phase cannot move backwards");
    }
  }
  let nextState = { ...state, ui: { ...ui, turn: { ...ui.turn, phase: nextPhase } } };
  const event = buildUiEvent(options, "ui:turn.phase", {
    turnId: ui.turn.id,
    phase: nextPhase
  });
  if (event) {
    nextState = recordEvent(nextState, event);
  }
  recordUiQualityMetric(options, {
    turnId: ui.turn.id,
    phase: nextPhase,
    commitPolicy: ui.turn.commitPolicy,
    signalCount: Array.isArray(ui.turn.signals) ? ui.turn.signals.length : 0,
    yielded: nextPhase === "yielded" || ui.turn.yielded,
    ts: resolveUiMetricNow(options)
  });
  return nextState;
}

export function yieldUiTurn(state, reason = null, options = {}) {
  let next = advanceUiTurn(state, "yielded", { recordEvent: false });
  const ui = normalizeUiState(next.ui ?? null);
  if (!ui.turn) return next;
  next = {
    ...next,
    ui: {
      ...ui,
      turn: { ...ui.turn, yielded: true, yieldReason: reason }
    }
  };
  const event = buildUiEvent(options, "ui:turn.yield", {
    turnId: ui.turn.id,
    reason
  });
  if (event) {
    next = recordEvent(next, event);
  }
  recordUiQualityMetric(options, {
    turnId: ui.turn.id,
    phase: "yielded",
    commitPolicy: ui.turn.commitPolicy,
    signalCount: Array.isArray(ui.turn.signals) ? ui.turn.signals.length : 0,
    yielded: true,
    ts: resolveUiMetricNow(options)
  });
  return next;
}

export function endUiTurn(state, options = {}) {
  const ui = normalizeUiState(state.ui ?? null);
  if (!ui.turn) return state;
  const turnId = ui.turn.id;
  const turnPhase = ui.turn.phase;
  const turnYielded = ui.turn.yielded;
  const endedAt = resolveUiMetricNow(options);
  const durationMs =
    Number.isFinite(ui.turn.startedAt) && Number.isFinite(endedAt)
      ? Math.max(0, Number(endedAt) - Number(ui.turn.startedAt))
      : null;
  const historyEntry = {
    id: turnId,
    phase: turnPhase,
    yielded: turnYielded,
    commitPolicy: ui.turn.commitPolicy
  };
  const history = [...ui.history, historyEntry];
  const trimmed =
    history.length > UI_TURN_HISTORY_LIMIT
      ? history.slice(history.length - UI_TURN_HISTORY_LIMIT)
      : history;
  let nextState = { ...state, ui: { ...ui, turn: null, history: trimmed } };
  const event = buildUiEvent(options, "ui:turn.end", {
    turnId,
    phase: turnPhase,
    yielded: turnYielded
  });
  if (event) {
    nextState = recordEvent(nextState, event);
  }
  recordUiQualityMetric(options, {
    turnId,
    phase: turnPhase,
    commitPolicy: ui.turn.commitPolicy,
    signalCount: Array.isArray(ui.turn.signals) ? ui.turn.signals.length : 0,
    yielded: turnYielded,
    durationMs,
    ts: endedAt
  });
  return nextState;
}

export function setSelection(state, selection) {
  return { ...state, selection: normalizeSelection(selection) };
}

function resolveListItemIds(state, listId, itemIds = null) {
  if (Array.isArray(itemIds) && itemIds.length > 0) {
    return itemIds.map((id) => String(id));
  }
  const widget = listId ? state.widgets?.[listId] : null;
  const list = widget?.props?.items ?? widget?.model?.items ?? [];
  if (!Array.isArray(list)) return [];
  return list.map((item, index) => {
    if (item && typeof item === "object" && !Array.isArray(item)) {
      return String(item.id ?? item.key ?? index);
    }
    return String(item ?? index);
  });
}

function normalizeListSelectionMode(mode, multiple) {
  if (mode === "toggle") return multiple ? "toggle" : "replace";
  if (mode === "range") return multiple ? "range" : "replace";
  return "replace";
}

function orderSelectedTargets(selected, listItemIds) {
  const selectedSet = new Set([...selected].map((id) => String(id)));
  const ordered = [];
  for (const id of listItemIds) {
    if (selectedSet.has(id)) ordered.push(id);
  }
  if (ordered.length > 0) return ordered;
  return [...selectedSet];
}

export function updateListSelection(state, options = {}) {
  const listId = options.listId ?? null;
  const itemId = options.itemId ?? null;
  if (!listId || !itemId) {
    return state;
  }

  const listItemIds = resolveListItemIds(state, listId, options.listItemIds ?? null);
  const targetId = String(itemId);
  if (listItemIds.length > 0 && !listItemIds.includes(targetId)) {
    return state;
  }
  const multiple = Boolean(options.multiple ?? false);
  const mode = normalizeListSelectionMode(options.mode ?? "replace", multiple);

  const existing =
    state.selection?.metadata?.listId === listId && Array.isArray(state.selection?.targetIds)
      ? state.selection
      : null;
  const selected = new Set((existing?.targetIds ?? []).map((id) => String(id)));
  let anchorId = existing?.anchorId ? String(existing.anchorId) : targetId;

  if (mode === "replace") {
    selected.clear();
    selected.add(targetId);
    anchorId = targetId;
  } else if (mode === "toggle") {
    if (selected.has(targetId)) {
      selected.delete(targetId);
    } else {
      selected.add(targetId);
      anchorId = targetId;
    }
  } else if (mode === "range") {
    const anchorIndex = listItemIds.indexOf(anchorId);
    const targetIndex = listItemIds.indexOf(targetId);
    if (anchorIndex === -1 || targetIndex === -1) {
      selected.clear();
      selected.add(targetId);
      anchorId = targetId;
    } else {
      selected.clear();
      const start = Math.min(anchorIndex, targetIndex);
      const end = Math.max(anchorIndex, targetIndex);
      for (let index = start; index <= end; index += 1) {
        const id = listItemIds[index];
        if (id !== undefined && id !== null) {
          selected.add(String(id));
        }
      }
    }
  }

  const targetIds = orderSelectedTargets(selected, listItemIds);
  if (targetIds.length === 0) {
    return setSelection(state, null);
  }

  return setSelection(state, {
    id: targetIds[0],
    kind: "list-item",
    targetIds,
    anchorId: anchorId ?? targetIds[0],
    metadata: {
      ...(existing?.metadata ?? {}),
      listId,
      multiple
    }
  });
}

export function setFocus(state, target, reason = "command", seq = null) {
  return setFocusCore(state, target, reason, seq);
}

export function initLayout(state, rootSpec) {
  const created = createLayout(rootSpec, state.idCounters);
  return { ...state, layout: created.layout, idCounters: created.counters };
}

export function splitLayout(state, targetId, axis = "h", ratio = 0.5, options = {}) {
  const updated = splitLayoutNode(state.layout, state.idCounters, targetId, axis, ratio, options);
  return { ...state, layout: updated.layout, idCounters: updated.counters };
}

export function wrapInTabs(state, targetId, options = {}) {
  const updated = wrapInTabsNode(state.layout, state.idCounters, targetId, options);
  return { ...state, layout: updated.layout, idCounters: updated.counters };
}

export function setActiveTab(state, tabsId, tabId) {
  const updated = setActiveTabNode(state.layout, state.idCounters, tabsId, tabId);
  return { ...state, layout: updated.layout, idCounters: updated.counters };
}

export function dockLayout(state, targetId, region) {
  const updated = dockLayoutNode(state.layout, state.idCounters, targetId, region);
  return { ...state, layout: updated.layout, idCounters: updated.counters };
}

export function setCommandState(state, id, enabled, reason = null) {
  const commands = { ...(state.commands ?? {}) };
  let reasonId = commands[id]?.reasonId ?? null;
  let nextState = state;
  if (enabled === false && reason) {
    const alloc = allocateId(state.idCounters, "reason", "reason");
    reasonId = alloc.id;
    const disableReasons = { ...(state.disableReasons ?? {}) };
    disableReasons[reasonId] = {
      id: reasonId,
      reason,
      ts: null,
      details: {}
    };
    nextState = { ...state, idCounters: alloc.counters, disableReasons };
  }
  commands[id] = {
    enabled: Boolean(enabled),
    reason: reason ?? null,
    reasonId
  };
  return { ...nextState, commands };
}

export function updateWidget(state, widgetId, patch) {
  const widget = state.widgets?.[widgetId];
  if (!widget) {
    throw new Error(`Unknown widget: ${widgetId}`);
  }
  const next = typeof patch === "function" ? patch(widget) : { ...widget, ...patch };
  return {
    ...state,
    widgets: { ...state.widgets, [widgetId]: next }
  };
}

export function updateWindow(state, windowId, patch) {
  const window = state.windows?.[windowId];
  if (!window) {
    throw new Error(`Unknown window: ${windowId}`);
  }
  const next = typeof patch === "function" ? patch(window) : { ...window, ...patch };
  return {
    ...state,
    windows: { ...state.windows, [windowId]: next }
  };
}

function allocateWidgetId(state, prefix = "widget") {
  const alloc = allocateId(state.idCounters, "widget", prefix);
  return { id: alloc.id, state: { ...state, idCounters: alloc.counters } };
}

function findWindowByRole(state, role, taskId) {
  for (const window of Object.values(state.windows ?? {})) {
    if (window.metadata?.role !== role) continue;
    if (taskId && window.taskId !== taskId) continue;
    return window;
  }
  return null;
}

function summarizeFocus(state) {
  const items = [];
  const focus = state.focus;
  if (!focus) {
    items.push({ id: "focus-none", label: "Focus: none" });
    return items;
  }
  items.push({
    id: "focus-target",
    label: `Focus: task=${focus.taskId ?? "none"} window=${focus.windowId ?? "none"} widget=${
      focus.widgetId ?? "none"
    }`
  });
  const last = state.focusHistory?.[state.focusHistory.length - 1];
  if (last?.reason) {
    items.push({ id: "focus-reason", label: `Reason: ${last.reason}` });
  }
  return items;
}

function summarizeCommands(state) {
  const items = [];
  const entries = Object.entries(state.commands ?? {}).sort(([a], [b]) => a.localeCompare(b));
  for (const [id, info] of entries) {
    if (info?.enabled === false) {
      items.push({ id: `cmd-${id}`, label: `${id}: disabled (${info.reason ?? "Disabled"})` });
    } else {
      items.push({ id: `cmd-${id}`, label: `${id}: enabled` });
    }
  }
  if (items.length === 0) {
    items.push({ id: "cmd-none", label: "No command state recorded" });
  }
  return items;
}

function summarizeTasks(state) {
  const items = [];
  const tasks = state.tasks ?? {};
  const workspace = state.workspace ?? null;
  const activeId = workspace?.activeTaskId ?? null;
  const orderedIds = Array.isArray(workspace?.taskIds) ? [...workspace.taskIds] : [];
  const extraIds = Object.keys(tasks)
    .filter((id) => !orderedIds.includes(id))
    .sort((a, b) => a.localeCompare(b));
  const taskIds = [...orderedIds, ...extraIds];
  for (const id of taskIds) {
    const task = tasks[id];
    if (!task) continue;
    const flags = [];
    if (id === activeId) flags.push("active");
    if (taskIsArchived(task)) flags.push("archived");
    const suffix = flags.length > 0 ? ` (${flags.join(", ")})` : "";
    const title = task.title ?? "Untitled";
    items.push({
      id: `task-${id}`,
      label: `${title} [${id}]${suffix}`
    });
  }
  if (items.length === 0) {
    items.push({ id: "task-none", label: "No tasks" });
  }
  return items;
}

function summarizePresentations(state) {
  const items = [];
  const entries = Object.values(state.presentations ?? {}).sort((a, b) => (a.id ?? "").localeCompare(b.id ?? ""));
  for (const presentation of entries) {
    const type = presentation.type ?? "presentation";
    const objectId = presentation.objectId ?? "unknown";
    const widgetId = presentation.widgetId ?? "none";
    items.push({
      id: `pres-${presentation.id ?? "unknown"}`,
      label: `${type}(${objectId}) widget=${widgetId}`
    });
  }
  if (items.length === 0) {
    items.push({ id: "pres-none", label: "No presentations" });
  }
  return items;
}

function truncateTranscriptText(text, max = 120) {
  if (typeof text !== "string") return "";
  if (text.length <= max) return text;
  return `${text.slice(0, max - 3)}...`;
}

function formatRecordingInputSummary(recording) {
  const inputText = truncateTranscriptText(recording?.input?.text ?? "", 72);
  if (inputText.length > 0) return inputText;
  const commandId = recording?.context?.commandId ?? null;
  if (typeof commandId === "string" && commandId.length > 0) return commandId;
  return "<no input>";
}

function buildTranscriptEntryItem(state, store, entryId) {
  const entry = store.entries?.[entryId];
  if (!entry) return null;
  const kind = entry.kind ?? "text";
  const stream = entry.streamId ?? "stdout";
  const text = truncateTranscriptText(entry.text ?? "");
  const seq = entry.seq ?? "?";
  const isFolded = Boolean(entry.metadata?.folded);
  const marker = isFolded ? "[+]" : "[-]";
  const suffix = text ? `: ${text}` : "";
  const foldedSuffix = isFolded ? " [folded]" : "";
  const presentation = buildPresentationForEntry(state, entry);
  const presentationId = entry.presentationId ?? null;
  const presentationType = presentation?.type ?? "value";
  const classParts = ["ui-transcript-entry", `is-${kind}`, `is-${stream}`];
  if (isFolded) classParts.push("is-folded");
  return {
    id: `transcript-${entryId}`,
    label: `  ${marker} ${seq} ${stream} ${kind}${foldedSuffix}${suffix}`,
    entryId,
    recordingId: entry.recordingId ?? null,
    kind,
    streamId: stream,
    presentationId,
    anchorId: entry.anchorId ?? null,
    presentationType,
    folded: isFolded,
    className: classParts.join(" "),
    disabled: false
  };
}

function buildTranscriptItems(state, options = {}) {
  const store = normalizeRecordingStore(state.recordingStore ?? null);
  const entryOrder = Array.isArray(store.entryOrder) ? [...store.entryOrder] : [];
  const limit = Number.isFinite(options.limit) ? Math.max(0, options.limit) : 100;
  const limitedEntryIds = limit > 0 ? entryOrder.slice(-limit) : entryOrder;
  const limitedEntrySet = new Set(limitedEntryIds);
  const recordingOrder = Array.isArray(store.recordingOrder) ? [...store.recordingOrder] : [];
  const items = [];

  for (const recordingId of recordingOrder) {
    const recording = store.recordings?.[recordingId];
    if (!recording) continue;
    const entryIds = (Array.isArray(recording.entryIds) ? recording.entryIds : []).filter(
      (entryId) => limitedEntrySet.has(entryId) && Boolean(store.entries?.[entryId])
    );
    if (entryIds.length === 0) continue;

    const collapsed = Boolean(recording.metadata?.collapsed);
    const marker = collapsed ? "[+]" : "[-]";
    const summary = formatRecordingInputSummary(recording);
    const commandId = recording.context?.commandId ?? "repl.eval";
    const classParts = ["ui-transcript-recording"];
    if (collapsed) classParts.push("is-collapsed");
    items.push({
      id: `transcript-recording-${recordingId}`,
      label: `${marker} ${commandId}: ${summary}`,
      recordingId,
      kind: "recording",
      entryCount: entryIds.length,
      collapsed,
      selectable: false,
      className: classParts.join(" "),
      command: RECORDING_TOGGLE_COMMAND,
      disabled: false
    });
    if (collapsed) continue;

    for (const entryId of entryIds) {
      const entryItem = buildTranscriptEntryItem(state, store, entryId);
      if (entryItem) {
        items.push(entryItem);
      }
    }
  }

  if (items.length === 0) {
    items.push({ id: "transcript-none", label: "No transcript entries", disabled: true, selectable: false });
  }
  return items;
}

function isStateLike(value) {
  return (
    value &&
    typeof value === "object" &&
    Object.prototype.hasOwnProperty.call(value, "workspace") &&
    Object.prototype.hasOwnProperty.call(value, "tasks") &&
    Object.prototype.hasOwnProperty.call(value, "windows")
  );
}

function maybeRevalidateStatePresentations(state, resolver) {
  if (typeof resolver !== "function") {
    return state;
  }
  return revalidatePresentationsCore(state, resolver).state;
}

function resolveCommandResultState(result, fallback) {
  if (!result || !result.ok) return fallback;
  const value = result.result ?? null;
  if (value && typeof value === "object" && value.state && isStateLike(value.state)) {
    return value.state;
  }
  if (isStateLike(value)) return value;
  return fallback;
}

function resolveRecordingEntryIdFromAnchor(store, anchorId) {
  const byAnchor = store?.byAnchor ?? {};
  const anchors = store?.anchors ?? {};
  return byAnchor?.[anchorId]?.entryId ?? anchors?.[anchorId]?.entryId ?? null;
}

function resolveRecordingTarget(ctx) {
  const item = ctx.item ?? ctx.payload?.item ?? null;
  const entryId = ctx.entryId ?? ctx.payload?.entryId ?? item?.entryId ?? null;
  if (entryId) {
    return { entryId };
  }
  const anchorId = ctx.anchorId ?? ctx.payload?.anchorId ?? item?.anchorId ?? null;
  if (anchorId) {
    return { anchorId };
  }
  return null;
}

function resolveRecordingId(ctx) {
  const item = ctx.item ?? ctx.payload?.item ?? null;
  const explicit = ctx.recordingId ?? ctx.payload?.recordingId ?? item?.recordingId ?? null;
  if (explicit) return explicit;
  const target = resolveRecordingTarget(ctx);
  if (!target) return null;
  const store = ctx.state?.recordingStore ?? null;
  let entryId = target.entryId ?? null;
  if (!entryId && target.anchorId) {
    entryId = resolveRecordingEntryIdFromAnchor(store, target.anchorId);
  }
  return entryId ? store?.entries?.[entryId]?.recordingId ?? null : null;
}

function resolveLatestTranscriptPackage(state) {
  const store = state?.recordingStore ?? null;
  const order = Array.isArray(store?.recordingOrder) ? store.recordingOrder : [];
  for (let index = order.length - 1; index >= 0; index -= 1) {
    const recordingId = order[index];
    const pkg = store?.recordings?.[recordingId]?.input?.package ?? null;
    if (typeof pkg === "string" && pkg.length > 0) {
      return pkg;
    }
  }
  return null;
}

function buildCommandPalettePreviewText(state, registry, commandId, options = {}) {
  if (!registry) {
    return "Preview: command registry unavailable.";
  }
  if (!commandId) {
    return "Preview: select a command to inspect inferred defaults.";
  }
  const command = registry.commands?.get(commandId) ?? null;
  if (!command) {
    return `Preview: ${commandId} is unavailable.`;
  }
  const beginner = resolveEffectiveBeginnerMode(state);
  const beginnerPolicy = resolveBeginnerCommandPolicy(state, command);
  const showExplanation =
    beginner.enabled &&
    beginner.showExplanations &&
    beginnerPolicy.explanation &&
    beginnerPolicy.guidanceId &&
    !resolveGuidanceDismissed(state).has(beginnerPolicy.guidanceId);
  if (!Array.isArray(command.args) || command.args.length === 0) {
    const base = `Preview: ${commandId} has no typed arguments.`;
    if (!showExplanation) return base;
    return `${base} ${beginnerPolicy.explanation}`;
  }
  const materialized = materializeInvocation(
    command,
    { commandId, args: {} },
    {
      state,
      selection: state.selection ?? null,
      package: options.package ?? resolveLatestTranscriptPackage(state),
      taskId: options.taskId ?? null,
      windowId: options.windowId ?? null
    }
  );
  const defaults = materialized.invocation?.defaults ?? {};
  const inferred = [];
  for (const arg of command.args) {
    const source = defaults?.[arg?.name]?.source ?? null;
    if (source) {
      inferred.push(`${arg.name} <- ${source}`);
    }
  }
  const missing = Array.isArray(materialized.missing) ? materialized.missing : [];
  const status = missing.length > 0 ? `missing: ${missing.join(", ")}` : "ready";
  if (inferred.length === 0) {
    const base = `Preview: ${commandId} (${status}; no inferred defaults).`;
    if (!showExplanation) return base;
    return `${base} ${beginnerPolicy.explanation}`;
  }
  const base = `Preview: ${commandId} (${inferred.join(", ")}; ${status}).`;
  if (!showExplanation) return base;
  return `${base} ${beginnerPolicy.explanation}`;
}

function resolveBeginnerCommandPolicy(state, command) {
  const beginner = resolveEffectiveBeginnerMode(state);
  const metadata = isPlainObject(command?.metadata?.beginner) ? command.metadata.beginner : {};
  const hiddenSet = new Set(beginner.hiddenCommandIds ?? []);
  const forceVisibleSet = new Set(beginner.forceVisibleCommandIds ?? []);
  let hidden = Boolean(metadata.hidden) || hiddenSet.has(command?.id ?? "");
  if (forceVisibleSet.has(command?.id ?? "")) {
    hidden = false;
  }
  const advanced = Boolean(metadata.advanced);
  const confirm = Boolean(metadata.confirm) || (beginner.confirmAdvanced && advanced);
  const guidanceId =
    typeof metadata.guidanceId === "string" && metadata.guidanceId.length > 0
      ? metadata.guidanceId
      : command?.id
        ? `command:${command.id}`
        : null;
  const explanation =
    typeof metadata.explanation === "string" && metadata.explanation.length > 0
      ? metadata.explanation
      : null;
  return { hidden, advanced, confirm, guidanceId, explanation };
}

function buildCommandPaletteItems(registry, options = {}) {
  if (!registry) {
    return [{ id: "cmd-none", label: "No command registry available" }];
  }
  const state = options.state ?? null;
  const beginner = resolveEffectiveBeginnerMode(state);
  const beginnerEnabled = Boolean(beginner.enabled);
  const dismissedGuidance = resolveGuidanceDismissed(state);
  const filter = String(options.filter ?? "").trim().toLowerCase();
  const excludeIds = new Set(options.excludeIds ?? []);
  const entries = [...registry.commands.values()].sort((a, b) => a.id.localeCompare(b.id));
  const items = [];
  for (const cmd of entries) {
    if (excludeIds.has(cmd.id)) {
      continue;
    }
    if (cmd.metadata?.paletteHidden) {
      continue;
    }
    const beginnerPolicy = resolveBeginnerCommandPolicy(state, cmd);
    if (beginnerEnabled && beginnerPolicy.hidden) {
      continue;
    }
    const title = cmd.title ?? cmd.id;
    const doc = cmd.doc ?? "";
    const haystack = `${cmd.id} ${title} ${doc}`.toLowerCase();
    if (filter && !haystack.includes(filter)) {
      continue;
    }
    const label = title && title !== cmd.id ? `${cmd.id} — ${title}` : cmd.id;
    items.push({
      id: `cmd-${cmd.id}`,
      label,
      targetCommandId: cmd.id,
      requiresConfirmation: beginnerEnabled && beginnerPolicy.confirm,
      explanation:
        beginnerEnabled &&
        beginner.showExplanations &&
        beginnerPolicy.explanation &&
        beginnerPolicy.guidanceId &&
        !dismissedGuidance.has(beginnerPolicy.guidanceId)
          ? beginnerPolicy.explanation
          : null,
      guidanceId: beginnerPolicy.guidanceId
    });
  }
  if (items.length === 0) {
    items.push({ id: "cmd-empty", label: filter ? "No commands matched" : "No commands registered" });
  }
  return items;
}

function clampIndex(index, length) {
  if (length <= 0) return -1;
  if (!Number.isFinite(index)) return 0;
  return Math.max(0, Math.min(length - 1, Math.trunc(index)));
}

function applySelectionToItems(items, selectedIndex) {
  if (!Array.isArray(items) || items.length === 0) return items;
  return items.map((item, index) => ({
    ...item,
    selected: index === selectedIndex
  }));
}

function resolveEffectiveKeymaps(state) {
  const keymaps = state?.customization?.effective?.keymaps ?? {};
  return {
    paneProfiles: isPlainObject(keymaps.paneProfiles) ? keymaps.paneProfiles : {},
    profiles: isPlainObject(keymaps.profiles) ? keymaps.profiles : {},
    customBindings: Array.isArray(keymaps.customBindings) ? keymaps.customBindings : []
  };
}

function buildActiveKeymapBindings(state) {
  const keymaps = resolveEffectiveKeymaps(state);
  const items = [];
  for (const pane of KEYMAP_PANES) {
    const profileId = keymaps.paneProfiles?.[pane] ?? null;
    const profile = profileId ? keymaps.profiles?.[profileId] ?? null : null;
    const bindings = Array.isArray(profile?.bindings) ? profile.bindings : [];
    for (const binding of bindings) {
      items.push({
        ...binding,
        pane: binding.pane ?? pane,
        source: `profile:${profileId}`
      });
    }
  }
  for (const binding of keymaps.customBindings) {
    items.push({
      ...binding,
      source: binding.source ?? "custom"
    });
  }
  return items.filter((binding) => typeof binding.key === "string" && typeof binding.commandId === "string");
}

function buildKeybindingFingerprint(binding) {
  return [
    binding.pane ?? "",
    binding.scope ?? "",
    binding.scopeId ?? "",
    binding.key ?? ""
  ].join("|");
}

function analyzeKeymapConflicts(state) {
  const bindings = buildActiveKeymapBindings(state);
  const byFingerprint = new Map();
  const conflicts = [];
  for (const binding of bindings) {
    const fingerprint = buildKeybindingFingerprint(binding);
    const prior = byFingerprint.get(fingerprint) ?? null;
    if (prior && prior.commandId !== binding.commandId) {
      conflicts.push({
        id: `keymap-conflict-${fingerprint}`,
        pane: binding.pane ?? prior.pane ?? null,
        key: binding.key,
        scope: binding.scope ?? prior.scope ?? null,
        scopeId: binding.scopeId ?? prior.scopeId ?? null,
        replacedCommandId: prior.commandId,
        winningCommandId: binding.commandId,
        replacedSource: prior.source ?? null,
        winningSource: binding.source ?? null
      });
    }
    byFingerprint.set(fingerprint, binding);
  }
  return conflicts;
}

function buildKeybindingConflictItems(state) {
  const conflicts = analyzeKeymapConflicts(state);
  if (conflicts.length === 0) {
    return [{ id: "kb-conflict-none", label: "No keymap conflicts detected", disabled: true, selectable: false }];
  }
  return conflicts.map((conflict, index) => {
    const scopeLabel = conflict.scopeId ? `${conflict.scope}(${conflict.scopeId})` : conflict.scope;
    const paneLabel = conflict.pane ? `${conflict.pane}: ` : "";
    return {
      id: `${conflict.id}-${index}`,
      label: `${paneLabel}${scopeLabel} ${conflict.key} -> ${conflict.winningCommandId} (replaces ${conflict.replacedCommandId})`,
      key: conflict.key,
      pane: conflict.pane,
      scope: conflict.scope,
      scopeId: conflict.scopeId,
      className: "ui-keybindings-conflict",
      metadata: conflict
    };
  });
}

function buildKeybindingItems(registry, options = {}) {
  const state = options.state ?? null;
  const keymaps = resolveEffectiveKeymaps(state);
  if (!registry) {
    return [{ id: "kb-none", label: "No keybindings registered" }];
  }
  const items = [];
  for (const pane of KEYMAP_PANES) {
    const profileId = keymaps.paneProfiles?.[pane] ?? "none";
    items.push({
      id: `kb-profile-${pane}`,
      label: `profile(${pane}): ${profileId}`,
      className: "ui-keybindings-profile",
      selectable: false
    });
  }
  const scopes = Array.isArray(registry.precedence)
    ? [...registry.precedence]
    : Object.keys(registry.keymaps ?? {});
  for (const scope of scopes) {
    if (scope === "global") {
      const entries = [...registry.keymaps.global.entries()].sort(([a], [b]) => a.localeCompare(b));
      for (const [key, commandId] of entries) {
        items.push({
          id: `kb-${scope}-${key}`,
          label: `${scope}: ${key} → ${commandId ?? "unbound"}`
        });
      }
      continue;
    }
    const scoped = registry.keymaps[scope];
    if (!scoped) continue;
    const scopedEntries = [...scoped.entries()].sort(([a], [b]) => String(a).localeCompare(String(b)));
    for (const [scopeId, map] of scopedEntries) {
      const entries = [...(map?.entries?.() ?? [])].sort(([a], [b]) => a.localeCompare(b));
      for (const [key, commandId] of entries) {
        items.push({
          id: `kb-${scope}-${scopeId}-${key}`,
          label: `${scope}(${scopeId}): ${key} → ${commandId ?? "unbound"}`
        });
      }
    }
  }
  const activeBindings = buildActiveKeymapBindings(state);
  if (activeBindings.length > 0) {
    for (const [index, binding] of activeBindings.entries()) {
      const scopeLabel = binding.scopeId ? `${binding.scope}(${binding.scopeId})` : binding.scope;
      items.push({
        id: `kb-active-${index}`,
        label: `active(${binding.pane ?? "global"}): ${scopeLabel} ${binding.key} -> ${binding.commandId}`,
        className: "ui-keybindings-active"
      });
    }
  }
  if (items.length === 0) {
    items.push({ id: "kb-empty", label: "No keybindings registered" });
  }
  return items;
}

function buildKeybindingTraceContext(options, taskId) {
  const override = options?.traceContext ?? {};
  return {
    taskId: override.taskId ?? options?.taskId ?? taskId ?? null,
    contextId: override.contextId ?? options?.contextId ?? null,
    widgetId: override.widgetId ?? options?.widgetId ?? null
  };
}

function buildKeybindingTraceItems(registry, options = {}) {
  if (!registry) {
    return [{ id: "kb-trace-none", label: "No keybinding registry available" }];
  }
  const key = options.key ?? null;
  if (!key) {
    return [{ id: "kb-trace-empty", label: "No key selected for trace" }];
  }
  const ctx = options.context ?? {};
  const resolved = resolveKeyWithTrace(registry, key, ctx);
  const baseTrace = Array.isArray(resolved.trace) ? resolved.trace : [];
  const precedence = Array.isArray(registry.precedence) ? registry.precedence : [];
  const seenScopes = new Set(baseTrace.map((entry) => entry.scope));
  const trace = [...baseTrace];
  if (resolved.commandId && baseTrace.length < precedence.length) {
    for (const scope of precedence) {
      if (seenScopes.has(scope)) continue;
      const scopeId = scope === "global" ? null : (ctx?.[`${scope}Id`] ?? null);
      trace.push({
        scope,
        scopeId,
        key,
        commandId: null,
        matched: false,
        reason: "skipped-after-match"
      });
    }
  }
  if (trace.length === 0) {
    return [{ id: "kb-trace-empty", label: "No trace available" }];
  }
  return trace.map((entry, index) => {
    const scopeLabel = entry.scopeId ? `${entry.scope}(${entry.scopeId})` : entry.scope;
    const commandLabel = entry.commandId ?? "unbound";
    let suffix = "";
    if (entry.matched) {
      suffix = " (match)";
    } else if (entry.reason) {
      suffix = ` (${entry.reason})`;
    }
    return {
      id: `kb-trace-${index}-${entry.scope}`,
      label: `${scopeLabel}: ${entry.key} → ${commandLabel}${suffix}`
    };
  });
}

function buildTaskListItems(state, options = {}) {
  const tasks = state.tasks ?? {};
  const workspace = state.workspace ?? null;
  const activeId = workspace?.activeTaskId ?? null;
  const includeArchived = options.includeArchived ?? false;
  const orderedIds = Array.isArray(workspace?.taskIds) ? [...workspace.taskIds] : [];
  const extraIds = Object.keys(tasks)
    .filter((id) => !orderedIds.includes(id))
    .sort((a, b) => a.localeCompare(b));
  const taskIds = [...orderedIds, ...extraIds];
  const items = [];
  for (const id of taskIds) {
    const task = tasks[id];
    if (!task) continue;
    if (taskIsArchived(task) && !includeArchived && !orderedIds.includes(id)) {
      continue;
    }
    const flags = [];
    if (id === activeId) flags.push("active");
    if (taskIsArchived(task)) flags.push("archived");
    const suffix = flags.length > 0 ? ` (${flags.join(", ")})` : "";
    const title = task.title ?? "Untitled";
    items.push({
      id,
      label: `${title} [${id}]${suffix}`,
      taskId: id,
      selected: id === activeId
    });
  }
  if (items.length === 0) {
    items.push({ id: "task-none", label: "No tasks" });
  }
  return items;
}

function buildSessionItems(state, options = {}) {
  const sessions = state.sessions ?? {};
  const order = normalizeSessionOrder(sessions, state.sessionOrder ?? null);
  const activeId = state.activeSessionId ?? null;
  const items = [];
  for (const id of order) {
    const session = sessions[id];
    if (!session) continue;
    const flags = [];
    if (id === activeId) flags.push("active");
    const suffix = flags.length > 0 ? ` (${flags.join(", ")})` : "";
    items.push({
      id,
      label: `${session.name ?? "Session"}${suffix}`,
      sessionId: id,
      name: session.name ?? "Session",
      notes: session.notes ?? "",
      selected: id === activeId
    });
  }
  if (items.length === 0) {
    items.push({ id: "session-none", label: "No sessions", disabled: true, selectable: false });
  }
  return items;
}

function summarizeWindows(state) {
  const items = [];
  const entries = Object.values(state.windows ?? {}).sort((a, b) => a.id.localeCompare(b.id));
  for (const window of entries) {
    items.push({
      id: `win-${window.id}`,
      label: `${window.id} (${window.kind ?? "window"}) task=${window.taskId ?? "none"}`
    });
  }
  if (items.length === 0) {
    items.push({ id: "win-none", label: "No windows" });
  }
  return items;
}

function summarizeJobs(state) {
  const items = [];
  const entries = [...(state.jobs ?? [])].sort((a, b) => (a.id ?? "").localeCompare(b.id ?? ""));
  for (const job of entries) {
    const progressCurrent =
      Number.isFinite(job?.progress?.current) ? Math.max(0, Math.trunc(job.progress.current)) : null;
    const progressTotal =
      Number.isFinite(job?.progress?.total) ? Math.max(0, Math.trunc(job.progress.total)) : null;
    const progressSuffix =
      progressCurrent !== null && progressTotal !== null ? ` ${progressCurrent}/${progressTotal}` : "";
    items.push({
      id: `job-${job.id ?? "unknown"}`,
      label: `${job.title ?? job.id ?? "job"} (${job.status ?? "unknown"}${progressSuffix})`
    });
  }
  if (items.length === 0) {
    items.push({ id: "job-none", label: "No jobs" });
  }
  return items;
}

function summarizeErrors(state) {
  const items = [];
  const entries = [...(state.errors ?? [])].sort((a, b) => (a.id ?? "").localeCompare(b.id ?? ""));
  for (const error of entries) {
    items.push({
      id: `err-${error.id ?? "unknown"}`,
      label: `${error.kind ?? "error"}: ${error.message ?? ""} (${error.status ?? "open"})`
    });
  }
  if (items.length === 0) {
    items.push({ id: "err-none", label: "No errors" });
  }
  return items;
}

function summarizeEventLog(state, limit = 12) {
  const entries = state.eventLog?.entries ?? [];
  const sliced = entries.slice(-limit);
  const items = sliced.map((entry) => ({
    id: `event-${entry.seq ?? "?"}`,
    label: `${entry.seq ?? "?"} ${entry.type ?? "event"}`
  }));
  if (items.length === 0) {
    items.push({ id: "event-none", label: "No events recorded" });
  }
  return items;
}

function summarizeUiTurn(state) {
  const ui = normalizeUiState(state.ui ?? null);
  const items = [];
  if (!ui.turn) {
    items.push({ id: "turn-idle", label: "Turn: idle" });
  } else {
    items.push({ id: `turn-${ui.turn.id}`, label: `Turn: ${ui.turn.id} (${ui.turn.phase})` });
    if (ui.turn.yielded) {
      items.push({
        id: `turn-${ui.turn.id}-yield`,
        label: `Yielded: ${ui.turn.yieldReason ?? "unspecified"}`
      });
    }
  }
  items.push({ id: "turn-queue", label: `Queued signals: ${ui.queue.length}` });
  if (ui.history.length > 0) {
    const last = ui.history[ui.history.length - 1];
    items.push({
      id: "turn-last",
      label: `Last turn: ${last.id} (${last.phase})`
    });
  }
  return items;
}

function summarizeDomEscapes(state) {
  const escapes = normalizeDomEscapes(state.domEscapes ?? null);
  if (escapes.length === 0) {
    return [{ id: "dom-escape-none", label: "No DOM escapes recorded" }];
  }
  return escapes.map((entry) => ({
    id: entry.id ?? "dom-escape",
    label: `${entry.kind ?? "dom.escape"}${entry.target ? ` → ${entry.target}` : ""}`
  }));
}

function summarizeCapabilities(state) {
  const capabilities = normalizeCapabilities(state.capabilities ?? null);
  const items = [];
  items.push({
    id: "cap-safe-mode",
    label: `Safe mode: ${capabilities.safeMode ? "enabled" : "disabled"}`
  });
  if (capabilities.granted.length === 0) {
    items.push({ id: "cap-none", label: "No capabilities granted" });
  } else {
    for (const cap of capabilities.granted) {
      items.push({ id: `cap-${cap}`, label: `Granted: ${cap}` });
    }
  }
  if (capabilities.log.length > 0) {
    for (const entry of capabilities.log) {
      const action = entry.action ?? "event";
      const capability = entry.capability ? ` ${entry.capability}` : "";
      items.push({ id: `cap-log-${entry.id}`, label: `Log: ${action}${capability}` });
    }
  }
  return items;
}

function summarizeCapabilityRequests(state) {
  const requests = normalizeCapabilityRequests(state.capabilityRequests ?? null);
  const counts = {
    pending: requests.filter((request) => request.status === "pending").length,
    granted: requests.filter((request) => request.status === "granted").length,
    denied: requests.filter((request) => request.status === "denied").length
  };
  const items = [];
  if (requests.length === 0) {
    items.push({ id: "cap-req-none", label: "No capability requests" });
    return items;
  }
  items.push({
    id: "cap-req-counts",
    label: `Requests: ${counts.pending} pending, ${counts.granted} granted, ${counts.denied} denied`
  });
  for (const request of requests) {
    const capability = request.capability ?? "unknown";
    const reason = request.reason ? ` (${request.reason})` : "";
    items.push({
      id: `cap-req-${request.id}`,
      label: `${capability}: ${request.status}${reason}`
    });
  }
  return items;
}

function summarizeWatches(state) {
  const watches = Array.isArray(state.watches) ? state.watches : [];
  if (watches.length === 0) {
    return [{ id: "watch-none", label: "No pinned watches" }];
  }
  return watches.map((watch) => {
    const summary = truncateTranscriptText(watch.valueSummary ?? "", 72);
    const suffix = summary.length > 0 ? ` => ${summary}` : "";
    return {
      id: watch.id,
      label: `${watch.label ?? watch.id}${suffix}`,
      watchId: watch.id,
      entryId: watch.entryId ?? null,
      presentationId: watch.presentationId ?? null,
      recordingId: watch.recordingId ?? null
    };
  });
}

function summarizeRuntimeInspector(state) {
  const runtimeInspector = normalizeRuntimeInspectorState(state.runtimeInspector ?? null);
  if (!runtimeInspector.targetId) {
    return [{ id: "runtime-inspector-none", label: "No runtime inspector snapshot" }];
  }
  const items = [];
  const typeLabel = runtimeInspector.targetType ?? runtimeInspector.view?.type ?? "value";
  items.push({
    id: "runtime-inspector-target",
    label: `Target: ${runtimeInspector.targetId} (${typeLabel})`
  });
  if (runtimeInspector.stale) {
    items.push({
      id: "runtime-inspector-stale",
      label: "Snapshot is stale"
    });
  }
  const summary =
    (typeof runtimeInspector.view?.summary === "string" && runtimeInspector.view.summary.length > 0
      ? runtimeInspector.view.summary
      : null) ??
    (typeof runtimeInspector.view?.title === "string" && runtimeInspector.view.title.length > 0
      ? runtimeInspector.view.title
      : null);
  if (summary) {
    items.push({
      id: "runtime-inspector-summary",
      label: `Summary: ${truncateTranscriptText(summary, 96)}`
    });
  }
  const sections = Array.isArray(runtimeInspector.view?.sections) ? runtimeInspector.view.sections : [];
  for (const section of sections) {
    const sectionId =
      typeof section?.id === "string" && section.id.length > 0
        ? section.id
        : `section-${items.length + 1}`;
    const title =
      typeof section?.title === "string" && section.title.length > 0
        ? section.title
        : sectionId;
    const rows = Array.isArray(section?.rows) ? section.rows : [];
    items.push({
      id: `runtime-inspector-section-${sectionId}`,
      label: `${title}: ${rows.length} row${rows.length === 1 ? "" : "s"}`
    });
    for (let index = 0; index < rows.length; index += 1) {
      const row = rows[index];
      const rowId =
        typeof row?.id === "string" && row.id.length > 0
          ? row.id
          : `${sectionId}-row-${index + 1}`;
      const rowLabel =
        typeof row?.label === "string" && row.label.length > 0
          ? row.label
          : rowId;
      const valueSummary =
        typeof row?.valueSummary === "string" && row.valueSummary.length > 0
          ? truncateTranscriptText(row.valueSummary, 72)
          : "";
      const place =
        row?.place && typeof row.place === "object" && typeof row.place.placeId === "string"
          ? row.place.placeId
          : null;
      const placeSuffix = place ? ` [place:${place}]` : "";
      const valueSuffix = valueSummary ? ` => ${valueSummary}` : "";
      items.push({
        id: `runtime-inspector-row-${sectionId}-${rowId}`,
        label: `  ${rowLabel}${valueSuffix}${placeSuffix}`
      });
    }
  }
  if (items.length === 0) {
    items.push({ id: "runtime-inspector-empty", label: "Runtime inspector snapshot is empty" });
  }
  return items;
}

function summarizeEditGroups(state) {
  const groups = Array.isArray(state.editGroups) ? state.editGroups : [];
  if (groups.length === 0) {
    return [{ id: "edit-none", label: "No staged edits" }];
  }
  return groups.map((group) => {
    const count = Array.isArray(group.edits) ? group.edits.length : 0;
    const countSuffix = count > 0 ? ` (${count})` : "";
    const statusSuffix = group.status ? ` [${group.status}]` : "";
    return {
      id: group.id,
      label: `${group.label ?? group.id}${countSuffix}${statusSuffix}`,
      editGroupId: group.id,
      status: group.status ?? null
    };
  });
}

function buildInspectorSections(state) {
  return {
    tasks: summarizeTasks(state),
    focus: summarizeFocus(state),
    commands: summarizeCommands(state),
    commandHistory: buildCommandHistoryItems(state, { limit: 5 }),
    capabilities: summarizeCapabilities(state),
    capabilityRequests: summarizeCapabilityRequests(state),
    runtimeInspector: summarizeRuntimeInspector(state),
    watches: summarizeWatches(state),
    stagedEdits: summarizeEditGroups(state),
    domEscapes: summarizeDomEscapes(state),
    turns: summarizeUiTurn(state),
    transcript: buildTranscriptItems(state, { limit: 5 }),
    presentations: summarizePresentations(state),
    windows: summarizeWindows(state),
    jobs: summarizeJobs(state),
    errors: summarizeErrors(state),
    eventLog: summarizeEventLog(state)
  };
}

export function openInspectorWindow(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  if (!taskId) {
    throw new Error("Inspector requires a task");
  }
  const existing = findWindowByRole(state, "inspector", taskId);
  if (existing) {
    return refreshInspectorWindow(state, existing.id);
  }

  const allocWindow = allocateId(state.idCounters, "window", "inspector");
  let nextState = {
    ...state,
    idCounters: allocWindow.counters
  };
  nextState = addWindow(nextState, {
    id: allocWindow.id,
    taskId,
    kind: "inspector",
    title: "System Inspector",
    metadata: { role: "inspector" }
  });

  const sectionItems = buildInspectorSections(nextState);

  let ids = {};
  let rootAlloc = allocateWidgetId(nextState, "inspector-root");
  nextState = addWidget(rootAlloc.state, {
    id: rootAlloc.id,
    kind: "container",
    windowId: allocWindow.id,
    props: { className: "ui-inspector-root" }
  });
  ids.rootId = rootAlloc.id;

  let titleAlloc = allocateWidgetId(nextState, "inspector-title");
  nextState = addWidget(titleAlloc.state, {
    id: titleAlloc.id,
    kind: "label",
    parentId: ids.rootId,
    props: { text: "System Inspector", className: "ui-window-title ui-inspector-title" }
  });
  ids.titleId = titleAlloc.id;

  const sections = [
    ["tasks", "Tasks"],
    ["focus", "Focus"],
    ["commands", "Commands"],
    ["commandHistory", "Command History"],
    ["capabilities", "Capabilities"],
    ["capabilityRequests", "Capability Requests"],
    ["runtimeInspector", "Runtime Inspector"],
    ["watches", "Pinned Watches"],
    ["stagedEdits", "Staged Edits"],
    ["domEscapes", "DOM Escapes"],
    ["turns", "UI Turn"],
    ["transcript", "Transcript"],
    ["presentations", "Presentations"],
    ["windows", "Windows"],
    ["jobs", "Jobs"],
    ["errors", "Errors"],
    ["eventLog", "Event Log"]
  ];

  ids.sections = {};
  for (const [key, title] of sections) {
    let labelAlloc = allocateWidgetId(nextState, `inspector-${key}-label`);
    nextState = addWidget(labelAlloc.state, {
      id: labelAlloc.id,
      kind: "label",
      parentId: ids.rootId,
      props: { text: title, className: "ui-inspector-section-title" }
    });
    let listAlloc = allocateWidgetId(nextState, `inspector-${key}-list`);
    const listProps = {
      items: sectionItems[key] ?? [],
      className: "ui-inspector-list"
    };
    if (key === "stagedEdits") {
      listProps.selectionCommand = LIST_SELECTION_UPDATE_COMMAND;
      listProps.selectionMode = "single";
      listProps.selectionActionBar = true;
      listProps.selectionActions = [
        { id: "apply-edit", label: "Apply" },
        { id: "undo-edit", label: "Undo" }
      ];
      listProps.selectionActionCommands = {
        "apply-edit": INSPECTOR_EDIT_APPLY_COMMAND,
        "undo-edit": INSPECTOR_EDIT_UNDO_COMMAND
      };
    }
    nextState = addWidget(listAlloc.state, {
      id: listAlloc.id,
      kind: "list",
      parentId: ids.rootId,
      props: listProps
    });
    ids.sections[key] = { labelId: labelAlloc.id, listId: listAlloc.id };
  }

  nextState = updateWindow(nextState, allocWindow.id, (window) => ({
    ...window,
    metadata: { ...(window.metadata ?? {}), role: "inspector", widgets: ids }
  }));

  return nextState;
}

export function openTranscriptWindow(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  if (!taskId) {
    throw new Error("Transcript requires a task");
  }
  const existing = findWindowByRole(state, "transcript", taskId);
  if (existing) {
    return refreshTranscriptWindow(state, existing.id, options);
  }

  const allocWindow = allocateId(state.idCounters, "window", "transcript");
  let nextState = {
    ...state,
    idCounters: allocWindow.counters
  };
  nextState = addWindow(nextState, {
    id: allocWindow.id,
    taskId,
    kind: "transcript",
    title: "Transcript",
    metadata: { role: "transcript" }
  });

  const items = buildTranscriptItems(nextState, { limit: options.limit });

  let ids = {};
  let rootAlloc = allocateWidgetId(nextState, "transcript-root");
  nextState = addWidget(rootAlloc.state, {
    id: rootAlloc.id,
    kind: "container",
    windowId: allocWindow.id,
    props: { className: "ui-transcript-root" }
  });
  ids.rootId = rootAlloc.id;

  let titleAlloc = allocateWidgetId(nextState, "transcript-title");
  nextState = addWidget(titleAlloc.state, {
    id: titleAlloc.id,
    kind: "label",
    parentId: ids.rootId,
    props: { text: "Transcript", className: "ui-window-title ui-transcript-title" }
  });
  ids.titleId = titleAlloc.id;

  let listAlloc = allocateWidgetId(nextState, "transcript-list");
  nextState = addWidget(listAlloc.state, {
    id: listAlloc.id,
    kind: "list",
    parentId: ids.rootId,
    props: {
      className: "ui-transcript-list",
      items,
      itemCommand: TRANSCRIPT_ITEM_OPEN_COMMAND,
      selectionCommand: LIST_SELECTION_UPDATE_COMMAND,
      selectionMode: "multi",
      selectionActionBar: true,
      selectionActions: [
        { id: "toggle-fold", label: "Toggle Fold" },
        { id: "pin-watch", label: "Pin Watch" }
      ],
      selectionActionCommands: {
        inspect: TRANSCRIPT_ITEM_OPEN_COMMAND,
        describe: RECORDING_COPY_WITH_CONTEXT_COMMAND,
        "do-again": RECORDING_REPLAY_AS_INPUT_COMMAND,
        "do-again-with-args": RECORDING_RERUN_COMMAND,
        "toggle-fold": RECORDING_TOGGLE_COMMAND,
        "pin-watch": INSPECTOR_WATCH_PIN_COMMAND
      }
    }
  });
  ids.listId = listAlloc.id;

  nextState = updateWindow(nextState, allocWindow.id, (window) => ({
    ...window,
    metadata: { ...(window.metadata ?? {}), role: "transcript", widgets: ids }
  }));

  return nextState;
}

export function refreshTranscriptWindow(state, windowId, options = {}) {
  const nextState = maybeRevalidateStatePresentations(
    state,
    options.presentationResolver ?? options.revalidatePresentations ?? null
  );
  const window = nextState.windows?.[windowId];
  if (!window || window.metadata?.role !== "transcript") {
    throw new Error("Window is not a transcript");
  }
  const widgets = window.metadata?.widgets ?? {};
  if (!widgets.listId) {
    return nextState;
  }
  const items = buildTranscriptItems(nextState, { limit: options.limit });
  return updateWidget(nextState, widgets.listId, (widget) => ({
    ...widget,
    props: { ...(widget.props ?? {}), items }
  }));
}

function buildCommandHistoryItems(state, options = {}) {
  const history = Array.isArray(state.commandHistory) ? [...state.commandHistory] : [];
  const limit = Number.isFinite(options.limit) ? Math.max(0, options.limit) : 100;
  const ordered = limit > 0 ? history.slice(-limit) : history;
  const items = [];
  for (const invocation of ordered) {
    const id = invocation.id ?? invocation.commandId ?? `inv-${items.length + 1}`;
    const commandId = invocation.commandId ?? "unknown";
    let argsText = "";
    if (invocation.args && typeof invocation.args === "object") {
      try {
        argsText = JSON.stringify(invocation.args);
      } catch (_err) {
        argsText = "[args]";
      }
    }
    if (argsText.length > 120) {
      argsText = `${argsText.slice(0, 117)}...`;
    }
    const label = argsText ? `${commandId} ${argsText}` : commandId;
    items.push({
      id: `history-${id}`,
      label,
      commandId,
      invocation,
      disabled: !commandId
    });
  }
  if (items.length === 0) {
    items.push({ id: "history-none", label: "No command history" });
  }
  return items;
}

export function openCommandHistoryWindow(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  if (!taskId) {
    throw new Error("Command history requires a task");
  }
  const existing = findWindowByRole(state, "command-history", taskId);
  if (existing) {
    return refreshCommandHistoryWindow(state, existing.id, options);
  }

  const allocWindow = allocateId(state.idCounters, "window", "command-history");
  let nextState = {
    ...state,
    idCounters: allocWindow.counters
  };
  nextState = addWindow(nextState, {
    id: allocWindow.id,
    taskId,
    kind: "history",
    title: "Command History",
    metadata: { role: "command-history" }
  });

  const items = buildCommandHistoryItems(nextState, { limit: options.limit });

  let ids = {};
  let rootAlloc = allocateWidgetId(nextState, "command-history-root");
  nextState = addWidget(rootAlloc.state, {
    id: rootAlloc.id,
    kind: "container",
    windowId: allocWindow.id,
    props: { className: "ui-command-history-root" }
  });
  ids.rootId = rootAlloc.id;

  let titleAlloc = allocateWidgetId(nextState, "command-history-title");
  nextState = addWidget(titleAlloc.state, {
    id: titleAlloc.id,
    kind: "label",
    parentId: ids.rootId,
    props: { text: "Command History" }
  });
  ids.titleId = titleAlloc.id;

  let listAlloc = allocateWidgetId(nextState, "command-history-list");
  nextState = addWidget(listAlloc.state, {
    id: listAlloc.id,
    kind: "list",
    parentId: ids.rootId,
    props: { items, itemCommand: COMMAND_HISTORY_EXECUTE_COMMAND }
  });
  ids.listId = listAlloc.id;

  nextState = updateWindow(nextState, allocWindow.id, (window) => ({
    ...window,
    metadata: { ...(window.metadata ?? {}), role: "command-history", widgets: ids }
  }));

  return nextState;
}

export function refreshCommandHistoryWindow(state, windowId, options = {}) {
  const nextState = maybeRevalidateStatePresentations(
    state,
    options.presentationResolver ?? options.revalidatePresentations ?? null
  );
  const window = nextState.windows?.[windowId];
  if (!window || window.metadata?.role !== "command-history") {
    throw new Error("Window is not a command history");
  }
  const widgets = window.metadata?.widgets ?? {};
  if (!widgets.listId) {
    return nextState;
  }
  const items = buildCommandHistoryItems(nextState, { limit: options.limit });
  return updateWidget(nextState, widgets.listId, (widget) => ({
    ...widget,
    props: { ...(widget.props ?? {}), items }
  }));
}

function normalizeProblemStatus(status, options = {}) {
  if (PROBLEM_STATUSES.includes(status)) return status;
  if (status === "resolved") return "resolved";
  if (status === "suppressed") return "suppressed";
  if (status === "acknowledged") return "active";
  if (status === "open" || status === "new" || status === null || status === undefined) {
    const count = Number.isInteger(options.count) ? options.count : 0;
    return count <= 1 ? "new" : "active";
  }
  return "active";
}

function normalizeProblemSeverity(severity, kind) {
  const value = typeof severity === "string" && severity.length > 0 ? severity : kind;
  if (value === "warning" || value === "warn") return "warning";
  if (value === "info") return "info";
  return "error";
}

function buildProblemExplanation(error, severity, status) {
  const reason = typeof error?.reason === "string" && error.reason.length > 0 ? error.reason : null;
  const summary =
    typeof error?.report?.summary === "string" && error.report.summary.length > 0
      ? error.report.summary
      : null;
  if (reason) {
    return `Why: ${reason}`;
  }
  if (summary) {
    return `Why: ${summary}`;
  }
  return `Why: this ${severity} is currently ${status}.`;
}

function compareProblemEntries(a, b) {
  const statusOrder = { new: 0, active: 1, resolved: 2, suppressed: 3 };
  const statusA = normalizeProblemStatus(a?.status, { count: a?.count });
  const statusB = normalizeProblemStatus(b?.status, { count: b?.count });
  const orderDiff = (statusOrder[statusA] ?? 9) - (statusOrder[statusB] ?? 9);
  if (orderDiff !== 0) return orderDiff;
  const tsA = Number.isInteger(a?.lastTs) ? a.lastTs : Number.isInteger(a?.ts) ? a.ts : 0;
  const tsB = Number.isInteger(b?.lastTs) ? b.lastTs : Number.isInteger(b?.ts) ? b.ts : 0;
  if (tsA !== tsB) return tsB - tsA;
  return String(a?.id ?? "").localeCompare(String(b?.id ?? ""));
}

function buildProblemsItems(state) {
  const entries = Array.isArray(state.errors) ? [...state.errors] : [];
  if (entries.length === 0) {
    return [{ id: "problems-none", label: "No problems", disabled: true, selectable: false }];
  }
  return entries.sort(compareProblemEntries).map((error, index) => {
    const severity = normalizeProblemSeverity(error?.severity, error?.kind ?? "error");
    const status = normalizeProblemStatus(error?.status, { count: error?.count });
    const countSuffix = Number.isInteger(error?.count) && error.count > 1 ? ` (${error.count})` : "";
    const statusSuffix = status ? ` [${status}]` : "";
    const label = `${severity}: ${error?.message ?? ""}`.trim();
    const classParts = ["ui-problems-item", `is-${severity}`, `is-${status}`];
    const explanation = buildProblemExplanation(error, severity, status);
    return {
      id: error.id ?? `problem-${index}`,
      label: `${label}${countSuffix}${statusSuffix}`.trim(),
      errorId: error.id ?? null,
      taskId: error.taskId ?? null,
      status,
      severity,
      count: Number.isInteger(error?.count) ? error.count : null,
      location: error.location ?? error.report?.location ?? null,
      presentationId: error.presentationId ?? null,
      explanation,
      guidanceId: error.id ? `problem:${error.id}` : null,
      className: classParts.join(" ")
    };
  });
}

export function openProblemsWindow(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  if (!taskId) {
    throw new Error("Problems window requires a task");
  }
  const existing = findWindowByRole(state, "problems", taskId);
  if (existing) {
    return refreshProblemsWindow(state, existing.id);
  }

  const allocWindow = allocateId(state.idCounters, "window", "problems");
  let nextState = {
    ...state,
    idCounters: allocWindow.counters
  };
  nextState = addWindow(nextState, {
    id: allocWindow.id,
    taskId,
    kind: "problems",
    title: "Problems",
    metadata: { role: "problems" }
  });

  const items = buildProblemsItems(nextState);

  let ids = {};
  let rootAlloc = allocateWidgetId(nextState, "problems-root");
  nextState = addWidget(rootAlloc.state, {
    id: rootAlloc.id,
    kind: "container",
    windowId: allocWindow.id,
    props: { className: "ui-problems-root" }
  });
  ids.rootId = rootAlloc.id;

  let titleAlloc = allocateWidgetId(nextState, "problems-title");
  nextState = addWidget(titleAlloc.state, {
    id: titleAlloc.id,
    kind: "label",
    parentId: ids.rootId,
    props: { text: "Problems", className: "ui-window-title ui-problems-title" }
  });
  ids.titleId = titleAlloc.id;

  let listAlloc = allocateWidgetId(nextState, "problems-list");
  nextState = addWidget(listAlloc.state, {
    id: listAlloc.id,
    kind: "list",
    parentId: ids.rootId,
    props: {
      className: "ui-problems-list",
      items,
      itemCommand: PROBLEMS_ITEM_OPEN_COMMAND,
      selectionCommand: LIST_SELECTION_UPDATE_COMMAND,
      selectionMode: "multi",
      selectionActionBar: true,
      selectionActions: [{ id: "open-debugger", label: "Open Debugger" }],
      selectionActionCommands: { "open-debugger": PROBLEMS_ITEM_OPEN_COMMAND }
    }
  });
  ids.listId = listAlloc.id;

  nextState = updateWindow(nextState, allocWindow.id, (window) => ({
    ...window,
    metadata: { ...(window.metadata ?? {}), role: "problems", widgets: ids }
  }));

  return nextState;
}

export function refreshProblemsWindow(state, windowId, options = {}) {
  const nextState = maybeRevalidateStatePresentations(
    state,
    options.presentationResolver ?? options.revalidatePresentations ?? null
  );
  const window = nextState.windows?.[windowId];
  if (!window || window.metadata?.role !== "problems") {
    throw new Error("Window is not a problems window");
  }
  const widgets = window.metadata?.widgets ?? {};
  if (!widgets.listId) {
    return nextState;
  }
  const items = buildProblemsItems(nextState);
  return updateWidget(nextState, widgets.listId, (widget) => ({
    ...widget,
    props: { ...(widget.props ?? {}), items }
  }));
}

export function refreshInspectorWindow(state, windowId, options = {}) {
  const revalidatedState = maybeRevalidateStatePresentations(
    state,
    options.presentationResolver ?? options.revalidatePresentations ?? null
  );
  const window = revalidatedState.windows?.[windowId];
  if (!window || window.metadata?.role !== "inspector") {
    throw new Error("Window is not an inspector");
  }
  const widgets = window.metadata?.widgets;
  if (!widgets?.sections) {
    return revalidatedState;
  }
  const sections = buildInspectorSections(revalidatedState);
  let nextState = revalidatedState;
  for (const [key, ids] of Object.entries(widgets.sections)) {
    nextState = updateWidget(nextState, ids.listId, (widget) => ({
      ...widget,
      props: { ...(widget.props ?? {}), items: sections[key] ?? [] }
    }));
  }
  return nextState;
}

function refreshInspectorWindowsForTask(state, taskId = null) {
  let nextState = state;
  const windows = Object.values(state.windows ?? {}).filter(
    (window) => window?.metadata?.role === "inspector" && (!taskId || window.taskId === taskId)
  );
  for (const window of windows) {
    nextState = refreshInspectorWindow(nextState, window.id);
  }
  return nextState;
}

function buildCapabilityMediationStatus(state) {
  const capabilities = normalizeCapabilities(state.capabilities ?? null);
  const policy = normalizeCapabilityPolicy(state.capabilityPolicy ?? null);
  const safeMode = capabilities.safeMode ? "enabled" : "disabled";
  return `Safe mode: ${safeMode} · Default policy: ${policy.defaultDecision}`;
}

function buildCapabilityRequestItems(requests, options = {}) {
  const pendingOnly = options.pendingOnly !== false;
  const visible = pendingOnly ? requests.filter((request) => request.status === "pending") : requests;
  if (visible.length === 0) {
    return [{ id: "capability-none", label: "No pending capability requests", disabled: true, placeholder: true }];
  }
  return visible.map((request) => {
    const capability = request.capability ?? "unknown";
    const reason = request.reason ? ` (${request.reason})` : "";
    return {
      id: request.id,
      label: `${capability}${reason}`,
      requestId: request.id,
      capability,
      status: request.status
    };
  });
}

export function openCapabilityMediationWindow(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  if (!taskId) {
    throw new Error("Capability mediation requires a task");
  }
  const existing = findWindowByRole(state, "capability-mediation", taskId);
  if (existing) {
    return refreshCapabilityMediationWindow(state, existing.id, options);
  }

  const allocWindow = allocateId(state.idCounters, "window", "capability-mediation");
  let nextState = {
    ...state,
    idCounters: allocWindow.counters
  };
  nextState = addWindow(nextState, {
    id: allocWindow.id,
    taskId,
    kind: "capability-mediation",
    title: "Capability Mediation",
    metadata: { role: "capability-mediation" }
  });

  const requests = normalizeCapabilityRequests(nextState.capabilityRequests ?? null);
  const items = buildCapabilityRequestItems(requests);
  const selectedIndex = items.findIndex((item) => item.id === options.selectedRequestId);
  const hasSelectable = items.some((item) => !item.placeholder);
  let resolvedIndex = selectedIndex;
  if (!hasSelectable) {
    resolvedIndex = -1;
  } else if (resolvedIndex < 0) {
    resolvedIndex = 0;
  }
  const selectedItems = resolvedIndex >= 0 ? applySelectionToItems(items, resolvedIndex) : items;
  const selectedRequestId = resolvedIndex >= 0 ? selectedItems[resolvedIndex]?.id ?? null : null;

  let ids = {};
  let rootAlloc = allocateWidgetId(nextState, "capability-mediation-root");
  nextState = addWidget(rootAlloc.state, {
    id: rootAlloc.id,
    kind: "container",
    windowId: allocWindow.id,
    props: { className: "ui-capability-mediation-root" }
  });
  ids.rootId = rootAlloc.id;

  let labelAlloc = allocateWidgetId(nextState, "capability-mediation-label");
  nextState = addWidget(labelAlloc.state, {
    id: labelAlloc.id,
    kind: "label",
    parentId: ids.rootId,
    props: { text: "Capability Requests" }
  });
  ids.labelId = labelAlloc.id;

  let statusAlloc = allocateWidgetId(nextState, "capability-mediation-status");
  nextState = addWidget(statusAlloc.state, {
    id: statusAlloc.id,
    kind: "label",
    parentId: ids.rootId,
    props: { text: buildCapabilityMediationStatus(nextState) }
  });
  ids.statusId = statusAlloc.id;

  let listAlloc = allocateWidgetId(nextState, "capability-mediation-list");
  nextState = addWidget(listAlloc.state, {
    id: listAlloc.id,
    kind: "list",
    parentId: ids.rootId,
    props: { items: selectedItems, itemCommand: CAPABILITY_SELECT_COMMAND }
  });
  ids.listId = listAlloc.id;

  let approveAlloc = allocateWidgetId(nextState, "capability-mediation-approve");
  nextState = addWidget(approveAlloc.state, {
    id: approveAlloc.id,
    kind: "button",
    parentId: ids.rootId,
    props: { text: "Approve", command: CAPABILITY_APPROVE_COMMAND }
  });
  ids.approveId = approveAlloc.id;

  let denyAlloc = allocateWidgetId(nextState, "capability-mediation-deny");
  nextState = addWidget(denyAlloc.state, {
    id: denyAlloc.id,
    kind: "button",
    parentId: ids.rootId,
    props: { text: "Deny", command: CAPABILITY_DENY_COMMAND }
  });
  ids.denyId = denyAlloc.id;

  let autoAlloc = allocateWidgetId(nextState, "capability-mediation-auto");
  nextState = addWidget(autoAlloc.state, {
    id: autoAlloc.id,
    kind: "button",
    parentId: ids.rootId,
    props: { text: "Auto-run Policy", command: CAPABILITY_AUTO_RUN_COMMAND }
  });
  ids.autoId = autoAlloc.id;

  nextState = updateWindow(nextState, allocWindow.id, (window) => ({
    ...window,
    metadata: {
      ...(window.metadata ?? {}),
      role: "capability-mediation",
      widgets: ids,
      mediation: { selectedRequestId }
    }
  }));

  return nextState;
}

export function refreshCapabilityMediationWindow(state, windowId, options = {}) {
  const window = state.windows?.[windowId];
  if (!window || window.metadata?.role !== "capability-mediation") {
    throw new Error("Window is not a capability mediation panel");
  }
  const widgets = window.metadata?.widgets ?? {};
  if (!widgets.listId || !widgets.statusId) {
    return state;
  }
  const requests = normalizeCapabilityRequests(state.capabilityRequests ?? null);
  const items = buildCapabilityRequestItems(requests);
  const selectedId = options.selectedRequestId ?? window.metadata?.mediation?.selectedRequestId ?? null;
  let selectedIndex = items.findIndex((item) => item.id === selectedId);
  const hasSelectable = items.some((item) => !item.placeholder);
  if (!hasSelectable) {
    selectedIndex = -1;
  } else if (selectedIndex < 0) {
    selectedIndex = 0;
  }
  const selectedItems = selectedIndex >= 0 ? applySelectionToItems(items, selectedIndex) : items;
  const nextSelectedId = selectedIndex >= 0 ? selectedItems[selectedIndex]?.id ?? null : null;

  let nextState = updateWidget(state, widgets.statusId, (widget) => ({
    ...widget,
    props: { ...(widget.props ?? {}), text: buildCapabilityMediationStatus(state) }
  }));
  nextState = updateWidget(nextState, widgets.listId, (widget) => ({
    ...widget,
    props: { ...(widget.props ?? {}), items: selectedItems }
  }));
  nextState = updateWindow(nextState, windowId, (nextWindow) => ({
    ...nextWindow,
    metadata: {
      ...(nextWindow.metadata ?? {}),
      mediation: { selectedRequestId: nextSelectedId }
    }
  }));
  return nextState;
}

export function applyCapabilityRequestSelection(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  const windowId =
    options.windowId ??
    findWindowByRole(state, "capability-mediation", taskId)?.id ??
    null;
  if (!windowId) {
    return state;
  }
  const requestId =
    options.requestId ??
    options.itemId ??
    options.item?.requestId ??
    options.item?.id ??
    null;
  return refreshCapabilityMediationWindow(state, windowId, { selectedRequestId: requestId });
}

export function resolveCapabilityRequestSelection(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  const windowId =
    options.windowId ??
    findWindowByRole(state, "capability-mediation", taskId)?.id ??
    null;
  if (!windowId) {
    return { requestId: null, request: null, windowId: null };
  }
  const window = state.windows?.[windowId];
  const selectedId = window?.metadata?.mediation?.selectedRequestId ?? null;
  const requests = normalizeCapabilityRequests(state.capabilityRequests ?? null);
  const request = requests.find((entry) => entry.id === selectedId) ?? null;
  return { requestId: selectedId, request, windowId };
}

export function openSessionListWindow(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  if (!taskId) {
    throw new Error("Session list requires a task");
  }
  const existing = findWindowByRole(state, "session-list", taskId);
  if (existing) {
    return refreshSessionListWindow(state, existing.id, options);
  }

  const allocWindow = allocateId(state.idCounters, "window", "session-list");
  let nextState = {
    ...state,
    idCounters: allocWindow.counters
  };
  nextState = addWindow(nextState, {
    id: allocWindow.id,
    taskId,
    kind: "session-list",
    title: "Sessions",
    metadata: { role: "session-list" }
  });

  const items = buildSessionItems(nextState);

  let ids = {};
  let rootAlloc = allocateWidgetId(nextState, "session-list-root");
  nextState = addWidget(rootAlloc.state, {
    id: rootAlloc.id,
    kind: "container",
    windowId: allocWindow.id,
    props: { className: "ui-session-list-root" }
  });
  ids.rootId = rootAlloc.id;

  let labelAlloc = allocateWidgetId(nextState, "session-list-label");
  nextState = addWidget(labelAlloc.state, {
    id: labelAlloc.id,
    kind: "label",
    parentId: ids.rootId,
    props: { text: "Sessions", className: "ui-window-title ui-session-list-title" }
  });
  ids.labelId = labelAlloc.id;

  let listAlloc = allocateWidgetId(nextState, "session-list");
  nextState = addWidget(listAlloc.state, {
    id: listAlloc.id,
    kind: "list",
    parentId: ids.rootId,
    props: {
      items,
      itemCommand: SESSION_OPEN_COMMAND,
      selectionCommand: LIST_SELECTION_UPDATE_COMMAND,
      selectionMode: "single",
      selectionActionBar: true,
      selectionActions: [
        { id: "open", label: "Open" },
        { id: "save", label: "Save" },
        { id: "rename", label: "Rename" },
        { id: "delete", label: "Delete" }
      ],
      selectionActionCommands: {
        open: SESSION_OPEN_COMMAND,
        save: SESSION_SAVE_COMMAND,
        rename: SESSION_RENAME_COMMAND,
        delete: SESSION_DELETE_COMMAND
      }
    }
  });
  ids.listId = listAlloc.id;

  nextState = updateWindow(nextState, allocWindow.id, (window) => ({
    ...window,
    metadata: {
      ...(window.metadata ?? {}),
      role: "session-list",
      widgets: ids
    }
  }));

  return nextState;
}

export function refreshSessionListWindow(state, windowId, options = {}) {
  const window = state.windows?.[windowId];
  if (!window || window.metadata?.role !== "session-list") {
    throw new Error("Window is not a session list");
  }
  const widgets = window.metadata?.widgets ?? {};
  if (!widgets.listId) {
    return state;
  }
  const items = buildSessionItems(state);
  return updateWidget(state, widgets.listId, (widget) => ({
    ...widget,
    props: { ...(widget.props ?? {}), items }
  }));
}

function refreshSessionListIfOpen(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  const windowId = findWindowByRole(state, "session-list", taskId)?.id ?? null;
  if (!windowId) return state;
  return refreshSessionListWindow(state, windowId, options);
}

export function openTaskListWindow(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  if (!taskId) {
    throw new Error("Task list requires a task");
  }
  const existing = findWindowByRole(state, "task-list", taskId);
  if (existing) {
    return refreshTaskListWindow(state, existing.id, options);
  }

  const allocWindow = allocateId(state.idCounters, "window", "task-list");
  let nextState = {
    ...state,
    idCounters: allocWindow.counters
  };
  nextState = addWindow(nextState, {
    id: allocWindow.id,
    taskId,
    kind: "task-list",
    title: "Tasks",
    metadata: { role: "task-list" }
  });

  const includeArchived = options.includeArchived ?? false;
  const items = buildTaskListItems(nextState, { includeArchived });

  let ids = {};
  let rootAlloc = allocateWidgetId(nextState, "task-list-root");
  nextState = addWidget(rootAlloc.state, {
    id: rootAlloc.id,
    kind: "container",
    windowId: allocWindow.id,
    props: { className: "ui-task-list-root" }
  });
  ids.rootId = rootAlloc.id;

  let labelAlloc = allocateWidgetId(nextState, "task-list-label");
  nextState = addWidget(labelAlloc.state, {
    id: labelAlloc.id,
    kind: "label",
    parentId: ids.rootId,
    props: { text: "Tasks" }
  });
  ids.labelId = labelAlloc.id;

  let listAlloc = allocateWidgetId(nextState, "task-list");
  nextState = addWidget(listAlloc.state, {
    id: listAlloc.id,
    kind: "list",
    parentId: ids.rootId,
    props: { items, itemCommand: TASK_SWITCH_COMMAND }
  });
  ids.listId = listAlloc.id;

  nextState = updateWindow(nextState, allocWindow.id, (window) => ({
    ...window,
    metadata: {
      ...(window.metadata ?? {}),
      role: "task-list",
      widgets: ids,
      taskList: { includeArchived }
    }
  }));

  return nextState;
}

export function refreshTaskListWindow(state, windowId, options = {}) {
  const window = state.windows?.[windowId];
  if (!window || window.metadata?.role !== "task-list") {
    throw new Error("Window is not a task list");
  }
  const widgets = window.metadata?.widgets;
  if (!widgets?.listId) {
    return state;
  }
  const includeArchived =
    options.includeArchived ?? window.metadata?.taskList?.includeArchived ?? false;
  const items = buildTaskListItems(state, { includeArchived });
  let nextState = updateWidget(state, widgets.listId, (widget) => ({
    ...widget,
    props: { ...(widget.props ?? {}), items }
  }));
  return updateWindow(nextState, windowId, (nextWindow) => ({
    ...nextWindow,
    metadata: {
      ...(nextWindow.metadata ?? {}),
      taskList: { includeArchived }
    }
  }));
}

export function openCommandPaletteWindow(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  if (!taskId) {
    throw new Error("Command palette requires a task");
  }
  const existing = findWindowByRole(state, "command-palette", taskId);
  if (existing) {
    return refreshCommandPaletteWindow(state, existing.id, options);
  }

  const allocWindow = allocateId(state.idCounters, "window", "command-palette");
  let nextState = {
    ...state,
    idCounters: allocWindow.counters
  };
  nextState = addWindow(nextState, {
    id: allocWindow.id,
    taskId,
    kind: "palette",
    title: "Command Palette",
    metadata: { role: "command-palette" }
  });

  let ids = {};
  let rootAlloc = allocateWidgetId(nextState, "command-palette-root");
  nextState = addWidget(rootAlloc.state, {
    id: rootAlloc.id,
    kind: "container",
    windowId: allocWindow.id,
    props: { className: "ui-command-palette-root" }
  });
  ids.rootId = rootAlloc.id;

  let labelAlloc = allocateWidgetId(nextState, "command-palette-label");
  nextState = addWidget(labelAlloc.state, {
    id: labelAlloc.id,
    kind: "label",
    parentId: ids.rootId,
    props: { text: "Commands" }
  });
  ids.labelId = labelAlloc.id;

  const filterValue = String(options.filter ?? "");
  let filterAlloc = allocateWidgetId(nextState, "command-palette-filter");
  const filterCommandId = Object.prototype.hasOwnProperty.call(options, "filterCommandId")
    ? options.filterCommandId
    : COMMAND_PALETTE_FILTER_COMMAND;
  nextState = addWidget(filterAlloc.state, {
    id: filterAlloc.id,
    kind: "text-input",
    parentId: ids.rootId,
    props: {
      placeholder: "Filter commands",
      value: filterValue,
      command: filterCommandId
    }
  });
  ids.filterId = filterAlloc.id;

  const items = buildCommandPaletteItems(options.registry ?? null, { filter: filterValue, state: nextState });
  const selectedIndex = clampIndex(0, items.length);
  const selectedItems = applySelectionToItems(items, selectedIndex);
  const selectedCommandId = items[selectedIndex]?.targetCommandId ?? null;
  const previewText = buildCommandPalettePreviewText(
    nextState,
    options.registry ?? null,
    selectedCommandId,
    { taskId, windowId: allocWindow.id }
  );
  let previewAlloc = allocateWidgetId(nextState, "command-palette-preview");
  nextState = addWidget(previewAlloc.state, {
    id: previewAlloc.id,
    kind: "label",
    parentId: ids.rootId,
    props: {
      text: previewText,
      className: "ui-command-palette-preview"
    }
  });
  ids.previewId = previewAlloc.id;
  let listAlloc = allocateWidgetId(nextState, "command-palette-list");
  nextState = addWidget(listAlloc.state, {
    id: listAlloc.id,
    kind: "list",
    parentId: ids.rootId,
    props: { items: selectedItems, itemCommand: COMMAND_PALETTE_EXECUTE_COMMAND }
  });
  ids.listId = listAlloc.id;

  nextState = updateWindow(nextState, allocWindow.id, (window) => ({
    ...window,
    metadata: {
      ...(window.metadata ?? {}),
      role: "command-palette",
      widgets: ids,
      palette: { selectedIndex, selectedCommandId }
    }
  }));

  return nextState;
}

export function refreshCommandPaletteWindow(state, windowId, options = {}) {
  const window = state.windows?.[windowId];
  if (!window || window.metadata?.role !== "command-palette") {
    throw new Error("Window is not a command palette");
  }
  const widgets = window.metadata?.widgets;
  if (!widgets?.listId || !widgets?.filterId) {
    return state;
  }
  const paletteState = window.metadata?.palette ?? {};
  const currentFilter =
    options.filter ??
    state.widgets?.[widgets.filterId]?.props?.value ??
    "";
  const filterValue = String(currentFilter ?? "");
  const items = buildCommandPaletteItems(options.registry ?? null, { filter: filterValue, state });
  const hasSelectionIndex = Number.isFinite(options.selectionIndex);
  let selectedIndex = hasSelectionIndex ? options.selectionIndex : (paletteState.selectedIndex ?? 0);
  const preferredCommandId = hasSelectionIndex
    ? null
    : (options.selectedCommandId ?? paletteState.selectedCommandId ?? null);
  if (preferredCommandId) {
    const matchIndex = items.findIndex((item) => item.targetCommandId === preferredCommandId);
    if (matchIndex !== -1) {
      selectedIndex = matchIndex;
    }
  }
  selectedIndex = clampIndex(selectedIndex, items.length);
  const selectedItems = applySelectionToItems(items, selectedIndex);
  const selectedCommandId = items[selectedIndex]?.targetCommandId ?? null;
  const previewText = buildCommandPalettePreviewText(
    state,
    options.registry ?? null,
    selectedCommandId,
    {
      taskId: window.taskId ?? options.taskId ?? null,
      windowId
    }
  );
  let nextState = state;
  nextState = updateWidget(nextState, widgets.filterId, (widget) => ({
    ...widget,
    props: { ...(widget.props ?? {}), value: filterValue }
  }));
  if (widgets.previewId) {
    nextState = updateWidget(nextState, widgets.previewId, (widget) => ({
      ...widget,
      props: { ...(widget.props ?? {}), text: previewText }
    }));
  }
  nextState = updateWidget(nextState, widgets.listId, (widget) => ({
    ...widget,
    props: { ...(widget.props ?? {}), items: selectedItems }
  }));
  nextState = updateWindow(nextState, windowId, (nextWindow) => ({
    ...nextWindow,
    metadata: {
      ...(nextWindow.metadata ?? {}),
      palette: { selectedIndex, selectedCommandId }
    }
  }));
  return nextState;
}

export function closeCommandPaletteWindow(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  const windowId =
    options.windowId ??
    findWindowByRole(state, "command-palette", taskId)?.id ??
    null;
  if (!windowId) {
    return state;
  }
  const window = state.windows?.[windowId];
  if (!window || window.metadata?.role !== "command-palette") {
    return state;
  }
  return removeWindow(state, windowId, { reason: options.reason ?? "command" });
}

function resolveTaskTargetId(state, ctx, options = {}) {
  return (
    options.taskId ??
    ctx?.targetTaskId ??
    ctx?.item?.taskId ??
    ctx?.itemId ??
    ctx?.taskId ??
    state.workspace?.activeTaskId ??
    null
  );
}

function resolveSessionTargetId(state, ctx, options = {}) {
  return (
    options.sessionId ??
    ctx?.sessionId ??
    ctx?.targetSessionId ??
    ctx?.item?.sessionId ??
    ctx?.itemId ??
    ctx?.payload?.sessionId ??
    state.activeSessionId ??
    null
  );
}

function findLayoutLeafForWindow(layout, windowId) {
  if (!layout?.nodes || !windowId) return null;
  for (const [id, node] of Object.entries(layout.nodes)) {
    if (node?.kind === "leaf" && node.props?.windowId === windowId) {
      return id;
    }
  }
  return null;
}

function findLayoutParent(layout, childId) {
  if (!layout?.nodes || !childId) return null;
  for (const [id, node] of Object.entries(layout.nodes)) {
    const children = node?.children ?? [];
    if (children.includes(childId)) {
      return { parentId: id, parent: node };
    }
  }
  return null;
}

function resolveLayoutTargetId(state, ctx) {
  const direct =
    ctx?.layoutId ??
    ctx?.targetLayoutId ??
    ctx?.item?.layoutId ??
    ctx?.itemId ??
    null;
  if (direct) {
    return direct;
  }
  const windowId = ctx?.windowId ?? state.focus?.windowId ?? null;
  return findLayoutLeafForWindow(state.layout, windowId);
}

export function applyCommandPaletteFilter(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  const windowId =
    options.windowId ??
    findWindowByRole(state, "command-palette", taskId)?.id ??
    null;
  if (!windowId) {
    return state;
  }
  const filterValue = options.filter ?? options.inputValue ?? "";
  return refreshCommandPaletteWindow(state, windowId, {
    registry: options.registry ?? null,
    filter: filterValue
  });
}

export function applyCommandPaletteSelection(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  const windowId =
    options.windowId ??
    findWindowByRole(state, "command-palette", taskId)?.id ??
    null;
  if (!windowId) {
    return state;
  }
  const window = state.windows?.[windowId];
  if (!window) return state;
  const paletteState = window.metadata?.palette ?? {};
  const delta = Number.isFinite(options.delta) ? options.delta : 0;
  const selectionIndex = Number.isFinite(options.index)
    ? options.index
    : (paletteState.selectedIndex ?? 0) + delta;
  return refreshCommandPaletteWindow(state, windowId, {
    registry: options.registry ?? null,
    filter: options.filter ?? null,
    selectionIndex,
    selectedCommandId: options.commandId ?? null
  });
}

export function resolveCommandPaletteSelection(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  const windowId =
    options.windowId ??
    findWindowByRole(state, "command-palette", taskId)?.id ??
    null;
  if (!windowId) {
    return { index: -1, item: null, commandId: null };
  }
  const window = state.windows?.[windowId];
  if (!window) return { index: -1, item: null, commandId: null };
  const paletteState = window.metadata?.palette ?? {};
  const widgets = window.metadata?.widgets ?? {};
  const items = state.widgets?.[widgets.listId]?.props?.items ?? [];
  const index = clampIndex(paletteState.selectedIndex ?? 0, items.length);
  const item = items[index] ?? null;
  const commandId = item?.targetCommandId ?? null;
  return { index, item, commandId };
}

export function registerCommandPaletteCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const filterId = options.filterCommandId ?? COMMAND_PALETTE_FILTER_COMMAND;
  const executeId = options.executeCommandId ?? COMMAND_PALETTE_EXECUTE_COMMAND;
  const nextId = options.selectNextCommandId ?? COMMAND_PALETTE_SELECT_NEXT_COMMAND;
  const prevId = options.selectPrevCommandId ?? COMMAND_PALETTE_SELECT_PREV_COMMAND;
  const execSelectedId = options.executeSelectedCommandId ?? COMMAND_PALETTE_EXECUTE_SELECTION_COMMAND;

  const ensure = (id, command) => {
    if (!registry.commands.has(id)) {
      registerCommand(registry, { ...command, id });
    }
  };

  const buildPaletteExecutionContext = (ctx, commandId, item = null) => {
    const invocation = {
      ...(ctx.invocation ?? {}),
      commandId,
      source: ctx.source ?? ctx.invocation?.source ?? "palette"
    };
    return {
      ...ctx,
      item: item ?? ctx.item ?? null,
      source: invocation.source,
      invocation
    };
  };

  ensure(filterId, {
    doc: "Filter command palette entries.",
    metadata: { paletteHidden: true },
    exec: (ctx) =>
      applyCommandPaletteFilter(ctx.state, {
        registry,
        windowId: ctx.windowId,
        taskId: ctx.taskId,
        inputValue: ctx.inputValue
      })
  });

  ensure(nextId, {
    doc: "Select next command palette entry.",
    metadata: { paletteHidden: true },
    exec: (ctx) =>
      applyCommandPaletteSelection(ctx.state, {
        registry,
        windowId: ctx.windowId,
        taskId: ctx.taskId,
        delta: 1
      })
  });

  ensure(prevId, {
    doc: "Select previous command palette entry.",
    metadata: { paletteHidden: true },
    exec: (ctx) =>
      applyCommandPaletteSelection(ctx.state, {
        registry,
        windowId: ctx.windowId,
        taskId: ctx.taskId,
        delta: -1
      })
  });

  ensure(executeId, {
    doc: "Execute the command palette item that was activated.",
    metadata: { paletteHidden: true },
    exec: (ctx) => {
      const target = ctx.item?.targetCommandId ?? null;
      if (!target) {
        return { ok: false, reason: "No target command" };
      }
      return executeCommand(registry, target, buildPaletteExecutionContext(ctx, target));
    }
  });

  ensure(execSelectedId, {
    doc: "Execute the currently selected command palette entry.",
    metadata: { paletteHidden: true },
    exec: (ctx) => {
      const selection = resolveCommandPaletteSelection(ctx.state, {
        taskId: ctx.taskId,
        windowId: ctx.windowId
      });
      if (!selection.commandId) {
        return { ok: false, reason: "No selection" };
      }
      return executeCommand(
        registry,
        selection.commandId,
        buildPaletteExecutionContext(
          { ...ctx, item: selection.item ?? ctx.item ?? null },
          selection.commandId,
          selection.item ?? ctx.item ?? null
        )
      );
    }
  });

  return registry;
}

export function registerTaskCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const listId = options.listCommandId ?? TASK_LIST_COMMAND;
  const switchId = options.switchCommandId ?? TASK_SWITCH_COMMAND;
  const closeId = options.closeCommandId ?? TASK_CLOSE_COMMAND;
  const archiveId = options.archiveCommandId ?? TASK_ARCHIVE_COMMAND;

  const ensure = (id, command) => {
    if (!registry.commands.has(id)) {
      registerCommand(registry, { ...command, id });
    }
  };

  ensure(listId, {
    title: "List Tasks",
    doc: "Open the task list for the current workspace.",
    exec: (ctx) =>
      openTaskListWindow(ctx.state, {
        taskId: ctx.taskId ?? ctx.state.workspace?.activeTaskId ?? null,
        includeArchived: ctx.includeArchived ?? false
      })
  });

  ensure(switchId, {
    title: "Switch Task",
    doc: "Switch to the selected task.",
    enabled: (ctx) => {
      const target = resolveTaskTargetId(ctx.state, ctx);
      return target && ctx.state.tasks?.[target]
        ? { enabled: true, reason: null }
        : { enabled: false, reason: "No target task" };
    },
    exec: (ctx) => {
      const target = resolveTaskTargetId(ctx.state, ctx);
      if (!target) {
        return ctx.state;
      }
      return setActiveTask(ctx.state, target, { reason: "command" });
    }
  });

  ensure(closeId, {
    title: "Close Task",
    doc: "Close the selected task and its windows.",
    enabled: (ctx) => {
      const target = resolveTaskTargetId(ctx.state, ctx);
      return target && ctx.state.tasks?.[target]
        ? { enabled: true, reason: null }
        : { enabled: false, reason: "No target task" };
    },
    exec: (ctx) => {
      const target = resolveTaskTargetId(ctx.state, ctx);
      if (!target) {
        return ctx.state;
      }
      return closeTask(ctx.state, target, { reason: "command" });
    }
  });

  ensure(archiveId, {
    title: "Archive Task",
    doc: "Archive the selected task.",
    enabled: (ctx) => {
      const target = resolveTaskTargetId(ctx.state, ctx);
      const task = target ? ctx.state.tasks?.[target] : null;
      if (!task) {
        return { enabled: false, reason: "No target task" };
      }
      if (taskIsArchived(task)) {
        return { enabled: false, reason: "Task already archived" };
      }
      return { enabled: true, reason: null };
    },
    exec: (ctx) => {
      const target = resolveTaskTargetId(ctx.state, ctx);
      if (!target) {
        return ctx.state;
      }
      return archiveTask(ctx.state, target, { reason: "command" });
    }
  });

  return registry;
}

export function registerSessionCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const listId = options.listCommandId ?? SESSION_LIST_COMMAND;
  const refreshId = options.refreshCommandId ?? SESSION_REFRESH_COMMAND;
  const createId = options.createCommandId ?? SESSION_CREATE_COMMAND;
  const openId = options.openCommandId ?? SESSION_OPEN_COMMAND;
  const saveId = options.saveCommandId ?? SESSION_SAVE_COMMAND;
  const renameId = options.renameCommandId ?? SESSION_RENAME_COMMAND;
  const deleteId = options.deleteCommandId ?? SESSION_DELETE_COMMAND;

  const ensure = (id, command) => {
    if (!registry.commands.has(id)) {
      registerCommand(registry, { ...command, id });
    }
  };

  ensure(listId, {
    title: "List Sessions",
    doc: "Open the session list for the current workspace.",
    exec: (ctx) =>
      openSessionListWindow(ctx.state, {
        taskId: ctx.taskId ?? ctx.state.workspace?.activeTaskId ?? null
      })
  });

  ensure(refreshId, {
    title: "Refresh Sessions",
    doc: "Refresh the session list window.",
    exec: (ctx) => {
      const windowId = ctx.windowId ?? ctx.payload?.windowId ?? null;
      if (!windowId) return ctx.state;
      return refreshSessionListWindow(ctx.state, windowId, ctx);
    }
  });

  ensure(createId, {
    title: "Create Session",
    doc: "Create a new session from the current workspace state.",
    exec: (ctx) => {
      const nextState = createSession(ctx.state, {
        name: ctx.name ?? ctx.payload?.name ?? null,
        notes: ctx.notes ?? ctx.payload?.notes ?? "",
        now: ctx.now ?? null
      });
      const refreshed = refreshSessionListIfOpen(nextState, { taskId: ctx.taskId ?? null });
      return {
        state: refreshed,
        output: {
          kind: "session.save",
          sessionId: refreshed.activeSessionId
        }
      };
    }
  });

  ensure(openId, {
    title: "Open Session",
    doc: "Open the selected session.",
    enabled: (ctx) => {
      const sessionId = resolveSessionTargetId(ctx.state, ctx);
      return sessionId && ctx.state.sessions?.[sessionId]
        ? { enabled: true, reason: null }
        : { enabled: false, reason: "No target session" };
    },
    exec: (ctx) => {
      const sessionId = resolveSessionTargetId(ctx.state, ctx);
      if (!sessionId) return ctx.state;
      const nextState = openSession(ctx.state, sessionId, { now: ctx.now ?? null });
      const refreshed = refreshSessionListIfOpen(nextState, { taskId: ctx.taskId ?? null });
      return {
        state: refreshed,
        output: { kind: "session.open", sessionId }
      };
    }
  });

  ensure(saveId, {
    title: "Save Session",
    doc: "Persist the selected session snapshot.",
    enabled: (ctx) => {
      const sessionId = resolveSessionTargetId(ctx.state, ctx);
      return sessionId && ctx.state.sessions?.[sessionId]
        ? { enabled: true, reason: null }
        : { enabled: false, reason: "No target session" };
    },
    exec: (ctx) => {
      const sessionId = resolveSessionTargetId(ctx.state, ctx);
      if (!sessionId) return ctx.state;
      const nextState = saveSession(ctx.state, sessionId, { now: ctx.now ?? null });
      const refreshed = refreshSessionListIfOpen(nextState, { taskId: ctx.taskId ?? null });
      return {
        state: refreshed,
        output: { kind: "session.save", sessionId }
      };
    }
  });

  ensure(renameId, {
    title: "Rename Session",
    doc: "Rename the selected session.",
    enabled: (ctx) => {
      const sessionId = resolveSessionTargetId(ctx.state, ctx);
      return sessionId && ctx.state.sessions?.[sessionId]
        ? { enabled: true, reason: null }
        : { enabled: false, reason: "No target session" };
    },
    exec: (ctx) => {
      const sessionId = resolveSessionTargetId(ctx.state, ctx);
      if (!sessionId) return ctx.state;
      const name = ctx.name ?? ctx.payload?.name ?? ctx.inputValue ?? null;
      const nextState = renameSession(ctx.state, sessionId, name, {
        notes: ctx.notes ?? ctx.payload?.notes ?? undefined
      });
      const refreshed = refreshSessionListIfOpen(nextState, { taskId: ctx.taskId ?? null });
      return {
        state: refreshed,
        output: { kind: "session.rename", sessionId, name }
      };
    }
  });

  ensure(deleteId, {
    title: "Delete Session",
    doc: "Delete the selected session.",
    metadata: { beginner: { advanced: true, confirm: true, explanation: "Remove a saved workspace snapshot." } },
    enabled: (ctx) => {
      const sessionId = resolveSessionTargetId(ctx.state, ctx);
      return sessionId && ctx.state.sessions?.[sessionId]
        ? { enabled: true, reason: null }
        : { enabled: false, reason: "No target session" };
    },
    exec: (ctx) => {
      const sessionId = resolveSessionTargetId(ctx.state, ctx);
      if (!sessionId) return ctx.state;
      const nextState = deleteSession(ctx.state, sessionId);
      const refreshed = refreshSessionListIfOpen(nextState, { taskId: ctx.taskId ?? null });
      return {
        state: refreshed,
        output: { kind: "session.delete", sessionId }
      };
    }
  });

  return registry;
}

export function registerLayoutCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const splitId = options.splitCommandId ?? LAYOUT_SPLIT_COMMAND;
  const tabsId = options.tabsCommandId ?? LAYOUT_TABS_COMMAND;
  const dockId = options.dockCommandId ?? LAYOUT_DOCK_COMMAND;
  const activeTabId = options.activeTabCommandId ?? LAYOUT_SET_ACTIVE_TAB_COMMAND;

  const ensure = (id, command) => {
    if (!registry.commands.has(id)) {
      registerCommand(registry, { ...command, id });
    }
  };

  ensure(splitId, {
    title: "Split Layout",
    doc: "Split the active layout leaf.",
    metadata: { beginner: { advanced: true, explanation: "Split the current panel into two panes." } },
    enabled: (ctx) => {
      const target = resolveLayoutTargetId(ctx.state, ctx);
      return target ? { enabled: true, reason: null } : { enabled: false, reason: "No layout target" };
    },
    exec: (ctx) => {
      const target = resolveLayoutTargetId(ctx.state, ctx);
      if (!target) return ctx.state;
      const axis = ctx.axis ?? "h";
      const ratio = Number.isFinite(ctx.ratio) ? ctx.ratio : 0.5;
      const insert = ctx.insert ?? "after";
      const windowId = ctx.newWindowId ?? null;
      return splitLayout(ctx.state, target, axis, ratio, { insert, windowId });
    }
  });

  ensure(tabsId, {
    title: "Wrap In Tabs",
    doc: "Wrap the active layout leaf in a tabs container.",
    metadata: { beginner: { advanced: true, explanation: "Convert a pane into a tab group." } },
    enabled: (ctx) => {
      const target = resolveLayoutTargetId(ctx.state, ctx);
      return target ? { enabled: true, reason: null } : { enabled: false, reason: "No layout target" };
    },
    exec: (ctx) => {
      const target = resolveLayoutTargetId(ctx.state, ctx);
      if (!target) return ctx.state;
      const newWindowId = ctx.newWindowId ?? null;
      const newTab = newWindowId ? { windowId: newWindowId } : null;
      return wrapInTabs(ctx.state, target, {
        newTab,
        insert: ctx.insert ?? "after",
        activateNew: Boolean(ctx.activateNew)
      });
    }
  });

  ensure(activeTabId, {
    title: "Activate Tab",
    doc: "Set the active tab in a tabs container.",
    metadata: { beginner: { advanced: true, explanation: "Switch the active tab in a tab group." } },
    enabled: (ctx) => {
      const tabsIdValue = ctx.tabsId ?? null;
      const tabId = ctx.tabId ?? resolveLayoutTargetId(ctx.state, ctx);
      if (!tabsIdValue || !tabId) {
        return { enabled: false, reason: "No tab target" };
      }
      return { enabled: true, reason: null };
    },
    exec: (ctx) => {
      const tabId = ctx.tabId ?? resolveLayoutTargetId(ctx.state, ctx);
      const layout = ctx.state.layout;
      let tabsIdValue = ctx.tabsId ?? null;
      if (!tabsIdValue && layout && tabId) {
        const parent = findLayoutParent(layout, tabId);
        if (parent?.parent?.kind === "tabs") {
          tabsIdValue = parent.parentId;
        }
      }
      if (!tabsIdValue || !tabId) return ctx.state;
      return setActiveTab(ctx.state, tabsIdValue, tabId);
    }
  });

  ensure(dockId, {
    title: "Dock Layout",
    doc: "Dock the active layout leaf into a region.",
    metadata: { beginner: { advanced: true, explanation: "Dock a pane into a specific layout region." } },
    enabled: (ctx) => {
      const target = resolveLayoutTargetId(ctx.state, ctx);
      return target ? { enabled: true, reason: null } : { enabled: false, reason: "No layout target" };
    },
    exec: (ctx) => {
      const target = resolveLayoutTargetId(ctx.state, ctx);
      if (!target) return ctx.state;
      const region = ctx.region ?? "left";
      return dockLayout(ctx.state, target, region);
    }
  });

  return registry;
}

export function registerListSelectionCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const selectId = options.selectCommandId ?? LIST_SELECTION_UPDATE_COMMAND;

  if (!registry.commands.has(selectId)) {
    registerCommand(registry, {
      id: selectId,
      title: "Update List Selection",
      doc: "Update list selection with replace, toggle, or range semantics.",
      enabled: (ctx) => {
        const listId = ctx.listId ?? ctx.payload?.listId ?? null;
        const itemId = ctx.itemId ?? ctx.payload?.itemId ?? null;
        if (!listId) return { enabled: false, reason: "No list id" };
        if (!itemId) return { enabled: false, reason: "No item id" };
        return { enabled: true, reason: null };
      },
      exec: (ctx) => {
        const listId = ctx.listId ?? ctx.payload?.listId ?? null;
        const itemId = ctx.itemId ?? ctx.payload?.itemId ?? null;
        if (!listId || !itemId) return ctx.state;
        return updateListSelection(ctx.state, {
          listId,
          itemId,
          mode: ctx.selectionMode ?? ctx.payload?.selectionMode ?? "replace",
          multiple: Boolean(ctx.multiple ?? ctx.payload?.multiple ?? false),
          listItemIds: ctx.listItemIds ?? ctx.payload?.listItemIds ?? null
        });
      }
    });
  }

  return registry;
}

export function registerRecordingCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const recordingId = options.recordingCommandId ?? RECORDING_APPEND_COMMAND;
  const entryId = options.entryCommandId ?? RECORDING_ENTRY_APPEND_COMMAND;
  const anchorId = options.anchorCommandId ?? RECORDING_ANCHOR_ATTACH_COMMAND;
  const foldId = options.foldCommandId ?? RECORDING_ENTRY_FOLD_COMMAND;
  const toggleId = options.toggleCommandId ?? RECORDING_TOGGLE_COMMAND;
  const copyAsFormId = options.copyAsFormCommandId ?? RECORDING_COPY_AS_FORM_COMMAND;
  const copyWithContextId = options.copyWithContextCommandId ?? RECORDING_COPY_WITH_CONTEXT_COMMAND;
  const replayAsInputId = options.replayAsInputCommandId ?? RECORDING_REPLAY_AS_INPUT_COMMAND;
  const rerunId = options.rerunCommandId ?? RECORDING_RERUN_COMMAND;
  const historyId = options.historyCommandId ?? COMMAND_HISTORY_APPEND_COMMAND;

  const ensure = (id, command) => {
    if (!registry.commands.has(id)) {
      registerCommand(registry, { ...command, id });
    }
  };

  const maybeApplyListSelectionFromCtx = (state, ctx) => {
    const listId = ctx.listId ?? ctx.payload?.listId ?? null;
    const itemId = ctx.itemId ?? ctx.payload?.itemId ?? ctx.item?.id ?? null;
    if (!listId || !itemId || ctx.item?.selectable === false) {
      return state;
    }
    return updateListSelection(state, {
      listId,
      itemId,
      mode: ctx.selectionMode ?? ctx.payload?.selectionMode ?? "replace",
      multiple: Boolean(ctx.multiple ?? ctx.payload?.multiple ?? false),
      listItemIds: ctx.listItemIds ?? ctx.payload?.listItemIds ?? null
    });
  };

  ensure(recordingId, {
    title: "Append Recording",
    doc: "Append a recording to the transcript.",
    enabled: (ctx) => (ctx?.recording || ctx?.payload?.recording ? { enabled: true, reason: null } : { enabled: false, reason: "No recording" }),
    exec: (ctx) => {
      const recording = ctx.recording ?? ctx.payload?.recording ?? null;
      if (!recording) return ctx.state;
      return appendRecording(ctx.state, recording);
    }
  });

  ensure(entryId, {
    title: "Append Recording Entry",
    doc: "Append an entry to the transcript.",
    enabled: (ctx) => (ctx?.entry || ctx?.payload?.entry ? { enabled: true, reason: null } : { enabled: false, reason: "No entry" }),
    exec: (ctx) => {
      const entry = ctx.entry ?? ctx.payload?.entry ?? null;
      if (!entry) return ctx.state;
      return appendRecordingEntry(ctx.state, entry);
    }
  });

  ensure(anchorId, {
    title: "Attach Recording Anchor",
    doc: "Attach an anchor to a transcript entry.",
    enabled: (ctx) => (ctx?.anchor || ctx?.payload?.anchor ? { enabled: true, reason: null } : { enabled: false, reason: "No anchor" }),
    exec: (ctx) => {
      const anchor = ctx.anchor ?? ctx.payload?.anchor ?? null;
      if (!anchor) return ctx.state;
      return attachRecordingAnchor(ctx.state, anchor);
    }
  });

  ensure(foldId, {
    title: "Fold Recording Entry",
    doc: "Fold or unfold a transcript entry.",
    enabled: (ctx) => {
      const entryIdValue = ctx.entryId ?? ctx.payload?.entryId ?? ctx.item?.entryId ?? null;
      return entryIdValue ? { enabled: true, reason: null } : { enabled: false, reason: "No entry id" };
    },
    exec: (ctx) => {
      const entryIdValue = ctx.entryId ?? ctx.payload?.entryId ?? ctx.item?.entryId ?? null;
      if (!entryIdValue) return ctx.state;
      const existing = Boolean(ctx.state.recordingStore?.entries?.[entryIdValue]?.metadata?.folded);
      const requested = ctx.folded ?? ctx.payload?.folded ?? null;
      const folded = requested === null || requested === undefined ? !existing : Boolean(requested);
      const selectedState = maybeApplyListSelectionFromCtx(ctx.state, ctx);
      return setRecordingEntryFolded(selectedState, entryIdValue, folded);
    }
  });

  ensure(toggleId, {
    title: "Toggle Recording Visibility",
    doc: "Toggle run collapse or entry fold state from transcript controls.",
    enabled: (ctx) => {
      const entryIdValue = ctx.entryId ?? ctx.payload?.entryId ?? ctx.item?.entryId ?? null;
      const recordingIdValue = resolveRecordingId(ctx) ?? null;
      return entryIdValue || recordingIdValue
        ? { enabled: true, reason: null }
        : { enabled: false, reason: "No recording target" };
    },
    exec: (ctx) => {
      const selectedState = maybeApplyListSelectionFromCtx(ctx.state, ctx);
      const entryIdValue = ctx.entryId ?? ctx.payload?.entryId ?? ctx.item?.entryId ?? null;
      if (entryIdValue) {
        const existing = Boolean(selectedState.recordingStore?.entries?.[entryIdValue]?.metadata?.folded);
        return setRecordingEntryFolded(selectedState, entryIdValue, !existing);
      }
      const recordingIdValue = resolveRecordingId(ctx) ?? null;
      if (!recordingIdValue) return selectedState;
      const existing = Boolean(selectedState.recordingStore?.recordings?.[recordingIdValue]?.metadata?.collapsed);
      return setRecordingCollapsed(selectedState, recordingIdValue, !existing);
    }
  });

  ensure(copyAsFormId, {
    title: "Copy Recording As Form",
    doc: "Copy a recording entry or anchor as a form payload.",
    enabled: (ctx) => (resolveRecordingTarget(ctx) ? { enabled: true, reason: null } : { enabled: false, reason: "No entry target" }),
    exec: (ctx) => {
      const target = resolveRecordingTarget(ctx);
      if (!target) return ctx.state;
      try {
        const output = copyAsFormRecording(ctx.state.recordingStore ?? null, target);
        return { state: ctx.state, output };
      } catch (_err) {
        return ctx.state;
      }
    }
  });

  ensure(copyWithContextId, {
    title: "Copy Recording With Context",
    doc: "Copy a recording entry with provenance context.",
    enabled: (ctx) => (resolveRecordingTarget(ctx) ? { enabled: true, reason: null } : { enabled: false, reason: "No entry target" }),
    exec: (ctx) => {
      const target = resolveRecordingTarget(ctx);
      if (!target) return ctx.state;
      try {
        const output = copyWithContextRecording(ctx.state.recordingStore ?? null, target);
        return { state: ctx.state, output };
      } catch (_err) {
        return ctx.state;
      }
    }
  });

  ensure(replayAsInputId, {
    title: "Replay Recording As Input",
    doc: "Materialize a previous recording as runnable input.",
    enabled: (ctx) => {
      const id = resolveRecordingId(ctx);
      return id ? { enabled: true, reason: null } : { enabled: false, reason: "No recording id" };
    },
    exec: (ctx) => {
      const id = resolveRecordingId(ctx);
      if (!id) return ctx.state;
      try {
        const output = replayAsInputRecording(ctx.state.recordingStore ?? null, id);
        return { state: ctx.state, output };
      } catch (_err) {
        return ctx.state;
      }
    }
  });

  ensure(rerunId, {
    title: "Re-Run Recording",
    doc: "Build a rerun command payload for a recording.",
    enabled: (ctx) => {
      const id = resolveRecordingId(ctx);
      return id ? { enabled: true, reason: null } : { enabled: false, reason: "No recording id" };
    },
    exec: (ctx) => {
      const id = resolveRecordingId(ctx);
      if (!id) return ctx.state;
      try {
        const output = reRunRecordingInput(ctx.state.recordingStore ?? null, id, {
          commandId: ctx.runCommandId ?? ctx.payload?.runCommandId ?? null
        });
        return { state: ctx.state, output };
      } catch (_err) {
        return ctx.state;
      }
    }
  });

  ensure(historyId, {
    title: "Append Command History",
    doc: "Record a command invocation in history.",
    enabled: (ctx) =>
      ctx?.invocation || ctx?.payload?.invocation ? { enabled: true, reason: null } : { enabled: false, reason: "No invocation" },
    exec: (ctx) => {
      const invocation = ctx.invocation ?? ctx.payload?.invocation ?? null;
      if (!invocation) return ctx.state;
      return recordCommandInvocation(ctx.state, invocation);
    }
  });

  return registry;
}

export function registerTranscriptCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const openId = options.openCommandId ?? TRANSCRIPT_OPEN_COMMAND;
  const refreshId = options.refreshCommandId ?? TRANSCRIPT_REFRESH_COMMAND;
  const itemOpenId = options.itemOpenCommandId ?? TRANSCRIPT_ITEM_OPEN_COMMAND;

  const ensure = (id, command) => {
    if (!registry.commands.has(id)) {
      registerCommand(registry, { ...command, id });
    }
  };

  ensure(openId, {
    title: "Open Transcript",
    doc: "Open the transcript window for the current task.",
    exec: (ctx) =>
      openTranscriptWindow(ctx.state, {
        taskId: ctx.taskId ?? ctx.state.workspace?.activeTaskId ?? null,
        limit: ctx.limit ?? ctx.payload?.limit ?? null
      })
  });

  ensure(refreshId, {
    title: "Refresh Transcript",
    doc: "Refresh the transcript window list.",
    exec: (ctx) => {
      const taskId = ctx.taskId ?? ctx.state.workspace?.activeTaskId ?? null;
      const windowId =
        ctx.windowId ??
        findWindowByRole(ctx.state, "transcript", taskId)?.id ??
        null;
      if (!windowId) return ctx.state;
      return refreshTranscriptWindow(ctx.state, windowId, {
        limit: ctx.limit ?? ctx.payload?.limit ?? null,
        presentationResolver:
          ctx.presentationResolver ??
          ctx.payload?.presentationResolver ??
          null
      });
    }
  });

  ensure(itemOpenId, {
    title: "Open Transcript Item",
    doc: "Open or inspect the selected transcript entry presentation.",
    enabled: (ctx) => {
      const item = ctx.item ?? ctx.payload?.item ?? null;
      const presentationId = item?.presentationId ?? null;
      return presentationId ? { enabled: true, reason: null } : { enabled: false, reason: "No presentation" };
    },
    exec: (ctx) => {
      const registryRef = ctx.registry ?? ctx.payload?.registry ?? null;
      if (!registryRef) return ctx.state;
      const item = ctx.item ?? ctx.payload?.item ?? null;
      const entryId = item?.entryId ?? null;
      let presentationId = item?.presentationId ?? null;
      if (!presentationId && entryId) {
        const entry = ctx.state.recordingStore?.entries?.[entryId];
        presentationId = entry?.presentationId ?? null;
      }
      if (!presentationId) return ctx.state;
      const presentation = ctx.state.presentations?.[presentationId] ?? { id: presentationId, type: "value" };
      const result = executePresentationCommand(registryRef, presentation, "click", ctx);
      return resolveCommandResultState(result, ctx.state);
    }
  });

  return registry;
}

export function registerCommandHistoryCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const openId = options.openCommandId ?? COMMAND_HISTORY_OPEN_COMMAND;
  const refreshId = options.refreshCommandId ?? COMMAND_HISTORY_REFRESH_COMMAND;
  const executeId = options.executeCommandId ?? COMMAND_HISTORY_EXECUTE_COMMAND;

  const ensure = (id, command) => {
    if (!registry.commands.has(id)) {
      registerCommand(registry, { ...command, id });
    }
  };

  ensure(openId, {
    title: "Open Command History",
    doc: "Open the command history window for the current task.",
    exec: (ctx) =>
      openCommandHistoryWindow(ctx.state, {
        taskId: ctx.taskId ?? ctx.state.workspace?.activeTaskId ?? null,
        limit: ctx.limit ?? ctx.payload?.limit ?? null
      })
  });

  ensure(refreshId, {
    title: "Refresh Command History",
    doc: "Refresh the command history list.",
    exec: (ctx) => {
      const taskId = ctx.taskId ?? ctx.state.workspace?.activeTaskId ?? null;
      const windowId =
        ctx.windowId ??
        findWindowByRole(ctx.state, "command-history", taskId)?.id ??
        null;
      if (!windowId) return ctx.state;
      return refreshCommandHistoryWindow(ctx.state, windowId, {
        limit: ctx.limit ?? ctx.payload?.limit ?? null,
        presentationResolver:
          ctx.presentationResolver ??
          ctx.payload?.presentationResolver ??
          null
      });
    }
  });

  ensure(executeId, {
    title: "Execute History Entry",
    doc: "Execute the selected command history entry.",
    enabled: (ctx) => {
      const invocation = ctx.invocation ?? ctx.payload?.invocation ?? ctx.item?.invocation ?? null;
      const commandId = invocation?.commandId ?? ctx.commandId ?? null;
      return commandId ? { enabled: true, reason: null } : { enabled: false, reason: "No command id" };
    },
    exec: (ctx) => {
      const registryRef = ctx.registry ?? ctx.payload?.registry ?? null;
      if (!registryRef) return ctx.state;
      const invocation = ctx.invocation ?? ctx.payload?.invocation ?? ctx.item?.invocation ?? null;
      const commandId = invocation?.commandId ?? ctx.commandId ?? null;
      if (!commandId) return ctx.state;
      const argsPayload = invocation?.args ?? {};
      const execCtx = { ...ctx, payload: argsPayload, invocation };
      const result = executeCommand(registryRef, commandId, execCtx);
      let nextState = resolveCommandResultState(result, ctx.state);
      if (result?.ok && result?.invocation) {
        nextState = recordCommandInvocation(nextState, result.invocation);
      }
      return nextState;
    }
  });

  return registry;
}

export function registerInspectorCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const pinId = options.pinWatchCommandId ?? INSPECTOR_WATCH_PIN_COMMAND;
  const unpinId = options.unpinWatchCommandId ?? INSPECTOR_WATCH_UNPIN_COMMAND;
  const stageId = options.stageEditCommandId ?? INSPECTOR_EDIT_STAGE_COMMAND;
  const applyId = options.applyEditCommandId ?? INSPECTOR_EDIT_APPLY_COMMAND;
  const undoId = options.undoEditCommandId ?? INSPECTOR_EDIT_UNDO_COMMAND;

  const pinSpec = normalizeCommandSpec({
    id: pinId,
    title: "Pin Watch",
    doc: "Pin the selected item as an inspector watch.",
    scope: "context",
    args: [
      { name: "entryId", type: "string", required: false, defaultFrom: ["selection"] },
      { name: "presentationId", type: "string", required: false, defaultFrom: ["presentation"] },
      { name: "recordingId", type: "string", required: false },
      { name: "label", type: "string", required: false },
      { name: "valueSummary", type: "string", required: false }
    ],
    metadata: { kind: "inspector.watch.pin", runtime: true, runtimeCommandId: "runtime.watch.pin" }
  });
  const unpinSpec = normalizeCommandSpec({
    id: unpinId,
    title: "Unpin Watch",
    doc: "Remove a watch from inspector pinned watches.",
    scope: "context",
    args: [{ name: "watchId", type: "string", required: true, defaultFrom: ["selection"] }],
    metadata: { kind: "inspector.watch.unpin", runtime: true, runtimeCommandId: "runtime.watch.unpin" }
  });
  const stageSpec = normalizeCommandSpec({
    id: stageId,
    title: "Stage Edit",
    doc: "Stage an edit group for inspector place edits.",
    scope: "context",
    args: [
      { name: "placeId", type: "string", required: false, defaultFrom: ["selection", "presentation"] },
      { name: "before", type: "string", required: false },
      { name: "after", type: "string", required: false },
      { name: "label", type: "string", required: false },
      { name: "edits", type: "list", required: false }
    ],
    metadata: { kind: "inspector.edit.stage", runtime: true, runtimeCommandId: "runtime.place.stage" }
  });
  const applySpec = normalizeCommandSpec({
    id: applyId,
    title: "Apply Staged Edit",
    doc: "Apply the selected staged edit group.",
    scope: "context",
    args: [{ name: "editGroupId", type: "string", required: true, defaultFrom: ["selection"] }],
    metadata: { kind: "inspector.edit.apply", runtime: true, runtimeCommandId: "runtime.place.apply" }
  });
  const undoSpec = normalizeCommandSpec({
    id: undoId,
    title: "Undo Staged Edit",
    doc: "Undo the selected staged edit group.",
    scope: "context",
    args: [{ name: "editGroupId", type: "string", required: true, defaultFrom: ["selection"] }],
    metadata: { kind: "inspector.edit.undo", runtime: true, runtimeCommandId: "runtime.place.undo" }
  });

  const ensure = (id, command) => {
    if (!registry.commands.has(id)) {
      registerCommand(registry, { ...command, id });
    }
  };

  const hasRuntimeClient = (ctx) => Boolean(ctx.runtimeCommandClient?.dispatchTypedCommand);
  const nextInvocationId = (ctx) =>
    ctx.invocationId ?? ctx.payload?.invocationId ?? `inv-${(ctx.state.commandHistory ?? []).length + 1}`;
  const nextInvocationTs = (ctx) => (Number.isInteger(ctx.ts) ? ctx.ts : null);
  const nextInvocationSource = (ctx, fallback) => ctx.source ?? ctx.payload?.source ?? fallback;

  const resolvePinContext = (ctx) => {
    const item = ctx.item ?? ctx.payload?.item ?? null;
    return {
      item,
      entryId: ctx.entryId ?? ctx.payload?.entryId ?? item?.entryId ?? null,
      presentationId: ctx.presentationId ?? ctx.payload?.presentationId ?? item?.presentationId ?? null,
      recordingId: ctx.recordingId ?? ctx.payload?.recordingId ?? item?.recordingId ?? null,
      label: ctx.label ?? ctx.payload?.label ?? item?.label ?? null,
      valueSummary: ctx.valueSummary ?? ctx.payload?.valueSummary ?? item?.valueSummary ?? null
    };
  };

  const resolveUnpinContext = (ctx) => {
    const item = ctx.item ?? ctx.payload?.item ?? null;
    return {
      watchId: ctx.watchId ?? ctx.payload?.watchId ?? item?.watchId ?? item?.id ?? null
    };
  };

  const resolveStageContext = (ctx) => {
    const payload = ctx.payload ?? {};
    const edit = ctx.edit ?? payload.edit ?? null;
    const edits = ctx.edits ?? payload.edits ?? null;
    const placeId = ctx.placeId ?? payload.placeId ?? edit?.placeId ?? null;
    const before = ctx.before ?? payload.before ?? edit?.before ?? null;
    const after = ctx.after ?? payload.after ?? ctx.value ?? payload.value ?? edit?.after ?? edit?.value ?? null;
    const label = ctx.label ?? payload.label ?? edit?.label ?? null;
    return { edit, edits, placeId, before, after, label };
  };

  const resolveEditGroupContext = (ctx) => {
    const item = ctx.item ?? ctx.payload?.item ?? null;
    return {
      editGroupId: ctx.editGroupId ?? ctx.payload?.editGroupId ?? item?.editGroupId ?? item?.id ?? null
    };
  };

  ensure(pinId, {
    title: pinSpec.title ?? "Pin Watch",
    doc: pinSpec.doc ?? "Pin the selected item as an inspector watch.",
    scope: pinSpec.scope ?? "context",
    args: pinSpec.args ?? [],
    metadata: { ...(pinSpec.metadata ?? {}), typed: pinSpec },
    enabled: (ctx) => {
      const pinCtx = resolvePinContext(ctx);
      const hasTarget = Boolean(pinCtx.entryId ?? pinCtx.presentationId ?? pinCtx.recordingId);
      return hasTarget ? { enabled: true, reason: null } : { enabled: false, reason: "No watch target" };
    },
    exec: (ctx) => {
      const pinCtx = resolvePinContext(ctx);
      const pending = hasRuntimeClient(ctx);
      const args = {
        entryId: pinCtx.entryId,
        presentationId: pinCtx.presentationId,
        recordingId: pinCtx.recordingId,
        label: pinCtx.label,
        valueSummary: pinCtx.valueSummary
      };
      const defaults = {};
      if (pinCtx.entryId && ctx.entryId == null && ctx.payload?.entryId == null) {
        defaults.entryId = { source: "selection" };
      }
      if (pinCtx.presentationId && ctx.presentationId == null && ctx.payload?.presentationId == null) {
        defaults.presentationId = { source: "selection" };
      }
      const invocation = {
        id: nextInvocationId(ctx),
        commandId: pinId,
        args,
        defaults,
        ts: nextInvocationTs(ctx),
        source: nextInvocationSource(ctx, "inspector"),
        result: pending ? { status: "pending" } : null
      };
      const validation = validateInvocation(invocation, pinSpec);
      if (!validation.ok) return ctx.state;
      let nextState = recordCommandInvocation(ctx.state, invocation);
      if (pending) return { state: nextState };
      nextState = pinWatch(nextState, {
        item: pinCtx.item,
        entryId: pinCtx.entryId,
        presentationId: pinCtx.presentationId,
        recordingId: pinCtx.recordingId,
        label: pinCtx.label,
        valueSummary: pinCtx.valueSummary,
        ts: ctx.ts ?? null,
        metadata: ctx.metadata ?? ctx.payload?.metadata ?? {}
      });
      return nextState;
    }
  });

  ensure(unpinId, {
    title: unpinSpec.title ?? "Unpin Watch",
    doc: unpinSpec.doc ?? "Remove a watch from inspector pinned watches.",
    scope: unpinSpec.scope ?? "context",
    args: unpinSpec.args ?? [],
    metadata: { ...(unpinSpec.metadata ?? {}), typed: unpinSpec },
    enabled: (ctx) => {
      const watchCtx = resolveUnpinContext(ctx);
      const watchId = watchCtx.watchId;
      return watchId ? { enabled: true, reason: null } : { enabled: false, reason: "No watch id" };
    },
    exec: (ctx) => {
      const watchCtx = resolveUnpinContext(ctx);
      if (!watchCtx.watchId) return ctx.state;
      const pending = hasRuntimeClient(ctx);
      const invocation = {
        id: nextInvocationId(ctx),
        commandId: unpinId,
        args: { watchId: watchCtx.watchId },
        defaults: {},
        ts: nextInvocationTs(ctx),
        source: nextInvocationSource(ctx, "inspector"),
        result: pending ? { status: "pending" } : null
      };
      const validation = validateInvocation(invocation, unpinSpec);
      if (!validation.ok) return ctx.state;
      let nextState = recordCommandInvocation(ctx.state, invocation);
      if (pending) return { state: nextState };
      nextState = unpinWatch(nextState, watchCtx.watchId);
      return nextState;
    }
  });

  ensure(stageId, {
    title: stageSpec.title ?? "Stage Edit",
    doc: stageSpec.doc ?? "Stage an edit group for inspector place edits.",
    scope: stageSpec.scope ?? "context",
    args: stageSpec.args ?? [],
    metadata: { ...(stageSpec.metadata ?? {}), typed: stageSpec },
    enabled: (ctx) => {
      const stageCtx = resolveStageContext(ctx);
      const hasInline = Boolean(stageCtx.placeId);
      const hasEdits = Array.isArray(stageCtx.edits) && stageCtx.edits.length > 0;
      const edit = stageCtx.edit ?? (hasEdits ? stageCtx.edits[0] : null);
      return edit || hasInline ? { enabled: true, reason: null } : { enabled: false, reason: "No edit payload" };
    },
    exec: (ctx) => {
      const stageCtx = resolveStageContext(ctx);
      const hasEdits = Array.isArray(stageCtx.edits) && stageCtx.edits.length > 0;
      const pending = hasRuntimeClient(ctx);
      const args = {
        placeId: stageCtx.placeId,
        before: stageCtx.before,
        after: stageCtx.after,
        label: stageCtx.label,
        edits: hasEdits ? stageCtx.edits : null
      };
      const defaults = {};
      if (stageCtx.placeId && ctx.placeId == null && ctx.payload?.placeId == null) {
        defaults.placeId = { source: "selection" };
      }
      const invocation = {
        id: nextInvocationId(ctx),
        commandId: stageId,
        args,
        defaults,
        ts: nextInvocationTs(ctx),
        source: nextInvocationSource(ctx, "inspector"),
        result: pending ? { status: "pending" } : null
      };
      const validation = validateInvocation(invocation, stageSpec);
      if (!validation.ok) return ctx.state;
      let nextState = recordCommandInvocation(ctx.state, invocation);
      if (pending) return { state: nextState };
      nextState = stageEdit(nextState, {
        edit: stageCtx.edit ?? null,
        edits: hasEdits ? stageCtx.edits : null,
        placeId: stageCtx.placeId,
        before: stageCtx.before,
        after: stageCtx.after,
        label: stageCtx.label,
        ts: ctx.ts ?? null,
        metadata: ctx.metadata ?? ctx.payload?.metadata ?? {}
      });
      return nextState;
    }
  });

  ensure(applyId, {
    title: applySpec.title ?? "Apply Staged Edit",
    doc: applySpec.doc ?? "Apply the selected staged edit group.",
    scope: applySpec.scope ?? "context",
    args: applySpec.args ?? [],
    metadata: { ...(applySpec.metadata ?? {}), typed: applySpec },
    enabled: (ctx) => {
      const editCtx = resolveEditGroupContext(ctx);
      const editGroupId = editCtx.editGroupId;
      return editGroupId ? { enabled: true, reason: null } : { enabled: false, reason: "No edit group id" };
    },
    exec: (ctx) => {
      const editCtx = resolveEditGroupContext(ctx);
      if (!editCtx.editGroupId) return ctx.state;
      const pending = hasRuntimeClient(ctx);
      const invocation = {
        id: nextInvocationId(ctx),
        commandId: applyId,
        args: { editGroupId: editCtx.editGroupId },
        defaults: {},
        ts: nextInvocationTs(ctx),
        source: nextInvocationSource(ctx, "inspector"),
        result: pending ? { status: "pending" } : null
      };
      const validation = validateInvocation(invocation, applySpec);
      if (!validation.ok) return ctx.state;
      let nextState = recordCommandInvocation(ctx.state, invocation);
      if (pending) return { state: nextState };
      nextState = applyEditGroup(nextState, editCtx.editGroupId, { ts: ctx.ts ?? null });
      return nextState;
    }
  });

  ensure(undoId, {
    title: undoSpec.title ?? "Undo Staged Edit",
    doc: undoSpec.doc ?? "Undo the selected staged edit group.",
    scope: undoSpec.scope ?? "context",
    args: undoSpec.args ?? [],
    metadata: { ...(undoSpec.metadata ?? {}), typed: undoSpec },
    enabled: (ctx) => {
      const editCtx = resolveEditGroupContext(ctx);
      const editGroupId = editCtx.editGroupId;
      return editGroupId ? { enabled: true, reason: null } : { enabled: false, reason: "No edit group id" };
    },
    exec: (ctx) => {
      const editCtx = resolveEditGroupContext(ctx);
      if (!editCtx.editGroupId) return ctx.state;
      const pending = hasRuntimeClient(ctx);
      const invocation = {
        id: nextInvocationId(ctx),
        commandId: undoId,
        args: { editGroupId: editCtx.editGroupId },
        defaults: {},
        ts: nextInvocationTs(ctx),
        source: nextInvocationSource(ctx, "inspector"),
        result: pending ? { status: "pending" } : null
      };
      const validation = validateInvocation(invocation, undoSpec);
      if (!validation.ok) return ctx.state;
      let nextState = recordCommandInvocation(ctx.state, invocation);
      if (pending) return { state: nextState };
      nextState = undoEditGroup(nextState, editCtx.editGroupId, { ts: ctx.ts ?? null });
      return nextState;
    }
  });

  return registry;
}

export function registerProblemsCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const openId = options.openCommandId ?? PROBLEMS_OPEN_COMMAND;
  const refreshId = options.refreshCommandId ?? PROBLEMS_REFRESH_COMMAND;
  const itemOpenId = options.itemOpenCommandId ?? PROBLEMS_ITEM_OPEN_COMMAND;

  const ensure = (id, command) => {
    if (!registry.commands.has(id)) {
      registerCommand(registry, { ...command, id });
    }
  };

  ensure(openId, {
    title: "Open Problems",
    doc: "Open the Problems window for the current task.",
    exec: (ctx) =>
      openProblemsWindow(ctx.state, {
        taskId: ctx.taskId ?? ctx.state.workspace?.activeTaskId ?? null
      })
  });

  ensure(refreshId, {
    title: "Refresh Problems",
    doc: "Refresh the Problems list.",
    exec: (ctx) => {
      const taskId = ctx.taskId ?? ctx.state.workspace?.activeTaskId ?? null;
      const windowId =
        ctx.windowId ??
        findWindowByRole(ctx.state, "problems", taskId)?.id ??
        null;
      if (!windowId) return ctx.state;
      return refreshProblemsWindow(ctx.state, windowId, {
        presentationResolver:
          ctx.presentationResolver ??
          ctx.payload?.presentationResolver ??
          null
      });
    }
  });

  ensure(itemOpenId, {
    title: "Open Problem",
    doc: "Open the debugger focused on the selected problem.",
    enabled: (ctx) => {
      const item = ctx.item ?? ctx.payload?.item ?? null;
      const errorId = item?.errorId ?? item?.id ?? ctx.errorId ?? ctx.payload?.errorId ?? null;
      if (!errorId) {
        return { enabled: false, reason: "No error selected" };
      }
      const error = ctx.state.errors?.find((entry) => entry.id === errorId) ?? null;
      return error ? { enabled: true, reason: null } : { enabled: false, reason: "Error not found" };
    },
    exec: (ctx) => {
      const item = ctx.item ?? ctx.payload?.item ?? null;
      const errorId = item?.errorId ?? item?.id ?? ctx.errorId ?? ctx.payload?.errorId ?? null;
      if (!errorId) return ctx.state;
      const error = ctx.state.errors?.find((entry) => entry.id === errorId) ?? null;
      if (!error) return ctx.state;
      const taskId = error.taskId ?? ctx.taskId ?? ctx.state.workspace?.activeTaskId ?? null;
      if (!taskId) return ctx.state;
      return openDebuggerWindow(ctx.state, { taskId, errorId: error.id });
    }
  });

  return registry;
}

export function registerDebuggerCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const restartCommandId = options.restartCommandId ?? DEBUGGER_RESTART_INVOKE_COMMAND;
  const restartSpec = normalizeCommandSpec({
    id: restartCommandId,
    title: "Invoke Restart",
    doc: "Invoke the selected restart.",
    scope: "context",
    args: [
      { name: "restartId", type: "string", required: true, defaultFrom: ["selection", "presentation"] },
      { name: "errorId", type: "string", required: true, defaultFrom: ["selection", "presentation"] },
      { name: "args", type: "map", required: false }
    ],
    metadata: { kind: "restart", runtime: true, runtimeCommandId: "runtime.restart.invoke" }
  });

  const ensure = (id, command) => {
    if (!registry.commands.has(id)) {
      registerCommand(registry, { ...command, id });
    }
  };

  const resolveRestartContext = (ctx) => {
    const item = ctx.item ?? ctx.payload?.item ?? null;
    const restartId = item?.restartId ?? ctx.restartId ?? ctx.payload?.restartId ?? null;
    const errorId =
      item?.errorId ??
      ctx.errorId ??
      ctx.payload?.errorId ??
      (ctx.windowId ? ctx.state.windows?.[ctx.windowId]?.metadata?.errorId ?? null : null) ??
      ctx.state.errors?.[ctx.state.errors.length - 1]?.id ??
      null;
    const error = errorId ? ctx.state.errors?.find((entry) => entry.id === errorId) ?? null : null;
    const restarts = Array.isArray(error?.restarts) ? error.restarts.map(normalizeRestart) : [];
    const restart = item?.restart ?? restarts.find((entry) => entry.id === restartId) ?? null;
    const taskId = error?.taskId ?? ctx.taskId ?? ctx.state.workspace?.activeTaskId ?? null;
    return { restartId, errorId, restart, error, taskId, item };
  };

  ensure(restartCommandId, {
    title: restartSpec.title ?? "Invoke Restart",
    doc: restartSpec.doc ?? "Invoke the selected restart.",
    scope: restartSpec.scope ?? "context",
    args: restartSpec.args ?? [],
    metadata: { ...(restartSpec.metadata ?? {}), typed: restartSpec },
    enabled: (ctx) => {
      const { restartId, errorId, error, restart } = resolveRestartContext(ctx);
      if (!restartId) return { enabled: false, reason: "No restart selected" };
      if (!errorId) return { enabled: false, reason: "No error selected" };
      if (!error) return { enabled: false, reason: "Error not found" };
      if (!restart) return { enabled: false, reason: "Restart not found" };
      return { enabled: true, reason: null };
    },
    exec: (ctx) => {
      const { restartId, errorId, error, restart, item } = resolveRestartContext(ctx);
      if (!restartId || !errorId || !error || !restart) return ctx.state;
      const hasRuntimeClient = Boolean(ctx.runtimeCommandClient?.dispatchTypedCommand);
      const args = { restartId, errorId };
      const restartArgs = ctx.args ?? ctx.payload?.args ?? null;
      if (restartArgs !== null && restartArgs !== undefined) {
        args.args = restartArgs;
      }
      const defaults = {};
      if (item?.restartId && ctx.restartId == null && ctx.payload?.restartId == null) {
        defaults.restartId = { source: "selection" };
      }
      if (item?.errorId && ctx.errorId == null && ctx.payload?.errorId == null) {
        defaults.errorId = { source: "selection" };
      }
      const invocation = {
        id: ctx.invocationId ?? ctx.payload?.invocationId ?? `inv-${(ctx.state.commandHistory ?? []).length}`,
        commandId: restartCommandId,
        args,
        defaults,
        ts: Number.isInteger(ctx.ts) ? ctx.ts : null,
        source: ctx.source ?? ctx.payload?.source ?? "debugger",
        result: hasRuntimeClient ? { status: "pending" } : null
      };
      const validation = validateInvocation(invocation, restartSpec);
      if (!validation.ok) return ctx.state;
      const nextState = recordCommandInvocation(ctx.state, invocation);
      if (hasRuntimeClient) {
        return { state: nextState };
      }
      return {
        state: nextState,
        output: {
          kind: "restart.invoke",
          restartId,
          errorId,
          args: restartArgs ?? null,
          restart
        }
      };
    }
  });

  return registry;
}

export function registerCapabilityCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const requestId = options.requestCommandId ?? CAPABILITY_REQUEST_COMMAND;
  const grantId = options.grantCommandId ?? CAPABILITY_GRANT_COMMAND;
  const revokeId = options.revokeCommandId ?? CAPABILITY_REVOKE_COMMAND;
  const openPanelId = options.openPanelCommandId ?? CAPABILITY_OPEN_PANEL_COMMAND;
  const selectId = options.selectCommandId ?? CAPABILITY_SELECT_COMMAND;
  const approveId = options.approveCommandId ?? CAPABILITY_APPROVE_COMMAND;
  const denyId = options.denyCommandId ?? CAPABILITY_DENY_COMMAND;
  const autoRunId = options.autoRunCommandId ?? CAPABILITY_AUTO_RUN_COMMAND;
  const safeModeEnableId = options.safeModeEnableCommandId ?? SAFE_MODE_ENABLE_COMMAND;
  const safeModeDisableId = options.safeModeDisableCommandId ?? SAFE_MODE_DISABLE_COMMAND;

  const resolveCapability = (ctx) => ctx.capability ?? ctx.payload?.capability ?? ctx.itemId ?? null;
  const resolveRequestId = (ctx) =>
    ctx.requestId ??
    ctx.payload?.requestId ??
    ctx.itemId ??
    ctx.item?.requestId ??
    ctx.item?.id ??
    null;

  const ensure = (id, command) => {
    if (!registry.commands.has(id)) {
      registerCommand(registry, { ...command, id });
    }
  };

  const refreshMediationWindow = (state, ctx) => {
    const taskId = ctx.taskId ?? state.workspace?.activeTaskId ?? null;
    const windowId =
      ctx.windowId ??
      findWindowByRole(state, "capability-mediation", taskId)?.id ??
      null;
    if (!windowId) return state;
    return refreshCapabilityMediationWindow(state, windowId);
  };

  ensure(requestId, {
    title: "Request Capability",
    doc: "Record a capability request for policy mediation.",
    metadata: { beginner: { advanced: true, hidden: true } },
    enabled: (ctx) => {
      const capability = resolveCapability(ctx);
      return capability
        ? { enabled: true, reason: null }
        : { enabled: false, reason: "No capability specified" };
    },
    exec: (ctx) => {
      const capability = resolveCapability(ctx);
      if (!capability) return ctx.state;
      const nextState = requestCapability(ctx.state, capability, {
        reason: ctx.reason ?? ctx.payload?.reason ?? null,
        taskId: ctx.taskId ?? null,
        windowId: ctx.windowId ?? null,
        commandId: requestId
      });
      return refreshMediationWindow(nextState, ctx);
    }
  });

  ensure(grantId, {
    title: "Grant Capability",
    doc: "Grant a capability after mediation.",
    metadata: { beginner: { advanced: true, hidden: true, confirm: true } },
    enabled: (ctx) => {
      const capability = resolveCapability(ctx);
      if (!capability) {
        return { enabled: false, reason: "No capability specified" };
      }
      const granted = normalizeCapabilities(ctx.state.capabilities ?? null).granted;
      return granted.includes(capability)
        ? { enabled: false, reason: "Capability already granted" }
        : { enabled: true, reason: null };
    },
    exec: (ctx) => {
      const capability = resolveCapability(ctx);
      if (!capability) return ctx.state;
      return grantCapability(ctx.state, capability, {
        reason: ctx.reason ?? ctx.payload?.reason ?? null,
        taskId: ctx.taskId ?? null,
        windowId: ctx.windowId ?? null,
        commandId: grantId
      });
    }
  });

  ensure(revokeId, {
    title: "Revoke Capability",
    doc: "Revoke a previously granted capability.",
    metadata: { beginner: { advanced: true, hidden: true, confirm: true } },
    enabled: (ctx) => {
      const capability = resolveCapability(ctx);
      if (!capability) {
        return { enabled: false, reason: "No capability specified" };
      }
      const granted = normalizeCapabilities(ctx.state.capabilities ?? null).granted;
      return granted.includes(capability)
        ? { enabled: true, reason: null }
        : { enabled: false, reason: "Capability not granted" };
    },
    exec: (ctx) => {
      const capability = resolveCapability(ctx);
      if (!capability) return ctx.state;
      return revokeCapability(ctx.state, capability, {
        reason: ctx.reason ?? ctx.payload?.reason ?? null,
        taskId: ctx.taskId ?? null,
        windowId: ctx.windowId ?? null,
        commandId: revokeId
      });
    }
  });

  ensure(openPanelId, {
    title: "Open Capability Mediation",
    doc: "Open the capability mediation panel.",
    metadata: { beginner: { advanced: true, hidden: true } },
    exec: (ctx) =>
      openCapabilityMediationWindow(ctx.state, {
        taskId: ctx.taskId ?? null,
        selectedRequestId: ctx.payload?.requestId ?? null
      })
  });

  ensure(selectId, {
    doc: "Select a capability request in the mediation panel.",
    metadata: { paletteHidden: true, beginner: { hidden: true } },
    exec: (ctx) =>
      applyCapabilityRequestSelection(ctx.state, {
        taskId: ctx.taskId ?? null,
        windowId: ctx.windowId ?? null,
        requestId: resolveRequestId(ctx),
        itemId: ctx.itemId ?? null,
        item: ctx.item ?? null
      })
  });

  const resolvePendingRequest = (ctx) => {
    const directId = resolveRequestId(ctx);
    if (directId) {
      const requests = normalizeCapabilityRequests(ctx.state.capabilityRequests ?? null);
      return requests.find((request) => request.id === directId) ?? null;
    }
    const selection = resolveCapabilityRequestSelection(ctx.state, {
      taskId: ctx.taskId ?? null,
      windowId: ctx.windowId ?? null
    });
    return selection.request;
  };

  ensure(approveId, {
    title: "Approve Capability Request",
    doc: "Approve the selected capability request.",
    metadata: { beginner: { advanced: true, hidden: true, confirm: true } },
    enabled: (ctx) => {
      const request = resolvePendingRequest(ctx);
      if (!request) {
        return { enabled: false, reason: "No capability request selected" };
      }
      if (request.status !== "pending") {
        return { enabled: false, reason: "Request already decided" };
      }
      return { enabled: true, reason: null };
    },
    exec: (ctx) => {
      const request = resolvePendingRequest(ctx);
      if (!request) return ctx.state;
      let nextState = applyCapabilityDecision(ctx.state, request.id, "grant", {
        reason: ctx.reason ?? ctx.payload?.reason ?? null,
        decidedBy: ctx.decidedBy ?? "user",
        commandId: approveId
      });
      return refreshMediationWindow(nextState, ctx);
    }
  });

  ensure(denyId, {
    title: "Deny Capability Request",
    doc: "Deny the selected capability request.",
    metadata: { beginner: { advanced: true, hidden: true, confirm: true } },
    enabled: (ctx) => {
      const request = resolvePendingRequest(ctx);
      if (!request) {
        return { enabled: false, reason: "No capability request selected" };
      }
      if (request.status !== "pending") {
        return { enabled: false, reason: "Request already decided" };
      }
      return { enabled: true, reason: null };
    },
    exec: (ctx) => {
      const request = resolvePendingRequest(ctx);
      if (!request) return ctx.state;
      let nextState = applyCapabilityDecision(ctx.state, request.id, "deny", {
        reason: ctx.reason ?? ctx.payload?.reason ?? null,
        decidedBy: ctx.decidedBy ?? "user",
        commandId: denyId
      });
      return refreshMediationWindow(nextState, ctx);
    }
  });

  ensure(autoRunId, {
    title: "Auto-run Capability Policy",
    doc: "Apply the current capability policy to all pending requests.",
    metadata: { beginner: { advanced: true, hidden: true } },
    exec: (ctx) => {
      let nextState = autoRunCapabilityPolicy(ctx.state, {
        policy: ctx.payload?.policy ?? null,
        decidedBy: ctx.decidedBy ?? "policy",
        commandId: autoRunId
      });
      return refreshMediationWindow(nextState, ctx);
    }
  });

  ensure(safeModeEnableId, {
    title: "Enable Safe Mode",
    doc: "Disable all capability-granted escapes.",
    metadata: { beginner: { advanced: true, hidden: true } },
    enabled: (ctx) =>
      ctx.state.capabilities?.safeMode ? { enabled: false, reason: "Safe mode already enabled" } : { enabled: true, reason: null },
    exec: (ctx) => {
      const nextState = setSafeMode(ctx.state, true, {
        reason: ctx.reason ?? ctx.payload?.reason ?? null,
        taskId: ctx.taskId ?? null,
        windowId: ctx.windowId ?? null,
        commandId: safeModeEnableId
      });
      return refreshMediationWindow(nextState, ctx);
    }
  });

  ensure(safeModeDisableId, {
    title: "Disable Safe Mode",
    doc: "Re-enable capability-granted escapes.",
    metadata: { beginner: { advanced: true, hidden: true, confirm: true } },
    enabled: (ctx) =>
      ctx.state.capabilities?.safeMode ? { enabled: true, reason: null } : { enabled: false, reason: "Safe mode already disabled" },
    exec: (ctx) => {
      const nextState = setSafeMode(ctx.state, false, {
        reason: ctx.reason ?? ctx.payload?.reason ?? null,
        taskId: ctx.taskId ?? null,
        windowId: ctx.windowId ?? null,
        commandId: safeModeDisableId
      });
      return refreshMediationWindow(nextState, ctx);
    }
  });

  return registry;
}

export function registerDomEscapeCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const escapeId = options.escapeCommandId ?? DOM_ESCAPE_COMMAND;
  const capability = options.capability ?? "dom.escape";

  if (!registry.commands.has(escapeId)) {
    registerCommand(registry, {
      id: escapeId,
      title: "DOM Escape",
      doc: "Execute a capability-gated DOM escape hatch.",
      metadata: { beginner: { advanced: true, hidden: true, confirm: true } },
      capability,
      exec: (ctx) => {
        const detail = ctx.detail ?? ctx.payload?.detail ?? null;
        const target = ctx.target ?? ctx.payload?.target ?? null;
        const kind = ctx.kind ?? ctx.payload?.kind ?? "dom.escape";
        return recordDomEscape(ctx.state, {
          kind,
          target,
          detail,
          capability,
          taskId: ctx.taskId ?? null,
          windowId: ctx.windowId ?? null,
          commandId: escapeId,
          ts: ctx.ts ?? null
        });
      }
    });
  }

  return registry;
}

export function registerCustomizationCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const themePresetId = options.themePresetCommandId ?? CUSTOMIZATION_THEME_PRESET_COMMAND;
  const themeOverridesId = options.themeOverridesCommandId ?? CUSTOMIZATION_THEME_OVERRIDES_COMMAND;
  const themeResetId = options.themeResetCommandId ?? CUSTOMIZATION_THEME_OVERRIDES_RESET_COMMAND;
  const keymapProfileId = options.keymapProfileCommandId ?? CUSTOMIZATION_KEYMAP_PROFILE_COMMAND;
  const beginnerEnableId = options.beginnerEnableCommandId ?? CUSTOMIZATION_BEGINNER_MODE_ENABLE_COMMAND;
  const beginnerDisableId = options.beginnerDisableCommandId ?? CUSTOMIZATION_BEGINNER_MODE_DISABLE_COMMAND;
  const guidanceDismissId = options.guidanceDismissCommandId ?? CUSTOMIZATION_GUIDANCE_DISMISS_COMMAND;
  const profileExportId = options.profileExportCommandId ?? CUSTOMIZATION_PROFILE_EXPORT_COMMAND;
  const profileImportId = options.profileImportCommandId ?? CUSTOMIZATION_PROFILE_IMPORT_COMMAND;

  const ensure = (id, command) => {
    if (!registry.commands.has(id)) {
      registerCommand(registry, { ...command, id });
    }
  };

  ensure(themePresetId, {
    title: "Set Theme Preset",
    doc: "Set the active theme preset and optional mode override.",
    metadata: { beginner: { explanation: "Switch the overall visual theme preset." } },
    enabled: (ctx) => {
      const presetId = ctx.presetId ?? ctx.payload?.presetId ?? null;
      return typeof presetId === "string" && presetId.length > 0
        ? { enabled: true, reason: null }
        : { enabled: false, reason: "No preset id" };
    },
    exec: (ctx) =>
      setThemePreset(ctx.state, ctx.presetId ?? ctx.payload?.presetId ?? null, {
        mode: ctx.mode ?? ctx.payload?.mode ?? null,
        layer: ctx.layer ?? ctx.payload?.layer ?? "session"
      })
  });

  ensure(themeOverridesId, {
    title: "Set Theme Overrides",
    doc: "Apply token-level theme overrides to the selected customization layer.",
    metadata: { beginner: { advanced: true, explanation: "Fine-tune colors, typography, and spacing tokens." } },
    exec: (ctx) =>
      setThemeOverrides(ctx.state, ctx.overrides ?? ctx.payload?.overrides ?? {}, {
        layer: ctx.layer ?? ctx.payload?.layer ?? "session"
      })
  });

  ensure(themeResetId, {
    title: "Reset Theme Overrides",
    doc: "Clear token-level theme overrides for the selected customization layer.",
    metadata: { beginner: { advanced: true, explanation: "Remove custom token overrides and return to preset defaults." } },
    exec: (ctx) =>
      resetThemeOverrides(ctx.state, {
        layer: ctx.layer ?? ctx.payload?.layer ?? "session"
      })
  });

  ensure(keymapProfileId, {
    title: "Assign Keymap Profile",
    doc: "Assign a keymap profile to a pane.",
    metadata: { beginner: { advanced: true, explanation: "Choose how keys behave in editor, REPL, and debugger panes." } },
    enabled: (ctx) => {
      const pane = ctx.pane ?? ctx.payload?.pane ?? null;
      const profileId = ctx.profileId ?? ctx.payload?.profileId ?? null;
      if (!KEYMAP_PANES.includes(pane)) return { enabled: false, reason: "No pane specified" };
      if (typeof profileId !== "string" || profileId.length === 0) return { enabled: false, reason: "No profile id" };
      return { enabled: true, reason: null };
    },
    exec: (ctx) =>
      setPaneKeymapProfile(
        ctx.state,
        ctx.pane ?? ctx.payload?.pane ?? null,
        ctx.profileId ?? ctx.payload?.profileId ?? null,
        { layer: ctx.layer ?? ctx.payload?.layer ?? "session" }
      )
  });

  ensure(beginnerEnableId, {
    title: "Enable Beginner Mode",
    doc: "Reduce advanced command visibility while keeping the same command system.",
    metadata: { beginner: { explanation: "Hide advanced commands while keeping the same underlying system." } },
    enabled: (ctx) =>
      resolveEffectiveBeginnerMode(ctx.state).enabled
        ? { enabled: false, reason: "Beginner mode already enabled" }
        : { enabled: true, reason: null },
    exec: (ctx) => setBeginnerMode(ctx.state, true, { layer: ctx.layer ?? ctx.payload?.layer ?? "session" })
  });

  ensure(beginnerDisableId, {
    title: "Disable Beginner Mode",
    doc: "Expose advanced command surfaces.",
    metadata: { beginner: { explanation: "Show advanced commands and customization controls." } },
    enabled: (ctx) =>
      resolveEffectiveBeginnerMode(ctx.state).enabled
        ? { enabled: true, reason: null }
        : { enabled: false, reason: "Beginner mode already disabled" },
    exec: (ctx) => setBeginnerMode(ctx.state, false, { layer: ctx.layer ?? ctx.payload?.layer ?? "session" })
  });

  ensure(guidanceDismissId, {
    title: "Dismiss Guidance",
    doc: "Dismiss a beginner guidance message for this session.",
    metadata: { paletteHidden: true, beginner: { hidden: true } },
    enabled: (ctx) => {
      const guidanceId = ctx.guidanceId ?? ctx.payload?.guidanceId ?? null;
      return typeof guidanceId === "string" && guidanceId.length > 0
        ? { enabled: true, reason: null }
        : { enabled: false, reason: "No guidance id" };
    },
    exec: (ctx) =>
      dismissGuidance(ctx.state, ctx.guidanceId ?? ctx.payload?.guidanceId ?? null, {
        layer: ctx.layer ?? ctx.payload?.layer ?? "session"
      })
  });

  ensure(profileExportId, {
    title: "Export Customization Profile",
    doc: "Export current customization sections as a portable profile payload.",
    metadata: { beginner: { advanced: true } },
    exec: (ctx) => ({
      state: ctx.state,
      output: {
        kind: "customization.profile.export",
        profile: exportCustomizationProfile(ctx.state.customization ?? null, {
          name: ctx.name ?? ctx.payload?.name ?? null,
          sourceLayer: ctx.sourceLayer ?? ctx.payload?.sourceLayer ?? "effective",
          now: ctx.now ?? null
        })
      }
    })
  });

  ensure(profileImportId, {
    title: "Import Customization Profile",
    doc: "Import and apply a customization profile with schema validation.",
    metadata: { beginner: { advanced: true, confirm: true } },
    enabled: (ctx) => {
      const profile = ctx.profile ?? ctx.payload?.profile ?? null;
      const validation = validateCustomizationProfile(profile);
      return validation.ok
        ? { enabled: true, reason: null }
        : { enabled: false, reason: validation.errors.join("; ") || "Invalid profile" };
    },
    exec: (ctx) => {
      const profile = ctx.profile ?? ctx.payload?.profile ?? null;
      const imported = importCustomizationProfile(ctx.state.customization ?? null, profile, {
        layer: ctx.layer ?? ctx.payload?.layer ?? "user"
      });
      if (!imported.ok) {
        return {
          state: ctx.state,
          output: {
            kind: "customization.profile.import.error",
            errors: imported.errors ?? []
          }
        };
      }
      return {
        state: setCustomization(ctx.state, imported.customization),
        output: {
          kind: "customization.profile.import",
          rollback: imported.rollback
        }
      };
    }
  });

  return registry;
}

export function registerCommandSurfaceCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const paletteOpenId = options.paletteOpenCommandId ?? COMMAND_PALETTE_OPEN_COMMAND;
  const paletteCloseId = options.paletteCloseCommandId ?? COMMAND_PALETTE_CLOSE_COMMAND;
  const keybindingsOpenId = options.keybindingsOpenCommandId ?? KEYBINDINGS_OPEN_COMMAND;
  const keybindingsCloseId = options.keybindingsCloseCommandId ?? KEYBINDINGS_CLOSE_COMMAND;
  const dismissId = options.dismissCommandId ?? COMMAND_SURFACE_DISMISS_COMMAND;
  const filterCommandId = options.filterCommandId ?? COMMAND_PALETTE_FILTER_COMMAND;

  const ensure = (id, command) => {
    if (!registry.commands.has(id)) {
      registerCommand(registry, { ...command, id });
    }
  };

  ensure(paletteOpenId, {
    title: "Command Palette",
    doc: "Open the command palette.",
    metadata: { paletteHidden: true },
    exec: (ctx) =>
      openCommandPaletteWindow(ctx.state, {
        registry,
        taskId: ctx.taskId,
        filter: ctx.filter ?? ctx.inputValue ?? "",
        filterCommandId
      })
  });

  ensure(paletteCloseId, {
    title: "Close Command Palette",
    doc: "Close the command palette.",
    metadata: { paletteHidden: true },
    exec: (ctx) =>
      closeCommandPaletteWindow(ctx.state, {
        taskId: ctx.taskId,
        windowId: ctx.windowId
      })
  });

  ensure(keybindingsOpenId, {
    title: "Keybindings",
    doc: "Open the keybinding viewer.",
    metadata: { paletteHidden: true },
    exec: (ctx) =>
      openKeybindingWindow(ctx.state, {
        registry,
        taskId: ctx.taskId
      })
  });

  ensure(keybindingsCloseId, {
    title: "Close Keybindings",
    doc: "Close the keybinding viewer.",
    metadata: { paletteHidden: true },
    exec: (ctx) =>
      closeKeybindingWindow(ctx.state, {
        taskId: ctx.taskId,
        windowId: ctx.windowId
      })
  });

  ensure(dismissId, {
    title: "Dismiss Command Surface",
    doc: "Close the active command palette or keybinding viewer window.",
    metadata: { paletteHidden: true },
    exec: (ctx) => {
      const taskId = ctx.taskId ?? ctx.state.workspace?.activeTaskId ?? null;
      const palette = findWindowByRole(ctx.state, "command-palette", taskId);
      if (palette) {
        return closeCommandPaletteWindow(ctx.state, { windowId: palette.id, taskId });
      }
      const keybindings = findWindowByRole(ctx.state, "keybindings", taskId);
      if (keybindings) {
        return closeKeybindingWindow(ctx.state, { windowId: keybindings.id, taskId });
      }
      return ctx.state;
    }
  });

  return registry;
}

export function bindCommandPaletteDefaults(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const scope = options.scope ?? "task";
  const taskId = options.taskId ?? null;
  const hasScopeId = scope !== "global";
  if (hasScopeId && !taskId) {
    throw new Error("Task id required for non-global palette bindings");
  }
  const bind = (key, commandId) => {
    bindKey(registry, scope, key, commandId, hasScopeId ? taskId : null);
  };
  bind("ArrowDown", COMMAND_PALETTE_SELECT_NEXT_COMMAND);
  bind("ArrowUp", COMMAND_PALETTE_SELECT_PREV_COMMAND);
  bind("Enter", COMMAND_PALETTE_EXECUTE_SELECTION_COMMAND);
  return registry;
}

export function bindCommandSurfaceDefaults(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const scope = options.scope ?? "global";
  const taskId = options.taskId ?? null;
  const hasScopeId = scope !== "global";
  if (hasScopeId && !taskId) {
    throw new Error("Task id required for non-global surface bindings");
  }
  const paletteOpenId = options.paletteOpenCommandId ?? COMMAND_PALETTE_OPEN_COMMAND;
  const keybindingsOpenId = options.keybindingsOpenCommandId ?? KEYBINDINGS_OPEN_COMMAND;
  const dismissId = options.dismissCommandId ?? COMMAND_SURFACE_DISMISS_COMMAND;
  const paletteKey = options.paletteKey ?? "Ctrl+Shift+P";
  const keybindingsKey = options.keybindingsKey ?? "Ctrl+Shift+K";
  const dismissKey = options.dismissKey ?? "Escape";

  const bind = (key, commandId) => {
    bindKey(registry, scope, key, commandId, hasScopeId ? taskId : null);
  };
  bind(paletteKey, paletteOpenId);
  bind(keybindingsKey, keybindingsOpenId);
  bind(dismissKey, dismissId);
  return registry;
}

export function applyCustomizationKeymapsToRegistry(state, registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const paneContextIds = isPlainObject(options.paneContextIds) ? options.paneContextIds : {};
  const clearExisting = options.clearExisting !== false;
  if (clearExisting) {
    for (const pane of KEYMAP_PANES) {
      const contextId = paneContextIds[pane] ?? `pane:${pane}`;
      if (registry.keymaps?.context?.has(contextId)) {
        registry.keymaps.context.delete(contextId);
      }
    }
  }

  const bindings = buildActiveKeymapBindings(state);
  for (const binding of bindings) {
    const scope = KEYMAP_SCOPE_KINDS.includes(binding.scope) ? binding.scope : "context";
    const resolvedScopeId =
      scope === "global"
        ? null
        : binding.scopeId ??
          (scope === "context" && binding.pane ? paneContextIds[binding.pane] ?? `pane:${binding.pane}` : null);
    if (scope !== "global" && !resolvedScopeId) {
      continue;
    }
    bindKey(registry, scope, binding.key, binding.commandId, resolvedScopeId);
  }
  return registry;
}

export function openKeybindingWindow(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  if (!taskId) {
    throw new Error("Keybinding viewer requires a task");
  }
  const existing = findWindowByRole(state, "keybindings", taskId);
  if (existing) {
    return refreshKeybindingWindow(state, existing.id, options);
  }

  const allocWindow = allocateId(state.idCounters, "window", "keybindings");
  let nextState = {
    ...state,
    idCounters: allocWindow.counters
  };
  nextState = addWindow(nextState, {
    id: allocWindow.id,
    taskId,
    kind: "keybindings",
    title: "Keybindings",
    metadata: { role: "keybindings" }
  });

  let ids = {};
  let rootAlloc = allocateWidgetId(nextState, "keybindings-root");
  nextState = addWidget(rootAlloc.state, {
    id: rootAlloc.id,
    kind: "container",
    windowId: allocWindow.id,
    props: { className: "ui-keybindings-root" }
  });
  ids.rootId = rootAlloc.id;

  let labelAlloc = allocateWidgetId(nextState, "keybindings-label");
  nextState = addWidget(labelAlloc.state, {
    id: labelAlloc.id,
    kind: "label",
    parentId: ids.rootId,
    props: { text: "Keybindings" }
  });
  ids.labelId = labelAlloc.id;

  const items = buildKeybindingItems(options.registry ?? null, { state: nextState });
  let listAlloc = allocateWidgetId(nextState, "keybindings-list");
  nextState = addWidget(listAlloc.state, {
    id: listAlloc.id,
    kind: "list",
    parentId: ids.rootId,
    props: { items }
  });
  ids.listId = listAlloc.id;

  const traceKey = options.traceKey ?? null;
  const traceContext = buildKeybindingTraceContext(options, taskId);
  const traceItems = buildKeybindingTraceItems(options.registry ?? null, {
    key: traceKey,
    context: traceContext
  });

  let traceLabelAlloc = allocateWidgetId(nextState, "keybindings-trace-label");
  const traceLabel = traceKey ? `Keybinding Trace: ${traceKey}` : "Keybinding Trace";
  nextState = addWidget(traceLabelAlloc.state, {
    id: traceLabelAlloc.id,
    kind: "label",
    parentId: ids.rootId,
    props: { text: traceLabel }
  });
  ids.traceLabelId = traceLabelAlloc.id;

  let traceListAlloc = allocateWidgetId(nextState, "keybindings-trace-list");
  nextState = addWidget(traceListAlloc.state, {
    id: traceListAlloc.id,
    kind: "list",
    parentId: ids.rootId,
    props: { items: traceItems }
  });
  ids.traceListId = traceListAlloc.id;

  const conflictItems = buildKeybindingConflictItems(nextState);
  let conflictLabelAlloc = allocateWidgetId(nextState, "keybindings-conflict-label");
  nextState = addWidget(conflictLabelAlloc.state, {
    id: conflictLabelAlloc.id,
    kind: "label",
    parentId: ids.rootId,
    props: { text: "Keymap Conflicts" }
  });
  ids.conflictLabelId = conflictLabelAlloc.id;

  let conflictListAlloc = allocateWidgetId(nextState, "keybindings-conflict-list");
  nextState = addWidget(conflictListAlloc.state, {
    id: conflictListAlloc.id,
    kind: "list",
    parentId: ids.rootId,
    props: { items: conflictItems }
  });
  ids.conflictListId = conflictListAlloc.id;

  nextState = updateWindow(nextState, allocWindow.id, (window) => ({
    ...window,
    metadata: {
      ...(window.metadata ?? {}),
      role: "keybindings",
      widgets: ids,
      trace: { key: traceKey, context: traceContext }
    }
  }));

  return nextState;
}

export function refreshKeybindingWindow(state, windowId, options = {}) {
  const window = state.windows?.[windowId];
  if (!window || window.metadata?.role !== "keybindings") {
    throw new Error("Window is not a keybinding viewer");
  }
  const widgets = window.metadata?.widgets;
  if (!widgets?.listId) {
    return state;
  }
  const items = buildKeybindingItems(options.registry ?? null, { state });
  let nextState = updateWidget(state, widgets.listId, (widget) => ({
    ...widget,
    props: { ...(widget.props ?? {}), items }
  }));

  const existingTrace = window.metadata?.trace ?? {};
  const traceKey = options.traceKey ?? existingTrace.key ?? null;
  const traceContext = buildKeybindingTraceContext(
    { ...options, traceContext: options.traceContext ?? existingTrace.context ?? {} },
    window.taskId
  );
  if (widgets.traceLabelId) {
    const traceLabel = traceKey ? `Keybinding Trace: ${traceKey}` : "Keybinding Trace";
    nextState = updateWidget(nextState, widgets.traceLabelId, (widget) => ({
      ...widget,
      props: { ...(widget.props ?? {}), text: traceLabel }
    }));
  }
  if (widgets.traceListId) {
    const traceItems = buildKeybindingTraceItems(options.registry ?? null, {
      key: traceKey,
      context: traceContext
    });
    nextState = updateWidget(nextState, widgets.traceListId, (widget) => ({
      ...widget,
      props: { ...(widget.props ?? {}), items: traceItems }
    }));
  }
  if (widgets.conflictListId) {
    const conflictItems = buildKeybindingConflictItems(nextState);
    nextState = updateWidget(nextState, widgets.conflictListId, (widget) => ({
      ...widget,
      props: { ...(widget.props ?? {}), items: conflictItems }
    }));
  }

  return updateWindow(nextState, windowId, (nextWindow) => ({
    ...nextWindow,
    metadata: {
      ...(nextWindow.metadata ?? {}),
      trace: { key: traceKey, context: traceContext }
    }
  }));
}

export function closeKeybindingWindow(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  const windowId =
    options.windowId ??
    findWindowByRole(state, "keybindings", taskId)?.id ??
    null;
  if (!windowId) {
    return state;
  }
  const window = state.windows?.[windowId];
  if (!window || window.metadata?.role !== "keybindings") {
    return state;
  }
  return removeWindow(state, windowId, { reason: options.reason ?? "command" });
}

function normalizeRuntimeDebuggerFrames(frames) {
  if (!Array.isArray(frames)) return [];
  return frames.map((frame, index) => {
    const frameId =
      typeof frame?.frameId === "string" && frame.frameId.length > 0
        ? frame.frameId
        : `frame-${index + 1}`;
    const fnName =
      typeof frame?.function === "string" && frame.function.length > 0
        ? frame.function
        : typeof frame?.label === "string" && frame.label.length > 0
          ? frame.label
          : "anonymous";
    const label =
      typeof frame?.label === "string" && frame.label.length > 0
        ? frame.label
        : fnName;
    const location = isPlainObject(frame?.location) ? { ...frame.location } : null;
    const locals = Array.isArray(frame?.locals)
      ? frame.locals.map((local, localIndex) => {
          const bindingId =
            typeof local?.bindingId === "string" && local.bindingId.length > 0
              ? local.bindingId
              : `${frameId}-local-${localIndex + 1}`;
          const name =
            typeof local?.name === "string" && local.name.length > 0 ? local.name : `local-${localIndex + 1}`;
          const valueSummary =
            typeof local?.valueSummary === "string" && local.valueSummary.length > 0
              ? local.valueSummary
              : "";
          return {
            bindingId,
            name,
            valueSummary,
            presentationId:
              typeof local?.presentationId === "string" && local.presentationId.length > 0
                ? local.presentationId
                : null,
            location: isPlainObject(local?.location) ? { ...local.location } : null
          };
        })
      : [];
    return {
      frameId,
      label,
      function: fnName,
      location,
      locals
    };
  });
}

function normalizeRuntimeRestartList(restarts) {
  if (!Array.isArray(restarts)) return [];
  const normalized = [];
  for (const restart of restarts) {
    if (!restart || typeof restart !== "object") continue;
    try {
      normalized.push(normalizeRestart(restart));
    } catch (_err) {
      // Ignore malformed restarts; runtime bridge should degrade safely.
    }
  }
  return normalized;
}

function normalizeRuntimeConditionPayload(payload, errorId, frames) {
  const condition = isPlainObject(payload?.condition) ? payload.condition : {};
  const fallbackStack = frames.map((frame) => ({
    frameId: frame.frameId,
    function: frame.function ?? frame.label ?? "anonymous",
    location: frame.location ?? null
  }));
  const reportInput = {
    ...condition,
    id:
      (typeof condition.id === "string" && condition.id.length > 0 ? condition.id : null) ??
      errorId,
    stack: Array.isArray(condition.stack) ? condition.stack : fallbackStack,
    sections: Array.isArray(condition.sections) ? condition.sections : []
  };
  try {
    return normalizeConditionReport(reportInput);
  } catch (_err) {
    return {
      id: errorId,
      kind: "error",
      message:
        typeof condition.message === "string" && condition.message.length > 0
          ? condition.message
          : typeof payload?.message === "string" && payload.message.length > 0
            ? payload.message
            : "",
      summary:
        typeof condition.summary === "string" && condition.summary.length > 0 ? condition.summary : "",
      sections: [],
      stack: fallbackStack,
      restarts: []
    };
  }
}

function resolveRuntimeTaskId(state, payload = {}, options = {}) {
  if (typeof payload?.taskId === "string" && payload.taskId.length > 0) {
    return payload.taskId;
  }
  if (typeof options?.taskId === "string" && options.taskId.length > 0) {
    return options.taskId;
  }
  return state.workspace?.activeTaskId ?? null;
}

function mergeRuntimeInspectorWatches(state, watches, options = {}) {
  if (!Array.isArray(watches)) return state;
  const ts = Number.isInteger(options.ts) ? options.ts : null;
  const nextWatches = [...(state.watches ?? [])];
  let changed = false;

  const findWatchIndex = (watch) => {
    if (!watch) return -1;
    if (watch.id) {
      const byId = nextWatches.findIndex((entry) => entry.id === watch.id);
      if (byId >= 0) return byId;
    }
    if (watch.entryId) {
      const byEntry = nextWatches.findIndex((entry) => entry.entryId && entry.entryId === watch.entryId);
      if (byEntry >= 0) return byEntry;
    }
    if (watch.presentationId) {
      const byPresentation = nextWatches.findIndex(
        (entry) => entry.presentationId && entry.presentationId === watch.presentationId
      );
      if (byPresentation >= 0) return byPresentation;
    }
    return -1;
  };

  for (let index = 0; index < watches.length; index += 1) {
    const raw = watches[index];
    if (!raw || typeof raw !== "object") continue;
    const normalized = normalizeWatch(
      {
        ...raw,
        updatedAt: Number.isInteger(raw.updatedAt) ? raw.updatedAt : ts
      },
      nextWatches.length + index
    );
    const existingIndex = findWatchIndex(normalized);
    const shouldRemove = raw.pinned === false || normalized.pinned === false;
    if (existingIndex >= 0) {
      if (shouldRemove) {
        nextWatches.splice(existingIndex, 1);
      } else {
        nextWatches[existingIndex] = normalizeWatch(
          {
            ...nextWatches[existingIndex],
            ...normalized,
            pinned: true
          },
          existingIndex
        );
      }
      changed = true;
      continue;
    }
    if (shouldRemove) continue;
    nextWatches.push(normalized);
    changed = true;
  }

  if (!changed) return state;
  return {
    ...state,
    watches: nextWatches,
    watchSeq: normalizeWatchSeq(state.watchSeq ?? null, nextWatches)
  };
}

function upsertRuntimeInspectorEditGroup(state, editGroup, options = {}) {
  if (!editGroup || typeof editGroup !== "object") {
    throw new Error("Runtime inspector edit-group payload requires editGroup object");
  }
  const ts = Number.isInteger(options.ts) ? options.ts : null;
  const groups = Array.isArray(state.editGroups) ? [...state.editGroups] : [];
  const index = groups.findIndex((entry) => entry.id === editGroup.id);
  const current = index >= 0 ? groups[index] : null;
  const status = EDIT_GROUP_STATUSES.includes(editGroup.status) ? editGroup.status : current?.status ?? "staged";
  const merged = normalizeEditGroup(
    {
      ...current,
      ...editGroup,
      status,
      createdAt:
        Number.isInteger(editGroup.createdAt)
          ? editGroup.createdAt
          : current?.createdAt ?? (status === "staged" ? ts : null),
      appliedAt:
        Number.isInteger(editGroup.appliedAt)
          ? editGroup.appliedAt
          : current?.appliedAt ?? (status === "applied" ? ts : null),
      undoneAt:
        Number.isInteger(editGroup.undoneAt)
          ? editGroup.undoneAt
          : current?.undoneAt ?? (status === "undone" ? ts : null),
      failedAt:
        Number.isInteger(editGroup.failedAt)
          ? editGroup.failedAt
          : current?.failedAt ?? (status === "failed" ? ts : null),
      metadata: {
        ...(current?.metadata ?? {}),
        ...(isPlainObject(editGroup.metadata) ? editGroup.metadata : {}),
        ...(editGroup.error ? { error: editGroup.error } : {})
      }
    },
    index >= 0 ? index : groups.length
  );
  if (index >= 0) {
    groups[index] = merged;
  } else {
    groups.push(merged);
  }
  return {
    ...state,
    editGroups: groups,
    editSeq: normalizeEditSeq(state.editSeq ?? null, groups)
  };
}

export function applyRuntimeInspectorUpdate(state, payload = {}, options = {}) {
  if (!payload || typeof payload !== "object") {
    throw new Error("Runtime inspector payload must be an object");
  }
  const ts = Number.isInteger(options.ts) ? options.ts : null;
  const type =
    typeof payload.type === "string" && payload.type.length > 0
      ? payload.type
      : payload.targetId && payload.view
        ? "snapshot"
        : null;
  if (!type) {
    throw new Error("Runtime inspector payload type is required");
  }

  const taskId = resolveRuntimeTaskId(state, payload, options);
  let nextState = state;
  if (type === "snapshot") {
    const targetId =
      (typeof payload.targetId === "string" && payload.targetId.length > 0
        ? payload.targetId
        : typeof payload.presentationId === "string" && payload.presentationId.length > 0
          ? payload.presentationId
          : null);
    if (!targetId) {
      throw new Error("Runtime inspector snapshot requires targetId");
    }
    const current = normalizeRuntimeInspectorState(state.runtimeInspector ?? null);
    nextState = {
      ...nextState,
      runtimeInspector: {
        ...current,
        targetId,
        targetType:
          (typeof payload.targetType === "string" && payload.targetType.length > 0
            ? payload.targetType
            : typeof payload.view?.type === "string" && payload.view.type.length > 0
              ? payload.view.type
              : current.targetType),
        stale: Boolean(payload.stale),
        view: isPlainObject(payload.view) ? { ...payload.view } : current.view,
        lastUpdatedAt: ts ?? current.lastUpdatedAt
      }
    };
    if (Array.isArray(payload.watches)) {
      nextState = mergeRuntimeInspectorWatches(nextState, payload.watches, { ts });
    }
  } else if (type === "watch.sync") {
    if (!Array.isArray(payload.watches)) {
      throw new Error("Runtime inspector watch.sync requires watches array");
    }
    nextState = mergeRuntimeInspectorWatches(nextState, payload.watches, { ts });
    const current = normalizeRuntimeInspectorState(nextState.runtimeInspector ?? null);
    nextState = {
      ...nextState,
      runtimeInspector: {
        ...current,
        lastUpdatedAt: ts ?? current.lastUpdatedAt
      }
    };
  } else if (type === "edit-group") {
    nextState = upsertRuntimeInspectorEditGroup(nextState, payload.editGroup ?? null, { ts });
    const current = normalizeRuntimeInspectorState(nextState.runtimeInspector ?? null);
    nextState = {
      ...nextState,
      runtimeInspector: {
        ...current,
        lastUpdatedAt: ts ?? current.lastUpdatedAt
      }
    };
    if (isPlainObject(payload.audit) && typeof payload.audit.entryText === "string" && payload.audit.entryText.length > 0) {
      nextState = recordEvent(nextState, {
        type: "runtime:inspector.audit",
        ts: ts ?? null,
        payload: {
          text: payload.audit.entryText,
          editGroupId: payload.editGroup?.id ?? null
        }
      });
    }
  } else {
    throw new Error(`Unsupported runtime inspector payload type: ${type}`);
  }
  return refreshInspectorWindowsForTask(nextState, taskId ?? null);
}

export function applyRuntimeJobUpdate(state, payload = {}, options = {}) {
  if (!payload || typeof payload !== "object") {
    throw new Error("Runtime job payload must be an object");
  }
  const ts = Number.isInteger(options.ts) ? options.ts : null;
  const taskId = resolveRuntimeTaskId(state, payload, options);
  const jobId =
    (typeof payload.id === "string" && payload.id.length > 0
      ? payload.id
      : typeof payload.jobId === "string" && payload.jobId.length > 0
        ? payload.jobId
        : typeof options.jobId === "string" && options.jobId.length > 0
          ? options.jobId
          : null);
  if (!jobId) {
    throw new Error("Runtime job payload requires id");
  }

  const job = {
    id: jobId,
    taskId,
    kind: typeof payload.kind === "string" && payload.kind.length > 0 ? payload.kind : null,
    title:
      (typeof payload.title === "string" && payload.title.length > 0
        ? payload.title
        : typeof payload.label === "string" && payload.label.length > 0
          ? payload.label
          : null) ?? `Job ${jobId}`,
    status:
      (typeof payload.status === "string" && payload.status.length > 0 ? payload.status : null) ?? "unknown",
    progress: isPlainObject(payload.progress) ? { ...payload.progress } : null,
    diagnostics: Array.isArray(payload.diagnostics) ? payload.diagnostics : [],
    updatedAt: ts ?? (Number.isInteger(payload.updatedAt) ? payload.updatedAt : null)
  };
  let nextState = upsertJob(state, job);
  if (isPlainObject(payload.audit) && typeof payload.audit.entryText === "string" && payload.audit.entryText.length > 0) {
    nextState = recordEvent(nextState, {
      type: "runtime:job.audit",
      ts: ts ?? null,
      payload: {
        text: payload.audit.entryText,
        jobId
      }
    });
  }
  return refreshInspectorWindowsForTask(nextState, taskId ?? null);
}

function refreshDebuggerWindowsForTask(state, taskId, errorId = null) {
  let nextState = state;
  const windows = Object.values(state.windows ?? {}).filter(
    (window) => window?.metadata?.role === "debugger" && (!taskId || window.taskId === taskId)
  );
  for (const window of windows) {
    const nextErrorId = errorId ?? window.metadata?.errorId ?? null;
    nextState = refreshDebuggerWindow(nextState, window.id, nextErrorId);
  }
  return nextState;
}

export function upsertRuntimeDebuggerSnapshot(state, payload = {}, options = {}) {
  if (!payload || typeof payload !== "object") {
    throw new Error("Runtime debugger snapshot payload must be an object");
  }
  const ts = Number.isInteger(options.ts) ? options.ts : null;
  const frames = normalizeRuntimeDebuggerFrames(payload.frames);
  const errorId =
    (typeof payload.errorId === "string" && payload.errorId.length > 0
      ? payload.errorId
      : typeof payload.condition?.id === "string" && payload.condition.id.length > 0
        ? payload.condition.id
        : null) ?? `runtime-error-${(state.errors ?? []).length + 1}`;
  const existing = (state.errors ?? []).find((entry) => entry.id === errorId) ?? null;
  const taskId =
    (typeof payload.taskId === "string" && payload.taskId.length > 0
      ? payload.taskId
      : typeof options.taskId === "string" && options.taskId.length > 0
        ? options.taskId
        : existing?.taskId ??
          state.workspace?.activeTaskId ??
          null);
  if (!taskId) return state;

  const report = normalizeRuntimeConditionPayload(payload, errorId, frames);
  const restartSource = Array.isArray(payload.restarts) ? payload.restarts : report.restarts;
  const restarts = normalizeRuntimeRestartList(restartSource);
  const location =
    isPlainObject(payload.location) ? payload.location : isPlainObject(report.location) ? report.location : null;
  const debuggerTarget = {
    ...(isPlainObject(existing?.debuggerTarget) ? existing.debuggerTarget : {}),
    ...(typeof payload.selectedFrameId === "string" && payload.selectedFrameId.length > 0
      ? { selectedFrameId: payload.selectedFrameId }
      : {})
  };

  const errors = [...(state.errors ?? [])];
  const index = errors.findIndex((entry) => entry.id === errorId);
  if (index !== -1) {
    const current = errors[index];
    errors[index] = {
      ...current,
      taskId,
      kind: report.kind ?? current.kind ?? "error",
      message: report.message || current.message || "",
      restarts,
      location,
      report,
      stack: frames,
      coalesceKey: current.coalesceKey ?? `runtime:${errorId}`,
      lastTs: ts ?? current.lastTs ?? null,
      status: payload.status ?? current.status ?? "open",
      debuggerTarget
    };
  } else {
    errors.push({
      id: errorId,
      taskId,
      kind: report.kind ?? "error",
      message: report.message ?? "",
      restarts,
      severity: payload.severity ?? null,
      location,
      report,
      stack: frames,
      coalesceKey: `runtime:${errorId}`,
      ts,
      lastTs: ts,
      status: payload.status ?? "open",
      count: 1,
      presentationId:
        typeof payload.presentationId === "string" && payload.presentationId.length > 0
          ? payload.presentationId
          : null,
      debuggerTarget
    });
  }

  let nextState = { ...state, errors };
  const openDebugger = options.openDebugger !== false;
  const existingDebuggerWindow = findWindowByRole(nextState, "debugger", taskId);
  if (openDebugger && !existingDebuggerWindow) {
    nextState = openDebuggerWindow(nextState, { taskId, errorId });
  } else {
    nextState = refreshDebuggerWindowsForTask(nextState, taskId, errorId);
  }
  return nextState;
}

export function applyRuntimeDebuggerRestartUpdate(state, payload = {}, options = {}) {
  if (!payload || typeof payload !== "object") {
    throw new Error("Runtime debugger restart payload must be an object");
  }
  const ts = Number.isInteger(options.ts) ? options.ts : null;
  const type = typeof payload.type === "string" && payload.type.length > 0 ? payload.type : "set";
  const errorId =
    typeof payload.errorId === "string" && payload.errorId.length > 0 ? payload.errorId : null;
  if (!errorId) {
    return state;
  }

  const existing = (state.errors ?? []).find((entry) => entry.id === errorId) ?? null;
  if (!existing) {
    if (type === "set" && Array.isArray(payload.restarts)) {
      return upsertRuntimeDebuggerSnapshot(
        state,
        {
          errorId,
          taskId: payload.taskId ?? options.taskId ?? state.workspace?.activeTaskId ?? null,
          condition: {
            id: errorId,
            kind: "error",
            message: payload.message ?? "",
            summary: payload.summary ?? ""
          },
          restarts: payload.restarts
        },
        { ...options, openDebugger: false, ts }
      );
    }
    return state;
  }

  const errors = [...(state.errors ?? [])];
  const index = errors.findIndex((entry) => entry.id === errorId);
  const current = errors[index];
  if (index === -1) return state;

  let restarts = current.restarts ?? [];
  if (type === "set" && Array.isArray(payload.restarts)) {
    restarts = normalizeRuntimeRestartList(payload.restarts);
  }
  if (type === "invoked" && Array.isArray(payload.restarts)) {
    restarts = normalizeRuntimeRestartList(payload.restarts);
  }

  const debuggerTarget = {
    ...(isPlainObject(current.debuggerTarget) ? current.debuggerTarget : {}),
    ...(typeof payload.restartId === "string" && payload.restartId.length > 0
      ? { lastInvokedRestartId: payload.restartId }
      : {}),
    ...(typeof payload.summary === "string" && payload.summary.length > 0
      ? { lastRestartSummary: payload.summary }
      : {}),
    ...(ts !== null ? { lastRestartTs: ts } : {})
  };

  errors[index] = {
    ...current,
    restarts,
    lastTs: ts ?? current.lastTs ?? null,
    debuggerTarget
  };
  let nextState = { ...state, errors };
  nextState = refreshDebuggerWindowsForTask(nextState, current.taskId ?? null, errorId);
  return nextState;
}

export function raiseError(state, error, options = {}) {
  const taskId = error.taskId ?? state.workspace?.activeTaskId ?? null;
  if (!taskId) {
    throw new Error("Error must reference a task");
  }
  const coalesceKey = error.coalesceKey ?? `${error.kind ?? "error"}:${error.message ?? ""}`;
  const errors = [...(state.errors ?? [])];
  const existingIndex = errors.findIndex(
    (entry) => entry.taskId === taskId && entry.coalesceKey === coalesceKey && entry.status !== "resolved"
  );

  let nextState = state;
  let errorId = null;
  if (existingIndex !== -1) {
    const existing = errors[existingIndex];
    const count = (existing.count ?? 1) + 1;
    errors[existingIndex] = {
      ...existing,
      count,
      lastTs: error.ts ?? existing.lastTs ?? null,
      message: error.message ?? existing.message,
      restarts: error.restarts ?? existing.restarts ?? [],
      severity: error.severity ?? existing.severity ?? null,
      location: error.location ?? existing.location ?? null,
      report: error.report ?? existing.report ?? null,
      stack: error.stack ?? existing.stack ?? null,
      status: error.status ?? existing.status ?? existing.status,
      presentationId: error.presentationId ?? existing.presentationId ?? null,
      debuggerTarget: error.debuggerTarget ?? existing.debuggerTarget ?? null
    };
    nextState = { ...state, errors };
    errorId = existing.id;
  } else {
    const alloc = allocateId(state.idCounters, "error", "error");
    errorId = alloc.id;
    const entry = {
      id: errorId,
      taskId,
      kind: error.kind ?? "error",
      message: error.message ?? "",
      restarts: Array.isArray(error.restarts) ? [...error.restarts] : [],
      severity: error.severity ?? null,
      location: error.location ?? null,
      report: error.report ?? null,
      stack: error.stack ?? null,
      coalesceKey,
      ts: error.ts ?? null,
      lastTs: error.ts ?? null,
      status: error.status ?? "open",
      count: 1,
      presentationId: error.presentationId ?? null,
      debuggerTarget: error.debuggerTarget ?? null
    };
    errors.push(entry);
    nextState = { ...state, idCounters: alloc.counters, errors };
  }

  if (options.openDebugger) {
    return openDebuggerWindow(nextState, { taskId, errorId });
  }
  return nextState;
}

export function acknowledgeError(state, errorId) {
  const errors = [...(state.errors ?? [])];
  const index = errors.findIndex((entry) => entry.id === errorId);
  if (index === -1) return state;
  errors[index] = { ...errors[index], status: "acknowledged" };
  return { ...state, errors };
}

export function upsertJob(state, job) {
  if (!job || !job.id) {
    throw new Error("Job must include an id");
  }
  const jobs = [...(state.jobs ?? [])];
  const index = jobs.findIndex((entry) => entry.id === job.id);
  if (index === -1) {
    jobs.push({ ...job });
  } else {
    jobs[index] = { ...jobs[index], ...job };
  }
  return { ...state, jobs };
}

function buildDebuggerContent(state, errorId) {
  const error = state.errors?.find((entry) => entry.id === errorId) ?? null;
  const restarts = Array.isArray(error?.restarts) ? error.restarts.map(normalizeRestart) : [];
  const reportSummary =
    typeof error?.report?.summary === "string" && error.report.summary.length > 0
      ? error.report.summary
      : null;
  const lastRestartSummary =
    typeof error?.debuggerTarget?.lastRestartSummary === "string" && error.debuggerTarget.lastRestartSummary.length > 0
      ? error.debuggerTarget.lastRestartSummary
      : null;
  const summaryParts = [];
  if (error) {
    summaryParts.push(`${error.kind ?? "error"}: ${error.message ?? ""}`.trim());
    if (reportSummary) summaryParts.push(reportSummary);
    if (lastRestartSummary) summaryParts.push(`last restart: ${lastRestartSummary}`);
  }
  const summary = summaryParts.length > 0 ? summaryParts.join(" | ") : "No error selected";
  const items = restarts.map((restart, index) => {
    const id = restart.id ?? `restart-${index}`;
    const title = restart.title ?? restart.id ?? `Restart ${index + 1}`;
    const metaParts = [];
    if (restart.recommended) metaParts.push("recommended");
    if (restart.safety) metaParts.push(restart.safety);
    if (Array.isArray(restart.argSchema) && restart.argSchema.length > 0) {
      metaParts.push(`args:${restart.argSchema.length}`);
    }
    const metaSuffix = metaParts.length > 0 ? ` (${metaParts.join(", ")})` : "";
    const reasonSuffix =
      typeof restart.recommendedReason === "string" && restart.recommendedReason.length > 0
        ? ` - ${restart.recommendedReason}`
        : "";
    const previewText =
      typeof restart.preview?.text === "string" && restart.preview.text.length > 0
        ? restart.preview.text
        : null;
    const previewSuffix = previewText ? ` [preview: ${previewText}]` : "";
    const safety = restart.safety ?? "safe";
    const classParts = ["ui-debugger-restart", `is-${safety}`];
    if (restart.recommended) classParts.push("is-recommended");
    if (previewText) classParts.push("has-preview");
    if (Array.isArray(restart.argSchema) && restart.argSchema.length > 0) classParts.push("has-args");
    const explanation =
      typeof restart.recommendedReason === "string" && restart.recommendedReason.length > 0
        ? `Why: ${restart.recommendedReason}`
        : typeof restart.description === "string" && restart.description.length > 0
          ? `Why: ${restart.description}`
          : `Why: ${title} can recover from the current condition.`;
    return {
      id,
      label: `${title}${metaSuffix}${reasonSuffix}${previewSuffix}`,
      restartId: restart.id ?? null,
      errorId: error?.id ?? null,
      restart,
      presentationType: "restart",
      recommended: restart.recommended,
      recommendedReason: restart.recommendedReason ?? null,
      safety,
      argSchema: Array.isArray(restart.argSchema) ? restart.argSchema : [],
      preview: restart.preview ?? null,
      description: restart.description ?? null,
      explanation,
      guidanceId: restart.id ? `restart:${restart.id}` : null,
      className: classParts.join(" ")
    };
  });
  if (items.length === 0) {
    items.push({ id: "restart-none", label: "No restarts available", disabled: true, selectable: false });
  }
  return { summary, items };
}

export function openDebuggerWindow(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  if (!taskId) {
    throw new Error("Debugger requires a task");
  }
  const errorId = options.errorId ?? state.errors?.[state.errors.length - 1]?.id ?? null;

  const existing = findWindowByRole(state, "debugger", taskId);
  if (existing) {
    return refreshDebuggerWindow(state, existing.id, errorId);
  }

  const allocWindow = allocateId(state.idCounters, "window", "debugger");
  let nextState = {
    ...state,
    idCounters: allocWindow.counters
  };
  nextState = addWindow(nextState, {
    id: allocWindow.id,
    taskId,
    kind: "debugger",
    title: "Debugger",
    metadata: { role: "debugger" }
  });

  let rootAlloc = allocateWidgetId(nextState, "debugger-root");
  nextState = addWidget(rootAlloc.state, {
    id: rootAlloc.id,
    kind: "container",
    windowId: allocWindow.id,
    props: { className: "ui-debugger-root" }
  });
  const rootId = rootAlloc.id;

  let titleAlloc = allocateWidgetId(nextState, "debugger-title");
  nextState = addWidget(titleAlloc.state, {
    id: titleAlloc.id,
    kind: "label",
    parentId: rootId,
    props: { text: "Debugger", className: "ui-window-title ui-debugger-title" }
  });

  let summaryAlloc = allocateWidgetId(nextState, "debugger-summary");
  const summary = buildDebuggerContent(nextState, errorId).summary;
  nextState = addWidget(summaryAlloc.state, {
    id: summaryAlloc.id,
    kind: "label",
    parentId: rootId,
    props: { text: summary, className: "ui-debugger-summary" }
  });

  let listAlloc = allocateWidgetId(nextState, "debugger-restarts");
  const items = buildDebuggerContent(nextState, errorId).items;
  nextState = addWidget(listAlloc.state, {
    id: listAlloc.id,
    kind: "list",
    parentId: rootId,
    props: {
      className: "ui-debugger-restarts",
      items,
      itemCommand: DEBUGGER_RESTART_INVOKE_COMMAND,
      selectionCommand: LIST_SELECTION_UPDATE_COMMAND,
      selectionMode: "multi",
      selectionActionBar: true,
      selectionActionCommands: {
        "invoke-restart": DEBUGGER_RESTART_INVOKE_COMMAND
      }
    }
  });

  nextState = updateWindow(nextState, allocWindow.id, (window) => ({
    ...window,
    metadata: {
      ...(window.metadata ?? {}),
      role: "debugger",
      widgets: { rootId, summaryId: summaryAlloc.id, restartsId: listAlloc.id },
      errorId
    }
  }));

  return nextState;
}

export function refreshDebuggerWindow(state, windowId, errorId = null) {
  const window = state.windows?.[windowId];
  if (!window || window.metadata?.role !== "debugger") {
    throw new Error("Window is not a debugger");
  }
  const widgets = window.metadata?.widgets ?? {};
  const activeErrorId = errorId ?? window.metadata?.errorId ?? null;
  if (!widgets.summaryId || !widgets.restartsId) {
    return state;
  }
  const { summary, items } = buildDebuggerContent(state, activeErrorId);
  let nextState = updateWidget(state, widgets.summaryId, (widget) => ({
    ...widget,
    props: { ...(widget.props ?? {}), text: summary }
  }));
  nextState = updateWidget(nextState, widgets.restartsId, (widget) => ({
    ...widget,
    props: { ...(widget.props ?? {}), items }
  }));
  nextState = updateWindow(nextState, windowId, (win) => ({
    ...win,
    metadata: { ...(win.metadata ?? {}), errorId: activeErrorId }
  }));
  return nextState;
}
