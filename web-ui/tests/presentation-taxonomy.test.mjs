import { test } from "node:test";
import assert from "node:assert/strict";

import {
  PRESENTATION_TAXONOMY_VERSION,
  normalizePresentationType,
  validatePresentationMetadata,
  applyPresentationDefaults
} from "../src/presentation-taxonomy.mjs";

test("presentation taxonomy version is allocated", () => {
  assert.equal(PRESENTATION_TAXONOMY_VERSION, "0");
});

test("normalizePresentationType falls back to value", () => {
  assert.equal(normalizePresentationType("unknown"), "value");
  assert.equal(normalizePresentationType(null), "value");
});

test("validatePresentationMetadata reports missing required fields", () => {
  const result = validatePresentationMetadata({ type: "symbol", metadata: { name: "FOO" } });
  assert.equal(result.ok, false);
  assert.deepEqual(result.missing, ["package"]);
});

test("applyPresentationDefaults sets type and metadata", () => {
  const next = applyPresentationDefaults({ presentationType: "frame" });
  assert.equal(next.type, "frame");
  assert.deepEqual(next.metadata, {});
});
