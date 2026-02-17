# Web UI Design Review: Scaling and Realtime Risks

Date: 2026-02-17  
Scope: design-level risks that become visible when many app types are built on the `CCL/WASM + web-ui` foundation  
Out of scope: production gate status, implementation-complete claims, release readiness

## Purpose

This review captures architecture concerns that are valid even with a clean current implementation:

1. Input floods (especially pointer/hover/drag).
2. Workload contention across heterogeneous app types.
3. Gaps that matter once the platform hosts many third-party apps, including game workloads.

The intent is to prevent foundational design lock-in that later forces expensive protocol or runtime rewrites.

## Current Architecture Signals (Relevant Observations)

1. `web-ui/bridge/ui-bridge.mjs` currently pushes every pointer, wheel, key, composition, and focus event into an in-memory queue (`eventQueue.push(...)`) with no explicit queue cap or coalescing policy.
2. `web-ui/bridge/ui-bridge.mjs` runs canvas/webgl hit-testing on pointer paths before enqueue.
3. `web-ui/bridge/codec.mjs` selection is deterministic and prefix-based, bounded by `maxEvents` and `maxBytes`, but queue growth before polling is not bounded there.
4. `scripts/wasm/lib/microkernel.mjs` supports pending polls and SAB transport backpressure for runtime event/command lanes.
5. `web-ui/src/runtime-command-client.mjs` times out pending runtime commands, but has no explicit in-flight limit or app-level quota policy.
6. Current core event wire format (`web-ui/spec/ui-wire-format-events-v1.md`) is stable, but workload classes are not explicitly separated.

These are not implementation bugs by themselves. They are design pressure points.

## Findings

### Critical

| ID | Concern | Why it matters |
|---|---|---|
| `SR-01` | Unbounded high-frequency input queue | Drag/hover/move-heavy surfaces can accumulate unbounded backlog and memory pressure during short stalls. |
| `SR-02` | No explicit input coalescing policy | Pointer move streams can dominate bridge bandwidth and runtime turn time, starving semantic commands. |
| `SR-03` | No lane-level QoS/priorities across message classes | Chatty lanes (output/progress/log) can delay user-visible control events under load. |
| `SR-04` | Missing app/plugin resource isolation model | A single heavy app can monopolize runtime, transport, and UI budgets in multi-app ecosystem scenarios. |

### Significant

| ID | Concern | Why it matters |
|---|---|---|
| `SR-05` | Hit-test cost on high-rate pointer paths | Per-event hit-test + coordinate mapping can become a primary CPU sink on dense scenes. |
| `SR-06` | No explicit backpressure contract for UI input producer | Runtime poll cadence becomes the implicit throttle; producer behavior under lag is undefined by profile. |
| `SR-07` | Command transport has timeout, not queue admission control | Burst command producers can create large pending sets and degraded UX without predictable rejection policy. |
| `SR-08` | Wire format lacks workload classes | Tooling, dashboards, and realtime surfaces need different guarantees (lossless vs lossy, ordered vs latest). |
| `SR-09` | State/persistence model may be too monolithic for binary-heavy apps | Creative tools and games introduce large binary assets and high-churn state that should not flow through one snapshot path. |
| `SR-10` | Capability model is global-first, not app-tenant-first | Ecosystem mode needs per-app grants, quotas, and kill switches, not only global policies. |

### Moderate

| ID | Concern | Why it matters |
|---|---|---|
| `SR-11` | Determinism goals can conflict with responsive coalescing | Need explicit tie-break rules for replayable but lossy/high-rate lanes. |
| `SR-12` | Limited device/input taxonomy | No explicit contract for pointer lock, gamepad, raw mouse deltas, multitouch gestures. |
| `SR-13` | No audio/realtime clock contract | Realtime apps need a clock model and scheduling boundaries separate from UI command turns. |
| `SR-14` | Protocol evolution risk under app diversity | More app classes will push additional event/value types; extension policy needs stronger profile partitioning. |

## Deep Dive: Pointer/Hover/Drag Flood Risk

### Problem shape

1. Drag and hover interactions generate dense `pointermove` streams.
2. Current bridge enqueues each event object.
3. If consumer poll lags briefly, queue depth grows.
4. Recovery can require processing stale move events that no longer represent meaningful user intent.

### Consequences

1. Memory growth from queued event objects.
2. Elevated GC churn in JS and host runtime.
3. Increased input-to-effect latency during recovery.
4. Starvation of lower-frequency, high-value events (command invokes, selection commits, focus changes).

### Design controls recommended now

1. Define an explicit input backpressure profile:
   1. Max queue depth per lane.
   2. Max queue bytes per lane.
   3. Required drop/coalesce behavior at thresholds.
