# Persistence Semantic Merge Contract v1

Status: Draft  
Version: 1.1.0  
Last updated: 2026-02-16  
Scope: Deterministic reader-driven semantic merge behavior for Lisp documents  
Depends on: `web-ui/spec/persistence-semantic-profile-v1.md`, `web-ui/spec/persistence-sync-and-conflict-protocol-v1.md`, `web-ui/spec/controlled-reader-contract-v1.md`
Compatibility: `v1.x` preserves normative requirements and failure semantics; incompatible changes require `v2`.

## 1. Purpose

This contract defines deterministic semantic merge rules when semantic-canonical persistence is active.

Applicability:

1. Required for `semantic-canonical-v1`.
2. Optional as an assistive lane in `file-primacy-v1`.

## 2. Semantic Objects (Lisp Docs)

The merge model assumes:

1. Stable `doc_id` for logical document identity.
2. Stable `form_id` identities per form.
3. Deterministic `FormGraph` ordering and node mapping.
4. Explicit trivia policy (`discard | preserve_as_trivia | preserve_surface`).

## 3. Controlled Reader Requirements

All Lisp-source documents <a id="REQ-PERSISTENCE-SEMANTIC-MERGE-CONTRACT-V1-FB3DD9989F"></a>MUST be ingested and modified through a controlled reader profile selected by workspace policy.

The controlled reader is a separate normative artifact:

1. `web-ui/spec/controlled-reader-contract-v1.md` defines reader profile surface, policy controls, and deterministic parsing constraints.
2. This merge contract consumes the reader outputs and policy decisions from that artifact.

The controlled reader profile <a id="REQ-PERSISTENCE-SEMANTIC-MERGE-CONTRACT-V1-62ED3CC7CE"></a>MUST define:

1. Allowed readtable behavior:
   fixed readtable, or explicit readtable-change forms tracked as first-class operations with deterministic scope.
2. Package behavior:
   `in-package` and `defpackage` are semantics-critical forms with explicit ordering rules.
3. Forbidden/restricted reader features:
   `#.` read-time evaluation is forbidden by default; if enabled it <a id="REQ-PERSISTENCE-SEMANTIC-MERGE-CONTRACT-V1-0953B3042E"></a>MUST be sandboxed, deterministic, and recorded as policy override.
4. Circular structure policy:
   `#n=` / `#n#` are either forbidden or normalized into canonical internal form.
5. Feature-conditional policy:
   `#+` / `#-` are either preserved as explicit conditional nodes or treated as opaque text regions by policy.
6. Readability boundary rules:
   policy <a id="REQ-PERSISTENCE-SEMANTIC-MERGE-CONTRACT-V1-467E59A9DD"></a>MUST define readable boundary behavior for autosave/merge, including dispatch macros and conditional regions.

The controlled reader <a id="REQ-PERSISTENCE-SEMANTIC-MERGE-CONTRACT-V1-F3E9A87D47"></a>MUST be capable of:

1. Producing normalized AST encodings.
2. Externalizing trivia under selected trivia policy.
3. Assigning stable identity anchors and deterministic rename behavior.

### 3.1 Dependency Hints (Non-Expanding, Syntactic)

Goal: improve conflict classification and UI ordering without macroexpansion.

Dependency hints <a id="REQ-PERSISTENCE-SEMANTIC-MERGE-CONTRACT-V1-E11B422AED"></a>MUST be derived without executing user code:

1. `referenced_symbols`: deterministic symbol set from operator/high-signal positions.
2. `defined_symbols`: symbols introduced by definition forms.
3. `package_affecting`: boolean for `in-package`, `defpackage`, and profile-defined package directives.

Use:

1. Conflict classification:
   mark definition-order-sensitive cases when package-affecting/definition edits interact with referenced forms.
2. Merge UI ordering:
   prioritize package-affecting and definition changes.
3. Safety warnings:
   warnings are heuristic and <a id="REQ-PERSISTENCE-SEMANTIC-MERGE-CONTRACT-V1-52ED05FB85"></a>MUST NOT depend on macroexpansion.

Out of scope:

1. Macroexpansion-based dependency tracking.
2. Executing macros or evaluating user code during merge analysis.

## 4. Merge Base Requirement

Semantic merge <a id="REQ-PERSISTENCE-SEMANTIC-MERGE-CONTRACT-V1-D4BB610A69"></a>MUST compute and record `base_commit_id`.

If merge base is unavailable:

1. Semantic merge <a id="REQ-PERSISTENCE-SEMANTIC-MERGE-CONTRACT-V1-8F4DA43195"></a>MUST abort with explicit error.
2. System MAY offer non-semantic fallback workflows.

## 5. Deterministic 3-Way Merge

Given `(base, local, incoming)` for each document:

1. Match primarily by `form_id`.
2. Classify added/removed/changed/moved forms.
3. Auto-resolve disjoint edits.
4. Emit explicit conflict entries for non-deterministic choices.
5. Produce deterministic candidate graph and conflict list.
6. Apply semantics-critical ordering constraints before cosmetic ordering policy.

