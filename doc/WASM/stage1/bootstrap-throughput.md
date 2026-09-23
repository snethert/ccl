# Bootstrap throughput directive (BOOT-TP-P2)

Status: P1 direction ADOPTED by the user on 2026-09-21, with Codex’s review corrections in section 8. P2’s BT-0 criterion change was explicitly accepted by the user: “I accept BT-0”. The authorization and preservation checks are in bootstrap-coverage-decision.json. The directive changes work priorities and review cadence; existing acceptance contracts remain in force.

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

Pass 2 without the whitelist (added in P2). With `validate-b-source` replaced by a no-op and all callees linked, the unchanged compiler lowers 456 of 2,823 as written (tier F, 16.2%) and 486 with declarations removed (tier G, 17.2%). The leading refusals are then pass-2 gaps, not the validator: `:HEAP-CONSTANT` 387 (quoted symbols and lists), `:B-CONDITION-ASSERTION` 367, acode `OR` 178, `:B-UNDECLARED-SPECIAL` 166, `%SVREF` 145, `NOT` 142, `%GVECTOR` 98. Tier E scores higher than G only because `MACROEXPAND-ALL` rewrites `OR` and `NOT`-bearing macros into `IF` and `LET`. Of the 267 operator names in `*nx1-operators*`, 49 appear in `wasm32-backend.lisp`; `outline.md:75` records 217 handled by x862 and 211 by arm642, and `outline.md:69` says Wasm needs a complete pass 2 for roughly the full surface.

Caveats. M-C1: top-level forms are split at column-0 parentheses; a form the reader rejects is skipped. M-C2: `level-0` includes x86-specific files whose functions the port will never compile. M-C3: tiers C to E change the source before compiling; they measure what the front end would admit if it handled those constructs, not what it handles. M-C4: only `DEFUN` is counted; `DEFMETHOD`, `DEFMACRO`, top-level `SETF` and `DEFSETF` forms are not. M-C5: the numbers are an order of magnitude, not a gate value.

## 4. Reading of the cause

- D-1. `validate-b-source` (`wasm32-backend.lisp:1668`) is a whitelist over source as written, applied before CCL's front end runs. It admits about thirty heads (`LET`, `IF`, `CAR`, `CONS`, `FUNCALL`, `UNWIND-PROTECT` and so on). It does not expand macros, so `WHEN`, `COND`, `SETF`, `DOLIST` and `PUSH` in a function body are refusals. Units have been working round this by expanding selected macros themselves (`population-consumers/lower.lisp`).
- D-2. Atoms are admitted only if NIL, T, a 30-bit integer, a pool literal, a registered keyword or a lexical variable. A free special variable, a quoted symbol and a named constant are therefore refusals, although symbols and bindings (S1-LL09-a, S1-LL17-a) and constant pools (S1-LL10-a) are accepted and integrated.
- D-3. Call-link names are limited to `[a-z0-9_-]` (`compile-call-form`, line 2464). `%car`, `*foo*` and `(setf x)` cannot be named, so generated code cannot be installed at, or call, real CCL symbols by name.
- D-4. Because of D-1 to D-3, each bootstrap effect has been delivered as a new leaf in C or JS plus a selected lambda, instead of by compiling the function CCL already has. `lib/misc.lisp:712-724` (three ordinary functions) became a C service, an adapter, three entries and a source rewriter.
- D-5. Review contributed. Audits 137 to 140 spent four rounds on refusal-test gaps in three small services; about sixty single-clause mutants found no service defect, and each finding drew another packet. Claude was checking that tests were airtight and not asking whether the unit moved L-1 or section 3.

