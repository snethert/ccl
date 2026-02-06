import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createRegistry,
  registerCommand,
  bindKey,
  resolveKey,
  resolveKeyWithTrace,
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

test("custom precedence allows widget/context to win", () => {
  const registry = createRegistry(["widget", "context", "task", "global"]);
  registerCommand(registry, { id: "cmd.global" });
  registerCommand(registry, { id: "cmd.task" });
  registerCommand(registry, { id: "cmd.context" });
  registerCommand(registry, { id: "cmd.widget" });
  bindKey(registry, "global", "K", "cmd.global");
  bindKey(registry, "task", "K", "cmd.task", "task-1");
  bindKey(registry, "context", "K", "cmd.context", "ctx-1");
  bindKey(registry, "widget", "K", "cmd.widget", "widget-1");

  const ctx = makeContext({ selection: null }, {
    taskId: "task-1",
    contextId: "ctx-1",
    widgetId: "widget-1"
  });
  const resolved = resolveKey(registry, "K", ctx);
  assert.equal(resolved, "cmd.widget");

  const trace = resolveKeyWithTrace(registry, "K", ctx);
  assert.equal(trace.commandId, "cmd.widget");
  assert.equal(trace.trace.length, 1);
  assert.deepEqual(trace.trace[0], {
    scope: "widget",
    scopeId: "widget-1",
    key: "K",
    commandId: "cmd.widget",
    matched: true,
    reason: null
  });

  const contextOnly = makeContext({ selection: null }, {
    taskId: "task-1",
    contextId: "ctx-1"
  });
  const fallthrough = resolveKeyWithTrace(registry, "K", contextOnly);
  assert.equal(fallthrough.commandId, "cmd.context");
  assert.equal(fallthrough.trace.length, 2);
  assert.equal(fallthrough.trace[0].scope, "widget");
  assert.equal(fallthrough.trace[0].reason, "missing-scope-id");
  assert.equal(fallthrough.trace[1].scope, "context");
  assert.equal(fallthrough.trace[1].matched, true);
});

test("resolveKeyWithTrace exposes scope decisions", () => {
  const registry = makeRegistry();
  const ctx = makeContext({ selection: null }, {
    taskId: "task-1",
    contextId: "ctx-1",
    widgetId: "widget-1"
  });
  const resolved = resolveKeyWithTrace(registry, "K", ctx);
  assert.equal(resolved.commandId, "cmd.global");
  assert.equal(resolved.trace.length, 1);
  assert.deepEqual(resolved.trace[0], {
    scope: "global",
    scopeId: null,
    key: "K",
    commandId: "cmd.global",
    matched: true,
    reason: null
  });

  const miss = resolveKeyWithTrace(registry, "Z", ctx);
  assert.equal(miss.commandId, null);
  assert.equal(miss.trace.length, registry.precedence.length);
  assert.equal(miss.trace[0].scope, "global");
  assert.equal(miss.trace[0].matched, false);
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
