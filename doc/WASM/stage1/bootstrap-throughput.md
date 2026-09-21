# Bootstrap throughput directive (BOOT-TP-P1)

Status: ADOPTED by the user on 2026-09-21, with Codex’s review corrections in section 8. The directive changes work priorities and review cadence; existing acceptance contracts remain in force.

Reader: Codex, as Stage 1 author. Items carry IDs so a reply can cite them.

## 1. Relayed user direction

- U-1. User, 2026-09-21, after audit 140: "are we accomplishing anything? How much of bootstrap is done?"
- U-2. Claude answered with the ledger and measurement in sections 2 and 3 and offered to write items BT-1 to BT-4 up for Codex. User: "yes".
- U-3. Nothing else in this document is the user's statement. Adoption, and acceptance of any unit, remain the user's decisions.

## 2. Ledger facts (at a8a35ea9)

- L-1. Stage 1 requires 31 variants. 21 are accepted, 10 are missing, 0 are unreviewed. That count did not change across Claude audits 126 to 140, a span of about 160 commits from 19 to 21 September.
- L-2. The ten missing are S1-LL15-a (bootstrap initializers), S1-LL14-a (fresh load of the bootstrap heap and code set), S1-NAMESPACE-a, S1-LOADER-a, and the six controls S1-LL01-a, S1-LL02-a, S1-LL03-a, S1-LL22-a, S1-LL24-a and S1-CONTRACTS-a. The six controls test a production bootstrap build, so all ten wait on the bootstrap existing.
- L-3. Work recorded against LL15 since 19 September covers 20 of the 34 registered `*lisp-system-pointer-functions*` callbacks. Each is a selected lambda compiled with private link names over a hand-written C or JS leaf. None is installed at a real CCL symbol; every README says so. Every unit ends "no LL15 credit".
- L-4. The retained startup worklist (LL15-b/c) is 16,169 functions in 167 compilation units.

## 3. Measurement

Instrument: `doc/WASM/stage1/bootstrap-throughput/measure.lisp`, run by `run.py` beside it through the retained compile driver, on the pinned kernel and image, with the compiler at a8a35ea9 unchanged. It is a reviewer instrument, not evidence; it has no packet.

Method. Every top-level `DEFUN` in `level-0/*.lisp` and `level-1/*.lisp` is read with the features `setup-target-features` would give the Wasm backend, wrapped as a `LAMBDA`, and passed to `compile-call-form`. Every function it calls is supplied as a call link under a generated legal name, so linking is never the reason for refusal. A function counts as admitted when `compile-call-form` returns without `UNSUPPORTED-WASM32-CODE`. Admitted does not mean it executes or matches native.

| Tier | Change made by the instrument before compiling | level-0 (813) | level-1 (2,010) | Total (2,823) |
|---|---|---|---|---|
| A | none; CCL callees linked | 45 | 133 | 178 (6.3%) |
| B | A, and CL functions linked too | 80 | 199 | 279 (9.9%) |
| C | B, and non-`SPECIAL` declarations removed | 109 | 266 | 375 (13.3%) |
| D | C, and `MACROEXPAND-ALL` applied first | 166 | 518 | 684 (24.2%) |
| E | D, and `(THE type x)` replaced by `x` | 233 | 708 | 941 (33.3%) |

Refusal codes at tier A: `:B-SOURCE` 1,645; `:B-DECLARATION` 408; `:B-CONDITION-ASSERTION` 362 (this code is raised for any `THE` other than `(THE LIST x)` inside a condition expansion, `wasm32-backend.lisp:2240`); `:B-CONDITION-GENERATED-FORM` 190; all other codes 40.

What the 1,882 functions still refused at tier E contain (categories overlap; a function can be in several):

| Count | Contains |
|---|---|
| 997 | a reference to a proclaimed special variable not declared `SPECIAL` in the lambda |
| 854 | a quoted symbol other than NIL or T |
| 581 | a reference to a named constant |
| 211 | an operator outside the validator's list after expansion: `LOAD-TIME-VALUE` 111, `SETF` 64 (left by an expansion the walker could not finish), `COMPILER-LET` 16, others under 12 each |
| 157 | a quoted list |
| 102 | `SETQ` of a special variable |
| 197 | none of the above |

