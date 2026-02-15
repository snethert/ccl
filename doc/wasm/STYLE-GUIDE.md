# Documentation Style Guide

**Version:** 1.0.0
**Status:** Active
**Scope:** Standards for technical documentation in `doc/wasm/`
**Last Updated:** 2026-02-15

## Purpose

This guide establishes consistent patterns for writing and maintaining technical documentation in the CCL WASM port project. Following these standards ensures documentation is professional, actionable, and maintainable.

## Document Structure

### Standard Template

All technical specification documents should follow this structure:

```markdown
# Document Title

**Status:** Active | Draft | Deprecated
**Scope:** One-line description of what this document covers
**Last Updated:** YYYY-MM-DD
**Doc Version:** X.Y.Z (style guide version this document conforms to)

## Purpose

Clear statement of what this document defines.

## Current Implementation Status

### ✅ What Works

- Feature 1
- Feature 2

### ❌ Critical Issues (MVP-X Blockers)

Description of blocking problems.

## [Core Content Sections]

The actual specification, organized logically.

## Testing & Validation

How to verify correct behavior.

## Implementation Notes

Technical details for developers implementing features.

## Future Work

Deferred to MVP-2 or later:

- ⏸️ Item 1
- ⏸️ Item 2

## Related Documentation

- [Doc Name](./file.md) – Brief description
- [§ Section](#anchor) – Internal reference
```

### Section Guidelines

| Section | Purpose | Required |
|---------|---------|----------|
| **Header Block** | Status, scope, last-updated date, doc version | Yes |
| **Purpose** | What the document defines | Yes |
| **Current Implementation Status** | Honest state assessment | Yes (for specs) |
| **Core Content** | Specification details | Yes |
| **Testing & Validation** | How to verify | Recommended |
| **Implementation Notes** | Developer guidance | As needed |
| **Future Work** | Deferred features | As needed |
| **Related Documentation** | Cross-references | Recommended |

## Version Management

### Style Guide Versioning

This style guide uses semantic versioning (MAJOR.MINOR.PATCH):

| Change Type | Version Bump | Examples |
|-------------|--------------|----------|
| **MAJOR** | Breaking structural changes | Required sections added/removed, incompatible format changes |
| **MINOR** | New recommendations | New optional sections, additional patterns, expanded guidelines |
| **PATCH** | Clarifications only | Typo fixes, example improvements, wording clarifications |

Current version: **1.0.0** (baseline established 2026-02-15)

### Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-15 | Initial baseline: structure template, status markers, cross-reference patterns, terminology standards, writing style guidelines |

### Document Conformance

Each specification document declares which style guide version it conforms to:

```markdown
**Doc Version:** 1.0.0
```

### Conformance Check Rule

**Standing Rule:** When visiting or updating any specification document in `doc/wasm/`:

1. Check the document's `Doc Version` field
2. Compare against current style guide version (`STYLE-GUIDE.md` header)
3. If versions differ:
   - Review the document against current style guide
   - Update structure, formatting, and cross-references to conform
   - Update `Doc Version` to current style guide version
   - Update `Last Updated` date

4. If `Doc Version` field is missing:
   - Document predates versioning
   - Apply full conformance update
   - Add `Doc Version` field with current version

This ensures all documentation stays consistent with the latest standards.

## Status Markers

Use consistent visual markers to indicate implementation state:

| Marker | Meaning | Usage |
|--------|---------|-------|
| ✅ | Working | Feature is implemented and tested |
| ❌ | Not Working / Broken | Feature is broken or missing |
| ⚠️ | Partial / Unstable | Feature exists but has known issues |
| ⏸️ | Deferred | Planned for future milestone |

### Examples

```markdown
- ✅ **stdio routing:** `kernel_request` handles stdin/stdout/stderr
- ❌ **FASL loading:** Returns -7 due to missing package hash table rebuild
- ⚠️ **Image persistence:** Works but has memory leak in cleanup path
- ⏸️ **Image format versioning:** Deferred to MVP-2
```

## Cross-Reference Patterns

### Relative Links

**Same directory:**
```markdown
[Roadmap](./roadmap.md) – MVP-1 vs MVP-2 strategy
```

**Parent directory:**
```markdown
[build script](../../scripts/wasm/build-wasm-boot.sh)
```

**Specific line:**
```markdown
[xwasmfasload.lisp:72](../../xdump/xwasmfasload.lisp#L72)
```

### Internal Sections

```markdown
See [§ Implementation Notes](#implementation-notes) for details.
```

### Cross-Reference Format

Always include a brief description after the link:

```markdown
## Related Documentation

- [Image Loader Spec](./image-loader-spec.md) – Kernel ABI for loading heap images
- [Bootstrap Architecture](./bootstrap-wasm32.md) – Level-0/Level-1 bootstrap sequence
- [Porting Status](./porting-status.md) – Overall feature implementation status
```

## Terminology Standards

### Two-Mode Architecture

**Use:**
- MVP-1: Library Mode (or Library/Embedded Mode)
- MVP-2: Full Runtime Mode

