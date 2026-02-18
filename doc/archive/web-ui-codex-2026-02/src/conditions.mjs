export const RESTART_SAFETY_LEVELS = Object.freeze(["safe", "destructive", "irreversible"]);

function normalizeString(value, fallback = null) {
  if (typeof value === "string" && value.length > 0) return value;
  return fallback;
}

function normalizeArray(value) {
  return Array.isArray(value) ? [...value] : [];
}

export function normalizeRestart(restart) {
  if (!restart || typeof restart !== "object") {
    throw new Error("Restart must be an object");
  }
  const safety = RESTART_SAFETY_LEVELS.includes(restart.safety) ? restart.safety : "safe";
  const recommendedReason = normalizeString(
    restart.recommendedReason ?? restart.recommendationReason ?? restart.recommendation?.reason,
    null
  );
  return {
    id: normalizeString(restart.id, null),
    title: normalizeString(restart.title, null),
    description: normalizeString(restart.description, null),
    safety,
    argSchema: normalizeArray(restart.argSchema),
    preview: restart.preview ?? null,
    recommended: Boolean(restart.recommended),
    recommendedReason
  };
}

export function normalizeConditionSection(section) {
  if (!section || typeof section !== "object") {
    return { id: null, title: null, text: "", actions: [], location: null };
  }
  return {
    id: normalizeString(section.id, null),
    title: normalizeString(section.title, null),
    text: normalizeString(section.text, ""),
    actions: normalizeArray(section.actions),
    location: section.location ?? null
  };
}

export function normalizeConditionReport(report) {
  if (!report || typeof report !== "object") {
    throw new Error("Condition report must be an object");
  }
  return {
    id: normalizeString(report.id, null),
    kind: normalizeString(report.kind, "error"),
    message: normalizeString(report.message, ""),
    summary: normalizeString(report.summary, ""),
    sections: normalizeArray(report.sections).map(normalizeConditionSection),
    stack: normalizeArray(report.stack),
    restarts: normalizeArray(report.restarts)
  };
}
