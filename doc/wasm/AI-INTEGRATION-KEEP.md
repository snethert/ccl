# KEEP: AI Integration Brainstorm and Design Notes

Status: KEEP DRAFT
Type: Design and brainstorming note (not a plan)
Sweep Policy: KEEP
Last Updated: 2026-02-17

## KEEP Notice

This is intentionally a thinking document.
It is not a roadmap, milestone chart, staffing plan, or compliance report.
It should stay readable and useful for creative design conversations.

## 1. What This Document Is

This doc answers one question:

How much AI can we realistically and creatively integrate into this web-based Lisp runtime and IDE without losing control or clarity?

This doc is meant to be:

1. concrete enough to act on,
2. simple enough to read quickly,
3. rich enough to spark new ideas.

## 2. Current Direction in Plain English

We now have a clear preferred mode:

1. high-quality remote model handles code and debugger operations,
2. local model does smart support work but does not touch code or debugger control directly.

That means:

1. local AI is a cognitive assistant,
2. remote AI is the heavy operator for hard technical actions.

## 3. 10-Second System View

The shortest useful mental model:

1. runtime emits state/events,
2. AI interprets and proposes next steps,
3. typed commands execute operations,
4. outcomes are recorded and replay-checked,
5. humans can intervene at any time.

The shortest useful role split:

1. Local AI: summarize, explain, compress, suggest.
2. Remote AI: diagnose deeply, control debugger flow, synthesize patches.
3. Human: approve, redirect, or halt.

## 4. What We Already Have (Core Concept Set)

These are the core ideas already established:

1. Restart-first debugging is the center of gravity.
2. Typed actions are better than free-form ad hoc action.
3. Replay and audit are non-negotiable.
4. Branching and rollback thinking is preferred over one-shot guessing.
5. Human override remains available.

Core operating loop already defined:

1. collect context,
2. form hypothesis,
3. plan action,
4. run action,
5. evaluate outcome,
6. continue, rollback, or escalate.

Core action families already defined:

1. inspect,
2. step,
3. breakpoint,
4. restart,
5. mutate state in bounded/reversible ways,
6. propose/apply patch when runtime repair is insufficient,
7. run tests and validate.

## 5. The Big Shift: Local AI as Cognitive Layer

The local model does not need to be weak.
It just needs to be aimed at the right job.

### What local AI should do

1. Keep the session understandable in real time.
2. Reduce context chaos.
3. Increase quality of escalations to remote engines.
4. Surface risks and contradictions early.
5. Help humans think faster.

### What local AI should not do in the current preferred profile

1. write source patches directly,
2. issue debugger control commands directly,
3. mutate runtime state directly.

## 6. Local Cognitive Roles (Detailed, Instant-Read)

Each role below is written so it is understandable immediately.

### 6.1 Session Narrator

What it does:
Keeps a live plain-language timeline of what happened.

Inputs:
events, transcript entries, command outcomes.

Outputs:
short running narrative and "current state" summary.

Why it matters:
prevents mental overload during long debugging sessions.

### 6.2 Problem Framer

What it does:
Turns vague intent into precise technical questions.

Inputs:
user text, current context snapshot.

Outputs:
clear problem statement and focused question set.

Why it matters:
better questions produce better remote-model answers.

### 6.3 Contradiction Detector

What it does:
Finds statements that conflict across docs, notes, and runtime behavior.

Inputs:
design text, session notes, observed outcomes.

Outputs:
list of contradictions with evidence snippets.

Why it matters:
many hard bugs hide behind conceptual contradiction.

### 6.4 Spec Gap Miner

What it does:
Finds undefined terms, missing semantics, and vague rules.

Inputs:
spec text and command/event schemas.

Outputs:
explicit gap list with suggested clarifying language.

Why it matters:
unclear specs create unstable implementation and unstable AI behavior.

### 6.5 Terminology Guardian

What it does:
Keeps naming and core concepts consistent.

Inputs:
docs, prompts, generated explanations.

Outputs:
normalization suggestions and term map.

Why it matters:
semantic drift causes expensive confusion later.

### 6.6 Decision Journaler

What it does:
Auto-captures decisions and why they were made.

