import { test } from "node:test";
import assert from "node:assert/strict";

import {
  TYPED_COMMAND_MODEL_VERSION,
  normalizeArgSpec,
  normalizeCommandSpec,
  validateInvocation,
  resolveArgumentDefaults,
  materializeInvocation,
  executeTypedCommand
} from "../src/typed-commands.mjs";

test("normalizeArgSpec defaults type and required", () => {
  const arg = normalizeArgSpec({ name: "symbol" });
  assert.equal(arg.type, "string");
  assert.equal(arg.required, false);
});

test("normalizeCommandSpec normalizes args", () => {
  const spec = normalizeCommandSpec({ id: "x.y", args: [{ name: "target", type: "symbol", required: true }] });
  assert.equal(spec.id, "x.y");
  assert.equal(spec.args[0].type, "symbol");
  assert.equal(spec.args[0].required, true);
});

test("validateInvocation detects missing required args", () => {
  const spec = { id: "do.thing", args: [{ name: "target", type: "symbol", required: true }] };
  const result = validateInvocation({ id: "inv-1", commandId: "do.thing", args: {} }, spec);
  assert.equal(result.ok, false);
  assert.deepEqual(result.missing, ["target"]);
});

test("typed command model version is allocated", () => {
  assert.equal(TYPED_COMMAND_MODEL_VERSION, "0");
});

test("resolveArgumentDefaults applies DWIM defaults from context", () => {
  const spec = {
    id: "editor.goto-definition",
    args: [
      { name: "selection", type: "selection", required: true, defaultFrom: ["selection"] },
      { name: "package", type: "package", required: true, defaultFrom: ["package"] }
    ]
  };
  const ctx = {
    selection: { id: "sel-1", targetIds: ["pres-1"] },
    transcriptContext: { package: "CL-USER" }
  };
  const resolved = resolveArgumentDefaults(spec, {}, ctx);
  assert.equal(resolved.missing.length, 0);
  assert.equal(resolved.args.selection.id, "sel-1");
  assert.equal(resolved.args.package, "CL-USER");
  assert.equal(resolved.defaults.selection.source, "selection");
  assert.equal(resolved.defaults.package.source, "package");
});

test("materializeInvocation merges defaults and args", () => {
  const spec = {
    id: "doc.open",
    args: [{ name: "target", type: "presentation", required: true, defaultFrom: ["presentation"] }]
  };
  const invocation = { id: "inv-1", commandId: "doc.open", args: {} };
  const ctx = { presentation: { id: "pres-7", type: "doc" } };
  const materialized = materializeInvocation(spec, invocation, ctx);
  assert.equal(materialized.invocation.commandId, "doc.open");
  assert.equal(materialized.invocation.args.target.id, "pres-7");
  assert.equal(materialized.missing.length, 0);
});

test("executeTypedCommand runs execution pipeline", () => {
  const spec = {
    id: "test.echo",
    args: [{ name: "value", type: "string", required: true }],
    exec: ({ args }) => ({ echoed: args.value })
  };
  const result = executeTypedCommand(spec, {
    id: "inv-2",
    commandId: "test.echo",
    args: { value: "ok" }
  });
  assert.equal(result.ok, true);
  assert.deepEqual(result.result, { echoed: "ok" });
  assert.deepEqual(result.invocation.result, { echoed: "ok" });
});
