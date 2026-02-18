const DEFAULT_CAPACITY = 256;

export function createEventLog(capacity = DEFAULT_CAPACITY) {
  const resolved = Number.isInteger(capacity) && capacity > 0 ? capacity : DEFAULT_CAPACITY;
  return { capacity: resolved, entries: [] };
}

export function normalizeEventLog(eventLog = null) {
  if (!eventLog) {
    return createEventLog();
  }
  const capacity =
    Number.isInteger(eventLog.capacity) && eventLog.capacity > 0 ? eventLog.capacity : DEFAULT_CAPACITY;
  const entries = Array.isArray(eventLog.entries) ? [...eventLog.entries] : [];
  return { capacity, entries };
}

export function recordEvent(eventLog, entry) {
  const normalized = normalizeEventLog(eventLog);
  const nextEntries = [...normalized.entries, entry];
  const overflow = nextEntries.length - normalized.capacity;
  const trimmed = overflow > 0 ? nextEntries.slice(overflow) : nextEntries;
  return { capacity: normalized.capacity, entries: trimmed };
}
