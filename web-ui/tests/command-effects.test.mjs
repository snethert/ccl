import { test } from "node:test";
import assert from "node:assert/strict";

import {
  extractCommandOutput,
  formatClipboardText,
  dispatchCommandOutput,
  handleCommandResultEffects
} from "../src/command-effects.mjs";

test("extractCommandOutput reads structured command output", () => {
  const output = extractCommandOutput({
    ok: true,
    result: { state: {}, output: { kind: "form", text: "(+ 1 2)" } }
  });
  assert.equal(output.kind, "form");
  assert.equal(output.text, "(+ 1 2)");
});

test("formatClipboardText formats form and form+context payloads", () => {
  assert.equal(formatClipboardText({ kind: "form", text: "(foo)" }), "(foo)");
  const contextual = formatClipboardText({
    kind: "form+context",
    text: "(bar)",
    package: "CL-USER",
    recordingId: "rec-1"
  });
  assert.ok(contextual.includes("; package: CL-USER"));
  assert.ok(contextual.includes("; recording: rec-1"));
  assert.ok(contextual.endsWith("(bar)"));
});

test("dispatchCommandOutput routes clipboard and runtime channels", () => {
  let clipboard = null;
  let runtime = null;
  const handlers = {
    clipboardWrite: ({ text }) => {
      clipboard = text;
    },
    runtimeDispatch: ({ output }) => {
      runtime = output;
    }
  };

  const copied = dispatchCommandOutput({ kind: "form", text: "(+ 1 2)" }, handlers);
  assert.equal(copied.handled, true);
  assert.equal(copied.channel, "clipboard");
  assert.equal(clipboard, "(+ 1 2)");

  const replayed = dispatchCommandOutput({ kind: "recording.replay", recordingId: "rec-1" }, handlers);
  assert.equal(replayed.handled, true);
  assert.equal(replayed.channel, "runtime");
  assert.equal(runtime.recordingId, "rec-1");

  const restarted = dispatchCommandOutput(
    { kind: "restart.invoke", restartId: "rst-1", errorId: "err-1" },
    handlers
  );
  assert.equal(restarted.handled, true);
  assert.equal(restarted.channel, "runtime");
  assert.equal(runtime.restartId, "rst-1");

  const sessionSaved = dispatchCommandOutput(
    { kind: "session.save", sessionId: "session-1" },
    handlers
  );
  assert.equal(sessionSaved.handled, true);
  assert.equal(sessionSaved.channel, "runtime");
  assert.equal(runtime.sessionId, "session-1");
});

test("handleCommandResultEffects returns non-handled for commands without output", () => {
  const result = handleCommandResultEffects({ ok: true, result: { state: {} } }, {});
  assert.equal(result.handled, false);
  assert.equal(result.reason, "No command effect output");
});