Caveats. M-C1: top-level forms are split at column-0 parentheses; a form the reader rejects is skipped. M-C2: `level-0` includes x86-specific files whose functions the port will never compile. M-C3: tiers C to E change the source before compiling; they measure what the front end would admit if it handled those constructs, not what it handles. M-C4: only `DEFUN` is counted; `DEFMETHOD`, `DEFMACRO`, top-level `SETF` and `DEFSETF` forms are not. M-C5: the numbers are an order of magnitude, not a gate value.

## 4. Reading of the cause

- D-1. `validate-b-source` (`wasm32-backend.lisp:1668`) is a whitelist over source as written, applied before CCL's front end runs. It admits about thirty heads (`LET`, `IF`, `CAR`, `CONS`, `FUNCALL`, `UNWIND-PROTECT` and so on). It does not expand macros, so `WHEN`, `COND`, `SETF`, `DOLIST` and `PUSH` in a function body are refusals. Units have been working round this by expanding selected macros themselves (`population-consumers/lower.lisp`).
- D-2. Atoms are admitted only if NIL, T, a 30-bit integer, a pool literal, a registered keyword or a lexical variable. A free special variable, a quoted symbol and a named constant are therefore refusals, although symbols and bindings (S1-LL09-a, S1-LL17-a) and constant pools (S1-LL10-a) are accepted and integrated.
- D-3. Call-link names are limited to `[a-z0-9_-]` (`compile-call-form`, line 2464). `%car`, `*foo*` and `(setf x)` cannot be named, so generated code cannot be installed at, or call, real CCL symbols by name.
- D-4. Because of D-1 to D-3, each bootstrap effect has been delivered as a new leaf in C or JS plus a selected lambda, instead of by compiling the function CCL already has. `lib/misc.lisp:712-724` (three ordinary functions) became a C service, an adapter, three entries and a source rewriter.
- D-5. Review contributed. Audits 137 to 140 spent four rounds on refusal-test gaps in three small services; about sixty single-clause mutants found no service defect, and each finding drew another packet. Claude was checking that tests were airtight and not asking whether the unit moved L-1 or section 3.

## 5. Directive

