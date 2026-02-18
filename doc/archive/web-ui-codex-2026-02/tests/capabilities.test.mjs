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
  CAPABILITY_APPROVE_COMMAND,
  CAPABILITY_DENY_COMMAND,
  CAPABILITY_AUTO_RUN_COMMAND,
  SAFE_MODE_ENABLE_COMMAND,
  SAFE_MODE_DISABLE_COMMAND,
  DOM_ESCAPE_COMMAND,
  makeContext
} from "../src/index.mjs";

test("capability requests can be approved or denied", () => {
  const registry = createRegistry();
  registerCapabilityCommands(registry);

  let state = createState();
  let ctx = makeContext(state);

  let result = executeCommand(registry, CAPABILITY_REQUEST_COMMAND, { ...ctx, capability: "dom.escape" });
  assert.equal(result.ok, true);
  state = result.result;
  assert.equal(state.capabilities.log.length, 1);
  assert.equal(state.capabilities.log[0].action, "request");
  assert.equal(state.capabilityRequests.length, 1);
  assert.equal(state.capabilityRequests[0].status, "pending");

  ctx = makeContext(state);
  result = executeCommand(registry, CAPABILITY_APPROVE_COMMAND, {
    ...ctx,
    requestId: state.capabilityRequests[0].id
  });
  assert.equal(result.ok, true);
  state = result.result;
  assert.deepEqual(state.capabilities.granted, ["dom.escape"]);
  assert.equal(state.capabilityRequests[0].status, "granted");
  assert.equal(state.capabilities.log[1].action, "grant");

  ctx = makeContext(state);
  result = executeCommand(registry, CAPABILITY_REQUEST_COMMAND, { ...ctx, capability: "dom.window" });
  assert.equal(result.ok, true);
  state = result.result;

  ctx = makeContext(state);
  result = executeCommand(registry, CAPABILITY_DENY_COMMAND, {
    ...ctx,
    requestId: state.capabilityRequests[1].id
  });
  assert.equal(result.ok, true);
  state = result.result;
  assert.equal(state.capabilityRequests[1].status, "denied");

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

test("auto-run applies capability policy decisions", () => {
  const registry = createRegistry();
  registerCapabilityCommands(registry);

  let state = createState({ capabilityPolicy: { defaultDecision: "grant" } });
  let ctx = makeContext(state);
  state = executeCommand(registry, CAPABILITY_REQUEST_COMMAND, { ...ctx, capability: "dom.escape" }).result;
  ctx = makeContext(state);
  const autoRun = executeCommand(registry, CAPABILITY_AUTO_RUN_COMMAND, ctx);
  assert.equal(autoRun.ok, true);
  state = autoRun.result;
  assert.equal(state.capabilityRequests[0].status, "granted");
  assert.ok(state.capabilities.granted.includes("dom.escape"));
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
