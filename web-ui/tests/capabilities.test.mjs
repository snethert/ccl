import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createRegistry,
  executeCommand,
  createState,
  registerCapabilityCommands,
  registerDomEscapeCommands,
  CAPABILITY_REQUEST_COMMAND,
  CAPABILITY_GRANT_COMMAND,
  CAPABILITY_REVOKE_COMMAND,
  SAFE_MODE_ENABLE_COMMAND,
  SAFE_MODE_DISABLE_COMMAND,
  DOM_ESCAPE_COMMAND,
  makeContext
} from "../src/index.mjs";

test("capability commands mutate state and log", () => {
  const registry = createRegistry();
  registerCapabilityCommands(registry);

  let state = createState();
  let ctx = makeContext(state);

  let result = executeCommand(registry, CAPABILITY_REQUEST_COMMAND, { ...ctx, capability: "dom.escape" });
  assert.equal(result.ok, true);
  state = result.result;
  assert.equal(state.capabilities.log.length, 1);
  assert.equal(state.capabilities.log[0].action, "request");

  ctx = makeContext(state);
  result = executeCommand(registry, CAPABILITY_GRANT_COMMAND, { ...ctx, capability: "dom.escape" });
  assert.equal(result.ok, true);
  state = result.result;
  assert.deepEqual(state.capabilities.granted, ["dom.escape"]);
  assert.equal(state.capabilities.log[1].action, "grant");

  ctx = makeContext(state);
  result = executeCommand(registry, SAFE_MODE_ENABLE_COMMAND, ctx);
  assert.equal(result.ok, true);
  state = result.result;
  assert.equal(state.capabilities.safeMode, true);

  ctx = makeContext(state);
  result = executeCommand(registry, SAFE_MODE_DISABLE_COMMAND, ctx);
  assert.equal(result.ok, true);
  state = result.result;
  assert.equal(state.capabilities.safeMode, false);

  ctx = makeContext(state);
  result = executeCommand(registry, CAPABILITY_REVOKE_COMMAND, { ...ctx, capability: "dom.escape" });
  assert.equal(result.ok, true);
  state = result.result;
  assert.deepEqual(state.capabilities.granted, []);
});

test("dom escape command is capability-gated and logged", () => {
  const registry = createRegistry();
  registerCapabilityCommands(registry);
  registerDomEscapeCommands(registry);

  let state = createState();
  let ctx = makeContext(state);

  let blocked = executeCommand(registry, DOM_ESCAPE_COMMAND, {
    ...ctx,
    target: "#root",
    detail: { reason: "probe" }
  });
  assert.equal(blocked.ok, false);
  assert.equal(blocked.reason, "Missing capability: dom.escape");

  state = executeCommand(registry, CAPABILITY_GRANT_COMMAND, {
    ...ctx,
    capability: "dom.escape"
  }).result;
  ctx = makeContext(state);

  const allowed = executeCommand(registry, DOM_ESCAPE_COMMAND, {
    ...ctx,
    target: "#root",
    detail: { reason: "probe" }
  });
  assert.equal(allowed.ok, true);
  state = allowed.result;
  assert.equal(state.domEscapes.length, 1);
  assert.equal(state.domEscapes[0].target, "#root");
});
