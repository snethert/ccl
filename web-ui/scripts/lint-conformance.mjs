import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const webUiRoot = path.resolve(__dirname, "..");
const cclRoot = path.resolve(webUiRoot, "..");
const workspaceRoot = path.resolve(cclRoot, "..");
const specDir = path.join(webUiRoot, "spec");

const requirementsIndexPath = path.join(specDir, "requirements-index-v1.json");
const evidenceIndexPath = path.join(specDir, "conformance-evidence-index-v1.json");

function toPosix(input) {
  return input.split(path.sep).join("/");
}

function listSpecMarkdownArtifacts() {
  return fs
    .readdirSync(specDir)
    .filter((name) => name.endsWith("-v1.md"))
    .sort((a, b) => a.localeCompare(b));
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

function stripTrailingPunctuation(token) {
  return token.replace(/[)\],;`'".]+$/g, "");
}

function extractCommandFileReferences(command) {
  const refs = new Set();
  const patterns = [
    /(?:^|\s)(ccl\/web-ui\/[A-Za-z0-9_./-]+)/g,
    /(?:^|\s)(web-ui\/[A-Za-z0-9_./-]+)/g,
    /(?:^|\s)((?:tests|scripts|spec)\/[A-Za-z0-9_./-]+)/g
  ];

  for (const pattern of patterns) {
    let match = pattern.exec(command);
    while (match) {
      const rawToken = stripTrailingPunctuation(match[1]);
      if (rawToken.length > 0) {
        refs.add(rawToken);
      }
      match = pattern.exec(command);
    }
  }

  return [...refs].sort((a, b) => a.localeCompare(b));
}

function resolveCommandReferencePath(token) {
  if (token.startsWith("ccl/web-ui/")) {
    return path.join(workspaceRoot, token);
  }
  if (token.startsWith("web-ui/")) {
    return path.join(cclRoot, token);
  }
  if (token.startsWith("tests/") || token.startsWith("scripts/") || token.startsWith("spec/")) {
    return path.join(webUiRoot, token);
  }
  return null;
}

function loadJsonDocument(filePath, errors) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch (error) {
    errors.push({
      code: "conformance.json-invalid",
      message: `Failed to parse JSON: ${filePath}`,
      path: toPosix(path.relative(cclRoot, filePath)),
      detail: String(error)
    });
    return null;
  }
}

function collectSpecAnchorsAndMustIssues(errors) {
  const anchorsById = new Map();
  const unanchoredMusts = [];

  for (const fileName of listSpecMarkdownArtifacts()) {
    const absolutePath = path.join(specDir, fileName);
    const artifact = toPosix(path.relative(cclRoot, absolutePath));
    const lines = fs.readFileSync(absolutePath, "utf8").split(/\r?\n/);

    let inCodeFence = false;

    for (let lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {
      const line = lines[lineIndex];

      if (/^\s*```/.test(line)) {
        inCodeFence = !inCodeFence;
        continue;
      }

      if (inCodeFence) {
        continue;
      }

      const inlineCodeRanges = buildInlineCodeRanges(line);
      const mustRegex = /\bMUST\b/g;
      let match = mustRegex.exec(line);

      while (match) {
        if (!isInRanges(match.index, inlineCodeRanges)) {
          const prefix = line.slice(0, match.index);
          const anchored = /<a id="REQ-[A-Za-z0-9-]+"><\/a>$/.test(prefix);
          if (!anchored) {
            unanchoredMusts.push({
              code: "conformance.requirement-missing-anchor",
              message: "Normative MUST is missing a stable REQ-* anchor.",
              path: artifact,
              line: lineIndex + 1,
              column: match.index + 1
            });
          }
        }
        match = mustRegex.exec(line);
      }

      const anchorRegex = /<a id="(REQ-[A-Za-z0-9-]+)"><\/a>MUST\b/g;
      let anchorMatch = anchorRegex.exec(line);
      while (anchorMatch) {
        const requirementId = anchorMatch[1];
        if (anchorsById.has(requirementId)) {
          errors.push({
            code: "conformance.requirement-anchor-duplicate",
            message: `Duplicate requirement anchor ${requirementId}.`,
            path: artifact,
            line: lineIndex + 1,
            column: anchorMatch.index + 1
          });
        } else {
          anchorsById.set(requirementId, {
            requirement_id: requirementId,
            artifact,
            anchor: `#${requirementId}`,
            line: lineIndex + 1
          });
        }
        anchorMatch = anchorRegex.exec(line);
      }
    }
  }

  errors.push(...unanchoredMusts);
  return anchorsById;
}