- D-6 (P2). The earlier accepted Stage 1 units are not defective, and the contract work in them (layout, call protocol, exceptions, bindings, closures, pools, collector, installer, materialization) does not depend on how much source is admitted. Each was, however, proven through the same dialect: about thirty source heads and 49 operators. A contract such as LL06-a (temporaries live across collection) or LL19-a (cleanup and restoration) holds for the operators that existed when it was accepted and has to be re-exercised as allocating and non-local operators are added.
- D-7 (P2). Four accepted units are C implementations of things CCL implements in Lisp: `symbols.c` (INTERN, FIND-SYMBOL, MAKE-SYMBOL; native `l0-symbol.lisp`, `l1-symhash.lisp`), `integer.c` and `float.c` (native `l0-bignum32.lisp`, `l0-float.lisp`, `l0-numbers.lisp`), `hash.c` (native `l0-hash.lisp`). Checked: they operate on native-shaped objects (hash vector subtag 74 with the native `nhash.vector` field offsets, native package tables), so they do not block the Lisp definitions. They are bounded (fixed capacity, 1,024 limbs, sealed package topology, a numeric subset). Each will meet its Lisp twin when level-0 compiles, and each then needs a decision: stay as the primitive beneath the Lisp function, as LAP does natively, or retire.
- D-8 (P2). The structural cause is the Stage 1 inventory, which Claude drafted on 15 September and the user adopted. It has a variant for each contract and none for compiler coverage. The largest piece of Stage 1 work is inside the single line S1-LL15-a, so the ledger could reach 21 of 31 with pass 2 at 49 of 267 operators, and nothing in the ledger asked for more. Codex followed the ledger. The omission is Claude's.

## 5. Directive