**Do NOT use:**
- "Replacement lane" or "legacy lane" (confusing)
- "ASCII-only" or "ASCII-first" (superseded by UTF-8 wire format)

### Feature Status

**Be specific:**
```markdown
❌ FASL loading fails with error code -7 when trying to find CCL::%FASLOAD
```

**Not vague:**
```markdown
⚠️ FASL loading has issues
```

## Writing Style

### Professional Tone

**Good:**
```markdown
WASM instances serve as isolated execution contexts with independent memory spaces.
```

**Bad:**
```markdown
The project's core bet is that WASM instances are processes.
```

Avoid:
- Casual asides ("The hard question is...")
- Marketing language ("innovative", "cutting-edge")
- Speculation without evidence ("probably", "seems like")
- First-person narrative ("I think", "we believe")

### Honesty Over Aspiration

**Good:**
```markdown
### ❌ Critical Issues (MVP-1 Blockers)

**FASL loading fails with error code -7**

Root cause: Package hash tables are never rebuilt after image load.
```

**Bad:**
```markdown
### Status

FASL loading is under development and will be available soon.
```

Document reality, not roadmap promises. Use "Future Work" section for planned features.

### Actionable Content

**Good:**
```markdown
### Testing

Verify image loads without entering toplevel:

```bash
node scripts/wasm/lib/load-image.mjs --mode boot-only wasm-boot.image
```

Expected: Returns 0, no errors.
```

**Bad:**
```markdown
### Testing

You can test the image loader using the load-image.mjs script.
```

Provide exact commands, expected outputs, and current behavior.

## Code Examples

### Formatting

Use language-specific syntax highlighting:

````markdown
```c
LispObj restore_fn = nrs_RESTORE_LISP_POINTERS.vcell;
```

```bash
node scripts/wasm/lib/load-image.mjs --mode boot-only wasm-boot.image
```

```lisp
(defun cross-xload-level-0 (target &optional force)
  ...)
```
````

### Context

Include enough context for standalone understanding:

**Good:**
```markdown
In [`lisp-kernel/wasm-kernel-stubs.c`](../../lisp-kernel/wasm-kernel-stubs.c) function `start_lisp()`, before calling `wasm_toplevel_loop()`:

```c
LispObj restore_fn = nrs_RESTORE_LISP_POINTERS.vcell;
```
```

**Bad:**
```markdown
Add this code:

```c
LispObj restore_fn = nrs_RESTORE_LISP_POINTERS.vcell;
```
```

## Tables

Use tables for structured data:

```markdown
### Return Codes

| Code | Meaning |
|------|---------|
| 0    | Success |
| -7   | Symbol lookup failure during boot |
| Other | Kernel-specific error codes |
```

## Document Lifecycle

### Status Values

| Status | Meaning |
|--------|---------|
| **Active** | Current, maintained specification |
| **Draft** | Work in progress, subject to change |
| **Deprecated** | Superseded, kept for reference |

### Last Updated

Update the `Last Updated` date whenever making substantial changes:

```markdown
**Last Updated:** 2026-02-15
```

### Obsolete Content

When removing obsolete content:
1. Move deferred features to "Future Work" instead of deleting
2. Update cross-references in other documents
3. Add deprecation notice if the entire document is obsolete

## Anti-Patterns

### ❌ Avoid These

**Vague status claims:**
```markdown
- Image loading: Mostly working
```

**Missing cross-references:**
```markdown
See the image loader spec for details.
```
(Should link: `[image loader spec](./image-loader-spec.md)`)

**Aspirational language:**
```markdown
The image loader will support dynamic module loading.
```
(Use "Future Work" section instead)

**Open-ended questions:**
```markdown
## Open Questions

- What is the canonical image format?
- Should we support versioning?
```
(Use "Future Work" with specific proposals)

**Mixing current and future:**
```markdown
The loader supports boot-only mode and will soon support automatic fixup.
```
(Separate "What Works" from "Future Work")

## Examples

### Well-Structured Document

See [`image-loader-spec.md`](./image-loader-spec.md) for a complete example following these guidelines.

### Key Patterns Demonstrated

1. **Clear header block** with status and scope
2. **Honest status section** using ✅/❌ markers
3. **Actionable testing section** with exact commands
4. **Cross-references with descriptions**
5. **Professional tone** throughout
6. **Separated current from future** work

## Enforcement

The documentation conformance check is a **standing rule** recorded in project memory. When any specification document in `doc/wasm/` is visited or updated:

1. Check `Doc Version` field against current style guide version
2. If outdated or missing: apply conformance update
3. Update `Doc Version` and `Last Updated` fields

This ensures continuous documentation quality without manual audits.

## Related Documentation

- [README](./README.md) – Project overview and current status
- [Roadmap](./roadmap.md) – MVP-1 vs MVP-2 strategy
- [Project Overview](./project-overview.md) – High-level architecture
- [Image Loader Spec](./image-loader-spec.md) – Reference implementation of this style guide