function lintRequirementsIndex({ anchorsById, requirementsDocument, errors }) {
  if (!requirementsDocument || !Array.isArray(requirementsDocument.requirements)) {
    errors.push({
      code: "conformance.requirements-index-invalid",
      message: "requirements-index-v1.json must contain a requirements array.",
      path: "web-ui/spec/requirements-index-v1.json"
    });
    return new Map();
  }

  const requirementsById = new Map();

  for (const entry of requirementsDocument.requirements) {
    const requirementId = entry?.requirement_id;
    if (typeof requirementId !== "string" || !/^REQ-[A-Z0-9-]+$/.test(requirementId)) {
      errors.push({
        code: "conformance.requirement-id-invalid",
        message: "Requirement entry has invalid requirement_id format.",
        path: "web-ui/spec/requirements-index-v1.json",
        detail: JSON.stringify(entry)
      });
      continue;
    }

    if (requirementsById.has(requirementId)) {
      errors.push({
        code: "conformance.requirement-id-duplicate",
        message: `Duplicate requirement_id in requirements index: ${requirementId}`,
        path: "web-ui/spec/requirements-index-v1.json"
      });
      continue;
    }

    requirementsById.set(requirementId, entry);

    if (entry.anchor !== `#${requirementId}`) {
      errors.push({
        code: "conformance.requirement-anchor-invalid",
        message: `Requirement ${requirementId} has mismatched anchor field ${entry.anchor}.`,
        path: "web-ui/spec/requirements-index-v1.json"
      });
    }

    if (typeof entry.artifact !== "string") {
      errors.push({
        code: "conformance.requirement-artifact-invalid",
        message: `Requirement ${requirementId} is missing a valid artifact path.`,
        path: "web-ui/spec/requirements-index-v1.json"
      });
      continue;
    }

    const artifactAbsPath = path.join(cclRoot, entry.artifact);
    if (!fs.existsSync(artifactAbsPath)) {
      errors.push({
        code: "conformance.requirement-artifact-missing",
        message: `Requirement ${requirementId} references missing artifact ${entry.artifact}.`,
        path: "web-ui/spec/requirements-index-v1.json"
      });
    }

    if (typeof entry.text_hash !== "string" || !/^[a-f0-9]{64}$/.test(entry.text_hash)) {
      errors.push({
        code: "conformance.requirement-text-hash-invalid",
        message: `Requirement ${requirementId} has invalid text_hash format.`,
        path: "web-ui/spec/requirements-index-v1.json"
      });
    }

    if (typeof entry.profile !== "string" || entry.profile.length === 0) {
      errors.push({
        code: "conformance.requirement-profile-invalid",
        message: `Requirement ${requirementId} has invalid profile value.`,
        path: "web-ui/spec/requirements-index-v1.json"
      });
    }

    if (typeof entry.status !== "string" || entry.status.length === 0) {
      errors.push({
        code: "conformance.requirement-status-invalid",
        message: `Requirement ${requirementId} has invalid status value.`,
        path: "web-ui/spec/requirements-index-v1.json"
      });
    }
  }

  for (const [requirementId, specAnchor] of anchorsById.entries()) {
    if (!requirementsById.has(requirementId)) {
      errors.push({
        code: "conformance.requirement-unindexed",
        message: `Spec anchor ${requirementId} is missing from requirements-index-v1.json.`,
        path: specAnchor.artifact,
        line: specAnchor.line
      });
    }
  }

  for (const [requirementId, requirement] of requirementsById.entries()) {
    const specAnchor = anchorsById.get(requirementId);
    if (!specAnchor) {
      errors.push({
        code: "conformance.requirement-stale-index",
        message: `Requirement ${requirementId} exists in requirements-index-v1.json but not in spec artifacts.`,
        path: "web-ui/spec/requirements-index-v1.json"
      });
      continue;
    }

    if (requirement.artifact !== specAnchor.artifact) {
      errors.push({
        code: "conformance.requirement-artifact-mismatch",
        message: `Requirement ${requirementId} artifact mismatch (${requirement.artifact} vs ${specAnchor.artifact}).`,
        path: "web-ui/spec/requirements-index-v1.json"
      });
    }
  }

  return requirementsById;
}

