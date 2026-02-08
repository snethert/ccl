import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function readSpec(relPath) {
  const fullPath = path.resolve(__dirname, "..", "..", relPath);
  return fs.readFileSync(fullPath, "utf8");
}

function assertContains(content, label, needle) {
  assert.ok(
    content.includes(needle),
    `${label} is missing required section: ${needle}`
  );
}

function assertAll(content, label, needles) {
  for (const needle of needles) {
    assertContains(content, label, needle);
  }
}

test("phase-0 specs are present and include required sections", () => {
  const specs = [
    {
      path: "web-ide/phase-0/output-recording-schema.md",
      required: [
        "## Version",
        "Schema version: `0`",
        "## Purpose",
        "## Goals",
        "## Schema",
        "### Recording",
        "### Recording Entry",
        "### Entry Kinds",
        "## Operations",
        "## Invariants"
      ]
    },
    {
      path: "web-ide/phase-0/presentation-taxonomy.md",
      required: [
        "## Version",
        "Schema version: `0`",
        "## Core Types and Required Metadata",
        "### value",
        "### symbol",
        "### definition",
        "### command",
        "### frame",
        "### binding",
        "### place",
        "### condition-section",
        "### restart",
        "### doc",
        "### location"
      ]
    },
    {
      path: "web-ide/phase-0/typed-command-model.md",
      required: [
        "## Version",
        "Schema version: `0`",
        "## Command Schema",
        "### Argument Types",
        "### Argument Schema",
        "## Invocation Model",
        "## Command History",
        "## Execution Pipeline"
      ]
    },
    {
      path: "web-ide/phase-0/editor-decision-memo.md",
      required: [
        "## Recommendation (Final)",
        "Runtime selected: CodeMirror 6.",
        "## Candidates",
        "## Evaluation Criteria",
        "## Recommendation",
        "## Spike Plan",
        "## Exit Criteria"
      ]
    },
    {
      path: "web-ide/phase-0/world-state-and-sessions.md",
      required: [
        "## Staleness and Revalidation",
        "### Revalidation Rules",
        "## Session Restore",
        "## Persistence Requirements"
      ]
    },
    {
      path: "web-ide/phase-0/theme-and-motion-contract.md",
      required: [
        "## Theme Tokens",
        "### Core Tokens",
        "## Motion Contract",
        "## Renderer Requirements"
      ]
    },
    {
      path: "web-ide/phase-0/restart-and-condition-contract.md",
      required: [
        "## Restart Schema",
        "### Safety Levels",
        "## Presentation Integration"
      ]
    },
    {
      path: "web-ide/phase-0/selection-and-action-model.md",
      required: [
        "## Action Bar Model",
        "### Example Multi-Select Actions",
        "## Command Integration"
      ]
    }
  ];

  for (const spec of specs) {
    const content = readSpec(spec.path);
    assertAll(content, spec.path, spec.required);
  }
});
