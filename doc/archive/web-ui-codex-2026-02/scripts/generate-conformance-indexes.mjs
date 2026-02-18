import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const webUiRoot = path.resolve(__dirname, "..");
const cclRoot = path.resolve(webUiRoot, "..");
const specDir = path.join(webUiRoot, "spec");

const matrixPath = path.join(specDir, "web-ui-conformance-matrix-v1.md");
const requirementsIndexPath = path.join(specDir, "requirements-index-v1.json");
const evidenceIndexPath = path.join(specDir, "conformance-evidence-index-v1.json");

const CURRENT_DATE = "2026-02-17";

const PROFILE_LANES = {
  "governance-base-v1": {
    lane_id: "lane.conformance.lint.v1",
    command: "node ccl/web-ui/scripts/lint-conformance.mjs"
  },
  "ui-visual-v1": {
    lane_id: "lane.ui-visual.v1",
    command: "node --test ccl/web-ui/tests/theme.test.mjs ccl/web-ui/tests/phase-3-ui-doctrine.test.mjs ccl/web-ui/tests/phase-7-accessibility.test.mjs ccl/web-ui/tests/phase-7-ui-conformance-fixtures.test.mjs ccl/web-ui/tests/phase-7-conformance-runner.test.mjs"
  },
  "persistence-v1": {
    lane_id: "lane.persistence.v1",
    command: "node --test ccl/web-ui/tests/persistence.test.mjs ccl/web-ui/tests/phase-1-persistence.test.mjs ccl/web-ui/tests/phase-4-sessions.test.mjs ccl/web-ui/tests/phase-4-restore.test.mjs ccl/web-ui/tests/persistence-conformance-fixtures.test.mjs"
  },
  "runtime-bridge-v1": {
    lane_id: "lane.runtime-bridge.v1",
    command: "node --test ccl/web-ui/tests/bridge-codec.test.mjs ccl/web-ui/tests/bridge-microkernel.test.mjs ccl/web-ui/tests/phase-5-runtime-bridge.test.mjs ccl/web-ui/tests/phase-5-runtime-command-roundtrip.test.mjs ccl/web-ui/tests/phase-5-runtime-command-dispatch.test.mjs ccl/web-ui/tests/phase-5-runtime-output.test.mjs ccl/web-ui/tests/phase-5-runtime-inspector-integration.test.mjs ccl/web-ui/tests/phase-5-runtime-restart-invoke.test.mjs"
  },
  "full-web-ui-v1": {
    lane_id: "lane.full-runtime.v1",
    command: "node ccl/web-ui/scripts/run-kernel-free-tests.mjs"
  },
  "unindexed-v1": {
    lane_id: "lane.full-runtime.v1",
    command: "node ccl/web-ui/scripts/run-kernel-free-tests.mjs"
  }
};

function toPosix(input) {
  return input.split(path.sep).join("/");
}

function stableHash(input) {
  return crypto.createHash("sha256").update(input).digest("hex");
}

function normalizeWhitespace(input) {
  return input.replace(/\s+/g, " ").trim();
}

function listSpecMarkdownArtifacts() {
  return fs
    .readdirSync(specDir)
    .filter((name) => name.endsWith("-v1.md"))
    .sort((a, b) => a.localeCompare(b));
}