- BT-1. Headline metric. Report two numbers in `STATUS.md` and in each unit README that touches the compiler or LL15: functions of the denominator that the unchanged compiler admits as written (tier A of the instrument, or Codex's better instrument), and functions that execute and match the native oracle. Denominator now: the 2,823 `DEFUN`s of M; as soon as practical, the 16,169-function startup worklist of L-4. A unit that moves neither number says so in its first line.
- BT-0 (P2). Proposed criterion change, needing the user's explicit authorization under S1-LL24-a: add coverage variants to the Stage 1 inventory so the ledger shows the work. Suggested: S1-LL15-c, every acode operator produced by compiling the retained startup worklist has a pass-2 lowering, reported as a count against the census operator list; S1-LL15-d, every function of the worklist compiles as written with no source rewriting, reported as a count. Both are counts that rise per commit, not pass/fail at the end. Codex is asked for better wording.
- BT-2. Work the front end in order of measured yield. Suggested order, each with its evidence: (a) retire the raw-source whitelist in favour of CCL's front end and admit by acode operator, lowering `OR`, `NOT`, `%SVREF` and `%GVECTOR` first (tiers F and G show the whitelist hides these pass-2 gaps; +10.9 points D over C is what expansion alone gives, and it removes the need for per-unit walkers); (b) `THE` (+9.1 points E over D; 910 functions carry it after expansion); (c) accept the standard declarations, honouring or ignoring `TYPE`, `FIXNUM`, `IGNORE`, `IGNORABLE`, `DYNAMIC-EXTENT`, `OPTIMIZE`, `INLINE`, `NOTINLINE` (+3.4 points C over B); (d) free special references and `SETQ` of specials (997 and 102 functions); (e) quoted symbols and lists through the accepted symbol and pool machinery (854 and 157); (f) named constants (581), see BT-H1; (g) `LOAD-TIME-VALUE` (111). Codex may reorder with reasons.
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
- Q-8 (P2). D-7: for each of the four C leaves, which way does Codex expect it to go when its Lisp twin compiles?
- Q-7. What is the shortest path from here to one real `level-0` file compiled whole, installed at its real symbols, and executed against native? Name the file.

## 8. Review record

Adopted by the user on 2026-09-21: “remember that and proceed”. The user further requires generated Lisp to resemble idiomatic CCL. This direction changes implementation priority, not acceptance of any pending unit.

Codex reproduced all five historical totals. They are diagnostic proxies, not a strict as-written baseline: the instrument uses SUBLIS on the whole form, including quoted data, and silently skips read failures. Its TARGET feature list also does not rebind the TARGET package while reading. A replacement must preserve source identities, bind target context before reading, retain every skip, and compare baseline and proposal on the same inventory. Compilation success does not imply executable dependency closure.

Q-1/Q-2: the whitelist was deliberate staging, protecting against host compiler-macro folding before acode validation. It is not the final front end. The next proposal uses CCL's actual front end (including lexical macro environments), disables host compiler macros at this boundary, and retains emitter refusal for unsupported acode. Legacy entry points remain unchanged. This is a trusted bootstrap-source compiler, not an untrusted macro sandbox.

Q-3/Q-4: general macro admission comes first. THE and declarations must retain CCL semantics, not be blanket-erased to inflate throughput. Special and constant admission needs owner identity and target-context checks; LOAD-TIME-VALUE needs a lifecycle contract. BT-3 requires symbol identity plus a safe wire encoding, not simply a wider name regexp. SETF function names remain an explicit obligation until their identity path is implemented.

Q-5: CALL-WITH-TARGET invokes WITH-CROSS-COMPILATION-TARGET, which rebinds TARGET to WASM32. The legacy string entry reads before this binding. The new source entry must read inside it. A directed NODE-SIZE test must produce 4 rather than the host's 8.

Q-6: retain collector, memory, atomics, numeric kernels and host acquisition at the low-level boundary. Compile population accessors, list algorithms, table policy and startup bookkeeping from CCL sources as the front end admits their dependencies. The native three-field population shape (zero GC link, type, data) supersedes the proposed two-field design; trace type and data strongly in Stage 1. Do not integrate that design or its consumer rewriter as-is.

Q-7: level-0/l0-symbol.lisp is a useful first whole-file target, not yet a demonstrated shortest path. Its accessor, constant, special-variable and dependency closure must be measured. Start execution with original MEMQ/ADJOIN definitions and ordinary list routines, not new handwritten substitutes. No whole-file or LL15 completion is claimed by this adoption.


### P2 review (34f3868f)

Codex recommends approval, with coverage measured against acode actually emitted
by the target-read startup worklist, including operand/flag variants, rather than
textual mentions of operator names. Report unchanged-source compilation and
native-matched execution separately. The two new criteria need terminal acceptance
conditions as well as progress counts; a correctness-fix commit may legitimately
leave either count flat. New allocating and nonlocal operators must exercise
movement and unwinding, not inherit a whole-backend guarantee from earlier units.
The user subsequently stated “I accept BT-0”. The inventory now includes
S1-LL15-c/d with terminal acceptance conditions and progress counts. All 31 prior
criteria and all 21 accepted results are preserved byte-for-byte at record level.

Q-8: move symbol/package and hash policy to the native Lisp definitions as their
dependencies become compilable. Keep the current services available until those
replacements are qualified. Numeric C kernels may remain target primitives where
measurement supports that choice, with Lisp owning the surrounding policy. No
service is retired or its declared bounds promoted by this recommendation.

### P3 (Claude, 21 September, after audit 143) — adopted by the user

Relayed user direction, given while audit 143 was running: U-4 “Ask CODEX to accomplish more work next time.” U-5, on SYMBOLP reading as an empty body: “Why not WASM32 compiler flags?!?” U-6 “Eventually we HAVE to change CCLs source to be properly integrated”.

- BT-7. Packet size. A packet carries a file's worth of work, not an operator's: the operators a chosen CCL file needs, that file compiled whole, and every dependency-closed definition in it executed against native. Report admitted, closed and executed; executed is the headline. Evidence stays proportional: R6 reused by compiler hash, one native rebuild per compiler change, unchanged parents bound by hash and not re-run.
- BT-8. Target branches go in CCL's files. Where a definition's body is selected by per-target reader conditionals, the deliverable is a `#+wasm32-target` branch in that file, and `level-0/WASM32/` holds what native ports write in LAP. This is additive shared-source work under the 16 September authorization, with R6 and R6a; every other target's reader skips the branch. “Shared source untouched” is no longer reported as a merit for such definitions. Tree size: 86 `x8664-target` sites in `level-0`, `level-1` and `lib`; 258 x8664 LAP functions.
- BT-9. The measure refuses, and does not count, a definition whose body is empty under the target read and non-empty under the native read, and a definition whose only body form is a call to itself for which pass 2 has no lowering (audit 143 F1, F2).


P3 adoption (2026-09-21): the user answered “Accept the lowering and adopt P3”. BT-7 through BT-9 now govern the next implementation packet. This also accepts the reviewed values lowering; it does not accept the two defective coverage counts from audit 143.

### P4 (Claude, 23 September, after audit 164) — adopted with identity corrections

Relayed user direction, given after audit 164: U-7 “validation runs are getting very long and expensive”, then “record it”.

Measured cost per delta packet at the class-table packet: whole-corpus compile in a disposable U1 (2,231 definitions, ~4,700 modules) 6–8 min; execution of ~6,500 cases at two placements before and after movement ~10 min; native R6/R6a ~10 min when a CCL source changes; and the pipeline is paid at least twice — the author's clean run and the reviewer's from-scratch replay — plus one full compile per probe attempt. For a packet that adds four callers and changes no compiler or runtime byte, all but a minute of that re-proves rows whose binaries, service binaries and harness files are hash-identical to the previous packet's.

- BT-10. Execution provenance. A row whose module binary, service binaries (`collector`, `integer`, `float`, `hash`, `hash-adapter`, `detector`, `eql`, `stub`), install and check files are hash-identical to those of a previously executed packet is bound to that execution by reference (packet id, artifact hashes) and is not re-executed. A packet executes its new and changed modules, plus a regression sample of bound rows (fixed size, seed recorded). The determinism the packets already assert by hash makes this the same evidence stated once.
- BT-11. Compile cache. Module compilation is keyed by compiler hash, mode, driver hash and source-file hash; a delta packet rebuilds only modules whose key changed and records the keys, so a full rebuild reproduces the cache. The whole-corpus compile becomes the exception (compiler, runtime or driver change), not the rule.
- BT-12. Probe support. The packet retains the compiled compiler (`compiler.dx64fsl`) and its driver so a probe compiles only its own forms against the retained modules. Probes are batched — one compile per audit — and follow the recorded hygiene: names joined to the explicit execution list, CCL-internal names package-qualified, no object-valued returns (return `CLASSP` and the like), `#+wasm32-target` guards for cases that diverge natively by design, single-input callers where a named cell is created.
- BT-13. One clean run per packet, tiered review. The author's retention is the from-scratch run (`execution_rebuilt: true`; `--reuse-output` validation is not retention). The reviewer's replay is tiered and the tier is stated in the audit: Tier 0, identity — packet, index, catalog and pin hashes, integrated bytes equal to proposal bytes — always; Tier 1, focused execution from the retained artifacts of the new and changed rows plus a sample, after verifying the artifacts' listed hashes — every packet; Tier 2, full from-scratch replay — when the compiler, runtime or drivers change, at integration of such a change, or when Tier 0/1 disagree with the record. Two full pipelines on one unchanged-compiler packet is the case to stop.
- BT-14. Native R6/R6a is unchanged: rebuilt once per CCL-source change, reused by proposal-manifest hash otherwise.

Expected effect for a delta packet: author ~30 min → ~5; reviewer ~20 min plus 8 per probe attempt → ~3 plus one 8-minute probe compile until BT-12 lands, then ~1. BT-10, BT-11 and BT-12 are one implementation packet for Codex; BT-13 and BT-14 take effect at the next audit.

#### P4 addendum (Claude, 23 September, same day) — measured phases, BT-15, and what the cost does not say

Relayed user question, after P4: “Should I be concerned about the execution speed of our generated code? Is our design inefficient? Is startup impossibly slow? Why do the tests take so long?” then “record it”.

Measured from the file birth and modification times of the audit-164 from-scratch replay of `2026-09-23-stage1-class-table-r1` (`packet.py verify`, 16-core macOS host, every phase single-threaded):

| phase | wall | shape |
|---|---|---|
| native CCL: load compiler, cross-compile 3,494 modules, emit 4,767 `.wat` | 2 min 42 s | one Lisp process |
| `wat2wasm` × 4,767 | 1 min 34 s | one subprocess per file, sequential |
| Node: 6,496 rows | 5 min 24 s (~50 ms per row) | sequential; per row a fresh worker, `WebAssembly.Module` compile of the module and services, projection of a 400–750-node native graph into linear memory, run, collection, whole-graph read-back and JSON comparison |
| checks and hashing | 13 s | 14,388 artifacts, 823 MB |
| whole `verify` | ~10 min | |
| one probe attempt | 4 min 13 s compile + 2 min 17 s execution | recompiles the corpus for two forms |

The author's ~30 min is this pipeline plus native R6/R6a and catalog work.

Answers, so they are not re-derived:

- **Generated-code speed: no evidence either way, and the suite does not measure it.** The Lisp work per row is microseconds inside ~50 ms of harness. The emitted design carries no known pathology (tagged fixnums and linear-memory objects as native CCL, direct calls, checked exceptions only on refusal paths, the collector as a separate module). The first meaningful benchmark is the first thing that runs long: cold-boot-init of an image, or one file compiled on the target. It is stated when the image/READY join lands, not before.
- **The inefficient design is the validation's, not the port's.** The suite is cumulative and from-scratch: 16 new comparisons cost 25,984 executions because no inherited row is ever dropped and nothing is cached. BT-10–12 are the remedy.
- **Startup: unmeasured; no image exists yet.** Per-row graph projection is not startup. The one startup question the current shape raises: the compiler emits 4,767 separate modules per corpus. If the shipped image is thousands of modules rather than one or a few, instantiation count will dominate browser startup (an engine compiles one large module on its own threads; it does not amortize thousands of small ones). Decision owed at the image/READY join: module granularity of the shipped image, with a measured instantiation time for the chosen shape.
- **Why the tests take so long:** no compile cache (BT-11), no execution provenance (BT-10), probes that rebuild the corpus (BT-12), and no parallelism at any stage with 16 cores idle.

- BT-15. Parallel drivers. `wat2wasm` runs in a process pool and rows execute across N workers (rows are already isolated in workers, so ordering is a sort at the end, not a change to any comparison); N is recorded in the packet. Deterministic artifacts are unchanged by construction, which the existing hash assertions show. Expected on its own: ~10 min → ~3 for a full replay; combined with BT-10/11, a delta packet's execution is seconds. Part of the same implementation packet as BT-10–12.

#### Codex review of P4 (23 September)

Read from `a0b2fb05` and `bbafc488` at the user's request before continuing
testing; imported verbatim, without changing their awaiting-adoption status.
The active class-growth packet changes the compiler and drivers and therefore
warrants a full run even under the proposed tiers. It uses four WABT assembly
workers and retains the actual compiled compiler and generated drivers for
review. This does not yet implement the compile cache or focused probe runner.

One correction to the measured-phase explanation: the retained class-table
`check.mjs` creates two Workers sequentially, one per placement. Each installs
the generated modules once, then loops over the corpus. Case resets reconstruct
services and state; graph projection, collection and read-back recur. Rows are
not currently separate Workers. Parallel row partitions need an explicit reset
contract and comparison against the sequential result; sorting alone does not
establish isolation. The reported wall times remain observations, and the
proposed speedups remain estimates.

For BT-10, execution identity must include the row's inputs, expected results,
globals, pools and class graph, mode/FP word, placement and movement settings,
engine identity, and all harness dependencies (including graph codecs), as well
as modules and services. BT-11 likewise needs the target architecture and the
complete compile-file environment and dependencies, not just an individual
definition's source hash. Those additions preserve the file-environment fix
from audit 157 and prevent cache reuse from hiding a changed oracle or setup.
No execution credit is reused by a partial key in the current packet.


#### P4 adoption and implementation selection (23 September)

The user instructed Codex: “PLEASE IMPLEMENT THIS PLAN: P4: faster validation
and focused review probes”. This adopts P4 with the complete-environment and
execution-identity corrections above. The selected implementation caches whole
CCL compiler sessions, preserves file compilation, separately caches WABT, and
uses explicit build, oracle, probe, execution and retention entry points. The
regression sample is 32 unchanged rows with seed `0x42545034`. Execution and
WABT default to four isolated workers/jobs. Identity validation reports zero
new execution; changed compiler, runtime or shared-driver identities force a
full corpus execution. No speedup guarantee, generated-code performance claim,
new original-definition execution or LL15 slot credit follows from this work.

The tooling packet is `tests/wasm/stage1/bootstrap-validation`. The pending
class-growth compiler/runtime proposal remains unchanged. Cross-dumped class
objects, READY and production module granularity remain runtime work.

#### Claude, after audit 165 (23 September) — corrections accepted

- The addendum's per-row description was wrong: `check.mjs` runs one Worker per placement, each installing once and looping the corpus, as Codex says (verified in the audit-164 replay's `check.mjs:16-22`). BT-15's row half is therefore conditional on a reset contract with a comparison against the sequential result; its `wat2wasm` half stands and is already paid for — measured 1 min 34 s → 30 s with Codex's four workers at audit 165.
- BT-10's execution key and BT-11's compile key are read with Codex's additions (inputs, expected results, globals, pools, class graph, mode word, placement and movement settings, engine identity, harness dependencies including graph codecs; target architecture and the whole `compile-file` environment). A partial key reuses no credit.
- Tier 2 measured at audit 165: full replay 12 min; three probe compiles at ~4 min each plus ~4 min execution — the probe cost BT-12 is for. One further reviewer rule from those probes: a target-only value needs its expectation stated on the `#-wasm32-target` side, and a native witness for a condition class the packet has not yet signalled needs the native pre-initialisation `inputs.lisp` already uses.

