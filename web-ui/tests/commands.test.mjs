import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createRegistry,
  registerCommand,
  bindKey,
  resolveKey,
  commandEnabled,
  executeCommand,
  makeContext
} from "../src/index.mjs";

function makeRegistry() {
  const registry = createRegistry();
  registerCommand(registry, { id: "cmd.global", exec: () => "global" });
  registerCommand(registry, { id: "cmd.task", exec: () => "task" });
  registerCommand(registry, { id: "cmd.context", exec: () => "context" });
  registerCommand(registry, { id: "cmd.widget", exec: () => "widget" });
  bindKey(registry, "global", "K", "cmd.global");
  bindKey(registry, "task", "K", "cmd.task", "task-1");
  bindKey(registry, "context", "K", "cmd.context", "ctx-1");
  bindKey(registry, "widget", "K", "cmd.widget", "widget-1");
  return registry;
}

test("command routing uses deterministic precedence", () => {
  const registry = makeRegistry();
  const ctx = makeContext({ selection: null }, {
    taskId: "task-1",
    contextId: "ctx-1",
    widgetId: "widget-1"
  });
  const resolved = resolveKey(registry, "K", ctx);
  assert.equal(resolved, "cmd.global");
});

test("enablement reasons are returned and enforce dispatch", () => {
  const registry = createRegistry();
  registerCommand(registry, {
    id: "cmd.disabled",
    enabled: () => ({ enabled: false, reason: "No selection" }),
    exec: () => "ran"
  });

  const ctx = makeContext({ selection: null });
  const enabled = commandEnabled(registry, "cmd.disabled", ctx);
  assert.equal(enabled.enabled, false);
  assert.equal(enabled.reason, "No selection");

  const exec = executeCommand(registry, "cmd.disabled", ctx);
  assert.equal(exec.ok, false);
  assert.equal(exec.reason, "No selection");
});

test("namespace policy can enforce namespaced ids", () => {
  const registry = createRegistry({ namespacePolicy: "require-dot" });
  assert.throws(() => registerCommand(registry, { id: "plain" }));
  registerCommand(registry, { id: "ns.command" });
});
