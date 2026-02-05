import { commandEnabled, executeCommand } from "./commands.mjs";
import { makeContext } from "./context.mjs";
import { createElement, createText } from "./vdom.mjs";

function mergeClassNames(...values) {
  return values.filter((value) => value && String(value).trim().length > 0).join(" ");
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

function renderContainer(state, widget, options = {}) {
  const props = pickProps(widget.props, ["id", "className", "style", "title", "role"]);
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
  const windowId = resolveWindowId(state, widget, options.windowId ?? null);
  const taskId = resolveTaskId(state, windowId, options.taskId ?? null);
  const ctx = buildContext(state, widget, options, windowId, taskId);

  const children = items.map((item, index) => {
    const itemId = item.id;
    const itemKey = item.key;
    const liClass = mergeClassNames("ui-list-item", item.className, item.selected ? "is-selected" : null);
    const liProps = {
      className: liClass,
      "data-item-id": itemId,
      "data-item-index": index,
      "data-list-id": widget.id
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
    return createElement("li", liProps, [button], itemKey);
  });

  return createElement("ul", { ...props, ...base }, children, widget.id);
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
    case "text-input":
    case "text-area":
      return renderTextInput(state, widget, options);
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
