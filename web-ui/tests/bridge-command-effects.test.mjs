import { test } from "node:test";
import assert from "node:assert/strict";

import { createCommandEffectBridge } from "../bridge/command-effects.mjs";

test("createCommandEffectBridge dispatches clipboard and runtime effects", () => {
  let clipboardText = null;
  let runtimeOutput = null;
  const bridge = createCommandEffectBridge({
    writeClipboard: (text) => {
      clipboardText = text;
    },
    dispatchRuntime: (output) => {
      runtimeOutput = output;
    }
  });

  const copyResult = bridge.handle(
    {
      ok: true,
      result: { output: { kind: "form", text: "(+ 1 2)" } }
    },
    { commandId: "repl.recording.copy-as-form" }
  );
  assert.equal(copyResult.handled, true);
  assert.equal(copyResult.channel, "clipboard");
  assert.equal(clipboardText, "(+ 1 2)");

  const replayResult = bridge.handle(
    {
      ok: true,
      result: { output: { kind: "recording.replay", recordingId: "rec-1" } }
    },
    { commandId: "repl.recording.replay-as-input" }
  );
  assert.equal(replayResult.handled, true);
  assert.equal(replayResult.channel, "runtime");
  assert.equal(runtimeOutput.recordingId, "rec-1");

  const restartResult = bridge.handle(
    {
      ok: true,
      result: { output: { kind: "restart.invoke", restartId: "rst-1", errorId: "err-1" } }
    },
    { commandId: "ui.debugger.restart.invoke" }
  );
  assert.equal(restartResult.handled, true);
  assert.equal(restartResult.channel, "runtime");
  assert.equal(runtimeOutput.restartId, "rst-1");
});