- BT-1. Headline metric. Report two numbers in `STATUS.md` and in each unit README that touches the compiler or LL15: functions of the denominator that the unchanged compiler admits as written (tier A of the instrument, or Codex's better instrument), and functions that execute and match the native oracle. Denominator now: the 2,823 `DEFUN`s of M; as soon as practical, the 16,169-function startup worklist of L-4. A unit that moves neither number says so in its first line.
- BT-2. Work the front end in order of measured yield. Suggested order, each with its evidence: (a) validate after macroexpansion, or on acode, instead of on raw source (+10.9 points D over C, and it removes the need for per-unit walkers); (b) `THE` (+9.1 points E over D; 910 functions carry it after expansion); (c) accept the standard declarations, honouring or ignoring `TYPE`, `FIXNUM`, `IGNORE`, `IGNORABLE`, `DYNAMIC-EXTENT`, `OPTIMIZE`, `INLINE`, `NOTINLINE` (+3.4 points C over B); (d) free special references and `SETQ` of specials (997 and 102 functions); (e) quoted symbols and lists through the accepted symbol and pool machinery (854 and 157); (f) named constants (581), see BT-H1; (g) `LOAD-TIME-VALUE` (111). Codex may reorder with reasons.
- BT-3. Real names. Lift the link-name restriction so a generated function can be installed at, and can call, any CCL function name including `(SETF name)`. The encoding of names in Wasm import and export strings is Codex's design; the requirement is that no unit needs private names such as `pop_contents` to stand for `POPULATION-CONTENTS`.
- BT-4. Compile CCL's definitions, do not rewrite its consumers. Where the target representation differs from native (strong populations, the TCR, hash vectors), express the difference where CCL expresses target differences: accessor definitions, target constants and `#+wasm-target` branches of the defining function. A source walker over consumers is test scaffolding and is not integrated.
- BT-5. Leaves. Write a leaf in C or JS only where Lisp cannot be the implementation on this port: the collector, memory and atomics primitives, host providers, float and bignum kernels already accepted. A leaf that re-implements a Lisp function CCL already defines needs a sentence saying why compiling that function is not possible yet, and which BT-2 item would make it possible.
- BT-H1. Hazard to check before BT-2(f). Native sources name layout constants through the `TARGET` package nickname. Read on the macOS host outside `with-cross-compilation-target`, `target::node-size` is `X8664::NODE-SIZE` (8), as the retained `native-forms.lisp` of STAGE1-STARTUP-REVIEW-137-R1 shows for the native oracle. For generated Wasm code the constant must come from `compiler/WASM32/wasm32-arch.lisp`. State where the compile path binds the nickname, and add one directed case that would fail if a host constant leaked.
- BT-6. What does not change: macOS U1 as the only reference; R6 and R6a; packets, pins and replay; the native oracle for every behavioural claim; Claude reviews before integration; acceptance and slot credit are the user's. The admission-predicate rule added to `CLAUDE.md` in 30ce60dc stays for code proposed for integration.

## 6. Review changes (Claude's commitments, effective now)

- R-1. Each audit opens with scope and throughput: does the unit belong on the hosts, and what does it move in L-1 or BT-1. Correctness follows.
- R-2. A gap in the testing of a refusal of malformed input is recorded as a carry item. Codex closes carry items inside its next packet. Claude does not recommend a dedicated follow-up packet for them and Codex need not produce one.
- R-3. Full single-clause mutant sweeps are run once, on the packet proposed for integration, not on each proposal round.
- R-4. A finding recommends a dedicated follow-up only if the service is wrong, a stated claim is false, the unit is out of scope, or the evidence chain does not bind.
- R-5. Claude reruns the instrument of section 3 at each audit that touches the compiler and records the tier-A number in the audit.

## 7. Questions for Codex

- Q-1. Is the source whitelist of D-1 deliberate staging with a planned replacement, or the intended final admission mechanism? If staging, what replaces it and when?
- Q-2. CCL's front end already reduces all of this source to acode. What stops admission being defined as coverage of acode operators, with `validate-b-source` retired?
- Q-3. Is any number in section 3 wrong, or made unfair by the method (M-C1 to M-C5)? Supply a better instrument if so; it replaces this one.
- Q-4. Which BT-2 items are cheap, and which need a decision record or a change to an accepted contract?
- Q-5. BT-H1: where is the `TARGET` nickname bound during a Wasm compile today?
- Q-6. Which already-reviewed leaves (hash, equality tables, population access, statistics, startup inputs) would Codex keep as C or JS under BT-5, and which become compiled Lisp once BT-2 lands?
- Q-7. What is the shortest path from here to one real `level-0` file compiled whole, installed at its real symbols, and executed against native? Name the file.

## 8. Review record

Adopted by the user on 2026-09-21: “remember that and proceed”. The user further requires generated Lisp to resemble idiomatic CCL. This direction changes implementation priority, not acceptance of any pending unit.

Codex reproduced all five historical totals. They are diagnostic proxies, not a strict as-written baseline: the instrument uses SUBLIS on the whole form, including quoted data, and silently skips read failures. Its TARGET feature list also does not rebind the TARGET package while reading. A replacement must preserve source identities, bind target context before reading, retain every skip, and compare baseline and proposal on the same inventory. Compilation success does not imply executable dependency closure.

Q-1/Q-2: the whitelist was deliberate staging, protecting against host compiler-macro folding before acode validation. It is not the final front end. The next proposal uses CCL's actual front end (including lexical macro environments), disables host compiler macros at this boundary, and retains emitter refusal for unsupported acode. Legacy entry points remain unchanged. This is a trusted bootstrap-source compiler, not an untrusted macro sandbox.

Q-3/Q-4: general macro admission comes first. THE and declarations must retain CCL semantics, not be blanket-erased to inflate throughput. Special and constant admission needs owner identity and target-context checks; LOAD-TIME-VALUE needs a lifecycle contract. BT-3 requires symbol identity plus a safe wire encoding, not simply a wider name regexp. SETF function names remain an explicit obligation until their identity path is implemented.

Q-5: CALL-WITH-TARGET invokes WITH-CROSS-COMPILATION-TARGET, which rebinds TARGET to WASM32. The legacy string entry reads before this binding. The new source entry must read inside it. A directed NODE-SIZE test must produce 4 rather than the host's 8.

Q-6: retain collector, memory, atomics, numeric kernels and host acquisition at the low-level boundary. Compile population accessors, list algorithms, table policy and startup bookkeeping from CCL sources as the front end admits their dependencies. The native three-field population shape (zero GC link, type, data) supersedes the proposed two-field design; trace type and data strongly in Stage 1. Do not integrate that design or its consumer rewriter as-is.

Q-7: level-0/l0-symbol.lisp is a useful first whole-file target, not yet a demonstrated shortest path. Its accessor, constant, special-variable and dependency closure must be measured. Start execution with original MEMQ/ADJOIN definitions and ordinary list routines, not new handwritten substitutes. No whole-file or LL15 completion is claimed by this adoption.

