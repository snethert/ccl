const DEFAULT_RECORDING_STATUS = "ok";
const DEFAULT_RECORDING_STREAM = "repl";
const DEFAULT_ENTRY_STREAM = "stdout";
const DEFAULT_ENTRY_KIND = "text";
const INPUT_KINDS = new Set(["unknown", "form", "file", "command"]);
export const OUTPUT_RECORDING_SCHEMA_VERSION = "0";

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === "[object Object]";
}

function normalizeString(value, fallback = null) {
  if (typeof value === "string" && value.length > 0) return value;
  return fallback;
}

function normalizeInt(value, fallback = null) {
  if (Number.isInteger(value)) return value;
  return fallback;
}

function normalizeArray(value) {
  return Array.isArray(value) ? [...value] : [];
}

function normalizeMetadata(value) {
  return isPlainObject(value) ? { ...value } : {};
}

function normalizeInput(input) {
  if (!input || typeof input !== "object") {
    return { kind: "unknown", text: "", package: null, sourceLocation: null };
  }
  const sourceLocation = isPlainObject(input.sourceLocation)
    ? {
        file: normalizeString(input.sourceLocation.file, null),
        line: normalizeInt(input.sourceLocation.line, null),
        column: normalizeInt(input.sourceLocation.column, null)
      }
    : null;
  const rawKind = normalizeString(input.kind, "unknown");
  const kind = INPUT_KINDS.has(rawKind) ? rawKind : "unknown";
  return {
    kind,
    text: normalizeString(input.text, ""),
    package: normalizeString(input.package, null),
    sourceLocation
  };
}

function normalizeContext(context) {
  if (!context || typeof context !== "object") {
    return { commandId: null, sessionId: null, workspaceId: null };
  }
  return {
    commandId: normalizeString(context.commandId, null),
    sessionId: normalizeString(context.sessionId, null),
    workspaceId: normalizeString(context.workspaceId, null)
  };
}

export function normalizeRecording(recording) {
  if (!recording || typeof recording !== "object") {
    throw new Error("Recording must be an object");
  }
  const entryIds = normalizeArray(recording.entryIds).filter((id) => typeof id === "string");
  return {
    id: normalizeString(recording.id, null),
    jobId: normalizeString(recording.jobId, null),
    status: normalizeString(recording.status, DEFAULT_RECORDING_STATUS),
    seqStart: normalizeInt(recording.seqStart, null),
    seqEnd: normalizeInt(recording.seqEnd, null),
    tsStart: normalizeInt(recording.tsStart, null),
    tsEnd: normalizeInt(recording.tsEnd, null),
    streamId: normalizeString(recording.streamId, DEFAULT_RECORDING_STREAM),
    input: normalizeInput(recording.input),
    context: normalizeContext(recording.context),
    entryIds,
    metadata: normalizeMetadata(recording.metadata)
  };
}

export function normalizeEntry(entry) {
  if (!entry || typeof entry !== "object") {
    throw new Error("Entry must be an object");
  }
  return {
    id: normalizeString(entry.id, null),
    recordingId: normalizeString(entry.recordingId, null),
    kind: normalizeString(entry.kind, DEFAULT_ENTRY_KIND),
    streamId: normalizeString(entry.streamId, DEFAULT_ENTRY_STREAM),
    seq: normalizeInt(entry.seq, null),
    ts: normalizeInt(entry.ts, null),
    text: normalizeString(entry.text, ""),
    anchorId: normalizeString(entry.anchorId, null),
    presentationId: normalizeString(entry.presentationId, null),
    metadata: normalizeMetadata(entry.metadata)
  };
}

export function normalizeAnchor(anchor) {
  if (!anchor || typeof anchor !== "object") {
    throw new Error("Anchor must be an object");
  }
  const rawRange = isPlainObject(anchor.range)
    ? {
        start: normalizeInt(anchor.range.start, null),
        end: normalizeInt(anchor.range.end, null)
      }
    : null;
  const range =
    rawRange && rawRange.start !== null && rawRange.end !== null && rawRange.start >= 0 && rawRange.end >= rawRange.start
      ? rawRange
      : null;
  const path = normalizeArray(anchor.path).filter((entry) => typeof entry === "string" || Number.isInteger(entry));
  return {
    id: normalizeString(anchor.id, null),
    entryId: normalizeString(anchor.entryId, null),
    range,
    path
  };
}

export function createRecordingStore() {
  return {
    recordings: {},
    entries: {},
    anchors: {},
    recordingOrder: [],
    entryOrder: [],
    byAnchor: {},
    byPresentation: {}
  };
}