### P5 (Claude, 23 September, after audit 166) — output and evidence retention — awaiting adoption

Relayed user direction, given during audit 166 when the disk filled: U-8 "You have created REAMS of evidence. 100s of GB. You need to figure out a better system for managing old tests." then "That was not enough!" and "Zip?".

Measured at that moment: `/private/tmp` held 238 GB in 2,697 `ccl-*` entries — every build, replay, probe and cache output either agent had written since 12 September, none deleted — plus 74 GB in Claude's scratchpad (three per-audit replays and per-probe copies of the review tree) and 10 GB in two dead Claude sessions' scratchpads; `ccl-evidence` holds 26 GB in 460 directories, 540 MB of it one compressed compiler session. The volume had 138 MB free. Deleting everything under `/private/tmp` older than two hours and the scratchpads freed 227 GB; nothing retained was touched.

The cause is structural, not one run: outputs are written to ad-hoc `/tmp` names, nothing deletes them, and every reviewer replay copied whole trees. Rules:

- BT-16. Outputs are disposable and self-deleting. Every build, replay, probe and qualification output lives under one root, `/private/tmp/ccl-work/<agent>/<packet-or-audit>/`, never an ad-hoc `/tmp` name. The command that retains a record deletes the tree it retained from (`packet.py retain`, and `verify` after it has written its report and sidecar); a `gc` entry point in the validation tooling deletes anything under that root older than 24 hours and is run by both agents before starting work. A tree that must outlive its run is a retained packet, not an output.
- BT-17. One shared, bounded cache per machine. The session and WABT caches are content-addressed and every entry is verified by manifest and hash on read, so author and reviewer share `~/Library/Caches/ccl-wasm-validation`; private caches and cache copies are not made. `gc` keeps the newest two sessions and trims WABT entries to 2 GB, oldest first.
- BT-18. A packet retains what cannot be regenerated and references what can. Retained: oracle rows, execution reports and sidecars, review inputs (probe sources, inputs, results), development failures, hashes of everything. Referenced by hash, not stored: compiled modules, assembled binaries and compiler sessions that a cold build reproduces (measured 6.5 minutes) — the current parent's session may be kept for `restore`; when a packet stops being the parent its `session.tar.gz` and module archives are removed from the store and their hashes stay in `packet.json`. Target for `ccl-evidence`: under 10 GB. Existing packets are trimmed under the same rule in one catalogued pass, oldest first, with the catalog and `repository.json` updated in the same commit.
- BT-19. Reviewer discipline. Claude copies no tree: `restore` into the shared cache, probes through the runner, focused execution by `--indices`, delete the output at the end of the audit; the audit records hashes and counts, not paths to trees. Scratchpad under 1 GB at all times; anything larger is a mistake to fix before continuing.
- Zip: not for outputs — they are reproducible and a restore is faster than an unzip. For the evidence store, superseded packets that BT-18 has trimmed may be moved as one archive per month to external storage with the archive's hash recorded in the catalog; that is the only place compression belongs.

BT-16 and BT-17 are one small change to the validation tooling (an output root, deletion after retention, `gc`); BT-18 is one catalogued pass over the store; BT-19 takes effect at audit 167.


#### P5 implementation selection (Codex, 23 September)

Steve instructed “proceed” after the cleanup report and the proposed next
step: fix the execution manifest and implement P5 cleanup, with rebuild-aware
verification preceding evidence-store trimming. The validation commands now
use managed output roots and a shared bounded cache. Leases protect active
commands. Retention validates the destination before deleting its source.
For investigations using repeated `--indices`, plain verification keeps the
run until explicit `finish` (or `--retain-to` on the final command); a report
alone is not durable retention. This preserves BT-19's in-place workflow.
The old evidence store is not trimmed until its archive-dependent verifiers
can regenerate or retrieve elided inputs. The under-10-GB target remains owed.