function lintEvidenceIndex({ requirementsById, evidenceDocument, errors }) {
  if (!evidenceDocument || !Array.isArray(evidenceDocument.evidence)) {
    errors.push({
      code: "conformance.evidence-index-invalid",
      message: "conformance-evidence-index-v1.json must contain an evidence array.",
      path: "web-ui/spec/conformance-evidence-index-v1.json"
    });
    return new Map();
  }

  const evidenceByRequirementId = new Map();

  for (const entry of evidenceDocument.evidence) {
    const requirementId = entry?.requirement_id;
    if (typeof requirementId !== "string" || !/^REQ-[A-Z0-9-]+$/.test(requirementId)) {
      errors.push({
        code: "conformance.evidence-requirement-id-invalid",
        message: "Evidence entry has invalid requirement_id format.",
        path: "web-ui/spec/conformance-evidence-index-v1.json",
        detail: JSON.stringify(entry)
      });
      continue;
    }

    if (evidenceByRequirementId.has(requirementId)) {
      errors.push({
        code: "conformance.evidence-duplicate",
        message: `Duplicate evidence mapping for ${requirementId}.`,
        path: "web-ui/spec/conformance-evidence-index-v1.json"
      });
      continue;
    }

    evidenceByRequirementId.set(requirementId, entry);

    const requirement = requirementsById.get(requirementId);
    if (!requirement) {
      errors.push({
        code: "conformance.evidence-stale-requirement",
        message: `Evidence entry ${requirementId} references unknown requirement.`,
        path: "web-ui/spec/conformance-evidence-index-v1.json"
      });
      continue;
    }

    if (entry.artifact !== requirement.artifact) {
      errors.push({
        code: "conformance.evidence-artifact-mismatch",
        message: `Evidence entry ${requirementId} artifact mismatch (${entry.artifact} vs ${requirement.artifact}).`,
        path: "web-ui/spec/conformance-evidence-index-v1.json"
      });
    }

    if (entry.anchor !== requirement.anchor) {
      errors.push({
        code: "conformance.evidence-anchor-mismatch",
        message: `Evidence entry ${requirementId} anchor mismatch (${entry.anchor} vs ${requirement.anchor}).`,
        path: "web-ui/spec/conformance-evidence-index-v1.json"
      });
    }

    if (typeof entry.command !== "string" || entry.command.trim().length === 0) {
      errors.push({
        code: "conformance.evidence-command-missing",
        message: `Evidence entry ${requirementId} has no executable command.`,
        path: "web-ui/spec/conformance-evidence-index-v1.json"
      });
      continue;
    }

    const commandFileRefs = extractCommandFileReferences(entry.command);
    for (const token of commandFileRefs) {
      const resolvedPath = resolveCommandReferencePath(token);
      if (!resolvedPath) {
        continue;
      }
      if (!fs.existsSync(resolvedPath)) {
        errors.push({
          code: "conformance.evidence-stale-reference",
          message: `Evidence entry ${requirementId} command references missing path ${token}.`,
          path: "web-ui/spec/conformance-evidence-index-v1.json"
        });
      }
    }
  }

  for (const requirementId of requirementsById.keys()) {
    if (!evidenceByRequirementId.has(requirementId)) {
      errors.push({
        code: "conformance.evidence-missing",
        message: `Requirement ${requirementId} has no evidence mapping.`,
        path: "web-ui/spec/conformance-evidence-index-v1.json"
      });
    }
  }

  return evidenceByRequirementId;
}

function parseRegisteredNamespaces() {
  const registryPath = path.join(specDir, "error-code-registry-v1.md");
  if (!fs.existsSync(registryPath)) {
    return null;
  }
  const lines = fs.readFileSync(registryPath, "utf8").split(/\r?\n/);
  const namespaces = new Set();
  for (const line of lines) {
    const match = line.match(/^\|\s*`([a-z][-a-z0-9]+)`\s*\|/);
    if (match) {
      namespaces.add(match[1]);
    }
  }
  return namespaces;
}

