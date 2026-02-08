export const PRESENTATION_TYPES = Object.freeze([
  "value",
  "symbol",
  "definition",
  "command",
  "frame",
  "binding",
  "place",
  "condition-section",
  "restart",
  "doc",
  "location"
]);
export const PRESENTATION_TAXONOMY_VERSION = "0";

export const PRESENTATION_REQUIRED_METADATA = Object.freeze({
  value: ["summary"],
  symbol: ["name", "package"],
  definition: ["name", "kind", "location"],
  command: ["commandId", "args", "title"],
  frame: ["frameId", "function", "location", "locals"],
  binding: ["name", "valueId", "scope"],
  place: ["placeId", "description", "setter", "valueId", "editable"],
  "condition-section": ["errorId", "sectionKey", "text"],
  restart: ["restartId", "title", "safety", "argSchema"],
  doc: ["subject", "docKind", "links"],
  location: ["file", "line", "column"]
});

export function normalizePresentationType(type) {
  if (typeof type !== "string") return "value";
  if (PRESENTATION_TYPES.includes(type)) return type;
  return "value";
}

export function validatePresentationMetadata(presentation) {
  if (!presentation || typeof presentation !== "object") {
    return { ok: false, reason: "Presentation must be an object", missing: [] };
  }
  const type = normalizePresentationType(presentation.type ?? presentation.presentationType ?? "value");
  const required = PRESENTATION_REQUIRED_METADATA[type] ?? [];
  const metadata = presentation.metadata ?? {};
  const missing = required.filter((key) => metadata?.[key] === undefined || metadata?.[key] === null);
  return {
    ok: missing.length === 0,
    type,
    missing
  };
}

export function applyPresentationDefaults(presentation) {
  if (!presentation || typeof presentation !== "object") {
    throw new Error("Presentation must be an object");
  }
  const type = normalizePresentationType(presentation.type ?? presentation.presentationType ?? "value");
  return {
    ...presentation,
    type,
    metadata: { ...(presentation.metadata ?? {}) }
  };
}