2. Define semantic coalescing:
   1. Coalesce consecutive `pointermove` by `(pointerId, target/window, drag session)`.
   2. Preserve ordering for structural events (`down`, `up`, `cancel`, `enter`, `leave`).
   3. Preserve latest position plus aggregate deltas for wheel/move.
3. Define overflow observability:
   1. Counter for dropped/coalesced events.
   2. Per-lane queue depth gauges.
   3. Overflow annotations in event-log replay for deterministic diagnostics.
4. Define drag session model:
   1. Stable session id from `pointerdown` to `up/cancel`.
   2. Optional pointer capture policy for out-of-bounds drags.
   3. Explicit stale-session discard rules on focus loss.

## Concerns That Emerge with App Variety

### 1) Workload classes need explicit profiles

A single behavior profile is not enough for all apps.

Recommended profile split:

1. `tooling-interactive-v1`:
   1. Favors determinism and rich semantics.
   2. Moderate coalescing.
2. `canvas-heavy-v1`:
   1. Favors throughput and bounded latency.
   2. Aggressive move/wheel coalescing.
3. `realtime-v1`:
   1. Favors latest-state delivery.
   2. Controlled loss on high-rate lanes.
   3. Tight queue bounds and strict QoS.

### 2) QoS and starvation boundaries

Transport should separate at least:

1. Control lane: command/result/error, focus/selection commits.
2. Interaction lane: pointer/wheel/move.
3. Telemetry lane: logs/progress/diagnostics/output.

Without this, high-volume telemetry can degrade core UX.

### 3) Tenant isolation for ecosystem mode

When hosting many apps/extensions:

1. Apply per-app limits for:
   1. CPU budget.
   2. Queue bytes.
   3. Command in-flight count.
   4. Persistence write rate.
2. Add per-app circuit breaker:
   1. Pause app.
   2. Kill app.
   3. Recover app without full runtime restart.

### 4) Asset and persistence architecture split

Binary assets (images, fonts, audio, meshes) should not be treated as ordinary UI-tree state payloads.

Recommend:

1. Structured state channel for commands/layout/model.
2. Asset channel for large immutable or versioned binaries.
3. Incremental content addressing for large assets and snapshots.

## Games: What Changes

Games are possible, but not with the exact same assumptions as IDE/wireframe tooling.

### Game-specific requirements not yet explicit

1. Realtime input APIs:
   1. Pointer lock/raw deltas.
   2. Gamepad.
   3. High-rate keyboard semantics.
2. Frame pacing model:
   1. Fixed timestep loop support.
   2. Clear separation of simulation tick vs UI command turn.
3. Realtime media:
   1. Audio clock and scheduling contract.
   2. Asset prefetch/streaming semantics.
4. Loss policy:
   1. Latest-state wins for high-rate control lanes.
   2. Strict ordering only where needed.

### Practical stance

1. For strategy, simulation, builder, and tool-like games, this foundation is promising with profile extensions.
2. For twitch/FPS-class workloads, the architecture needs a dedicated realtime profile and stricter hot-path contracts before claiming viability.

## Recommended Design Actions (Before Broad App Ecosystem Expansion)

1. Add `input-backpressure-and-coalescing-contract-v1.md`.
2. Add `bridge-qos-and-lane-contract-v1.md`.
3. Add `app-tenant-isolation-and-quotas-contract-v1.md`.
4. Add `realtime-surface-profile-v1.md` (games/heavy simulation lane).
5. Add `asset-streaming-and-binary-state-contract-v1.md`.
6. Add telemetry fields:
   1. `ui_input_queue_depth`.
   2. `ui_input_queue_bytes`.
   3. `ui_input_events_coalesced`.
   4. `ui_input_events_dropped`.
   5. `runtime_command_inflight`.
   6. Per-lane saturation counters.
7. Add stress fixtures beyond current scale lanes:
   1. Pointer storm drag test.
   2. Hover density test over deep scene.
   3. Mixed lane contention test (input + logs + jobs + command burst).
   4. Realtime profile replay determinism-with-loss test.

## Decision Guidance

If the platform goal includes "variety of serious apps" and potential game-class workloads, the primary architectural decision is:

1. Keep one generic event/transport behavior and accept chronic contention risk, or
2. Introduce profile-based QoS/coalescing/quotas now while protocol surfaces are still controllable.

This review recommends option 2.

## Companion Patch Map

The concrete `SR-*` to spec insertion map is in:

`web-ui/DESIGN-REVIEW-SCALING-PATCH-MAP-2026-02-17.md`
