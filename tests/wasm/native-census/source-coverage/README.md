# Static source-coverage accounting

Surface counts over pristine U1 source, describing how much of CCL the census
must eventually account for and how much of it a single native darwinx8664
observation run can never read.

This is **analysis, not execution evidence**. It confers no gate credit,
discharges no `S0-*` obligation, and makes no claim about what the compiler or
loader does with any form it counts. Findings and limits are written up in
[`doc/WASM/stage0/source-coverage-analysis.md`](../../../../doc/WASM/stage0/source-coverage-analysis.md).

## Run

Python 3 standard library only. No native build, no image, no shared-source
patch; every file is opened read-only.

```sh
python3 tests/wasm/native-census/source-coverage/controls.py
python3 tests/wasm/native-census/source-coverage/analyze.py \
    --output doc/WASM/evidence/source-coverage-summary.json
```

`controls.py` must report `0 failed`. It exits nonzero otherwise.

## What the lexer does and does not do

`lexer.py` resolves only the lexical structure needed to count top-level forms
and locate reader-conditional and read-time-evaluation sites: string literals,
character literals, line and block comments, single- and multiple-escape
symbols, and parenthesis depth.

It is **not** a reader. It does not expand macros, evaluate `#.`, select
`#+`/`#-` branches, or resolve packages. A top-level `defmacro`-generated form
counts as one form here however many definitions it expands into, so the
reported form count is a lower bound on the definitions a traversal must
account for.

In strict mode (the default) an unterminated string, block comment or escaped
symbol, or a paren depth closing below zero, raises `LexError` rather than
returning a count derived from a guess.

## Controls

`controls.py` runs 25 checks. All positive cases must pass and all rejection
controls must reject.

- 17 positive lexical cases, including the three regressions below.
- 5 rejection controls a permissive lexer would fail.
- Agreement with the reviewed first source traversal: `lib/dumplisp.lisp` must
  lex to exactly the **16** top-level forms published in
  `doc/WASM/stage0/source-traversal.md`. An independent lexer that does not
  reproduce that number invalidates every other count here.
- Whole-corpus strictness: every analysed `.lisp` file must lex strictly. A file
  needing the permissive path is a lexer gap, not a file to drop from the
  denominator.
- Determinism: two `analyze.py` runs must produce identical JSON.

### Retained original failures

The first lexer failed the whole-corpus strictness control on two pristine U1
files. Both were real Common Lisp reader rules the lexer did not implement, not
defects in CCL. Each is now a named positive case:

| File | Construct | Rule missed |
| --- | --- | --- |
| `level-1/l1-reader.lisp:2886` | `(nfunction \|#\\\|-reader\| ...)` | backslash is a single-escape *inside* `\|...\|`, so `\\\|` is a literal bar and does not close the symbol |
| `library/parse-ffi.lisp:1012` | `(\|#\| \|##\|)` | symbols named `#` and `##` written with multiple-escape bars, which must not start a `#\|` block comment |

Both desynchronised paren depth for the remainder of the file, which is exactly
the failure mode a surface counter must not have. They are retained here
because they are also the smallest concrete instance of this deliverable's own
subject: a corner case that only a strict whole-corpus check surfaces.

## Reported buckets

| Bucket | Contents |
| --- | --- |
| `all` | every `.lisp` file in the analysed subtrees |
| `x8664` | files not marked for another target by path |
| `x8664_cold` | `x8664` minus `tools/`, which is compiled but reached only through `REQUIRE` and so is absent from any cold-boot observation |

`corpus_sha256` covers the analysed path list and file contents, so a changed
corpus produces a changed digest.

## Known limits

- Compound reader conditionals (`#+(and ...)`) are counted but not evaluated;
  they are reported as `cond_compound` and excluded from the read/unread split.
  `cond_unread` is therefore a lower bound within the classified set.
- `DARWIN_X8664_FEATURES` is an approximation of a v1.13 darwinx8664 feature
  set, not a captured `*features*`. A misclassified feature moves sites between
  the read and unread buckets; the per-feature table makes that visible.
- File-level target exclusion is by path marker only, and is conservative: a
  file is excluded only on an unambiguous architecture marker. Arch-specific
  code inside an otherwise shared file stays in the count.
- Construct counts are regular-expression matches over source text, not
  resolved call sites. They locate families to investigate; they are not a
  dependency graph, and `contracts/census.md` is explicit that LL15-b accepts
  the joined instrumented graph and not source regex counts.
