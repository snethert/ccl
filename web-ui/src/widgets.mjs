import { commandEnabled, executeCommand } from "./commands.mjs";
import { makeContext } from "./context.mjs";
import { createElement, createText } from "./vdom.mjs";
import { buildScene, hitTestScene } from "../backends/canvas/scene.mjs";
import { createCanvasBackend } from "../backends/canvas/renderer.mjs";
import { createWebGLBackend } from "../backends/webgl/renderer.mjs";

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
  return {
    "data-widget-id": widget.id,
    "data-widget-kind": widget.kind,
    className: baseClass
  };
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
  return makeContext(state, {
    taskId,
    windowId,
    widgetId: widget.id,
    contextId: widget.props?.contextId ?? null,
    selection: state.selection ?? null
  });
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
    if (options?.onCommandResult) {
      options.onCommandResult({ commandId, ctx: commandCtx, result, event });
    }
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
      selected: false,
      commandId: null
    };
  });
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

  const renderRow = (item, index, kind = "li", extraProps = {}) => {
    const itemId = item.id;
    const itemKey = item.key;
    const rowClass = mergeClassNames("ui-list-item", item.className, item.selected ? "is-selected" : null);
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
        listId: widget.id,
        item: item.raw,
        itemId,
        itemIndex: index,
        eventType: event?.type ?? null
      }),
      commandId
    );

    const button = createElement("button", command.props, [createText(item.label)], `${itemKey}-button`);
    return createElement(kind, rowProps, [button], itemKey);
  };

  if (!virtualConfig) {
    const children = items.map((item, index) => renderRow(item, index));
    return createElement("ul", { ...props, ...base }, children, widget.id);
  }

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
  return createElement("div", virtualProps, [spacer], widget.id);
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
    if (options?.onCommandResult) {
      options.onCommandResult({ commandId, ctx: commandCtx, result, event });
    }
  };

  const canvasProps = {
    ...props,
    ...base,
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
    if (options?.onCommandResult) {
      options.onCommandResult({ commandId, ctx: commandCtx, result, event });
    }
  };

  const canvasProps = {
    ...props,
    ...base,
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
