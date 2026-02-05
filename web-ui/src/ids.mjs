export function createIdGenerator(prefix = "id") {
  let counter = 0;
  return function nextId() {
    const id = `${prefix}-${counter}`;
    counter += 1;
    return id;
  };
}

export function initIdCounters(kinds = []) {
  const counters = {};
  for (const kind of kinds) {
    counters[kind] = 0;
  }
  return counters;
}

export function allocateId(counters, kind, prefix = kind) {
  const current = Number.isInteger(counters?.[kind]) ? counters[kind] : 0;
  const id = `${prefix}-${current}`;
  return {
    id,
    counters: { ...counters, [kind]: current + 1 }
  };
}
