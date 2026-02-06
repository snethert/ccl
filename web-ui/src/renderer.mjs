import { normalizeChildren } from "./vdom.mjs";

function isSameType(a, b) {
  if (!a || !b) return false;
  if (a.kind !== b.kind) return false;
  if (a.kind === "element") {
    return a.tag === b.tag;
  }
  return true;
}

function keyForTree(tree, index) {
  if (tree && tree.key !== null && tree.key !== undefined) {
    return String(tree.key);
  }
  return `__index_${index}`;
}

function keyForInstance(instance, index) {
  return keyForTree(instance.tree, index);
}

function assertUniqueKeys(items, keyFn, context) {
  const seen = new Set();
  items.forEach((item, index) => {
    const key = keyFn(item, index);
    if (seen.has(key)) {
      throw new Error(`Duplicate key '${key}' in ${context}`);
    }
    seen.add(key);
  });
}

function updateProps(handle, prevProps, nextProps, backend) {
  const prevKeys = Object.keys(prevProps);
  const nextKeys = Object.keys(nextProps);
  for (const key of prevKeys) {
    if (!Object.prototype.hasOwnProperty.call(nextProps, key)) {
      backend.removeProp(handle, key, prevProps[key]);
    }
  }
  for (const key of nextKeys) {
    const prev = prevProps[key];
    const next = nextProps[key];
    if (prev !== next) {
      backend.setProp(handle, key, next, prev);
    }
  }
}

function mount(tree, backend) {
  if (tree.kind === "text") {
    const handle = backend.createText(tree.text);
    return { tree, handle, children: [] };
  }
  const handle = backend.createElement(tree.tag);
  updateProps(handle, {}, tree.props ?? {}, backend);
  const children = [];
  const normalizedChildren = normalizeChildren(tree.children ?? []);
  assertUniqueKeys(normalizedChildren, keyForTree, `children of <${tree.tag}>`);
  for (const child of normalizedChildren) {
    const childInstance = mount(child, backend);
    children.push(childInstance);
    backend.appendChild(handle, childInstance.handle);
  }
  return { tree: { ...tree, children: normalizedChildren }, handle, children };
}

function unmount(instance, backend) {
  for (const child of instance.children) {
    unmount(child, backend);
  }
  if (backend.destroy) {
    backend.destroy(instance.handle);
  }
}

function updateInstance(instance, nextTree, backend) {
  if (!isSameType(instance.tree, nextTree)) {
    throw new Error("updateInstance called with mismatched node types");
  }
  if (nextTree.kind === "text") {
    if (instance.tree.text !== nextTree.text) {
      backend.setText(instance.handle, nextTree.text);
    }
    instance.tree = nextTree;
    return instance;
  }
  updateProps(instance.handle, instance.tree.props ?? {}, nextTree.props ?? {}, backend);
  const normalizedChildren = normalizeChildren(nextTree.children ?? []);
  assertUniqueKeys(normalizedChildren, keyForTree, `children of <${nextTree.tag}>`);
  instance.children = reconcileChildren(instance.handle, instance.children, normalizedChildren, backend);
  instance.tree = { ...nextTree, children: normalizedChildren };
  return instance;
}

function reconcileChildren(parentHandle, oldChildren, newChildrenTrees, backend) {
  assertUniqueKeys(oldChildren, keyForInstance, "previous children");
  const oldByKey = new Map();
  oldChildren.forEach((child, index) => {
    oldByKey.set(keyForInstance(child, index), child);
  });

  const nextChildren = [];
  const reused = new Set();

  newChildrenTrees.forEach((childTree, index) => {
    const key = keyForTree(childTree, index);
    const prev = oldByKey.get(key);
    if (prev && isSameType(prev.tree, childTree)) {
      const updated = updateInstance(prev, childTree, backend);
      nextChildren.push(updated);
      reused.add(prev);
      return;
    }
    const mounted = mount(childTree, backend);
    nextChildren.push(mounted);
  });

  for (const child of oldChildren) {
    if (!reused.has(child)) {
      backend.removeChild(parentHandle, child.handle);
      unmount(child, backend);
    }
  }

  let anchor = null;
  for (let i = nextChildren.length - 1; i >= 0; i -= 1) {
    backend.insertBefore(parentHandle, nextChildren[i].handle, anchor);
    anchor = nextChildren[i].handle;
  }

  return nextChildren;
}

export function createRoot(backend, container, options = {}) {
  let rootInstance = null;
  let pendingTree = null;
  let pendingSet = false;
  let scheduled = false;
  const schedule = typeof options.schedule === "function" ? options.schedule : null;

  function apply(tree) {
    if (!tree) {
      if (rootInstance) {
        backend.removeChild(container, rootInstance.handle);
        unmount(rootInstance, backend);
        rootInstance = null;
      }
      return;
    }
    if (!rootInstance) {
      const instance = mount(tree, backend);
      backend.appendChild(container, instance.handle);
      rootInstance = instance;
      return;
    }
    if (isSameType(rootInstance.tree, tree)) {
      rootInstance = updateInstance(rootInstance, tree, backend);
      return;
    }
    const next = mount(tree, backend);
    if (backend.replaceChild) {
      backend.replaceChild(container, next.handle, rootInstance.handle);
    } else {
      backend.removeChild(container, rootInstance.handle);
      backend.appendChild(container, next.handle);
    }
    unmount(rootInstance, backend);
    rootInstance = next;
  }

  function flush() {
    scheduled = false;
    if (!pendingSet) return;
    const tree = pendingTree;
    pendingTree = null;
    pendingSet = false;
    apply(tree);
  }

  return {
    render(tree) {
      if (!schedule) {
        apply(tree);
        return;
      }
      pendingTree = tree;
      pendingSet = true;
      if (!scheduled) {
        scheduled = true;
        schedule(flush);
      }
    },
    flush() {
      if (!schedule) return;
      flush();
    },
    unmount() {
      if (schedule) {
        pendingTree = null;
        scheduled = false;
      }
      if (!rootInstance) return;
      backend.removeChild(container, rootInstance.handle);
      unmount(rootInstance, backend);
      rootInstance = null;
    },
    getInstance() {
      return rootInstance;
    }
  };
}
