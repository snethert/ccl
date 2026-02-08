function isPlainObject(value) {
  return Object.prototype.toString.call(value) === "[object Object]";
}

export function markPresentationStale(presentation, reason = null) {
  if (!presentation || typeof presentation !== "object") {
    throw new Error("Presentation must be an object");
  }
  const metadata = isPlainObject(presentation.metadata) ? { ...presentation.metadata } : {};
  metadata.stale = true;
  if (reason) {
    metadata.staleReason = reason;
  }
  return { ...presentation, metadata };
}

export function revalidatePresentations(state, resolver) {
  if (!state || typeof state !== "object") {
    throw new Error("State is required");
  }
  if (typeof resolver !== "function") {
    return { state, stale: [] };
  }
  const presentations = state.presentations ?? {};
  const next = { ...presentations };
  const stale = [];
  for (const [id, presentation] of Object.entries(presentations)) {
    const result = resolver(presentation);
    if (result && result.ok && result.presentation) {
      next[id] = result.presentation;
    } else {
      next[id] = markPresentationStale(presentation, result?.reason ?? null);
      stale.push(id);
    }
  }
  return { state: { ...state, presentations: next }, stale };
}