function lintErrorCodeNamespaces(errors) {
  const registered = parseRegisteredNamespaces();
  if (!registered) {
    errors.push({
      code: "conformance.error-registry-missing",
      message: "error-code-registry-v1.md not found; cannot validate error-code namespaces.",
      path: "web-ui/spec/error-code-registry-v1.md"
    });
    return;
  }

  for (const fileName of listSpecMarkdownArtifacts()) {
    if (fileName === "error-code-registry-v1.md") {
      continue;
    }
    const absolutePath = path.join(specDir, fileName);
    const artifact = toPosix(path.relative(cclRoot, absolutePath));
    const lines = fs.readFileSync(absolutePath, "utf8").split(/\r?\n/);

    let inFailureSemantics = false;
    const seen = new Set();

    for (let lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {
      const line = lines[lineIndex];

      if (/^#+\s.*Failure Semantics/i.test(line)) {
        inFailureSemantics = true;
        continue;
      }
      if (inFailureSemantics && /^#+\s/.test(line)) {
        inFailureSemantics = false;
        continue;
      }

      if (!inFailureSemantics) {
        continue;
      }

      const codeMatch = line.match(/^\|\s*`([a-z][-a-z0-9]+)\./);
      if (!codeMatch) {
        continue;
      }

      const namespace = codeMatch[1];
      if (seen.has(namespace)) {
        continue;
      }
      seen.add(namespace);

      if (!registered.has(namespace)) {
        errors.push({
          code: "conformance.error-namespace-unregistered",
          message: `Error-code namespace "${namespace}" is used but not registered in error-code-registry-v1.md.`,
          path: artifact,
          line: lineIndex + 1
        });
      }
    }
  }
}

function parseSpecIndexRequiredArtifacts(errors) {
  const specIndexPath = path.join(specDir, "spec-index-v1.md");
  if (!fs.existsSync(specIndexPath)) {
    errors.push({
      code: "conformance.spec-index-missing",
      message: "spec-index-v1.md not found.",
      path: "web-ui/spec/spec-index-v1.md"
    });
    return { required: [], informational: new Set() };
  }
  const lines = fs.readFileSync(specIndexPath, "utf8").split(/\r?\n/);
  const required = [];
  const informational = new Set();

  for (let i = 0; i < lines.length; i += 1) {
    const row = lines[i].match(/^\|\s*`([^`]+)`\s*\|\s*`(required|required-planned|informational)`\s*\|/);
    if (!row) {
      continue;
    }
    const artifactPath = row[1];
    const artifactClass = row[2];
    if (artifactClass === "informational") {
      informational.add(artifactPath);
    }
    required.push({ path: artifactPath, class: artifactClass, line: i + 1 });
  }
  return { required, informational };
}

function lintSpecIndexArtifactExistence({ specIndexArtifacts, errors }) {
  for (const entry of specIndexArtifacts) {
    const absolutePath = path.join(cclRoot, entry.path);
    if (!fs.existsSync(absolutePath)) {
      errors.push({
        code: "conformance.spec-index-artifact-missing",
        message: `Spec-index artifact "${entry.path}" (class=${entry.class}) does not exist on disk.`,
        path: "web-ui/spec/spec-index-v1.md",
        line: entry.line
      });
    }
  }
}

const REQUIRED_METADATA_FIELDS = ["Status", "Version", "Last updated", "Scope", "Depends on", "Compatibility"];

function lintArtifactMetadata({ informationalPaths, errors }) {
  for (const fileName of listSpecMarkdownArtifacts()) {
    const absolutePath = path.join(specDir, fileName);
    const artifact = toPosix(path.relative(cclRoot, absolutePath));
    const content = fs.readFileSync(absolutePath, "utf8");
    const headerLines = content.split(/\r?\n/).slice(0, 30);

    for (const field of REQUIRED_METADATA_FIELDS) {
      const pattern = new RegExp(`^${field.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*:`);
      const found = headerLines.some((line) => pattern.test(line));
      if (!found) {
        errors.push({
          code: "conformance.metadata-field-missing",
          message: `Required metadata field "${field}" is missing.`,
          path: artifact
        });
      }
    }
  }
}

// Artifacts that are meta-governance or catalog documents without operational
// failure modes.  These are exempt from the Failure Semantics section
// requirement but still require a Conformance section.
const FAILURE_SEMANTICS_EXEMPT = new Set([
  "error-code-registry-v1.md",
  "glossary-v1.md",
  "persistence-failure-mode-matrix-v1.md",
  "ui-conformance-matrix-v1.md"
]);

function lintRequiredSections({ informationalPaths, errors }) {
  for (const fileName of listSpecMarkdownArtifacts()) {
    const absolutePath = path.join(specDir, fileName);
    const artifact = toPosix(path.relative(cclRoot, absolutePath));
    const fullPath = `web-ui/spec/${fileName}`;

    if (informationalPaths.has(fullPath)) {
      continue;
    }

    const content = fs.readFileSync(absolutePath, "utf8");

    if (!/^#+\s+(?:\d+\.\s*)?Conformance\s*$/m.test(content)) {
      errors.push({
        code: "conformance.section-conformance-missing",
        message: "Required Conformance section is missing.",
        path: artifact
      });
    }

    if (!FAILURE_SEMANTICS_EXEMPT.has(fileName) &&
        !/^#+\s+(?:\d+\.\s*)?Failure Semantics\s*$/m.test(content)) {
      errors.push({
        code: "conformance.section-failure-semantics-missing",
        message: "Required Failure Semantics section is missing.",
        path: artifact
      });
    }
  }
}

function lintRegistryDuplicateNamespaces(errors) {
  const registryPath = path.join(specDir, "error-code-registry-v1.md");
  if (!fs.existsSync(registryPath)) {
    return;
  }
  const lines = fs.readFileSync(registryPath, "utf8").split(/\r?\n/);
  const seen = new Map();

  for (let i = 0; i < lines.length; i += 1) {
    const match = lines[i].match(/^\|\s*`([a-z][-a-z0-9]+)`\s*\|/);
    if (!match) {
      continue;
    }
    const namespace = match[1];
    if (seen.has(namespace)) {
      errors.push({
        code: "conformance.error-namespace-duplicate",
        message: `Duplicate error-code namespace "${namespace}" in registry (first at line ${seen.get(namespace)}).`,
        path: "web-ui/spec/error-code-registry-v1.md",
        line: i + 1
      });
    } else {
      seen.set(namespace, i + 1);
    }
  }
}

function formatIssue(issue) {
  const location = issue.line
    ? `${issue.path}:${issue.line}${issue.column ? `:${issue.column}` : ""}`
    : issue.path;
  const detail = issue.detail ? ` (${issue.detail})` : "";
  return `[${issue.code}] ${location} ${issue.message}${detail}`;
}

function main() {
  const jsonMode = process.argv.includes("--json");
  const errors = [];

  const anchorsById = collectSpecAnchorsAndMustIssues(errors);
  const requirementsDocument = loadJsonDocument(requirementsIndexPath, errors);
  const evidenceDocument = loadJsonDocument(evidenceIndexPath, errors);

  const requirementsById = lintRequirementsIndex({ anchorsById, requirementsDocument, errors });
  lintEvidenceIndex({ requirementsById, evidenceDocument, errors });
  lintErrorCodeNamespaces(errors);

  const { required: specIndexArtifacts, informational: informationalPaths } = parseSpecIndexRequiredArtifacts(errors);
  lintSpecIndexArtifactExistence({ specIndexArtifacts, errors });
  lintArtifactMetadata({ informationalPaths, errors });
  lintRequiredSections({ informationalPaths, errors });
  lintRegistryDuplicateNamespaces(errors);

  const summary = {
    ok: errors.length === 0,
    timestamp: new Date().toISOString(),
    anchors_found: anchorsById.size,
    requirements_indexed: requirementsById.size,
    error_count: errors.length,
    errors
  };

  if (jsonMode) {
    process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);
  } else if (errors.length === 0) {
    process.stdout.write("Conformance lint passed: all MUST anchors, requirement mappings, and evidence references are valid.\n");
  } else {
    process.stderr.write("Conformance lint failed.\n");
    for (const issue of errors) {
      process.stderr.write(`${formatIssue(issue)}\n`);
    }
  }

  process.exit(errors.length === 0 ? 0 : 1);
}

main();