Inputs:
session conversation, accepted/rejected options.

Outputs:
compact decision log.

Why it matters:
prevents repetitive rediscovery.

### 6.7 What-If Studio

What it does:
Simulates consequences of candidate ideas at design level.

Inputs:
candidate idea plus current constraints.

Outputs:
scenario cards with plausible consequences.

Why it matters:
safe exploration before expensive implementation.

### 6.8 Tradeoff Cartographer

What it does:
Makes tradeoffs explicit instead of implicit.

Inputs:
option set and target outcomes.

Outputs:
pros/cons and downside summaries per option.

Why it matters:
improves decision quality under uncertainty.

### 6.9 Prompt Compiler

What it does:
Builds high-signal escalation packets for remote models.

Inputs:
context snapshot, problem framing, evidence.

Outputs:
clean prompt packet for Claude/Codex.

Why it matters:
reduces wasted remote cycles and bad responses.

### 6.10 Context Compressor

What it does:
Continuously distills long sessions into compact state capsules.

Inputs:
transcript, events, decisions, outcomes.

Outputs:
short, current, high-value context summary.

Why it matters:
keeps handoffs fast and coherent.

### 6.11 Evidence Curator

What it does:
Organizes logs, traces, outcomes, and notes into coherent bundles.

Inputs:
artifact streams from runtime and session.

Outputs:
labeled evidence bundles.

Why it matters:
reproducibility and debugging quality both improve.

### 6.12 Incident Storyteller

What it does:
Converts noisy traces into readable incident narrative.

Inputs:
event sequence and failure records.

Outputs:
what happened, when, and why likely.

Why it matters:
accelerates triage and postmortems.

### 6.13 Explanation Layer

What it does:
Rewrites technical state for different readers.

Inputs:
diagnostics and technical traces.

Outputs:
audience-specific explanation variants.

Why it matters:
keeps communication quality high across skill levels.

### 6.14 Learning Coach

What it does:
Teaches concepts from real project incidents.

Inputs:
session history and outcomes.

Outputs:
targeted learning summaries.

Why it matters:
turns failures into compounding capability.

### 6.15 Discoverability Engine

What it does:
Suggests relevant internal artifacts while you work.

Inputs:
current focus + key terms.

Outputs:
ranked "read this now" suggestions.

Why it matters:
reduces search overhead and context switching.

### 6.16 Knowledge Graph Builder

What it does:
Maintains map of entities and relationships.

Inputs:
docs, commands, event types, concepts.

Outputs:
navigable concept graph.

Why it matters:
helps large-system reasoning stay coherent.

### 6.17 UX Copy Co-Author

What it does:
Drafts better runtime/debugger/user-facing wording.

Inputs:
current copy and real error contexts.

Outputs:
clearer microcopy candidates.

Why it matters:
great debugging UX depends on precise language.

### 6.18 Postmortem Drafter

What it does:
Creates first-pass retrospective from artifact bundle.

Inputs:
incident timeline, decisions, outcomes.

Outputs:
postmortem draft.

Why it matters:
shortens closure time after incidents.

### 6.19 Meeting Ghostwriter

What it does:
Turns session state into agenda, notes, and open questions.

Inputs:
current decision state.

Outputs:
planning artifacts.

Why it matters:
keeps momentum across sessions.

### 6.20 Creativity Partner

What it does:
Generates non-obvious design options.

Inputs:
goals and constraints.

Outputs:
brainstorm alternatives.

Why it matters:
prevents local maxima in design thinking.

## 7. System Status Manager (Local AI Opportunity)

Yes, this is a strong and realistic local-AI feature.

### What it is

A persistent, always-on "system health brain" that explains runtime condition continuously.

### What it watches

1. runtime event stream health,
2. queue/backpressure behavior,
3. command success/failure trend,
4. replay stability outcomes,
5. UI responsiveness signals.

### What it produces

1. current health state (`healthy`, `degraded`, `incident`, `recovering`, `unknown`),
2. top active risks,
3. probable causes,
4. "what changed recently",
5. suggested next checks.

### Why this is unique in your web runtime

Because your browser runtime naturally emits rich structured telemetry, this status manager can be both continuous and cheap.

