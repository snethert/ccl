import { commandEnabled, executeCommand } from "./commands.mjs";
import { handleCommandResultEffects } from "./command-effects.mjs";
import { makeContext } from "./context.mjs";
import { createElement, createText } from "./vdom.mjs";
import { buildSelectionActions } from "./selection-actions.mjs";
import { buildScene, hitTestScene } from "../backends/canvas/scene.mjs";
import { createCanvasBackend } from "../backends/canvas/renderer.mjs";
import { createWebGLBackend } from "../backends/webgl/renderer.mjs";

const COMMAND_HISTORY_APPEND_COMMAND = "ui.command-history.append";

function mergeClassNames(...values) {
  return values.filter((value) => value && String(value).trim().length > 0).join(" ");
}

function toKebabCase(key) {
  return key.replace(/[A-Z]/g, (match) => `-${match.toLowerCase()}`);
}

function styleObjectToString(style) {
  return Object.entries(style)
    .map(([key, value]) => `${toKebabCase(key)}: ${value};`)
    .join(" ");
}

function mergeStyle(base, additions) {
  if (!additions || Object.keys(additions).length === 0) {
    return base ?? null;
  }
  if (!base) return additions;
  if (typeof base === "string") {
    const suffix = styleObjectToString(additions);
    return `${base}${base.trim().endsWith(";") ? "" : ";"} ${suffix}`;
  }
  if (typeof base === "object") {
    return { ...base, ...additions };
  }
  return additions;
}

function coerceNumber(value, fallback = null) {
  const num = Number(value);
  if (!Number.isFinite(num)) return fallback;
  return num;
}

function resolveVirtualConfig(widget) {
  const virtual = widget.props?.virtual ?? widget.model?.virtual ?? false;
  if (!virtual) return null;
  const rowHeight = coerceNumber(widget.props?.rowHeight ?? widget.model?.rowHeight, null);
  const viewportHeight = coerceNumber(widget.props?.viewportHeight ?? widget.model?.viewportHeight, null);
  if (!rowHeight || !viewportHeight) return null;
  const overscan = coerceNumber(widget.props?.overscan ?? widget.model?.overscan ?? 4, 4);
  const scrollTop = coerceNumber(widget.props?.scrollTop ?? widget.model?.scrollTop ?? 0, 0);
  return {
    rowHeight,
    viewportHeight,
    overscan: Math.max(0, overscan),
    scrollTop: Math.max(0, scrollTop)
  };
}

function resolveDirtyOptions(widget) {
  const props = widget.props ?? {};
  const model = widget.model ?? {};
  const dirty = props.dirty ?? model.dirty ?? null;
  const dirtyRects = props.dirtyRects ?? model.dirtyRects ?? null;
  const dirtyIds = props.dirtyIds ?? model.dirtyIds ?? null;
  const dirtyNodes = props.dirtyNodes ?? model.dirtyNodes ?? null;
  const options = {};
  if (Array.isArray(dirty) && dirty.length > 0) {
    options.dirty = dirty;
  }
  if (Array.isArray(dirtyRects) && dirtyRects.length > 0) {
    options.dirtyRects = dirtyRects;
  }
  if (Array.isArray(dirtyIds) && dirtyIds.length > 0) {
    options.dirtyIds = dirtyIds;
  }
  if (Array.isArray(dirtyNodes) && dirtyNodes.length > 0) {
    options.dirtyNodes = dirtyNodes;
  }
  return Object.keys(options).length > 0 ? options : null;
}

function computeVirtualRange(count, config) {
  const start = Math.max(0, Math.floor(config.scrollTop / config.rowHeight) - config.overscan);
  const end = Math.min(
    count,
    Math.ceil((config.scrollTop + config.viewportHeight) / config.rowHeight) + config.overscan
  );
  const totalHeight = count * config.rowHeight;
  return { start, end, totalHeight };
}

function pickProps(props, allowedKeys = []) {
  if (!props) return {};
  const out = {};
  for (const [key, value] of Object.entries(props)) {
    if (value === undefined) continue;
    if (allowedKeys.includes(key)) {
      out[key] = value;
      continue;
    }
    if (key.startsWith("data-") || key.startsWith("aria-")) {
      out[key] = value;
    }
  }
  return out;
}

function widgetBaseProps(widget, baseClass) {
  const props = {
    "data-widget-id": widget.id,
    "data-widget-kind": widget.kind,
    className: baseClass
  };
  const presentationId = widget.props?.presentationId ?? widget.model?.presentationId ?? null;
  if (presentationId) {
    props["data-presentation-id"] = presentationId;
  }
  return props;
}

function resolveAccessibilityProps(widget, defaults = {}) {
  const config = widget.props?.accessibility ?? widget.model?.accessibility ?? null;
  const enabled = Boolean(config?.enabled);
  if (!enabled) {
    return {
      role: "presentation",
      "aria-hidden": "true",
      "data-accessible": "false"
    };
  }
  const label = config?.label ?? defaults.label ?? null;
  const role = config?.role ?? "img";
  const tabIndex = Number.isInteger(config?.tabIndex) ? config.tabIndex : 0;
  const props = {
    role,
    tabIndex,
    "data-accessible": "true"
  };
  if (label) {
    props["aria-label"] = String(label);
  }
  return props;
}

