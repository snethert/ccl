import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { createState, setThemeMode } from "../src/state.mjs";
import { stableStringify } from "./snapshot.mjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");
const thisTestPath = "web-ui/tests/phase-7-ui-conformance-fixtures.test.mjs";

function readSpecJson(relPath) {
  const fullPath = path.resolve(repoRoot, relPath);
  return JSON.parse(fs.readFileSync(fullPath, "utf8"));
}

function readSpecText(relPath) {
  const fullPath = path.resolve(repoRoot, relPath);
  return fs.readFileSync(fullPath, "utf8");
}

function colorLuminance(color) {
  const toLinear = (channel) => {
    const value = channel / 255;
    if (value <= 0.03928) return value / 12.92;
    return ((value + 0.055) / 1.055) ** 2.4;
  };
  return (
    0.2126 * toLinear(color.r) +
    0.7152 * toLinear(color.g) +
    0.0722 * toLinear(color.b)
  );
}

function contrastRatio(foreground, background) {
  const l1 = colorLuminance(foreground);
  const l2 = colorLuminance(background);
  const light = Math.max(l1, l2);
  const dark = Math.min(l1, l2);
  return (light + 0.05) / (dark + 0.05);
}

function fixtureById(fixtures, id) {
  const fixture = fixtures.find((entry) => entry.id === id);
  assert.ok(fixture, `missing fixture: ${id}`);
  return fixture;
}

function assertionById(fixture, id) {
  const assertion = (fixture.assertions ?? []).find((entry) => entry.id === id);
  assert.ok(assertion, `${fixture.id} missing assertion: ${id}`);
  return assertion;
}

test("required conformance fixtures are bound to executable tests", () => {
  const fixtureSpec = readSpecJson("web-ui/spec/ui-conformance-fixtures-v1.json");
  const required = fixtureSpec.fixtures.filter((fixture) => fixture.status === "required");
  assert.ok(required.length > 0, "expected required fixtures");

  for (const fixture of required) {
    assert.ok(
      Array.isArray(fixture.existingTests) && fixture.existingTests.length > 0,
      `${fixture.id} must bind at least one test`
    );
    for (const relPath of fixture.existingTests) {
      const resolved = path.resolve(repoRoot, relPath);
      assert.equal(fs.existsSync(resolved), true, `${fixture.id} bound test missing: ${relPath}`);
    }
  }
});

test("critical fixtures previously unbound now include explicit bound tests", () => {
  const fixtureSpec = readSpecJson("web-ui/spec/ui-conformance-fixtures-v1.json");
  const ids = [
    "vis.component.state-matrix.v1",
    "vis.selection.contrast.v1",
    "motion.class-timing.v1",
    "motion.interrupt-determinism.v1"
  ];
  for (const id of ids) {
    const fixture = fixtureById(fixtureSpec.fixtures, id);
    assert.equal(fixture.existingTests.includes(thisTestPath), true, `${id} must bind ${thisTestPath}`);
  }
});

test("high-contrast and forced-colors lanes are modeled in tokens and fixture execution profile", () => {
  const tokenSpec = readSpecJson("web-ui/spec/ui-visual-tokens-v1.json");
  const fixtureSpec = readSpecJson("web-ui/spec/ui-conformance-fixtures-v1.json");

  const tokenModes = Object.keys(tokenSpec.modes ?? {});
  for (const mode of ["dark", "light", "high-contrast", "forced-colors"]) {
    assert.equal(tokenModes.includes(mode), true, `token mode missing: ${mode}`);
    assert.equal(
      (fixtureSpec.executionProfile?.modes ?? []).includes(mode),
      true,
      `execution profile mode missing: ${mode}`
    );
  }

  const forcedColorsFixture = fixtureById(
    fixtureSpec.fixtures,
    "a11y.high-contrast.forced-colors.v1"
  );
  assert.deepEqual(forcedColorsFixture.modeLanes, ["high-contrast", "forced-colors"]);
});