export function normalizeRecordingStore(store = null) {
  const base = createRecordingStore();
  if (!store || typeof store !== "object") {
    return base;
  }
  const normalized = {
    recordings: typeof store.recordings === "object" && store.recordings ? { ...store.recordings } : base.recordings,
    entries: typeof store.entries === "object" && store.entries ? { ...store.entries } : base.entries,
    anchors: typeof store.anchors === "object" && store.anchors ? { ...store.anchors } : base.anchors,
    recordingOrder: Array.isArray(store.recordingOrder) ? [...store.recordingOrder] : base.recordingOrder,
    entryOrder: Array.isArray(store.entryOrder) ? [...store.entryOrder] : base.entryOrder,
    byAnchor: typeof store.byAnchor === "object" && store.byAnchor ? { ...store.byAnchor } : base.byAnchor,
    byPresentation:
      typeof store.byPresentation === "object" && store.byPresentation ? { ...store.byPresentation } : base.byPresentation
  };
  if (typeof store.truncation === "object" && store.truncation) {
    normalized.truncation = { ...store.truncation };
  }
  return normalized;
}

export function appendRecording(store, recording) {
  const normalized = normalizeRecording(recording);
  if (!normalized.id) {
    throw new Error("Recording id is required");
  }
  const next = normalizeRecordingStore(store ?? null);
  if (next.recordings[normalized.id]) {
    throw new Error(`Recording already exists: ${normalized.id}`);
  }
  return {
    ...next,
    recordings: { ...next.recordings, [normalized.id]: normalized },
    recordingOrder: [...next.recordingOrder, normalized.id]
  };
}

function resolveLastStreamSeq(store, streamId) {
  const stream = normalizeString(streamId, DEFAULT_ENTRY_STREAM);
  const entries = store.entries ?? {};
  const order = Array.isArray(store.entryOrder) ? store.entryOrder : [];
  let lastSeq = null;
  for (let index = order.length - 1; index >= 0; index -= 1) {
    const entryId = order[index];
    const entry = entries[entryId];
    if (!entry || entry.streamId !== stream || !Number.isInteger(entry.seq)) continue;
    lastSeq = entry.seq;
    break;
  }
  return { stream, lastSeq };
}

function updateRecordingBounds(recording, entry) {
  const nextEntryIds = [...(recording.entryIds ?? []), entry.id];
  let seqStart = recording.seqStart ?? null;
  let seqEnd = recording.seqEnd ?? null;
  if (Number.isInteger(entry.seq)) {
    if (seqStart === null || entry.seq < seqStart) seqStart = entry.seq;
    if (seqEnd === null || entry.seq > seqEnd) seqEnd = entry.seq;
  }
  let tsStart = recording.tsStart ?? null;
  let tsEnd = recording.tsEnd ?? null;
  if (Number.isInteger(entry.ts)) {
    if (tsStart === null || entry.ts < tsStart) tsStart = entry.ts;
    if (tsEnd === null || entry.ts > tsEnd) tsEnd = entry.ts;
  }
  return {
    ...recording,
    entryIds: nextEntryIds,
    seqStart,
    seqEnd,
    tsStart,
    tsEnd
  };
}

export function appendEntry(store, entry) {
  const normalized = normalizeEntry(entry);
  if (!normalized.id) {
    throw new Error("Entry id is required");
  }
  if (!normalized.recordingId) {
    throw new Error("Entry recordingId is required");
  }
  const next = normalizeRecordingStore(store ?? null);
  if (next.entries[normalized.id]) {
    throw new Error(`Entry already exists: ${normalized.id}`);
  }
  const recording = next.recordings?.[normalized.recordingId] ?? null;
  if (!recording) {
    throw new Error(`Recording not found for entry: ${normalized.recordingId}`);
  }
  if (Number.isInteger(normalized.seq)) {
    const { stream, lastSeq } = resolveLastStreamSeq(next, normalized.streamId);
    if (lastSeq !== null && normalized.seq <= lastSeq) {
      throw new Error(`Entry seq must increase for stream ${stream}`);
    }
  }
  const byAnchor = { ...next.byAnchor };
  if (normalized.anchorId) {
    byAnchor[normalized.anchorId] = {
      entryId: normalized.id,
      range: null,
      path: []
    };
  }
  const byPresentation = { ...next.byPresentation };
  if (normalized.presentationId) {
    byPresentation[normalized.presentationId] = normalized.id;
  }
  const updatedRecording = updateRecordingBounds(recording, normalized);
  return {
    ...next,
    recordings: { ...next.recordings, [updatedRecording.id]: updatedRecording },
    entries: { ...next.entries, [normalized.id]: normalized },
    entryOrder: [...next.entryOrder, normalized.id],
    byAnchor,
    byPresentation
  };
}

