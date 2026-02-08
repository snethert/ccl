export const DEFAULT_ACTIONS_BY_TYPE = Object.freeze({
  value: ["inspect", "describe"],
  symbol: ["go-to-definition", "find-references", "describe", "inspect"],
  definition: ["open-source", "describe"],
  command: ["do-again", "do-again-with-args"],
  frame: ["inspect-frame", "jump-to-source"],
  binding: ["inspect", "watch"],
  place: ["edit", "inspect"],
  "condition-section": ["explain", "open-doc"],
  restart: ["invoke-restart"],
  doc: ["open-doc", "inspect-subject"],
  location: ["open-source"]
});

const ACTION_LABELS = Object.freeze({
  inspect: "Inspect",
  describe: "Describe",
  "go-to-definition": "Go to Definition",
  "find-references": "Find References",
  "open-source": "Open Source",
  "do-again": "Do Again",
  "do-again-with-args": "Do Again With Args",
  "inspect-frame": "Inspect Frame",
  "jump-to-source": "Jump to Source",
  watch: "Watch",
  edit: "Edit",
  explain: "Explain",
  "open-doc": "Open Doc",
  "invoke-restart": "Invoke Restart",
  "inspect-subject": "Inspect Subject"
});

function normalizeSelection(selection) {
  if (!selection || typeof selection !== "object") return null;
  const targetIds = Array.isArray(selection.targetIds)
    ? selection.targetIds
    : selection.targetId
      ? [selection.targetId]
      : selection.target
        ? [selection.target]
        : [];
  return { ...selection, targetIds };
}

export function buildSelectionActions(selection, presentations, options = {}) {
  const normalized = normalizeSelection(selection);
  if (!normalized || normalized.targetIds.length === 0) return [];
  const actionsByType = options.actionsByType ?? DEFAULT_ACTIONS_BY_TYPE;
  const types = normalized.targetIds
    .map((id) => presentations?.[id]?.type ?? "value")
    .filter(Boolean);
  if (types.length === 0) return [];
  let common = null;
  for (const type of types) {
    const actions = actionsByType[type] ?? [];
    if (!common) {
      common = new Set(actions);
    } else {
      common = new Set(actions.filter((action) => common.has(action)));
    }
  }
  const result = common ? Array.from(common) : [];
  return result.map((id) => ({
    id,
    label: ACTION_LABELS[id] ?? id
  }));
}