test("high-contrast and forced-colors tokens satisfy minimum contrast baselines", () => {
  const tokenSpec = readSpecJson("web-ui/spec/ui-visual-tokens-v1.json");
  const highContrast = tokenSpec.modes?.["high-contrast"]?.color;
  const forcedColors = tokenSpec.modes?.["forced-colors"]?.color;

  assert.ok(highContrast, "missing high-contrast mode");
  assert.ok(forcedColors, "missing forced-colors mode");

  assert.ok(
    contrastRatio(highContrast.textPrimary, highContrast.bg) >= 7,
    "high-contrast textPrimary/bg must meet >=7:1"
  );
  assert.ok(
    contrastRatio(highContrast.selectionText, highContrast.selection) >= 4.5,
    "high-contrast selectionText/selection must meet >=4.5:1"
  );
  assert.ok(
    contrastRatio(forcedColors.focus, forcedColors.surface) >= 3,
    "forced-colors focus/surface must meet >=3:1"
  );
  assert.ok(
    contrastRatio(forcedColors.border, forcedColors.surface) >= 3,
    "forced-colors border/surface must meet >=3:1"
  );
});

test("runner contract defines harness semantics and schema lane compatibility", () => {
  const runnerContract = readSpecText("web-ui/spec/ui-conformance-runner-contract-v1.md");
  const reportSchema = readSpecJson("web-ui/spec/ui-conformance-report-schema-v1.json");
  const fixtureSpec = readSpecJson("web-ui/spec/ui-conformance-fixtures-v1.json");

  for (const harness of ["snapshot", "geometry", "contrast", "parity", "timing", "replay", "keyboard"]) {
    assert.equal(runnerContract.includes(`\`${harness}\``), true, `runner contract missing harness: ${harness}`);
  }
  assert.equal(
    runnerContract.includes("ui-conformance-report-schema-v1.json"),
    true,
    "runner contract must reference report schema"
  );
  assert.equal(
    runnerContract.includes("parityBackendPairs"),
    true,
    "runner contract must define parityBackendPairs semantics"
  );

  const modeEnum = reportSchema.properties?.env?.properties?.mode?.enum ?? [];
  for (const mode of [...(fixtureSpec.executionProfile?.modes ?? []), "mixed"]) {
    assert.equal(modeEnum.includes(mode), true, `report schema env.mode missing: ${mode}`);
  }
});

test("parity fixtures declare explicit backend pair scopes", () => {
  const fixtureSpec = readSpecJson("web-ui/spec/ui-conformance-fixtures-v1.json");

  const domCanvasFixture = fixtureById(fixtureSpec.fixtures, "parity.dom-canvas.visual.v1");
  assert.deepEqual(domCanvasFixture.parityBackendPairs, [["dom", "canvas"]]);
  assert.deepEqual(domCanvasFixture.backendLanes, ["dom", "canvas"]);

  const domWebGlFixture = fixtureById(fixtureSpec.fixtures, "parity.dom-webgl.visual.v1");
  assert.deepEqual(domWebGlFixture.parityBackendPairs, [["dom", "webgl"]]);
  assert.deepEqual(domWebGlFixture.backendLanes, ["dom", "webgl"]);

  const a11yProxyParity = fixtureById(fixtureSpec.fixtures, "a11y.proxy-parity.v1");
  assert.deepEqual(a11yProxyParity.parityBackendPairs, [["canvas", "webgl"]]);
  assert.deepEqual(a11yProxyParity.backendLanes, ["canvas", "webgl"]);
});

test("responsive viewport lanes and touch target requirements are explicitly specified", () => {
  const fixtureSpec = readSpecJson("web-ui/spec/ui-conformance-fixtures-v1.json");
  const fixtureCatalog = readSpecText("web-ui/spec/ui-conformance-fixture-catalog-v1.md");
  const componentContract = readSpecText("web-ui/spec/ui-component-visual-contract-v1.md");

  const viewportIds = (fixtureSpec.executionProfile?.viewports ?? []).map((entry) => entry.id);
  assert.equal(viewportIds.includes("desktop-lg"), true);
  assert.equal(viewportIds.includes("tablet"), true);
  assert.equal(viewportIds.includes("mobile"), true);

  assert.equal(fixtureSpec.executionProfile?.touchTargets?.minHitSizePx >= 44, true);

  const responsiveFixture = fixtureById(fixtureSpec.fixtures, "vis.responsive.touch-targets.v1");
  assert.equal(responsiveFixture.status, "required");
  assert.equal(responsiveFixture.existingTests.includes(thisTestPath), true);
  assert.equal(
    assertionById(responsiveFixture, "coarse-pointer-hit-target-min").target >= 44,
    true
  );

  assert.equal(fixtureCatalog.includes("desktop-lg"), true);
  assert.equal(fixtureCatalog.includes("tablet"), true);
  assert.equal(fixtureCatalog.includes("mobile"), true);
  assert.equal(fixtureCatalog.includes(">=44x44"), true);

  assert.equal(componentContract.includes("coarse-pointer lanes"), true);
  assert.equal(componentContract.includes(">=44x44px"), true);
  assert.equal(componentContract.includes("Min height (fine pointer lanes): `32px`"), true);
});