export function attachAnchor(store, anchor) {
  const normalized = normalizeAnchor(anchor);
  if (!normalized.id) {
    throw new Error("Anchor id is required");
  }
  if (!normalized.entryId) {
    throw new Error("Anchor entryId is required");
  }
  const next = normalizeRecordingStore(store ?? null);
  if (next.anchors[normalized.id]) {
    throw new Error(`Anchor already exists: ${normalized.id}`);
  }
  if (!next.entries?.[normalized.entryId]) {
    throw new Error(`Entry not found for anchor: ${normalized.entryId}`);
  }
  const entry = next.entries[normalized.entryId];
  const updatedEntry = entry.anchorId ? entry : { ...entry, anchorId: normalized.id };
  return {
    ...next,
    entries: { ...next.entries, [updatedEntry.id]: updatedEntry },
    anchors: { ...next.anchors, [normalized.id]: normalized },
    byAnchor: {
      ...next.byAnchor,
      [normalized.id]: {
        entryId: normalized.entryId,
        range: normalized.range,
        path: normalized.path
      }
    }
  };
}

export function setEntryFolded(store, entryId, folded) {
  const next = store ?? createRecordingStore();
  const entry = next.entries?.[entryId];
  if (!entry) {
    return next;
  }
  const metadata = { ...(entry.metadata ?? {}), folded: Boolean(folded) };
  return {
    ...next,
    entries: { ...next.entries, [entryId]: { ...entry, metadata } }
  };
}

function resolveEntryFromTarget(store, target) {
  const next = store ?? createRecordingStore();
  const entries = next.entries ?? {};
  const byAnchor = next.byAnchor ?? {};
  const anchors = next.anchors ?? {};

  let entryId = null;
  let anchorId = null;
  if (typeof target === "string") {
    if (entries[target]) {
      entryId = target;
    } else if (byAnchor[target]?.entryId) {
      entryId = byAnchor[target].entryId;
      anchorId = target;
    } else if (anchors[target]?.entryId) {
      entryId = anchors[target].entryId;
      anchorId = target;
    }
  } else if (target && typeof target === "object") {
    if (typeof target.entryId === "string" && entries[target.entryId]) {
      entryId = target.entryId;
    }
    if (!entryId && typeof target.anchorId === "string") {
      if (byAnchor[target.anchorId]?.entryId) {
        entryId = byAnchor[target.anchorId].entryId;
        anchorId = target.anchorId;
      } else if (anchors[target.anchorId]?.entryId) {
        entryId = anchors[target.anchorId].entryId;
        anchorId = target.anchorId;
      }
    }
  }

  if (!entryId || !entries[entryId]) {
    throw new Error("Entry target not found");
  }
  if (!anchorId) {
    const entryAnchorId = entries[entryId].anchorId ?? null;
    anchorId = entryAnchorId || null;
  }
  return { entry: entries[entryId], anchorId };
}

function resolveRecording(next, recordingId) {
  const recording = next.recordings?.[recordingId] ?? null;
  if (!recording) {
    throw new Error(`Recording not found: ${recordingId}`);
  }
  return recording;
}

function resolveEntryFormText(entry) {
  const metadata = entry?.metadata ?? {};
  if (typeof metadata.formText === "string") return metadata.formText;
  if (typeof metadata.form === "string") return metadata.form;
  if (typeof entry?.text === "string") return entry.text;
  return "";
}

export function copyAsForm(store, target) {
  const next = store ?? createRecordingStore();
  const { entry, anchorId } = resolveEntryFromTarget(next, target);
  return {
    kind: "form",
    text: resolveEntryFormText(entry),
    entryId: entry.id,
    recordingId: entry.recordingId ?? null,
    anchorId
  };
}

export function copyWithContext(store, target) {
  const next = store ?? createRecordingStore();
  const copied = copyAsForm(next, target);
  const entry = next.entries?.[copied.entryId] ?? null;
  const recording = copied.recordingId ? next.recordings?.[copied.recordingId] ?? null : null;
  return {
    kind: "form+context",
    text: copied.text,
    entryId: copied.entryId,
    recordingId: copied.recordingId,
    anchorId: copied.anchorId,
    streamId: entry?.streamId ?? null,
    seq: entry?.seq ?? null,
    context: recording?.context ?? { commandId: null, sessionId: null, workspaceId: null },
    package: recording?.input?.package ?? null,
    sourceLocation: recording?.input?.sourceLocation ?? null,
    jobId: recording?.jobId ?? null
  };
}

export function replayAsInput(store, recordingId) {
  const next = store ?? createRecordingStore();
  const recording = resolveRecording(next, recordingId);
  return {
    kind: "recording.replay",
    recordingId: recording.id,
    input: { ...(recording.input ?? {}) },
    context: { ...(recording.context ?? {}) }
  };
}

export function reRunRecording(store, recordingId, options = {}) {
  const replay = replayAsInput(store, recordingId);
  return {
    kind: "recording.rerun",
    recordingId: replay.recordingId,
    commandId: options.commandId ?? replay.context.commandId ?? "repl.eval",
    payload: {
      input: replay.input,
      context: {
        ...replay.context,
        sourceRecordingId: replay.recordingId
      }
    }
  };
}