function resolveWindowId(state, widget, fallbackWindowId = null) {
  if (widget.windowId) return widget.windowId;
  let current = widget;
  while (current && current.parentId) {
    current = state.widgets?.[current.parentId];
    if (current?.windowId) {
      return current.windowId;
    }
  }
  return fallbackWindowId ?? null;
}

function resolveTaskId(state, windowId, fallbackTaskId = null) {
  if (windowId && state.windows?.[windowId]) {
    return state.windows[windowId].taskId ?? fallbackTaskId;
  }
  return fallbackTaskId ?? null;
}

function resolveCommandId(widget) {
  return widget.props?.command ?? widget.props?.commandId ?? widget.model?.command ?? null;
}

function buildContext(state, widget, options, windowId, taskId) {
  const runtimeContext =
    typeof options?.runtimeContextResolver === "function"
      ? options.runtimeContextResolver({ state, widget, windowId, taskId })
      : options?.runtimeContext ?? null;
  return {
    ...makeContext(state, {
      taskId,
      windowId,
      widgetId: widget.id,
      contextId: widget.props?.contextId ?? null,
      selection: state.selection ?? null
    }),
    runtimeCommandClient: options?.runtimeCommandClient ?? null,
    runtimeContext
  };
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

function resolveResultState(result, fallback = null) {
  const value = result?.result ?? null;
  if (isStateLike(value)) return value;
  if (value && typeof value === "object" && isStateLike(value.state)) return value.state;
  return fallback;
}

function withResultState(result, state) {
  if (!isStateLike(state)) return result;
  const value = result?.result ?? null;
  if (isStateLike(value)) {
    return { ...result, result: state };
  }
  if (value && typeof value === "object" && isStateLike(value.state)) {
    return { ...result, result: { ...value, state } };
  }
  return { ...result, result: state };
}

function withInvocationId(invocation, state) {
  if (!invocation || typeof invocation !== "object") return invocation;
  if (typeof invocation.id === "string" && invocation.id.length > 0) return invocation;
  const nextIndex = Array.isArray(state?.commandHistory) ? state.commandHistory.length + 1 : 1;
  return {
    ...invocation,
    id: `inv-${nextIndex}`
  };
}

function maybeAppendCommandHistory(options, commandId, commandCtx, result) {
  const registry = options?.registry ?? null;
  if (!registry || !registry.commands?.has(COMMAND_HISTORY_APPEND_COMMAND)) return result;
  if (commandId === COMMAND_HISTORY_APPEND_COMMAND) return result;
  if (!result?.ok || !result?.invocation) return result;
  const state = resolveResultState(result, commandCtx?.state ?? null);
  if (!isStateLike(state)) return result;
  const invocation = withInvocationId(result.invocation, state);
  const historyResult = executeCommand(registry, COMMAND_HISTORY_APPEND_COMMAND, {
    ...commandCtx,
    state,
    invocation
  });
  if (!historyResult?.ok) return result;
  const nextState = resolveResultState(historyResult, state);
  return withResultState(result, nextState);
}

function notifyCommandResult(options, payload) {
  const result = maybeAppendCommandHistory(
    options,
    payload.commandId ?? null,
    payload.ctx ?? null,
    payload.result ?? null
  );
  const nextPayload = { ...payload, result };
  const handlers = options?.commandEffectHandlers ?? null;
  if (handlers) {
    handleCommandResultEffects(nextPayload.result, handlers, {
      commandId: nextPayload.commandId ?? null,
      ctx: nextPayload.ctx ?? null,
      event: nextPayload.event ?? null
    });
  }
  if (options?.onCommandResult) {
    options.onCommandResult(nextPayload);
  }
}

function applyCommandProps(
  props,
  widget,
  options,
  ctx,
  handlerName = "onClick",
  buildCtx = null,
  commandIdOverride = null
) {
  const commandId = commandIdOverride ?? resolveCommandId(widget);
  if (!commandId) {
    return { props, commandId: null, enabled: true };
  }
  const registry = options?.registry ?? null;
  if (!registry) {
    return {
      props: { ...props, "data-command-id": commandId, disabled: true, "data-disabled-reason": "No registry" },
      commandId,
      enabled: false
    };
  }
  const enablement = commandEnabled(registry, commandId, ctx);
  const disabled = Boolean(props.disabled) || !enablement.enabled;
  const nextProps = { ...props, "data-command-id": commandId };
  if (disabled) {
    nextProps.disabled = true;
    if (enablement.reason) {
      nextProps["data-disabled-reason"] = enablement.reason;
    }
  }
  nextProps[handlerName] = (event) => {
    const commandCtx = buildCtx ? buildCtx(ctx, event) : ctx;
    const result = executeCommand(registry, commandId, commandCtx);
    notifyCommandResult(options, { commandId, ctx: commandCtx, result, event });
  };
  return { props: nextProps, commandId, enabled: enablement.enabled };
}

function resolveItemCommandId(item, widget) {
  if (item && typeof item === "object" && !Array.isArray(item)) {
    return (
      item.command ??
      item.commandId ??
      widget.props?.itemCommand ??
      widget.props?.command ??
      widget.model?.itemCommand ??
      widget.model?.command ??
      null
    );
  }
  return widget.props?.itemCommand ?? widget.props?.command ?? widget.model?.itemCommand ?? widget.model?.command ?? null;
}

function normalizeListItems(items) {
  if (!Array.isArray(items)) return [];
  return items.map((item, index) => {
    if (item && typeof item === "object" && !Array.isArray(item)) {
      const id = item.id ?? item.key ?? index;
      const label = item.label ?? item.text ?? item.value ?? id;
      return {
        raw: item,
        id: String(id),
        key: String(id),
        label: String(label ?? ""),
        className: item.className ?? null,
        disabled: Boolean(item.disabled),
        selectable: item.selectable !== false,
        selected: Boolean(item.selected),
        commandId: item.command ?? item.commandId ?? null
      };
    }
    return {
      raw: item,
      id: String(item ?? index),
      key: String(item ?? index),
      label: String(item ?? ""),
      className: null,
      disabled: false,
      selectable: true,
      selected: false,
      commandId: null
    };
  });
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function resolveListSelectionConfig(widget) {
  const props = widget.props ?? {};
  const model = widget.model ?? {};
  const nested = isPlainObject(props.selection)
    ? props.selection
    : isPlainObject(model.selection)
      ? model.selection
      : {};
  const commandId = props.selectionCommand ?? nested.command ?? model.selectionCommand ?? null;
  const mode = props.selectionMode ?? nested.mode ?? model.selectionMode ?? "single";
  const multiple = mode === "multi" || mode === "multiple";
  const actionBar = Boolean(props.selectionActionBar ?? nested.actionBar ?? model.selectionActionBar ?? false);
  const actionCommand = props.selectionActionCommand ?? nested.actionCommand ?? model.selectionActionCommand ?? null;
  const actionCommands =
    (isPlainObject(props.selectionActionCommands) ? props.selectionActionCommands : null) ??
    (isPlainObject(nested.actionCommands) ? nested.actionCommands : null) ??
    (isPlainObject(model.selectionActionCommands) ? model.selectionActionCommands : null) ??
    {};
  return {
    commandId: commandId ? String(commandId) : null,
    multiple,
    actionBar,
    actionCommand: actionCommand ? String(actionCommand) : null,
    actionCommands
  };
}

function resolveListSelection(state, listId) {
  const selection = state.selection ?? null;
  if (!selection || !Array.isArray(selection.targetIds)) return null;
  const scopedListId = selection.metadata?.listId ?? null;
  if (scopedListId && scopedListId !== listId) return null;
  return {
    ...selection,
    targetIds: selection.targetIds.map((id) => String(id)),
    anchorId: selection.anchorId ? String(selection.anchorId) : null
  };
}

function resolveListSelectionActionData(state, items, selection) {
  if (!selection || selection.targetIds.length === 0) {
    return { selectedItems: [], actions: [] };
  }
  const selectedSet = new Set(selection.targetIds);
  const selectedItems = items.filter((item) => selectedSet.has(item.id));
  const presentationMap = {};
  for (const item of selectedItems) {
    const raw = item.raw;
    const presentationId = raw?.presentationId ?? null;
    if (presentationId && state.presentations?.[presentationId]) {
      presentationMap[item.id] = state.presentations[presentationId];
      continue;
    }
    const presentationType = raw?.presentationType ?? raw?.type ?? null;
    if (presentationType) {
      presentationMap[item.id] = { id: item.id, type: presentationType };
    }
  }
  const actions = buildSelectionActions(
    {
      id: selection.id ?? selection.targetIds[0] ?? null,
      targetIds: selection.targetIds
    },
    presentationMap
  );
  return { selectedItems, actions };
}

function normalizeSelectionActions(actions) {
  if (!Array.isArray(actions)) return [];
  const normalized = [];
  for (const action of actions) {
    if (typeof action === "string" && action.length > 0) {
      normalized.push({ id: action, label: action });
      continue;
    }
    if (!action || typeof action !== "object") continue;
    const id = typeof action.id === "string" && action.id.length > 0 ? action.id : null;
    if (!id) continue;
    const label = typeof action.label === "string" && action.label.length > 0 ? action.label : id;
    normalized.push({ id, label });
  }
  return normalized;
}

function normalizeTreeItems(items) {
  if (!Array.isArray(items)) return [];
  return items.map((item, index) => {
    if (item && typeof item === "object" && !Array.isArray(item)) {
      const id = item.id ?? item.key ?? index;
      return {
        raw: item,
        id: String(id),
        label: String(item.label ?? item.text ?? item.value ?? id ?? ""),
        expanded: Boolean(item.expanded),
        selected: Boolean(item.selected),
        disabled: Boolean(item.disabled),
        className: item.className ?? null,
        commandId: item.command ?? item.commandId ?? null,
        children: normalizeTreeItems(item.children ?? [])
      };
    }
    const id = item ?? index;
    return {
      raw: item,
      id: String(id),
      label: String(item ?? ""),
      expanded: false,
      selected: false,
      disabled: false,
      className: null,
      commandId: null,
      children: []
    };
  });
}

function flattenTreeItems(items, depth = 0, out = []) {
  for (const item of items) {
    out.push({ item, depth });
    if (item.expanded && item.children && item.children.length > 0) {
      flattenTreeItems(item.children, depth + 1, out);
    }
  }
  return out;
}

function normalizeTableColumns(columns) {
  if (!Array.isArray(columns)) return [];
  return columns.map((column, index) => {
    if (column && typeof column === "object" && !Array.isArray(column)) {
      const id = column.id ?? column.key ?? index;
      return {
        id: String(id),
        index,
        label: String(column.label ?? column.title ?? id ?? ""),
        width: column.width ?? null,
        className: column.className ?? null
      };
    }
    return {
      id: String(column ?? index),
      index,
      label: String(column ?? ""),
      width: null,
      className: null
    };
  });
}

function normalizeTableRows(rows) {
  if (!Array.isArray(rows)) return [];
  return rows.map((row, index) => {
    if (row && typeof row === "object" && !Array.isArray(row)) {
      const id = row.id ?? row.key ?? index;
      return {
        raw: row,
        id: String(id),
        cells: row.cells ?? row.values ?? row.data ?? {},
        className: row.className ?? null,
        disabled: Boolean(row.disabled),
        selected: Boolean(row.selected),
        commandId: row.command ?? row.commandId ?? null
      };
    }
    return {
      raw: row,
      id: String(row ?? index),
      cells: {},
      className: null,
      disabled: false,
      selected: false,
      commandId: null
    };
  });
}

function renderContainer(state, widget, options = {}) {
  const props = pickProps(widget.props, ["id", "className", "style", "title", "role", "width", "height"]);
  const mergedClass = mergeClassNames("ui-widget ui-container", props.className);
  const base = widgetBaseProps(widget, mergedClass);
  const children = widget.childIds.map((childId) => renderWidget(state, childId, options));
  return createElement("div", { ...props, ...base }, children, widget.id);
}

function renderLabel(widget) {
  const props = pickProps(widget.props, ["id", "className", "style", "title"]);
  const mergedClass = mergeClassNames("ui-widget ui-label", props.className);
  const base = widgetBaseProps(widget, mergedClass);
  const text = widget.props?.text ?? widget.model?.text ?? "";
  return createElement("span", { ...props, ...base }, [createText(String(text))], widget.id);
}

function renderButton(state, widget, options = {}) {
  const props = pickProps(widget.props, ["id", "className", "style", "title", "disabled", "type"]);
  const mergedClass = mergeClassNames("ui-widget ui-button", props.className);
  const base = widgetBaseProps(widget, mergedClass);
  const label = widget.props?.label ?? widget.props?.text ?? widget.model?.text ?? "";
  const type = props.type ?? "button";
  const windowId = resolveWindowId(state, widget, options.windowId ?? null);
  const taskId = resolveTaskId(state, windowId, options.taskId ?? null);
  const ctx = buildContext(state, widget, options, windowId, taskId);
  const command = applyCommandProps({ ...props, ...base, type }, widget, options, ctx);
  return createElement("button", command.props, [createText(String(label))], widget.id);
}

function renderList(state, widget, options = {}) {
  const props = pickProps(widget.props, ["id", "className", "style", "title", "role"]);
  const mergedClass = mergeClassNames("ui-widget ui-list", props.className);
  const base = widgetBaseProps(widget, mergedClass);
  const items = normalizeListItems(widget.props?.items ?? widget.model?.items ?? []);
  const virtualConfig = resolveVirtualConfig(widget);
  const windowId = resolveWindowId(state, widget, options.windowId ?? null);
  const taskId = resolveTaskId(state, windowId, options.taskId ?? null);
  const ctx = buildContext(state, widget, options, windowId, taskId);
  const registry = options?.registry ?? null;
  const listItemIds = items.filter((item) => item.selectable !== false).map((item) => item.id);
  const selectionConfig = resolveListSelectionConfig(widget);
  const selection = resolveListSelection(state, widget.id);
  const selectedSet = new Set(selection?.targetIds ?? []);
  const actionData = selectionConfig.actionBar
    ? resolveListSelectionActionData(state, items, selection)
    : { selectedItems: [], actions: [] };
  const selectedItems = actionData.selectedItems;
  const builtActions = actionData.actions;
  const customActions = normalizeSelectionActions(
    widget.props?.selectionActions ?? widget.model?.selectionActions ?? []
  );
  const actionMap = new Map();
  for (const action of builtActions) {
    if (!actionMap.has(action.id)) {
      actionMap.set(action.id, action);
    }
  }
  for (const action of customActions) {
    if (!actionMap.has(action.id)) {
      actionMap.set(action.id, action);
    }
  }
  const actions = [...actionMap.values()];

  function resolveSelectionMode(event) {
    if (!selectionConfig.multiple) {
      return "replace";
    }
    if (event?.shiftKey) {
      return "range";
    }
    if (event?.metaKey || event?.ctrlKey) {
      return "toggle";
    }
    return "replace";
  }

  function dispatchCommand(commandId, commandCtx, event) {
    if (!commandId || !registry) return { ok: false, reason: "No command" };
    const enablement = commandEnabled(registry, commandId, commandCtx);
    if (!enablement.enabled) {
      return { ok: false, reason: enablement.reason ?? "Disabled" };
    }
    const result = executeCommand(registry, commandId, commandCtx);
    notifyCommandResult(options, { commandId, ctx: commandCtx, result, event });
    return result;
  }

  const renderRow = (item, index, kind = "li", extraProps = {}) => {
    const itemId = item.id;
    const itemKey = item.key;
    const rowClass = mergeClassNames(
      "ui-list-item",
      item.className,
      item.selected || selectedSet.has(itemId) ? "is-selected" : null
    );
    const rowProps = {
      className: rowClass,
      "data-list-id": widget.id,
      ...extraProps
    };

    const buttonProps = {
      type: "button",
      className: "ui-list-button",
      "data-item-id": itemId,
      "data-item-index": index,
      "data-list-id": widget.id
    };
    const itemCommandId = item.commandId ?? resolveItemCommandId(item.raw, widget);
    const selectionCommandId = selectionConfig.commandId;
    const selectionCtx = {
      ...ctx,
      registry: options?.registry ?? ctx.registry ?? null,
      listId: widget.id,
      item: item.raw,
      itemId,
      itemIndex: index,
      listItemIds,
      multiple: selectionConfig.multiple,
      selectionMode: "replace"
    };

    const selectionEnablement =
      selectionCommandId && registry && item.selectable !== false
        ? commandEnabled(registry, selectionCommandId, selectionCtx)
        : { enabled: false, reason: null };
    const itemEnablement =
      itemCommandId && registry ? commandEnabled(registry, itemCommandId, selectionCtx) : { enabled: false, reason: null };
    const hasAnyCommand = Boolean(selectionCommandId || itemCommandId);
    const canSelect = Boolean(selectionCommandId) && selectionEnablement.enabled;
    const canActivate = Boolean(itemCommandId) && itemEnablement.enabled;
    if (itemCommandId) {
      buttonProps["data-command-id"] = itemCommandId;
    } else if (selectionCommandId) {
      buttonProps["data-command-id"] = selectionCommandId;
    }
    if (selectionCommandId) {
      buttonProps["data-selection-command-id"] = selectionCommandId;
    }

    if (item.disabled || (!registry && hasAnyCommand) || (hasAnyCommand && !canSelect && !canActivate)) {
      buttonProps.disabled = true;
      buttonProps["data-disabled-reason"] =
        itemEnablement.reason ??
        selectionEnablement.reason ??
        (registry ? "Disabled" : "No registry");
    }

    buttonProps.onClick = (event) => {
      if (!registry) return;
      const selectionMode = resolveSelectionMode(event);
      const commandCtx = {
        ...selectionCtx,
        selectionMode,
        eventType: event?.type ?? null
      };
      if (selectionCommandId && selectionEnablement.enabled) {
        dispatchCommand(selectionCommandId, commandCtx, event);
      }
      const modifierSelect = selectionMode !== "replace";
      if (itemCommandId && itemEnablement.enabled && !modifierSelect) {
        dispatchCommand(itemCommandId, commandCtx, event);
      }
    };

    const button = createElement("button", buttonProps, [createText(item.label)], `${itemKey}-button`);
    return createElement(kind, rowProps, [button], itemKey);
  };

  let listNode = null;
  if (!virtualConfig) {
    const children = items.map((item, index) => renderRow(item, index));
    listNode = createElement("ul", { ...props, ...base }, children, selectionConfig.actionBar ? `${widget.id}-list` : widget.id);
  } else {
    const range = computeVirtualRange(items.length, virtualConfig);
    const visible = [];
    for (let index = range.start; index < range.end; index += 1) {
      const item = items[index];
      if (!item) continue;
      const rowStyle = {
        position: "absolute",
        top: `${index * virtualConfig.rowHeight}px`,
        height: `${virtualConfig.rowHeight}px`,
        left: 0,
        right: 0
      };
      visible.push(renderRow(item, index, "div", { style: rowStyle, "data-virtual-index": index }));
    }
    const viewportStyle = mergeStyle(props.style, {
      position: "relative",
      overflowY: "auto",
      height: `${virtualConfig.viewportHeight}px`
    });
    const virtualProps = {
      ...props,
      ...base,
      className: mergeClassNames("ui-widget ui-list ui-virtual-list", props.className),
      style: viewportStyle,
      "data-virtual-start": range.start,
      "data-virtual-end": range.end,
      "data-virtual-total": items.length
    };
    const spacer = createElement(
      "div",
      { className: "ui-virtual-spacer", style: { position: "relative", height: `${range.totalHeight}px` } },
      visible,
      `${widget.id}-spacer`
    );
    listNode = createElement("div", virtualProps, [spacer], selectionConfig.actionBar ? `${widget.id}-list` : widget.id);
  }

  if (!selectionConfig.actionBar || !selection || actions.length === 0) {
    return listNode;
  }

  const selectedRawItems = selectedItems.map((entry) => entry.raw);
  const firstSelected = selectedItems[0] ?? null;
  const actionButtons = actions.map((action, index) => {
    const commandId = selectionConfig.actionCommands?.[action.id] ?? selectionConfig.actionCommand ?? null;
    const buttonProps = {
      type: "button",
      className: "ui-list-action-button",
      "data-action-id": action.id,
      "data-list-id": widget.id
    };
    if (!commandId) {
      buttonProps.disabled = true;
    }
    const command = commandId
      ? applyCommandProps(
          buttonProps,
          widget,
          options,
          ctx,
          "onClick",
          (baseCtx, event) => ({
            ...baseCtx,
            registry: options?.registry ?? baseCtx.registry ?? null,
            listId: widget.id,
            actionId: action.id,
            action,
            selectedItemIds: selection.targetIds,
            selectedItems: selectedRawItems,
            item: firstSelected?.raw ?? null,
            itemId: firstSelected?.id ?? null,
            itemIndex: firstSelected ? listItemIds.indexOf(firstSelected.id) : -1,
            eventType: event?.type ?? null
          }),
          commandId
        )
      : { props: buttonProps };
    return createElement(
      "button",
      command.props,
      [createText(String(action.label ?? action.id))],
      `${widget.id}-action-${action.id}-${index}`
    );
  });
  const actionBar = createElement(
    "div",
    {
      className: "ui-list-actions",
      "data-list-id": widget.id,
      "data-selection-size": selection.targetIds.length
    },
    actionButtons,
    `${widget.id}-actions`
  );
  return createElement("div", { className: "ui-list-shell" }, [actionBar, listNode], widget.id);
}

function renderTree(state, widget, options = {}) {
  const props = pickProps(widget.props, ["id", "className", "style", "title", "role"]);
  const mergedClass = mergeClassNames("ui-widget ui-tree", props.className);
  const base = widgetBaseProps(widget, mergedClass);
  const items = normalizeTreeItems(widget.props?.items ?? widget.model?.items ?? []);
  const flat = flattenTreeItems(items);
  const virtualConfig = resolveVirtualConfig(widget);
  const indent = coerceNumber(widget.props?.indent ?? widget.model?.indent ?? 16, 16);
  const windowId = resolveWindowId(state, widget, options.windowId ?? null);
  const taskId = resolveTaskId(state, windowId, options.taskId ?? null);
  const ctx = buildContext(state, widget, options, windowId, taskId);

  const renderRow = (entry, index, kind = "div", extraProps = {}) => {
    const item = entry.item;
    const rowClass = mergeClassNames("ui-tree-row", item.className, item.selected ? "is-selected" : null);
    const paddingLeft = `${entry.depth * indent}px`;
    const rowProps = {
      className: rowClass,
      "data-tree-id": widget.id,
      "data-item-id": item.id,
      "data-item-index": index,
      ...extraProps,
      style: mergeStyle(extraProps.style, { paddingLeft })
    };

    const buttonProps = {
      type: "button",
      className: "ui-tree-button",
      "data-item-id": item.id,
      "data-item-index": index,
      "data-tree-id": widget.id
    };
    if (item.disabled) {
      buttonProps.disabled = true;
    }
    const commandId = item.commandId ?? resolveItemCommandId(item.raw, widget);
    const command = applyCommandProps(
      buttonProps,
      widget,
      options,
      ctx,
      "onClick",
      (baseCtx, event) => ({
        ...baseCtx,
        treeId: widget.id,
        item: item.raw,
        itemId: item.id,
        itemIndex: index,
        depth: entry.depth,
        eventType: event?.type ?? null
      }),
      commandId
    );

    const button = createElement("button", command.props, [createText(item.label)], `${item.id}-button`);
    return createElement(kind, rowProps, [button], item.id);
  };

  if (!virtualConfig) {
    const children = flat.map((entry, index) => renderRow(entry, index));
    return createElement("div", { ...props, ...base }, children, widget.id);
  }

  const range = computeVirtualRange(flat.length, virtualConfig);
  const visible = [];
  for (let index = range.start; index < range.end; index += 1) {
    const entry = flat[index];
    if (!entry) continue;
    const rowStyle = {
      position: "absolute",
      top: `${index * virtualConfig.rowHeight}px`,
      height: `${virtualConfig.rowHeight}px`,
      left: 0,
      right: 0
    };
    visible.push(renderRow(entry, index, "div", { style: rowStyle, "data-virtual-index": index }));
  }
  const viewportStyle = mergeStyle(props.style, {
    position: "relative",
    overflowY: "auto",
    height: `${virtualConfig.viewportHeight}px`
  });
  const virtualProps = {
    ...props,
    ...base,
    className: mergeClassNames("ui-widget ui-tree ui-virtual-tree", props.className),
    style: viewportStyle,
    "data-virtual-start": range.start,
    "data-virtual-end": range.end,
    "data-virtual-total": flat.length
  };
  const spacer = createElement(
    "div",
    { className: "ui-virtual-spacer", style: { position: "relative", height: `${range.totalHeight}px` } },
    visible,
    `${widget.id}-spacer`
  );
  return createElement("div", virtualProps, [spacer], widget.id);
}

function renderTable(state, widget, options = {}) {
  const props = pickProps(widget.props, ["id", "className", "style", "title", "role"]);
  const mergedClass = mergeClassNames("ui-widget ui-table", props.className);
  const base = widgetBaseProps(widget, mergedClass);
  const columns = normalizeTableColumns(widget.props?.columns ?? widget.model?.columns ?? []);
  const rows = normalizeTableRows(widget.props?.rows ?? widget.model?.rows ?? []);
  const virtualConfig = resolveVirtualConfig(widget);
  const rowHeight = virtualConfig?.rowHeight ?? coerceNumber(widget.props?.rowHeight ?? widget.model?.rowHeight, 24) ?? 24;
  const windowId = resolveWindowId(state, widget, options.windowId ?? null);
  const taskId = resolveTaskId(state, windowId, options.taskId ?? null);
  const ctx = buildContext(state, widget, options, windowId, taskId);

  const headerCells = columns.map((column) => {
    const cellStyle = column.width ? { flex: `0 0 ${column.width}px` } : { flex: "1 1 0" };
    return createElement(
      "div",
      { className: mergeClassNames("ui-table-header-cell", column.className), style: cellStyle },
      [createText(column.label)],
      `${widget.id}-header-${column.id}`
    );
  });
  const header = createElement("div", { className: "ui-table-header" }, headerCells, `${widget.id}-header`);

  const renderRow = (row, index, extraProps = {}) => {
    const rowClass = mergeClassNames("ui-table-row", row.className, row.selected ? "is-selected" : null);
    const rowProps = {
      className: rowClass,
      "data-table-id": widget.id,
      "data-row-id": row.id,
      "data-row-index": index,
      ...extraProps
    };

    const commandId = row.commandId ?? resolveItemCommandId(row.raw ?? row, widget);
    const command = applyCommandProps(
      rowProps,
      widget,
      options,
      ctx,
      "onClick",
      (baseCtx, event) => ({
        ...baseCtx,
        tableId: widget.id,
        row: row.raw,
        rowId: row.id,
        rowIndex: index,
        eventType: event?.type ?? null
      }),
      commandId
    );

    const cellNodes = columns.map((column) => {
      const cellStyle = column.width ? { flex: `0 0 ${column.width}px` } : { flex: "1 1 0" };
      const value =
        (Array.isArray(row.cells) ? row.cells[column.index] : row.cells?.[column.id]) ??
        "";
      return createElement(
        "div",
        { className: "ui-table-cell", style: cellStyle },
        [createText(String(value ?? ""))],
        `${row.id}-${column.id}`
      );
    });

    return createElement("div", command.props, cellNodes, row.id);
  };

  const bodyRows = [];
  if (!virtualConfig) {
    rows.forEach((row, index) => {
      const rowStyle = { height: `${rowHeight}px` };
      bodyRows.push(renderRow(row, index, { style: rowStyle }));
    });
    const body = createElement("div", { className: "ui-table-body" }, bodyRows, `${widget.id}-body`);
    return createElement("div", { ...props, ...base }, [header, body], widget.id);
  }

  const range = computeVirtualRange(rows.length, virtualConfig);
  for (let index = range.start; index < range.end; index += 1) {
    const row = rows[index];
    if (!row) continue;
    const rowStyle = {
      position: "absolute",
      top: `${index * virtualConfig.rowHeight}px`,
      height: `${virtualConfig.rowHeight}px`,
      left: 0,
      right: 0,
      display: "flex"
    };
    bodyRows.push(renderRow(row, index, { style: rowStyle, "data-virtual-index": index }));
  }

  const viewportStyle = mergeStyle(props.style, {
    position: "relative",
    overflowY: "auto",
    height: `${virtualConfig.viewportHeight}px`
  });
  const virtualProps = {
    ...props,
    ...base,
    className: mergeClassNames("ui-widget ui-table ui-virtual-table", props.className),
    style: viewportStyle,
    "data-virtual-start": range.start,
    "data-virtual-end": range.end,
    "data-virtual-total": rows.length
  };
  const spacer = createElement(
    "div",
    { className: "ui-virtual-spacer", style: { position: "relative", height: `${range.totalHeight}px` } },
    bodyRows,
    `${widget.id}-body`
  );
  const body = createElement("div", { className: "ui-table-body" }, [spacer], `${widget.id}-body-wrap`);
  return createElement("div", virtualProps, [header, body], widget.id);
}

function renderTextInput(state, widget, options = {}) {
  const props = pickProps(widget.props, [
    "id",
    "className",
    "style",
    "title",
    "disabled",
    "placeholder",
    "value",
    "type",
    "rows",
    "cols"
  ]);
  const mergedClass = mergeClassNames("ui-widget ui-text-input", props.className);
  const base = widgetBaseProps(widget, mergedClass);
  const value = widget.props?.value ?? widget.model?.value ?? "";
  const windowId = resolveWindowId(state, widget, options.windowId ?? null);
  const taskId = resolveTaskId(state, windowId, options.taskId ?? null);
  const ctx = buildContext(state, widget, options, windowId, taskId);
  const command = applyCommandProps(
    { ...props, ...base, value },
    widget,
    options,
    ctx,
    "onInput",
    (inputCtx, event) => ({
      ...inputCtx,
      inputValue: event?.target?.value ?? ""
    })
  );
  const multiline = widget.kind === "text-area" || widget.props?.multiline || widget.model?.multiline;
  if (multiline) {
    const { type, ...rest } = command.props;
    return createElement("textarea", rest, [], widget.id);
  }
  const type = props.type ?? "text";
  return createElement("input", { ...command.props, type }, [], widget.id);
}

function renderCanvasView(state, widget, options = {}) {
  const props = pickProps(widget.props, ["id", "className", "style", "title", "width", "height"]);
  const mergedClass = mergeClassNames("ui-widget ui-canvas-view", props.className);
  const base = widgetBaseProps(widget, mergedClass);
  const width = widget.props?.width ?? widget.model?.width ?? 320;
  const height = widget.props?.height ?? widget.model?.height ?? 200;
  const sceneNodes = widget.props?.scene ?? widget.model?.scene ?? [];
  const scene = buildScene(sceneNodes, { rootId: widget.id });
  const dirtyOptions = resolveDirtyOptions(widget);
  const windowId = resolveWindowId(state, widget, options.windowId ?? null);
  const taskId = resolveTaskId(state, windowId, options.taskId ?? null);
  const ctx = buildContext(state, widget, options, windowId, taskId);
  const registry = options?.registry ?? null;
  const defaultCommandId = resolveCommandId(widget);
  const a11yProps = resolveAccessibilityProps(widget, { label: "Canvas view" });

  const onCanvasRender = (node) => {
    if (!node) return;
    if (!node.__canvasBackend) {
      node.__canvasBackend = createCanvasBackend({ canvas: node, document: node.ownerDocument });
    }
    node.__canvasScene = scene;
    if (dirtyOptions) {
      node.__canvasBackend.render(scene, dirtyOptions);
    } else {
      node.__canvasBackend.render(scene);
    }
  };

  const onCanvasClick = (event) => {
    const target = event.currentTarget ?? event.target;
    const backend = target?.__canvasBackend;
    const activeScene = target?.__canvasScene ?? scene;
    if (!backend || !activeScene) return;
    const rect = target.getBoundingClientRect();
    const point = {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top
    };
    const hit = hitTestScene(activeScene, point);
    if (!hit) return;
    const commandId = hit.props?.commandId ?? defaultCommandId;
    if (!commandId || !registry) return;
    const enablement = commandEnabled(registry, commandId, ctx);
    if (!enablement.enabled) return;
    const commandCtx = {
      ...ctx,
      canvasId: widget.id,
      hitId: hit.id,
      hitKind: hit.kind,
      hitProps: hit.props,
      point
    };
    const result = executeCommand(registry, commandId, commandCtx);
    notifyCommandResult(options, { commandId, ctx: commandCtx, result, event });
  };

  const canvasProps = {
    ...props,
    ...base,
    ...a11yProps,
    width,
    height,
    __canvasRender: onCanvasRender,
    onClick: onCanvasClick
  };

  if (defaultCommandId) {
    canvasProps["data-command-id"] = defaultCommandId;
  }
  return createElement("canvas", canvasProps, [], widget.id);
}

function renderWebGLView(state, widget, options = {}) {
  const props = pickProps(widget.props, ["id", "className", "style", "title", "width", "height"]);
  const mergedClass = mergeClassNames("ui-widget ui-webgl-view", props.className);
  const base = widgetBaseProps(widget, mergedClass);
  const width = widget.props?.width ?? widget.model?.width ?? 320;
  const height = widget.props?.height ?? widget.model?.height ?? 200;
  const sceneNodes = widget.props?.scene ?? widget.model?.scene ?? [];
  const scene = buildScene(sceneNodes, { rootId: widget.id });
  const dirtyOptions = resolveDirtyOptions(widget);
  const windowId = resolveWindowId(state, widget, options.windowId ?? null);
  const taskId = resolveTaskId(state, windowId, options.taskId ?? null);
  const ctx = buildContext(state, widget, options, windowId, taskId);
  const registry = options?.registry ?? null;
  const defaultCommandId = resolveCommandId(widget);
  const a11yProps = resolveAccessibilityProps(widget, { label: "WebGL view" });

  const onWebGLRender = (node) => {
    if (!node) return;
    if (!node.__webglBackend) {
      node.__webglBackend = createWebGLBackend({ canvas: node, document: node.ownerDocument });
    }
    node.__webglScene = scene;
    if (dirtyOptions) {
      node.__webglBackend.render(scene, dirtyOptions);
    } else {
      node.__webglBackend.render(scene);
    }
  };

  const onWebGLClick = (event) => {
    const target = event.currentTarget ?? event.target;
    const backend = target?.__webglBackend;
    const activeScene = target?.__webglScene ?? scene;
    if (!backend || !activeScene) return;
    const rect = target.getBoundingClientRect();
    const point = {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top
    };
    const hit = hitTestScene(activeScene, point);
    if (!hit) return;
    const commandId = hit.props?.commandId ?? defaultCommandId;
    if (!commandId || !registry) return;
    const enablement = commandEnabled(registry, commandId, ctx);
    if (!enablement.enabled) return;
    const commandCtx = {
      ...ctx,
      webglId: widget.id,
      hitId: hit.id,
      hitKind: hit.kind,
      hitProps: hit.props,
      point
    };
    const result = executeCommand(registry, commandId, commandCtx);
    notifyCommandResult(options, { commandId, ctx: commandCtx, result, event });
  };

  const canvasProps = {
    ...props,
    ...base,
    ...a11yProps,
    width,
    height,
    __webglRender: onWebGLRender,
    onClick: onWebGLClick
  };

  if (defaultCommandId) {
    canvasProps["data-command-id"] = defaultCommandId;
  }
  return createElement("canvas", canvasProps, [], widget.id);
}

export function renderWidget(state, widgetId, options = {}) {
  const widget = state.widgets?.[widgetId];
  if (!widget) {
    throw new Error(`Unknown widget: ${widgetId}`);
  }
  switch (widget.kind) {
    case "container":
    case "root":
      return renderContainer(state, widget, options);
    case "label":
      return renderLabel(widget);
    case "button":
      return renderButton(state, widget, options);
    case "list":
      return renderList(state, widget, options);
    case "tree":
      return renderTree(state, widget, options);
    case "table":
      return renderTable(state, widget, options);
    case "text-input":
    case "text-area":
      return renderTextInput(state, widget, options);
    case "canvas-view":
      return renderCanvasView(state, widget, options);
    case "webgl-view":
      return renderWebGLView(state, widget, options);
    default:
      return renderContainer(state, widget, options);
  }
}

export function renderWindow(state, windowId, options = {}) {
  const window = state.windows?.[windowId];
  if (!window) {
    throw new Error(`Unknown window: ${windowId}`);
  }
  const windowClass = mergeClassNames("ui-window");
  const props = {
    "data-window-id": window.id,
    "data-window-kind": window.kind ?? "window",
    ...(window.taskId ? { "data-task-id": window.taskId } : {}),
    className: windowClass
  };
  const children = window.rootWidgetId
    ? [
        renderWidget(state, window.rootWidgetId, {
          ...options,
          windowId: window.id,
          taskId: window.taskId ?? options.taskId ?? null
        })
      ]
    : [];
  return createElement("section", props, children, `window-${window.id}`);
}