test("vis.component.state-matrix.v1 defines required state coverage targets", () => {
  const fixtureSpec = readSpecJson("web-ui/spec/ui-conformance-fixtures-v1.json");
  const fixture = fixtureById(fixtureSpec.fixtures, "vis.component.state-matrix.v1");

  assert.equal(assertionById(fixture, "button-states").target, 6);
  assert.equal(assertionById(fixture, "input-states").target, 6);
  assert.equal(assertionById(fixture, "list-row-states").target, 7);
  assert.equal(fixture.requiredHarness, "snapshot");
});

test("vis.selection.contrast.v1 aligns with multi-mode token contrast expectations", () => {
  const fixtureSpec = readSpecJson("web-ui/spec/ui-conformance-fixtures-v1.json");
  const tokenSpec = readSpecJson("web-ui/spec/ui-visual-tokens-v1.json");
  const fixture = fixtureById(fixtureSpec.fixtures, "vis.selection.contrast.v1");

  const textContrastMin = assertionById(fixture, "selection-text-contrast").target;
  const boundaryContrastMin = assertionById(fixture, "selection-boundary-contrast").target;
  for (const mode of fixtureSpec.executionProfile?.modes ?? []) {
    const color = tokenSpec.modes?.[mode]?.color;
    assert.ok(color, `missing token colors for mode: ${mode}`);
    assert.ok(
      contrastRatio(color.selectionText, color.selection) >= textContrastMin,
      `${mode} selection text contrast below fixture threshold`
    );
    const boundaryRatio = Math.max(
      contrastRatio(color.selection, color.surface),
      contrastRatio(color.border, color.surface)
    );
    assert.ok(
      boundaryRatio >= boundaryContrastMin,
      `${mode} selection boundary contrast below fixture threshold`
    );
  }
});

test("motion.class-timing.v1 stays within approved duration bounds", () => {
  const fixtureSpec = readSpecJson("web-ui/spec/ui-conformance-fixtures-v1.json");
  const tokenSpec = readSpecJson("web-ui/spec/ui-visual-tokens-v1.json");
  const fixture = fixtureById(fixtureSpec.fixtures, "motion.class-timing.v1");
  const durations = tokenSpec.motion?.durationMs ?? {};

  const fastTarget = assertionById(fixture, "inline-state-fast").target;
  const normalTarget = assertionById(fixture, "surface-enter-normal").target;
  const maxTarget = assertionById(fixture, "max-duration").target;

  assert.ok(durations.fast <= fastTarget, `fast duration ${durations.fast} exceeds ${fastTarget}`);
  assert.ok(
    durations.normal <= normalTarget,
    `normal duration ${durations.normal} exceeds ${normalTarget}`
  );
  assert.ok(durations.slow <= maxTarget, `slow duration ${durations.slow} exceeds ${maxTarget}`);
});

test("motion.interrupt-determinism.v1 maps to deterministic last-writer-wins state outcomes", () => {
  const fixtureSpec = readSpecJson("web-ui/spec/ui-conformance-fixtures-v1.json");
  const fixture = fixtureById(fixtureSpec.fixtures, "motion.interrupt-determinism.v1");

  assert.equal(assertionById(fixture, "interrupted-end-state-deterministic").target, "repeatable");
  assert.equal(assertionById(fixture, "concurrent-transition-policy").target, true);

  const modes = ["light", "high-contrast", "dark", "forced-colors"];
  const applySequence = () => {
    let state = createState();
    for (const mode of modes) {
      state = setThemeMode(state, mode);
    }
    return state;
  };

  const runA = applySequence();
  const runB = applySequence();
  assert.equal(stableStringify(runA.theme), stableStringify(runB.theme));
  assert.equal(runA.theme.mode, "forced-colors");
});
