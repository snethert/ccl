function isNode(value) {
  return value && typeof value === "object" && (value.kind === "element" || value.kind === "text");
}

function normalizeChild(value, out) {
  if (value === null || value === undefined || value === false) {
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((entry) => normalizeChild(entry, out));
    return;
  }
  if (typeof value === "string" || typeof value === "number") {
    out.push(createText(String(value)));
    return;
  }
  if (isNode(value)) {
    out.push(value);
    return;
  }
  throw new Error(`Unsupported child type: ${typeof value}`);
}

export function normalizeChildren(children) {
  const out = [];
  normalizeChild(children, out);
  return out;
}

export function createText(text, key = null) {
  if (text === null || text === undefined) {
    throw new Error("Text node requires a value");
  }
  return {
    kind: "text",
    text: String(text),
    key
  };
}

export function createElement(tag, props = null, children = null, keyOverride = null) {
  if (!tag) {
    throw new Error("Element tag is required");
  }
  const normalizedProps = props ? { ...props } : {};
  let key = keyOverride;
  if (key === null || key === undefined) {
    key = null;
  }
  if ((key === null || key === undefined) && Object.prototype.hasOwnProperty.call(normalizedProps, "key")) {
    key = normalizedProps.key;
    delete normalizedProps.key;
  }
  const normalizedChildren = normalizeChildren(children);
  return {
    kind: "element",
    tag,
    props: normalizedProps,
    children: normalizedChildren,
    key
  };
}

export function h(tag, props, ...children) {
  return createElement(tag, props, children);
}
