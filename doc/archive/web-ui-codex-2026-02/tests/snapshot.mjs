function sortValue(value) {
  if (Array.isArray(value)) {
    return value.map(sortValue);
  }
  if (value && typeof value === "object") {
    const out = {};
    for (const key of Object.keys(value).sort()) {
      out[key] = sortValue(value[key]);
    }
    return out;
  }
  return value;
}

export function stableStringify(value) {
  return JSON.stringify(sortValue(value), null, 2);
}

export function serializeState(state, version = "0") {
  return {
    version,
    state: sortValue(state)
  };
}

export function snapshotToString(snapshot) {
  return stableStringify(snapshot);
}
