import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createRegistry,
  executeCommand,
  createState,
  registerCapabilityCommands,
  CAPABILITY_REQUEST_COMMAND,
  CAPABILITY_GRANT_COMMAND,
  CAPABILITY_REVOKE_COMMAND,
  SAFE_MODE_ENABLE_COMMAND,
  SAFE_MODE_DISABLE_COMMAND,
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
