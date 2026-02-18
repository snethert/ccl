import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const webUiRoot = path.resolve(__dirname, "..");
const specRoot = path.join(webUiRoot, "spec");
const registerPath = path.join(webUiRoot, "PRODUCTION-SPEC-GAP-REGISTER.md");
const requirementsPath = path.join(specRoot, "requirements-index-v1.json");
const evidencePath = path.join(specRoot, "conformance-evidence-index-v1.json");

const START_MARKER = "<!-- AUTO-GENERATED-GATE-STATUS:START -->";
const END_MARKER = "<!-- AUTO-GENERATED-GATE-STATUS:END -->";

// Keep this list in lockstep with the active blocker table in:
// web-ui/spec/conformance-gate-profiles-v1.md (Section 3).
const GATE_DEFINITIONS = [
  {
    gate_id: "gate.conformance.lint.v1",
    command: "node scripts/lint-conformance.mjs --json",
    severity: "blocker",
    scopes: ["full-runtime-v1"]
  },
  {
    gate_id: "gate.tests.fast.v1",
    command: "npm run -s test:gate:fast",
    severity: "blocker",
    scopes: ["full-runtime-v1"]
  },
  {
    gate_id: "gate.runtime.bridge.v1",
    command: "node --test tests/bridge-microkernel.test.mjs tests/phase-5-runtime-output.test.mjs tests/phase-5-runtime-command-roundtrip.test.mjs tests/phase-5-runtime-command-dispatch.test.mjs tests/phase-5-runtime-inspector-integration.test.mjs tests/phase-5-runtime-restart-invoke.test.mjs",
    severity: "blocker",
    scopes: ["full-runtime-v1"]
  },
  {
    gate_id: "gate.browser.render-only.v1",
    command: "npm run -s test:browser:render",
    severity: "blocker",
    scopes: ["full-runtime-v1"]
  },
  {
    gate_id: "gate.browser.kernel-preflight.v1",
    command: "npm run -s test:browser:kernel-preflight",
    severity: "blocker",
    scopes: ["full-runtime-v1"]
  },
  {
    gate_id: "gate.browser.kernel-smoke.v1",
    command: "npm run -s test:browser",
    severity: "blocker",
    scopes: ["full-runtime-v1"]
  }
];

const CLAIM_SCOPES = ["full-runtime-v1"];

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function runGate(definition) {
  const startedAt = new Date();
  const startMs = Date.now();
  const result = spawnSync(definition.command, {
    cwd: webUiRoot,
    shell: true,
    encoding: "utf8",
    maxBuffer: 16 * 1024 * 1024
  });
  const durationMs = Date.now() - startMs;

  const stdout = result.stdout ?? "";
  const stderr = result.stderr ?? "";
  const combinedOutput = `${stdout}\n${stderr}`.trim();

  return {
    gate_id: definition.gate_id,
    command: definition.command,
    severity: definition.severity,
    scopes: definition.scopes,
    started_at: startedAt.toISOString(),
    duration_ms: durationMs,
    exit_code: result.status,
    status: result.status === 0 ? "pass" : "fail",
    output_preview: combinedOutput.split(/\r?\n/).slice(-8).join("\n")
  };
}

function summarizeRegistryCoverage(requirementsDocument, evidenceDocument) {
  const requirements = Array.isArray(requirementsDocument.requirements)
    ? requirementsDocument.requirements
    : [];
  const evidence = Array.isArray(evidenceDocument.evidence)
    ? evidenceDocument.evidence
    : [];

  const requirementIds = new Set(requirements.map((entry) => entry.requirement_id));
  const evidenceIds = new Set(evidence.map((entry) => entry.requirement_id));

  const unmappedRequirements = [...requirementIds].filter((id) => !evidenceIds.has(id));
  const staleEvidence = [...evidenceIds].filter((id) => !requirementIds.has(id));

  return {
    requirements_total: requirementIds.size,
    evidence_total: evidenceIds.size,
    artifacts_total: new Set(requirements.map((entry) => entry.artifact)).size,
    unmapped_requirements: unmappedRequirements,
    stale_evidence: staleEvidence
  };
}

