import { test } from "node:test";
import assert from "node:assert/strict";

import {
  OUTPUT_RECORDING_SCHEMA_VERSION,
  normalizeRecording,
  normalizeEntry,
  createRecordingStore,
  appendRecording,
  appendEntry,
  attachAnchor,
  setEntryFolded,
  copyAsForm,
  copyWithContext,
  replayAsInput,
  reRunRecording
} from "../src/recordings.mjs";

test("normalizeRecording applies defaults", () => {
  const recording = normalizeRecording({ id: "rec-1" });
  assert.equal(recording.id, "rec-1");
  assert.equal(recording.status, "ok");
  assert.equal(recording.streamId, "repl");
  assert.equal(recording.input.kind, "unknown");
  assert.deepEqual(recording.entryIds, []);
});

test("normalizeEntry applies defaults", () => {
  const entry = normalizeEntry({ id: "ent-1" });
  assert.equal(entry.id, "ent-1");
  assert.equal(entry.kind, "text");
  assert.equal(entry.streamId, "stdout");
  assert.equal(entry.text, "");
});

test("appendRecording and appendEntry build indexes", () => {
  const store = createRecordingStore();
  const withRecording = appendRecording(store, { id: "rec-1" });
  const withEntry = appendEntry(withRecording, {
    id: "ent-1",
    recordingId: "rec-1",
    seq: 12,
    anchorId: "anc-1",
    presentationId: "pres-1"
  });
  assert.deepEqual(withEntry.recordingOrder, ["rec-1"]);
  assert.deepEqual(withEntry.entryOrder, ["ent-1"]);
  assert.equal(withEntry.byAnchor["anc-1"].entryId, "ent-1");
  assert.equal(withEntry.byPresentation["pres-1"], "ent-1");
  assert.deepEqual(withEntry.recordings["rec-1"].entryIds, ["ent-1"]);
  assert.equal(withEntry.recordings["rec-1"].seqStart, 12);
  assert.equal(withEntry.recordings["rec-1"].seqEnd, 12);
});

test("attachAnchor stores anchor and index", () => {
  let store = createRecordingStore();
  store = appendRecording(store, { id: "rec-1" });
  store = appendEntry(store, { id: "ent-1", recordingId: "rec-1" });
  const next = attachAnchor(store, {
    id: "anc-1",
    entryId: "ent-1",
    range: { start: 0, end: 4 },
    path: ["a", "b"]
  });
  assert.equal(next.anchors["anc-1"].entryId, "ent-1");
  assert.equal(next.byAnchor["anc-1"].range.start, 0);
  assert.equal(next.entries["ent-1"].anchorId, "anc-1");
});

test("setEntryFolded toggles entry metadata", () => {
  let store = createRecordingStore();
  store = appendRecording(store, { id: "rec-1" });
  store = appendEntry(store, { id: "ent-1", recordingId: "rec-1" });
  const folded = setEntryFolded(store, "ent-1", true);
  assert.equal(folded.entries["ent-1"].metadata.folded, true);
});

test("output recording schema version is allocated", () => {
  assert.equal(OUTPUT_RECORDING_SCHEMA_VERSION, "0");
});

test("copyAsForm and copyWithContext resolve entry and anchor targets", () => {
  let store = createRecordingStore();
  store = appendRecording(store, {
    id: "rec-1",
    input: {
      kind: "form",
      text: "(+ 1 2)",
      package: "CL-USER",
      sourceLocation: { file: "demo.lisp", line: 1, column: 1 }
    },
    context: { commandId: "repl.eval", sessionId: "s-1", workspaceId: "w-1" }
  });
  store = appendEntry(store, {
    id: "ent-1",
    recordingId: "rec-1",
    text: "(+ 1 2)",
    anchorId: "anc-1",
    seq: 12,
    streamId: "stdout"
  });
  store = attachAnchor(store, { id: "anc-1", entryId: "ent-1", range: { start: 0, end: 7 }, path: [] });

  const copied = copyAsForm(store, "anc-1");
  assert.equal(copied.text, "(+ 1 2)");
  assert.equal(copied.entryId, "ent-1");

  const contextual = copyWithContext(store, { entryId: "ent-1" });
  assert.equal(contextual.text, "(+ 1 2)");
  assert.equal(contextual.package, "CL-USER");
  assert.equal(contextual.context.commandId, "repl.eval");
  assert.equal(contextual.seq, 12);
});

test("replayAsInput and reRunRecording produce deterministic rerun payloads", () => {
  let store = createRecordingStore();
  store = appendRecording(store, {
    id: "rec-1",
    context: { commandId: "repl.eval", sessionId: "s-1", workspaceId: "w-1" },
    input: { kind: "form", text: "(foo 9)", package: "CL-USER" }
  });

  const replay = replayAsInput(store, "rec-1");
  assert.equal(replay.kind, "recording.replay");
  assert.equal(replay.input.text, "(foo 9)");

  const rerun = reRunRecording(store, "rec-1");
  assert.equal(rerun.kind, "recording.rerun");
  assert.equal(rerun.commandId, "repl.eval");
  assert.equal(rerun.payload.context.sourceRecordingId, "rec-1");
});

test("appendEntry enforces recording invariants", () => {
  const store = appendRecording(createRecordingStore(), { id: "rec-1" });
  assert.throws(() => appendEntry(store, { id: "ent-missing-recording" }), /recordingId is required/);
  assert.throws(
    () => appendEntry(store, { id: "ent-unknown-recording", recordingId: "rec-missing" }),
    /Recording not found/
  );
});

test("appendEntry enforces increasing seq per stream when seq is provided", () => {
  let store = createRecordingStore();
  store = appendRecording(store, { id: "rec-1" });
  store = appendEntry(store, { id: "ent-1", recordingId: "rec-1", streamId: "stdout", seq: 10 });
  store = appendEntry(store, { id: "ent-2", recordingId: "rec-1", streamId: "stderr", seq: 3 });
  assert.throws(
    () => appendEntry(store, { id: "ent-3", recordingId: "rec-1", streamId: "stdout", seq: 10 }),
    /must increase/
  );
  assert.throws(
    () => appendEntry(store, { id: "ent-4", recordingId: "rec-1", streamId: "stdout", seq: 9 }),
    /must increase/
  );
});

test("attachAnchor validates entry and canonicalizes invalid ranges", () => {
  let store = createRecordingStore();
  store = appendRecording(store, { id: "rec-1" });
  store = appendEntry(store, { id: "ent-1", recordingId: "rec-1" });
  assert.throws(
    () => attachAnchor(store, { id: "anc-missing", entryId: "ent-missing" }),
    /Entry not found/
  );
  const anchored = attachAnchor(store, {
    id: "anc-1",
    entryId: "ent-1",
    range: { start: 9, end: 4 },
    path: ["ok", { ignored: true }, 2]
  });
  assert.equal(anchored.anchors["anc-1"].range, null);
  assert.deepEqual(anchored.anchors["anc-1"].path, ["ok", 2]);
});

test("normalizeRecording input kind supports file and command", () => {
  const fileRecording = normalizeRecording({
    id: "rec-file",
    input: { kind: "file", text: "src/demo.lisp" }
  });
  const commandRecording = normalizeRecording({
    id: "rec-command",
    input: { kind: "command", text: "compile-file" }
  });
  const unknownRecording = normalizeRecording({
    id: "rec-unknown",
    input: { kind: "cell", text: "(+ 1 2)" }
  });
  assert.equal(fileRecording.input.kind, "file");
  assert.equal(commandRecording.input.kind, "command");
  assert.equal(unknownRecording.input.kind, "unknown");
});