## 8. Runtime Performance Tuning Manager (Local AI Opportunity)

This is another high-value non-code-control lane.

### What it is

A workload-aware tuning advisor that shifts runtime knobs based on active usage patterns.

### Workload classes

1. typing-heavy,
2. stepping-heavy,
3. replay-heavy,
4. background-job-heavy,
5. mixed contention.

### Tuning knobs it can recommend

1. queue/batch behavior,
2. coalescing aggressiveness,
3. scheduling bias,
4. telemetry sampling levels,
5. virtualization/cache pressure settings.

### Control loop

1. observe,
2. classify,
3. propose profile adjustment,
4. apply bounded change,
5. measure impact,
6. keep or revert.

### Why this is powerful

It lets the runtime adapt to real usage shape instead of static defaults.

## 9. Locale and App Asset Autoload Orchestrator (Local AI Opportunity)

This idea is strong and very web-native.

### What it is

A smart loader that predicts when locale assets should be fetched and activated.

### Signals it can use

1. explicit locale preferences,
2. current app/workspace context,
3. script/language in active content,
4. recent user session behavior.

### Assets it can coordinate

1. translation packs,
2. locale formatting rules,
3. IME-related support assets,
4. fallback font bundles,
5. app/domain glossary packs.

### What good looks like

1. fewer missing-locale moments,
2. less visible fallback behavior,
3. smoother language transitions.

## 10. Web-Native Opportunities You Get "For Free"

These are opportunities you have because this is browser runtime, not classic desktop runtime:

1. Worker-level isolation for speculative analysis tasks.
2. Cheap parallel local specialist agents.
3. Native rich telemetry streams.
4. Session persistence for durable cognitive continuity.
5. Offline-capable local cognitive assistance.
6. Strong interactive visual surfaces for status and explanation.
7. Shareable reproducibility capsules without full machine images.

## 11. Beyond What We Already Covered (New Idea Surface)

Further opportunities worth exploring:

1. Adaptive cost router:
   decide when to escalate to remote model vs stay local.
2. Drift sentinel:
   compare current behavior against healthy baseline patterns.
3. Replay critic:
   explain why replay diverged and where first divergence appears.
4. Compatibility sentinel:
   continuously test mixed protocol assumptions and raise warnings.
5. Quality narrator:
   convert raw quality signals into a concise confidence report.
6. Scenario simulator:
   "if we change profile X under workload Y, expected impact is Z."
7. Conversational control center:
   one NL surface for status, explanation, and next-step discovery.

## 12. Delegation Model (Simple and Explicit)

Preferred split right now:

### Local model

1. summarize and explain,
2. detect contradictions and gaps,
3. generate escalation packets,
4. propose performance/locale/status recommendations.

### Remote model

1. deep debugger strategy,
2. hard root-cause synthesis,
3. patch generation and high-impact technical decisions.

### Human

1. approve critical direction,
2. override model behavior,
3. halt or redirect sessions.

### Explicit Prohibition in This Profile

Local AI is explicitly prohibited from:

1. issuing debugger control commands,
2. issuing runtime mutation commands,
3. generating source patches for execution,
4. applying source patches,
5. selecting or invoking runtime restarts.

If any of those actions are needed, they are remote-model tasks (with human override available).

## 12.1 Remote Debugging Playbooks (Detailed)

These preserve the deeper coding/debugging brainstorming while honoring the local-model prohibition.

### Playbook A: Restart-First Recovery

Use when:

1. runtime halts on a recoverable condition,
2. restart metadata is available.

Remote model flow:

1. read condition summary, frames, locals, and restart set,
2. rank restart candidates by safety and expected success,
3. invoke top safe candidate through typed command path,
4. validate resumed state and immediate recurrence risk,
5. escalate to deeper analysis if instability remains.

Primary output:

1. restart choice + rationale,
2. post-restart verdict,
3. next step if unresolved.

### Playbook B: Step + Breakpoint Root-Cause Isolation

Use when:

1. restart attempts are inconclusive,
2. cause location is unclear.

Remote model flow:

1. install temporary diagnostic breakpoints (entry and/or exit),
2. run controlled stepping,
3. capture value transitions at critical boundaries,
4. identify first divergence ("first bad value"),
5. produce narrowed hypothesis set with confidence notes.

Primary output:

1. causal chain candidate,
2. minimum set of suspicious loci,
3. suggested repair path type (state repair vs patch).

### Playbook C: Reversible Runtime Repair Before Patching

Use when:

1. failure appears state-bound,
2. source change is not yet justified.

Remote model flow:

1. attempt reversible binding/place repair,
2. rerun focused scenario,
3. measure whether condition is removed and side-effects remain bounded,
4. keep as temporary mitigation or rollback and escalate.

Primary output:

1. mutation attempt record,
2. rollback/keep decision,
3. confidence in "state issue vs code issue".

### Playbook D: Patch Synthesis + Focused Validation

Use when:

1. runtime-level repair is insufficient,
2. root cause points to code defect.

Remote model flow:

1. generate minimal patch candidate first,
2. define expected behavior changes,
3. run targeted validation workload,
4. compare observed deltas with expected deltas,
5. accept or reject candidate.

Accept candidate when:

1. target condition resolves,
2. replay remains stable enough,
3. no major new regressions appear.

Reject candidate when:

1. failure shifts without net improvement,
2. risk surface grows significantly,
3. replay confidence collapses.

### Playbook E: Counterfactual Branch Analysis

Use when:

1. several plausible fixes compete,
2. wrong choice is expensive.

Remote model flow:

1. define alternative branch actions,
2. evaluate branches in controlled order,
3. score each by resolution quality and side-effect cost,
4. choose dominant branch and explain why.

### Playbook F: Incident Closure

Use when:

1. primary failure appears resolved.

Remote model flow:

1. run post-fix confidence probes,
2. verify no immediate recurrence patterns,
3. produce closure summary:
   cause, actions taken, alternatives rejected, residual risk.

## 12.2 Coding Opportunity Map (Remote-Only Coding Authority)

Coding-focused opportunities that remain in scope:

1. minimal patch generation for narrow faults,
2. multi-variant patch generation with expected outcome annotations,
3. targeted test-set synthesis tied to changed behavior,
4. post-fix regression probe generation,
5. structured patch explanation for human review.

Local AI role here remains support-only:

1. context packaging,
2. explanation rewriting,
3. evidence organization.

## 12.3 Escalation Packet Template for Remote Debug/Coding Tasks

Recommended packet structure:

1. Problem summary:
   one-paragraph technical statement.
2. Current runtime snapshot:
   condition, frame state, key locals, latest outcomes.
3. Attempts already made:
   restarts, steps, breakpoints, state repairs, validation runs.
4. Material changes so far:
   what changed and what did not.
5. Open decision request:
   exactly what the remote model should decide now.
6. Success criteria:
   explicit completion conditions.

Why this helps:

1. reduces remote back-and-forth,
2. improves first-pass decision quality,
3. keeps debugging sessions coherent across turns.

## 12.4 Smart Git: AI Semantic Merge (Frontier-Model Led)

This is one of the highest-upside opportunities in the whole project.

Plain version:

1. treat merge as a reasoning task, not just a text diff task,
2. let the high-quality remote model do semantic conflict reasoning,
3. keep merge execution deterministic and auditable.

### Why this is worth doing

Classic line-based merge misses intent.
A smart merge layer can understand:

1. what each side was trying to do,
2. whether the two changes are actually compatible,
3. which resolution preserves behavior and design constraints better.

### Controlled reader is not a blocker

Controlled reader is the safety boundary that makes AI merge trustworthy.

Interpretation:

1. controlled reader normalizes raw inputs into safe structured facts,
2. frontier model reasons on those structured facts,
3. merge engine verifies invariants and applies deterministic output.

So you still get smart reasoning, but with safety and reproducibility.

### What the frontier model can do in merge

1. classify conflict type:
   naming conflict, semantic behavior conflict, protocol mismatch, ordering conflict, data-shape conflict.
2. reconstruct intent:
   infer what each branch is trying to achieve.
3. generate ranked merge candidates:
   candidate A/B/C with rationale and risk notes.