function parseProfileByArtifact() {
  const specIndexPath = path.join(specDir, "spec-index-v1.md");
  const content = fs.readFileSync(specIndexPath, "utf8");
  const lines = content.split(/\r?\n/);
  const profileByArtifact = new Map();
  let currentProfile = null;

  for (const line of lines) {
    const headingMatch = line.match(/^###\s+.+\(`([^`]+)`\)/);
    if (headingMatch) {
      currentProfile = headingMatch[1];
      continue;
    }

    const rowMatch = line.match(/^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|/);
    if (!rowMatch || !currentProfile) {
      continue;
    }

    const artifact = rowMatch[1];
    if (!artifact.startsWith("web-ui/spec/") || !artifact.endsWith("-v1.md")) {
      continue;
    }

    profileByArtifact.set(artifact, currentProfile);
  }

  return profileByArtifact;
}

function buildInlineCodeRanges(line) {
  const ranges = [];
  let i = 0;

  while (i < line.length) {
    if (line[i] !== "`") {
      i += 1;
      continue;
    }

    let tickCount = 1;
    while (i + tickCount < line.length && line[i + tickCount] === "`") {
      tickCount += 1;
    }

    const delimiter = "`".repeat(tickCount);
    const closeIndex = line.indexOf(delimiter, i + tickCount);
    if (closeIndex === -1) {
      break;
    }

    ranges.push([i, closeIndex + tickCount]);
    i = closeIndex + tickCount;
  }

  return ranges;
}

function isInRanges(index, ranges) {
  for (const [start, end] of ranges) {
    if (index >= start && index < end) {
      return true;
    }
  }
  return false;
}

function makeRequirementId({ artifact, lineText, mustOffset, matchOrdinal, usedBaseIds }) {
  const token = path
    .basename(artifact, ".md")
    .replace(/[^A-Za-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .toUpperCase();
  const digest = stableHash(`${artifact}|${lineText}|${mustOffset}|${matchOrdinal}`).slice(0, 10).toUpperCase();
  const baseId = `REQ-${token}-${digest}`;
  const seen = usedBaseIds.get(baseId) ?? 0;
  usedBaseIds.set(baseId, seen + 1);
  if (seen === 0) {
    return baseId;
  }
  return `${baseId}-D${String(seen + 1).padStart(2, "0")}`;
}

function normalizeStatus(rawStatus) {
  if (!rawStatus) {
    return "unknown";
  }
  return rawStatus.trim().toLowerCase().replace(/\s+/g, "-");
}

function anchorMustRequirements({ artifactRelPath, profile, status, usedBaseIds }) {
  const absolutePath = path.join(cclRoot, artifactRelPath);
  const original = fs.readFileSync(absolutePath, "utf8");
  const lines = original.split(/\r?\n/);

  const requirements = [];
  const rewrittenLines = [];

  let inCodeFence = false;

  for (let lineNumber = 0; lineNumber < lines.length; lineNumber += 1) {
    const rawLine = lines[lineNumber];
    const fenceToggle = /^\s*```/.test(rawLine);
    if (fenceToggle) {
      inCodeFence = !inCodeFence;
      rewrittenLines.push(rawLine);
      continue;
    }

    if (inCodeFence) {
      rewrittenLines.push(rawLine);
      continue;
    }

    const line = rawLine.replace(/<a id="REQ-[A-Za-z0-9-]+"><\/a>/g, "");
    const inlineCodeRanges = buildInlineCodeRanges(line);
    const mustRegex = /\bMUST\b/g;

    let cursor = 0;
    let result = "";
    let matchOrdinal = 0;
    let match = mustRegex.exec(line);

    while (match) {
      const mustOffset = match.index;
      result += line.slice(cursor, mustOffset);

      if (isInRanges(mustOffset, inlineCodeRanges)) {
        result += "MUST";
      } else {
        const normalizedLine = normalizeWhitespace(line);
        const requirementId = makeRequirementId({
          artifact: artifactRelPath,
          lineText: normalizedLine,
          mustOffset,
          matchOrdinal,
          usedBaseIds
        });
        result += `<a id="${requirementId}"></a>MUST`;

        requirements.push({
          requirement_id: requirementId,
          artifact: artifactRelPath,
          anchor: `#${requirementId}`,
          text_hash: stableHash(normalizedLine),
          profile,
          status
        });
        matchOrdinal += 1;
      }

      cursor = mustOffset + 4;
      match = mustRegex.exec(line);
    }

    result += line.slice(cursor);
    rewrittenLines.push(result);
  }

  const rewritten = rewrittenLines.join("\n");
  if (rewritten !== original) {
    fs.writeFileSync(absolutePath, rewritten);
  }

  return requirements;
}

function buildEvidenceIndex(requirements) {
  return requirements.map((entry) => {
    const lane = PROFILE_LANES[entry.profile] ?? PROFILE_LANES["unindexed-v1"];
    return {
      requirement_id: entry.requirement_id,
      artifact: entry.artifact,
      anchor: entry.anchor,
      lane_id: lane.lane_id,
      command: lane.command,
      status: "mapped"
    };
  });
}

function buildCoverageSummary(requirements, evidenceIndex) {
  const byProfile = new Map();
  const evidenceByRequirement = new Map(evidenceIndex.map((entry) => [entry.requirement_id, entry]));

  for (const requirement of requirements) {
    if (!byProfile.has(requirement.profile)) {
      byProfile.set(requirement.profile, { requirements: 0, mapped: 0, unmapped: 0 });
    }

    const bucket = byProfile.get(requirement.profile);
    bucket.requirements += 1;
    if (evidenceByRequirement.has(requirement.requirement_id)) {
      bucket.mapped += 1;
    } else {
      bucket.unmapped += 1;
    }
  }

  return [...byProfile.entries()]
    .map(([profile, counts]) => ({ profile, ...counts }))
    .sort((a, b) => a.profile.localeCompare(b.profile));
}