Ordering/tie-breaks <a id="REQ-PERSISTENCE-SEMANTIC-MERGE-CONTRACT-V1-2E36FF47AC"></a>MUST NOT depend on hash-map iteration order.

Semantics-critical ordering constraint:

1. `defpackage` / `in-package` (and other package-affecting directives) <a id="REQ-PERSISTENCE-SEMANTIC-MERGE-CONTRACT-V1-97166CF605"></a>MUST remain before forms whose interpretation depends on them unless explicit `MergeRecord` override exists.
2. If both sides edit package-affecting forms and changes are non-identical, classify as conflict.

## 6. Conflict Taxonomy

Supported semantic conflict types:

1. `same-form-edited`
2. `delete-vs-edit`
3. `insert-collision`
4. `rename-identity`
5. `macro-dependent`
6. `order-conflict-only`
7. `trivia-only`

Each conflict record SHOULD include:

1. `doc_id`
2. `form_id` (if available)
3. `local_formnode_id`
4. `incoming_formnode_id`
5. `base_formnode_id`
6. `auto_resolvable`
7. `auto_resolution_kind`

## 7. Auto-Resolution Rules

By default, semantic auto-merge MAY resolve:

1. Disjoint form edits.
2. Order-only differences using deterministic order policy.
3. Trivia-only differences under active trivia policy.

By default, semantic auto-merge <a id="REQ-PERSISTENCE-SEMANTIC-MERGE-CONTRACT-V1-3DD6DC5E38"></a>MUST NOT finalize silently for:

1. same-form divergent edits without deterministic structural rule,
2. macro-dependent conflicts,
3. identity-ambiguous rename collisions.

## 8. Merge Candidate and Finalization

Semantic merge <a id="REQ-PERSISTENCE-SEMANTIC-MERGE-CONTRACT-V1-9D2D60ACF0"></a>MUST follow merge-candidate-first flow:

1. Write merge candidate snapshot and commit with:
   `intent=merge`, `finalized=false`, `candidate_of={base_commit_id, local_commit_id, incoming_commit_id}`.
2. Preserve unresolved conflict metadata when present.
3. Require explicit user acceptance (or explicit deterministic policy gate) before advancing `workspace/main`.

Accepted merge SHOULD produce `MergeRecord` with per-doc/per-form resolution audit.

Rule:

1. Candidate commits <a id="REQ-PERSISTENCE-SEMANTIC-MERGE-CONTRACT-V1-E3915F65BA"></a>MUST be intrinsically marked by `finalized=false`; ref naming alone is insufficient.

## 9. MergeRecord Semantics

`MergeRecord` SHOULD contain:

1. `base_commit_id`
2. `base_selection_spec_id` (algorithm version or deterministic tie-break spec id)
3. `local_commit_id`
4. `incoming_commit_id`
5. `doc_resolutions[]`
6. `form_resolutions[]`
7. `tool_version`
8. `created_at`

Rule:

1. `MergeRecord` <a id="REQ-PERSISTENCE-SEMANTIC-MERGE-CONTRACT-V1-225CF65ED7"></a>MUST reference the actual base commit used and the base-selection algorithm/spec id.

Resolution outcomes SHOULD include:

1. `kept_local`
2. `kept_incoming`
3. `merged_structural`
4. `manual_edit`
5. `deleted`
6. `moved`
7. `renamed_identity_preserved`
8. `renamed_identity_split`

## 10. Macro-Dependency Policy

Macro-dependent conflicts SHOULD be flagged conservatively.

Rules:

1. Semantic merge <a id="REQ-PERSISTENCE-SEMANTIC-MERGE-CONTRACT-V1-0A95AD108D"></a>MUST NOT treat macroexpansion output as canonical persisted source.
2. Expansion MAY be used for diagnostics only.
3. Macro-dependent auto-finalization is disabled by default.

## 11. Compatibility and Fallback

When semantic merge cannot proceed:

1. System <a id="REQ-PERSISTENCE-SEMANTIC-MERGE-CONTRACT-V1-A369B1CF49"></a>MUST preserve refs and current workspace state.
2. System <a id="REQ-PERSISTENCE-SEMANTIC-MERGE-CONTRACT-V1-7BAABB5BDC"></a>MUST surface explicit fallback options.
3. Fallback MAY use file-level merge workflow without silent ref advancement.

## 12. Error Codes

Implementations <a id="REQ-PERSISTENCE-SEMANTIC-MERGE-CONTRACT-V1-77FD7F6225"></a>MUST expose:

1. `ERR_SEMANTIC_MERGE_BASE_MISSING`
2. `ERR_SEMANTIC_IDENTITY_UNRESOLVED`
3. `ERR_SEMANTIC_MACRO_DEPENDENT_CONFLICT`
4. `ERR_SEMANTIC_MERGE_REQUIRES_ACCEPTANCE`

## 13. Conformance

An implementation is conformant only if:

1. Semantic merge output is deterministic for identical inputs/policies.
2. Conflict taxonomy and audit metadata are emitted consistently.
3. Merge-candidate-first gate is always enforced.
4. No silent mainline advancement occurs from semantic auto-merge.
