function normalizeTargets(selection) {
  if (!selection) return [];
  if (Array.isArray(selection.targetIds)) return selection.targetIds;
  if (Array.isArray(selection.targets)) return selection.targets;
  if (selection.targetId) return [selection.targetId];
  if (selection.target) return [selection.target];
  return [];
}

export function normalizeSelection(selection) {
  if (!selection) return null;
  if (typeof selection === "string") {
    return {
      id: selection,
      kind: "item",
      targetIds: [selection],
      anchorId: selection,
      metadata: {}
    };
  }
  if (typeof selection !== "object") {
    throw new Error("Selection must be an object or string");
  }
  const targetIds = normalizeTargets(selection);
  const fallbackId = targetIds.length > 0 ? targetIds[0] : null;
  const id = selection.id ?? fallbackId;
  if (!id) {
    throw new Error("Selection must include an id or target");
  }
  const anchorId = selection.anchorId ?? selection.target ?? selection.targetId ?? fallbackId;
  return {
    id,
    kind: selection.kind ?? "item",
    targetIds: [...targetIds],
    anchorId: anchorId ?? null,
    metadata: selection.metadata ?? {}
  };
}

export function setSelection(state, selection) {
  return {
    ...state,
    selection: normalizeSelection(selection)
  };
}