function renderConformanceMatrix({ requirements, evidenceIndex, coverageSummary }) {
  const laneRows = [...new Map(
    evidenceIndex.map((entry) => [entry.lane_id, { lane_id: entry.lane_id, command: entry.command }])
  ).values()].sort((a, b) => a.lane_id.localeCompare(b.lane_id));

  const evidenceByRequirement = new Map(evidenceIndex.map((entry) => [entry.requirement_id, entry]));

  const traceabilityRows = requirements
    .map((requirement) => {
      const evidence = evidenceByRequirement.get(requirement.requirement_id);
      const lane = evidence ? `\`${evidence.lane_id}\`` : "`unmapped`";
      const command = evidence ? `\`${evidence.command}\`` : "`unmapped`";
      return `| \`${requirement.requirement_id}\` | \`${requirement.artifact}\` | \`${requirement.anchor}\` | \`${requirement.profile}\` | ${lane} | ${command} |`;
    })
    .join("\n");

  const coverageRows = coverageSummary
    .map((row) => `| \`${row.profile}\` | ${row.requirements} | ${row.mapped} | ${row.unmapped} |`)
    .join("\n");

  const laneTableRows = laneRows
    .map((row) => `| \`${row.lane_id}\` | \`${row.command}\` |`)
    .join("\n");

  const lines = [
    "# Web UI Conformance Matrix v1",
    "",
    "Status: Draft  ",
    "Version: 1.1.0  ",
    `Last updated: ${CURRENT_DATE}  `,
    "Scope: Requirement-level requirement-to-evidence traceability across `web-ui` v1 claims  ",
    "Depends on: `web-ui/spec/spec-index-v1.md`, `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/requirements-index-v1.json`, `web-ui/spec/conformance-evidence-index-v1.json`  ",
    "Compatibility: `v1.x` preserves requirement IDs, evidence lane IDs, and mapping semantics; incompatible mapping model changes require `v2`.",
    "",
    "## 1. Purpose",
    "",
    "This artifact is the human-readable projection of requirement-level conformance mappings.",
    "Machine-enforceable source data lives in:",
    "",
    "1. `web-ui/spec/requirements-index-v1.json`",
    "2. `web-ui/spec/conformance-evidence-index-v1.json`",
    "",
    "## 2. Evidence Lanes",
    "",
    "| Lane ID | Command |",
    "|---|---|",
    laneTableRows,
    "",
    "## 3. Requirement-Level Traceability",
    "",
    "| Requirement ID | Artifact | Anchor | Profile | Evidence Lane | Command |",
    "|---|---|---|---|---|---|",
    traceabilityRows,
    "",
    "## 4. Coverage Summary",
    "",
    "| Profile | Requirements | Mapped | Unmapped |",
    "|---|---:|---:|---:|",
    coverageRows,
    "",
    "## 5. Failure Semantics",
    "",
    "| Code | Meaning | Retryability | Caller obligation |",
    "|---|---|---|---|",
    "| `conformance-matrix.requirement-unmapped` | Requirement exists in requirements index without evidence mapping. | No | Add mapping in `conformance-evidence-index-v1.json`. |",
    "| `conformance-matrix.evidence-stale` | Evidence command references missing script or test artifact. | No | Update evidence command or restore referenced artifact. |",
    "| `conformance-matrix.evidence-failed` | Linked evidence command exits non-zero. | Conditional | Resolve failure, rerun command, and refresh evidence status. |",
    "",
    "## 6. Conformance",
    "",
    "This matrix is conformant when the requirements and evidence registries are present, every requirement has an evidence mapping, and no evidence entry references missing artifacts.",
    ""
  ];

  return lines.join("\n");
}

function main() {
  const profileByArtifact = parseProfileByArtifact();
  const artifactNames = listSpecMarkdownArtifacts().filter((name) => name !== "web-ui-conformance-matrix-v1.md");

  const usedBaseIds = new Map();
  const requirements = [];

  for (const name of artifactNames) {
    const artifactRelPath = toPosix(path.relative(cclRoot, path.join(specDir, name)));
    const content = fs.readFileSync(path.join(specDir, name), "utf8");
    const statusMatch = content.match(/^Status:\s*([^\n\r]+)/m);
    const status = normalizeStatus(statusMatch ? statusMatch[1] : "unknown");
    const profile = profileByArtifact.get(artifactRelPath) ?? "unindexed-v1";

    const fileRequirements = anchorMustRequirements({
      artifactRelPath,
      profile,
      status,
      usedBaseIds
    });

    requirements.push(...fileRequirements);
  }

  requirements.sort((a, b) => {
    const byArtifact = a.artifact.localeCompare(b.artifact);
    if (byArtifact !== 0) {
      return byArtifact;
    }
    return a.requirement_id.localeCompare(b.requirement_id);
  });

  const evidenceIndex = buildEvidenceIndex(requirements);
  const coverageSummary = buildCoverageSummary(requirements, evidenceIndex);

  const requirementsDocument = {
    version: "1.0.0",
    generated_at: new Date().toISOString(),
    requirements
  };

  const evidenceDocument = {
    version: "1.0.0",
    generated_at: new Date().toISOString(),
    evidence: evidenceIndex
  };

  fs.writeFileSync(requirementsIndexPath, `${JSON.stringify(requirementsDocument, null, 2)}\n`);
  fs.writeFileSync(evidenceIndexPath, `${JSON.stringify(evidenceDocument, null, 2)}\n`);

  const matrix = renderConformanceMatrix({ requirements, evidenceIndex, coverageSummary });
  fs.writeFileSync(matrixPath, matrix);

  const summary = {
    artifacts_scanned: artifactNames.length,
    requirements_indexed: requirements.length,
    evidence_mappings: evidenceIndex.length,
    lanes: [...new Set(evidenceIndex.map((entry) => entry.lane_id))].sort()
  };

  process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);
}

main();