function deriveClaims(gateResults, coverage) {
  const resultsByScope = new Map();

  for (const scope of CLAIM_SCOPES) {
    const scopeGates = gateResults.filter((gate) => gate.scopes.includes(scope));
    const blockingFailures = scopeGates
      .filter((gate) => gate.severity === "blocker" && gate.status !== "pass")
      .map((gate) => gate.gate_id);

    if (coverage.unmapped_requirements.length > 0) {
      blockingFailures.push("gate.registry.requirement-coverage.v1");
    }
    if (coverage.stale_evidence.length > 0) {
      blockingFailures.push("gate.registry.evidence-consistency.v1");
    }

    resultsByScope.set(scope, {
      scope,
      status: blockingFailures.length === 0 ? "pass" : "blocked",
      blocking_failures: blockingFailures
    });
  }

  return [...resultsByScope.values()];
}

function formatDurationMs(durationMs) {
  return (durationMs / 1000).toFixed(2);
}

function renderGateStatusMarkdown({ generatedAt, coverage, gateResults, claims }) {
  const coverageRows = [
    `| Requirements indexed | ${coverage.requirements_total} |`,
    `| Evidence mappings | ${coverage.evidence_total} |`,
    `| Requirement artifacts | ${coverage.artifacts_total} |`,
    `| Unmapped requirements | ${coverage.unmapped_requirements.length} |`,
    `| Stale evidence entries | ${coverage.stale_evidence.length} |`
  ].join("\n");

  const gateRows = gateResults
    .map((gate) => {
      const scopes = gate.scopes.map((scope) => `\`${scope}\``).join(", ");
      return `| \`${gate.gate_id}\` | ${scopes} | \`${gate.severity}\` | \`${gate.status}\` | ${formatDurationMs(gate.duration_ms)} | \`${gate.command}\` |`;
    })
    .join("\n");

  const claimRows = claims
    .map((claim) => {
      const failures =
        claim.blocking_failures.length === 0
          ? "none"
          : claim.blocking_failures.map((gateId) => `\`${gateId}\``).join(", ");
      return `| \`${claim.scope}\` | \`${claim.status}\` | ${failures} |`;
    })
    .join("\n");

  const lines = [
    `Generated at: ${generatedAt.toISOString()} (UTC)`,
    "",
    "| Signal | Value |",
    "|---|---:|",
    coverageRows,
    "",
    "| Gate ID | Claim scopes | Severity | Result | Duration (s) | Command |",
    "|---|---|---|---|---:|---|",
    gateRows,
    "",
    "| Claim scope | Verdict | Blocking failures |",
    "|---|---|---|",
    claimRows
  ];

  if (coverage.unmapped_requirements.length > 0) {
    lines.push("");
    lines.push("Unmapped requirements:");
    for (const requirementId of coverage.unmapped_requirements) {
      lines.push(`- \`${requirementId}\``);
    }
  }

  if (coverage.stale_evidence.length > 0) {
    lines.push("");
    lines.push("Stale evidence entries:");
    for (const requirementId of coverage.stale_evidence) {
      lines.push(`- \`${requirementId}\``);
    }
  }

  return lines.join("\n");
}

function updateRegisterSection(markdown) {
  const current = fs.readFileSync(registerPath, "utf8");
  const start = current.indexOf(START_MARKER);
  const end = current.indexOf(END_MARKER);

  if (start === -1 || end === -1 || end < start) {
    throw new Error(
      `Could not locate auto-generated marker block in ${path.relative(webUiRoot, registerPath)}`
    );
  }

  const before = current.slice(0, start + START_MARKER.length);
  const after = current.slice(end);
  const next = `${before}\n${markdown}\n${after}`;
  fs.writeFileSync(registerPath, next);
}

function main() {
  const strict = process.argv.includes("--strict");

  const requirementsDocument = readJson(requirementsPath);
  const evidenceDocument = readJson(evidencePath);
  const coverage = summarizeRegistryCoverage(requirementsDocument, evidenceDocument);

  const gateResults = GATE_DEFINITIONS.map(runGate);
  const claims = deriveClaims(gateResults, coverage);
  const generatedAt = new Date();

  const markdown = renderGateStatusMarkdown({
    generatedAt,
    coverage,
    gateResults,
    claims
  });

  updateRegisterSection(markdown);

  const summary = {
    generated_at: generatedAt.toISOString(),
    requirements_total: coverage.requirements_total,
    evidence_total: coverage.evidence_total,
    unmapped_requirements: coverage.unmapped_requirements.length,
    stale_evidence: coverage.stale_evidence.length,
    claims
  };

  process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);

  const hasBlockedClaim = claims.some((claim) => claim.status !== "pass");
  if (strict && hasBlockedClaim) {
    process.exit(1);
  }
}

main();