4. predict blast radius:
   what likely breaks or shifts if candidate X is chosen.
5. generate follow-up validation strategy:
   targeted tests and checks tied to the chosen merge.
6. generate human-readable merge explanation:
   why this resolution was selected and what tradeoff it makes.

### Smart merge pipeline (simple version)

1. Gather merge inputs:
   base, left, right, metadata, related artifacts.
2. Controlled read:
   convert each side into structured semantic facts.
3. Conflict map:
   identify where left/right collide semantically.
4. Frontier-model reasoning:
   produce ranked merge candidates.
5. Deterministic verifier:
   run schema/invariant/replay checks.
6. Choose outcome:
   auto-merge low risk, or request human choice for high risk.
7. Emit merge artifact:
   merged result + explanation + validation report.

### Merge classes and how to handle them

Class 1: mechanical compatibility

1. changes are independent or trivially composable,
2. can usually auto-merge.

Class 2: policy-preserving semantic conflict

1. both sides valid but intent differs,
2. model ranks options and suggests safest path,
3. may require human choice depending on risk threshold.

Class 3: invariant-threatening conflict

1. one or more options break key invariants,
2. auto-merge should be blocked,
3. requires explicit intervention.

### Automation tiers (suggested)

Tier A: Auto-merge

1. low-risk conflict class only,
2. deterministic checks all pass.

Tier B: Auto-propose + auto-verify

1. model proposes,
2. system verifies,
3. human reviews summary and accepts quickly.

Tier C: Human-decided merge

1. model provides ranked candidates,
2. human picks final resolution.

Tier D: Hard block

1. invariant/replay failures,
2. no merge commit until resolved.

### What "Smart Git integrated into the project" can feel like

Inside IDE flow:

1. "Explain this conflict in one screen."
2. "Show top 3 merge resolutions with risk."
3. "Pick lowest-risk option that preserves debugger behavior."
4. "Generate focused tests for this merge."
5. "Summarize why this merge is safe enough."

### High-value Smart Git features to brainstorm next

1. Intent-aware commit synthesis:
   commit messages that reflect actual semantic change, not only file diffs.
2. Merge replay report:
   one-click "does merged behavior replay stably?"
3. Conflict heat map:
   visualize high-risk files/areas over time.
4. Semantic blame:
   explain not only "who changed this line" but "what decision introduced this behavior."
5. Auto-generated merge narrative:
   short plain-language summary for review and future archaeology.

### What not to lose

Even with strong AI merge reasoning:

1. deterministic verification remains mandatory,
2. explicit rollback path remains mandatory,
3. clear audit trail remains mandatory.

## 13. Fast Quality Checks for This Whole System

You know the integration is working when:

1. local summaries are accurate and materially useful,
2. escalation packets reduce remote back-and-forth,
3. status manager catches degradation early,
4. tuning suggestions improve responsiveness measurably,
5. locale orchestration reduces fallback friction,
6. smart merge recommendations reduce manual conflict time without increasing regressions,
7. human trust in outputs rises over time.

You know it is failing when:

1. summaries are polished but wrong,
2. contradiction detector creates noise,
3. status manager cries wolf constantly,
4. tuning oscillates settings without stable benefit,
5. smart merge suggestions look plausible but fail downstream checks,
6. local-vs-remote handoff creates confusion instead of clarity.

## 14. Open Questions for Next Brainstorm Sessions

1. Which local cognitive roles are highest value for your daily workflow right now?
2. What minimum packet format do you want for remote escalation?
3. How aggressive should runtime tuning be before automatic revert?
4. Which locale heuristics are acceptable vs too invasive?
5. Which outputs must always include confidence markers?
6. Which opportunities should remain strictly advisory forever?
7. Which merge classes should be auto-merge vs human-decided?
8. What minimum verifier set must pass before accepting AI merge output?
9. How should merge explanations be formatted for future debugging archaeology?

## 15. Conformance Statement for This Document

This document is conformant with its own intent if:

1. it stays design-focused and brainstorming-friendly,
2. it explains ideas clearly without requiring interpretation guesswork,
3. it avoids turning into roadmap bureaucracy,
4. it remains explicitly marked KEEP.
