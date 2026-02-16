function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

function hashSeed(seed) {
  const text = String(seed ?? "seed");
  let hash = 2166136261;
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function createDeterministicRng(seed) {
  let state = hashSeed(seed);
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = Math.imul(state ^ (state >>> 15), state | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

const DEFAULT_EXECUTION_PROFILE = Object.freeze({
  seed: "persistence-conformance-v1",
  startMs: 1_700_000_000_000,
  leaseTtlMs: 15_000,
  suspendGraceMs: 60_000,
  defaultLeaseName: "lease/workspace/main",
  defaultRemoteId: "remote-1"
});

function normalizeExecutionProfile(profile = {}) {
  const leaseTtlMs = Number.isFinite(profile.leaseTtlMs)
    ? Math.max(1, Math.trunc(profile.leaseTtlMs))
    : DEFAULT_EXECUTION_PROFILE.leaseTtlMs;
  const suspendGraceMs = Number.isFinite(profile.suspendGraceMs)
    ? Math.max(0, Math.trunc(profile.suspendGraceMs))
    : DEFAULT_EXECUTION_PROFILE.suspendGraceMs;
  return {
    seed: String(profile.seed ?? DEFAULT_EXECUTION_PROFILE.seed),
    startMs: Number.isFinite(profile.startMs)
      ? Math.trunc(profile.startMs)
      : DEFAULT_EXECUTION_PROFILE.startMs,
    leaseTtlMs,
    suspendGraceMs,
    defaultLeaseName: String(profile.defaultLeaseName ?? DEFAULT_EXECUTION_PROFILE.defaultLeaseName),
    defaultRemoteId: String(profile.defaultRemoteId ?? DEFAULT_EXECUTION_PROFILE.defaultRemoteId)
  };
}

function createStore() {
  return {
    objects: new Set(),
    commits: new Map(),
    refs: new Map(),
    leases: new Map(),
    conflicts: new Map(),
    incomingRefs: new Set()
  };
}

function sortedEntries(iterable) {
  return Array.from(iterable).sort(([a], [b]) => String(a).localeCompare(String(b)));
}

function snapshotStore(store) {
  const refs = {};
  for (const [refName, ref] of sortedEntries(store.refs)) {
    refs[refName] = {
      ref_name: ref.ref_name,
      current_commit_id: ref.current_commit_id ?? null,
      previous_commit_id: ref.previous_commit_id ?? null,
      refgen: ref.refgen,
      protected_ref: ref.protected_ref === true
    };
  }

  const leases = {};
  for (const [leaseName, lease] of sortedEntries(store.leases)) {
    leases[leaseName] = deepClone(lease);
  }

  const conflicts = {};
  for (const [conflictId, conflict] of sortedEntries(store.conflicts)) {
    conflicts[conflictId] = deepClone(conflict);
  }

  const commits = {};
  for (const [commitId, commit] of sortedEntries(store.commits)) {
    commits[commitId] = {
      commit_id: commit.commit_id,
      parents: [...commit.parents],
      finalized: commit.finalized === true,
      closure: [...commit.closure]
    };
  }

  return {
    refs,
    leases,
    conflicts,
    commits,
    incomingRefs: Array.from(store.incomingRefs).sort(),
    objects: Array.from(store.objects).sort()
  };
}

function snapshotState(runtime) {
  return {
    nowMs: runtime.nowMs,
    crashed: runtime.crashed,
    local: snapshotStore(runtime.local),
    remote: snapshotStore(runtime.remote)
  };
}

function mapUnion(localMap, remoteMap) {
  const out = new Map();
  for (const [key, value] of localMap) out.set(key, value);
  for (const [key, value] of remoteMap) out.set(key, value);
  return out;
}

function isAncestor(commits, ancestorId, descendantId) {
  if (!ancestorId || !descendantId) return false;
  if (ancestorId === descendantId) return true;
  const queue = [descendantId];
  const seen = new Set();

  while (queue.length > 0) {
    const current = queue.shift();
    if (!current || seen.has(current)) continue;
    seen.add(current);
    if (current === ancestorId) return true;
    const commit = commits.get(current);
    if (!commit) continue;
    for (const parent of commit.parents ?? []) {
      if (!seen.has(parent)) queue.push(parent);
    }
  }
  return false;
}

function toErrorRecord(error, step, phase = null) {
  return {
    op_id: String(step?.id ?? step?.op ?? "unknown-op"),
    op: String(step?.op ?? "unknown"),
    phase: phase ?? error?.phase ?? null,
    code: String(error?.code ?? "ERR_UNHANDLED_EXCEPTION"),
    message: String(error?.message ?? "Unhandled exception"),
    injected: error?.injected === true
  };
}

function createOpError(code, message, details = {}) {
  const error = new Error(message);
  error.code = code;
  error.phase = details.phase ?? null;
  error.injected = details.injected === true;
  return error;
}

function normalizeFaultPlan(faults = []) {
  const byOp = new Map();
  if (!Array.isArray(faults)) return byOp;

  faults.forEach((fault, index) => {
    if (!fault || typeof fault !== "object") return;
    const opId = String(fault.op_id ?? "").trim();
    if (!opId) return;
    const phase = String(fault.phase ?? "before").trim();
    const action = String(fault.action ?? "error").trim();
    const defaultCode = action === "partition" ? "ERR_SYNC_NETWORK" : "ERR_FAULT_INJECTED";
    const count = Number.isInteger(fault.count) && fault.count > 0 ? fault.count : 1;
    const remaining = fault.once === false ? Number.POSITIVE_INFINITY : count;
    const entry = {
      id: String(fault.id ?? `${opId}:${phase}:${index}`),
      op_id: opId,
      phase,
      action,
      code: String(fault.code ?? defaultCode),
      remaining
    };
    if (!byOp.has(opId)) byOp.set(opId, []);
    byOp.get(opId).push(entry);
  });

  return byOp;
}

function hasUnresolvedConflicts(store, refName) {
  for (const conflict of store.conflicts.values()) {
    if (conflict?.ref_name === refName && conflict?.status !== "resolved") {
      return true;
    }
  }
  return false;
}

function ensureCommitReadable(store, commitId) {
  const commit = store.commits.get(commitId);
  if (!commit) {
    throw createOpError("ERR_COMMIT_MISSING", `commit missing: ${commitId}`);
  }
  for (const objectId of commit.closure) {
    if (!store.objects.has(objectId)) {
      throw createOpError("ERR_COMMIT_UNREADABLE", `commit closure missing object: ${objectId}`);
    }
  }
  return commit;
}

function normalizeCommit(step) {
  const commitId = String(step.commit_id ?? "").trim();
  if (!commitId) {
    throw createOpError("ERR_INVALID_INPUT", "put_commit requires commit_id");
  }
  const parents = Array.isArray(step.parents) ? step.parents.map((entry) => String(entry)) : [];
  const closureList = Array.isArray(step.closure) ? step.closure.map((entry) => String(entry)) : [];
  const closureSet = new Set([...closureList, commitId]);
  return {
    commit_id: commitId,
    parents,
    finalized: step.finalized !== false,
    closure: Array.from(closureSet)
  };
}

function putCommit(store, step) {
  const commit = normalizeCommit(step);
  store.commits.set(commit.commit_id, commit);
  for (const objectId of commit.closure) {
    store.objects.add(objectId);
  }
  return commit;
}

function normalizeRefSeed(step) {
  const refName = String(step.ref_name ?? "").trim();
  if (!refName) {
    throw createOpError("ERR_INVALID_INPUT", "seed_ref requires ref_name");
  }
  const commitId = step.commit_id === null ? null : String(step.commit_id ?? "").trim();
  if (commitId === "") {
    throw createOpError("ERR_INVALID_INPUT", "seed_ref requires commit_id or null");
  }
  const refgen = Number.isInteger(step.refgen) ? Math.max(0, step.refgen) : 0;
  return {
    ref_name: refName,
    current_commit_id: commitId,
    previous_commit_id: step.previous_commit_id ? String(step.previous_commit_id) : null,
    refgen,
    protected_ref: step.protected_ref === true
  };
}

function normalizeTargets(rawTarget) {
  const target = String(rawTarget ?? "local");
  if (target === "local") return ["local"];
  if (target === "remote") return ["remote"];
  if (target === "both") return ["local", "remote"];
  throw createOpError("ERR_INVALID_INPUT", `unsupported target: ${target}`);
}

function verifyProtectedGuard(runtime, step, ref, commit, options = {}) {
  const missingGuardCode = options.missingGuardCode ?? "ERR_SEMANTIC_GUARD_REQUIRED";
  const unresolvedConflictCode = options.unresolvedConflictCode ?? "ERR_UNRESOLVED_CONFLICTS";
  const guard = step.semantic_guard;
  const requiredKeys = [
    "requires_current_commit_id",
    "requires_no_unresolved_conflicts",
    "requires_lease_epoch",
    "requires_finalized"
  ];

  if (!guard || typeof guard !== "object") {
    throw createOpError(missingGuardCode, "protected ref requires semantic_guard");
  }
  for (const key of requiredKeys) {
    if (!(key in guard)) {
      throw createOpError(missingGuardCode, `protected semantic_guard missing ${key}`);
    }
  }
  if (guard.requires_no_unresolved_conflicts !== true || guard.requires_finalized !== true) {
    throw createOpError(missingGuardCode, "protected semantic_guard requires strict conflict/finalized gates");
  }
  if (String(guard.requires_current_commit_id) !== String(ref.current_commit_id ?? "")) {
    throw createOpError("ERR_SEMANTIC_GUARD_FAILED", "requires_current_commit_id mismatch");
  }
  if (guard.requires_finalized === true && commit.finalized !== true) {
    throw createOpError("ERR_FINALIZATION_REQUIRED", "destination commit is not finalized");
  }
  if (hasUnresolvedConflicts(runtime.local, ref.ref_name)) {
    throw createOpError(unresolvedConflictCode, "unresolved conflicts block protected ref move");
  }

  const leaseName = String(step.lease_name ?? runtime.executionProfile.defaultLeaseName);
  const lease = runtime.local.leases.get(leaseName);
  if (!lease) {
    throw createOpError("ERR_LEASE_REQUIRED", "lease missing for protected ref");
  }
  if (!step.writer_token || String(step.writer_token) !== String(lease.writer_token)) {
    throw createOpError("ERR_LEASE_REQUIRED", "writer token mismatch");
  }
  if (Number(guard.requires_lease_epoch) !== Number(lease.epoch)) {
    throw createOpError("ERR_LEASE_REQUIRED", "lease epoch mismatch");
  }
  if (runtime.nowMs >= Number(lease.expires_at)) {
    throw createOpError("ERR_LEASE_REQUIRED", "lease expired");
  }
}

function evaluateInvariants(runtime, invariantIds = []) {
  const diagnostics = [];

  function checkRefsResolveCompleteClosure(store, label, protectedOnly) {
    for (const [refName, ref] of store.refs) {
      if (!ref.current_commit_id) continue;
      if (protectedOnly && ref.protected_ref !== true) continue;
      const commit = store.commits.get(ref.current_commit_id);
      if (!commit) {
        diagnostics.push({
          code: "invariant-failed",
          message: `${label} ref ${refName} points to missing commit ${ref.current_commit_id}`
        });
        continue;
      }
      for (const objectId of commit.closure) {
        if (!store.objects.has(objectId)) {
          diagnostics.push({
            code: "invariant-failed",
            message: `${label} ref ${refName} closure missing object ${objectId}`
          });
        }
      }
    }
  }

  for (const invariantId of invariantIds) {
    switch (String(invariantId)) {
      case "no_half_state_refs":
        checkRefsResolveCompleteClosure(runtime.local, "local", false);
        checkRefsResolveCompleteClosure(runtime.remote, "remote", false);
        break;
      case "protected_refs_resolve_complete_closure":
        checkRefsResolveCompleteClosure(runtime.local, "local", true);
        checkRefsResolveCompleteClosure(runtime.remote, "remote", true);
        break;
      case "single_writer_per_lease":
        for (const [leaseName, lease] of runtime.local.leases) {
          if (!lease.writer_token || !Number.isInteger(lease.epoch) || lease.epoch < 1) {
            diagnostics.push({
              code: "invariant-failed",
              message: `lease ${leaseName} has invalid writer token/epoch`
            });
          }
        }
        break;
      default:
        diagnostics.push({
          code: "invariant-unknown",
          message: `unknown invariant id: ${invariantId}`
        });
        break;
    }
  }

  return diagnostics;
}

function evaluateExpectations(runtime, errors, expect = {}) {
  const diagnostics = [];
  const errorCodes = new Set(errors.map((entry) => entry.code));
  const state = snapshotState(runtime);

  function checkRefSnapshot(refs, scope, refName, expected) {
    const ref = refs[refName];
    if (!ref) {
      diagnostics.push({
        code: "expectation-failed",
        message: `${scope} ref missing: ${refName}`
      });
      return;
    }
    if ("commit_id" in expected && ref.current_commit_id !== expected.commit_id) {
      diagnostics.push({
        code: "expectation-failed",
        message: `${scope} ref ${refName} expected commit ${expected.commit_id}, got ${ref.current_commit_id}`
      });
    }
    if ("refgen" in expected && Number(ref.refgen) !== Number(expected.refgen)) {
      diagnostics.push({
        code: "expectation-failed",
        message: `${scope} ref ${refName} expected refgen ${expected.refgen}, got ${ref.refgen}`
      });
    }
    if ("protected_ref" in expected && Boolean(ref.protected_ref) !== Boolean(expected.protected_ref)) {
      diagnostics.push({
        code: "expectation-failed",
        message: `${scope} ref ${refName} protected_ref mismatch`
      });
    }
  }

  if (expect && typeof expect === "object") {
    if (Array.isArray(expect.error_codes)) {
      for (const code of expect.error_codes) {
        if (!errorCodes.has(String(code))) {
          diagnostics.push({
            code: "expectation-failed",
            message: `expected error code missing: ${code}`
          });
        }
      }
    }

    if (Array.isArray(expect.error_codes_absent)) {
      for (const code of expect.error_codes_absent) {
        if (errorCodes.has(String(code))) {
          diagnostics.push({
            code: "expectation-failed",
            message: `unexpected error code present: ${code}`
          });
        }
      }
    }

    if ("crashed" in expect && Boolean(state.crashed) !== Boolean(expect.crashed)) {
      diagnostics.push({
        code: "expectation-failed",
        message: `crash state mismatch: expected=${Boolean(expect.crashed)} actual=${Boolean(state.crashed)}`
      });
    }

    if (expect.local_refs && typeof expect.local_refs === "object") {
      for (const [refName, expected] of Object.entries(expect.local_refs)) {
        checkRefSnapshot(state.local.refs, "local", refName, expected ?? {});
      }
    }

    if (expect.remote_refs && typeof expect.remote_refs === "object") {
      for (const [refName, expected] of Object.entries(expect.remote_refs)) {
        checkRefSnapshot(state.remote.refs, "remote", refName, expected ?? {});
      }
    }

    if (Array.isArray(expect.incoming_local_ref_prefixes)) {
      const refNames = Object.keys(state.local.refs);
      for (const prefix of expect.incoming_local_ref_prefixes) {
        const found = refNames.some((name) => name.startsWith(String(prefix)));
        if (!found) {
          diagnostics.push({
            code: "expectation-failed",
            message: `expected local incoming ref prefix not found: ${prefix}`
          });
        }
      }
    }

    if (Array.isArray(expect.incoming_remote_ref_prefixes)) {
      const refNames = Object.keys(state.remote.refs);
      for (const prefix of expect.incoming_remote_ref_prefixes) {
        const found = refNames.some((name) => name.startsWith(String(prefix)));
        if (!found) {
          diagnostics.push({
            code: "expectation-failed",
            message: `expected remote incoming ref prefix not found: ${prefix}`
          });
        }
      }
    }

    diagnostics.push(...evaluateInvariants(runtime, expect.invariants ?? []));
  }

  return {
    ok: diagnostics.length === 0,
    diagnostics,
    snapshot: state
  };
}

export function validatePersistenceFixtureSet(fixtureSet) {
  const errors = [];
  if (!fixtureSet || typeof fixtureSet !== "object") {
    return { ok: false, errors: [{ path: "$", message: "fixture set must be an object" }] };
  }
  if (!fixtureSet.metadata || typeof fixtureSet.metadata !== "object") {
    errors.push({ path: "$.metadata", message: "missing metadata object" });
  }
  if (!Array.isArray(fixtureSet.scenarios)) {
    errors.push({ path: "$.scenarios", message: "scenarios must be an array" });
  } else if (fixtureSet.scenarios.length === 0) {
    errors.push({ path: "$.scenarios", message: "scenarios must not be empty" });
  } else {
    fixtureSet.scenarios.forEach((scenario, index) => {
      if (!scenario || typeof scenario !== "object") {
        errors.push({ path: `$.scenarios[${index}]`, message: "scenario must be an object" });
        return;
      }
      if (!scenario.id || typeof scenario.id !== "string") {
        errors.push({ path: `$.scenarios[${index}].id`, message: "scenario id is required" });
      }
      if (!Array.isArray(scenario.script) || scenario.script.length === 0) {
        errors.push({ path: `$.scenarios[${index}].script`, message: "scenario script must not be empty" });
      }
    });
  }
  return { ok: errors.length === 0, errors };
}

export function createPersistenceFaultHarness(options = {}) {
  const executionProfile = normalizeExecutionProfile(options.executionProfile);
  const rng = createDeterministicRng(options.seed ?? executionProfile.seed);

  function newRuntimeState() {
    return {
      executionProfile,
      nowMs: executionProfile.startMs,
      crashed: false,
      local: createStore(),
      remote: createStore(),
      events: [],
      errors: [],
      eventSeq: 0
    };
  }

  function emit(runtime, kind, payload = {}) {
    runtime.eventSeq += 1;
    runtime.events.push({
      seq: runtime.eventSeq,
      ts: runtime.nowMs,
      kind,
      ...deepClone(payload)
    });
  }

  function injectFault(runtime, faultPlan, step, phase) {
    const opId = String(step?.id ?? step?.op ?? "unknown-op");
    const faults = faultPlan.get(opId);
    if (!faults) return;
    for (const fault of faults) {
      if (fault.phase !== phase || fault.remaining <= 0) continue;
      if (Number.isFinite(fault.remaining)) fault.remaining -= 1;
      if (fault.action === "crash") {
        runtime.crashed = true;
        throw createOpError(
          "ERR_HARNESS_CRASH",
          `injected crash at ${opId}:${phase}`,
          { phase, injected: true }
        );
      }
      if (fault.action === "partition") {
        throw createOpError(
          fault.code || "ERR_SYNC_NETWORK",
          `injected partition at ${opId}:${phase}`,
          { phase, injected: true }
        );
      }
      throw createOpError(
        fault.code || "ERR_FAULT_INJECTED",
        `injected fault at ${opId}:${phase}`,
        { phase, injected: true }
      );
    }
  }

  function runScenario(rawScenario) {
    const scenario = rawScenario && typeof rawScenario === "object" ? rawScenario : {};
    const runtime = newRuntimeState();
    const faultPlan = normalizeFaultPlan(scenario.faults);

    function fail(code, message, details = {}) {
      throw createOpError(code, message, details);
    }

    function applyTargets(step, fn) {
      const targets = normalizeTargets(step.target);
      for (const target of targets) {
        fn(target === "local" ? runtime.local : runtime.remote, target);
      }
    }

    function opPutCommit(step) {
      injectFault(runtime, faultPlan, step, "before");
      applyTargets(step, (store) => {
        const commit = putCommit(store, step);
        emit(runtime, "commit.put", {
          op_id: String(step.id ?? step.op),
          target: step.target ?? "local",
          commit_id: commit.commit_id
        });
      });
      injectFault(runtime, faultPlan, step, "after");
    }

    function opSeedRef(step) {
      injectFault(runtime, faultPlan, step, "before");
      applyTargets(step, (store) => {
        const record = normalizeRefSeed(step);
        store.refs.set(record.ref_name, record);
        emit(runtime, "ref.seed", {
          op_id: String(step.id ?? step.op),
          target: step.target ?? "local",
          ref_name: record.ref_name
        });
      });
      injectFault(runtime, faultPlan, step, "after");
    }

    function opSeedConflict(step) {
      const conflictId = String(step.conflict_id ?? step.id ?? `conflict-${runtime.eventSeq + 1}`);
      const refName = String(step.ref_name ?? "workspace/main");
      runtime.local.conflicts.set(conflictId, {
        conflict_id: conflictId,
        ref_name: refName,
        status: String(step.status ?? "unresolved")
      });
      emit(runtime, "conflict.seed", { op_id: String(step.id ?? step.op), conflict_id: conflictId, ref_name: refName });
    }

    function opClearConflicts(step) {
      const refName = step.ref_name ? String(step.ref_name) : null;
      if (!refName) {
        runtime.local.conflicts.clear();
      } else {
        for (const [conflictId, conflict] of runtime.local.conflicts) {
          if (conflict.ref_name === refName) {
            runtime.local.conflicts.delete(conflictId);
          }
        }
      }
      emit(runtime, "conflict.clear", { op_id: String(step.id ?? step.op), ref_name: refName });
    }

    function opAdvanceTime(step) {
      const delta = Number.isFinite(step.ms) ? Math.trunc(step.ms) : 0;
      runtime.nowMs += Math.max(0, delta);
      emit(runtime, "time.advance", { op_id: String(step.id ?? step.op), ms: Math.max(0, delta) });
    }

    function opLeaseAcquire(step) {
      injectFault(runtime, faultPlan, step, "before");
      const leaseName = String(step.lease_name ?? executionProfile.defaultLeaseName);
      const mode = String(step.mode ?? "normal");
      const existing = runtime.local.leases.get(leaseName) ?? null;

      if (mode === "normal" && existing && runtime.nowMs < Number(existing.expires_at)) {
        fail("ERR_LEASE_HELD", `lease held: ${leaseName}`);
      }
      if (mode === "takeover" && existing) {
        const allowed =
          runtime.nowMs >= Number(existing.expires_at) + executionProfile.suspendGraceMs ||
          step.force_takeover === true;
        if (!allowed) {
          fail("ERR_TAKEOVER_NOT_ALLOWED", `takeover not allowed for ${leaseName}`);
        }
      }

      const nextEpoch = Number(existing?.epoch ?? 0) + 1;
      const ttlMs = Number.isFinite(step.ttl_ms) ? Math.max(1, Math.trunc(step.ttl_ms)) : executionProfile.leaseTtlMs;
      const lease = {
        lease_name: leaseName,
        owner_instance_id: String(step.owner_instance_id ?? "instance-1"),
        writer_token: String(step.writer_token ?? `writer-${nextEpoch}`),
        epoch: nextEpoch,
        expires_at: runtime.nowMs + ttlMs,
        last_heartbeat_at: runtime.nowMs
      };
      runtime.local.leases.set(leaseName, lease);
      injectFault(runtime, faultPlan, step, "after_commit");
      emit(runtime, "lease.acquire", { op_id: String(step.id ?? step.op), lease_name: leaseName, epoch: nextEpoch });
    }

    function opRefAdvance(step) {
      injectFault(runtime, faultPlan, step, "before_guard");
      const refName = String(step.ref_name ?? "");
      const ref = runtime.local.refs.get(refName);
      if (!ref) fail("ERR_REF_NOT_FOUND", `ref not found: ${refName}`);
      const expectedRefgen = Number(step.expected_refgen);
      if (!Number.isFinite(expectedRefgen) || expectedRefgen !== Number(ref.refgen)) {
        fail("ERR_REFGEN_MISMATCH", `refgen mismatch for ${refName}`);
      }

      const commitId = String(step.new_commit_id ?? "");
      const commit = ensureCommitReadable(runtime.local, commitId);
      const protectedRef = step.protected_ref === true || ref.protected_ref === true;
      if (protectedRef) {
        verifyProtectedGuard(runtime, step, ref, commit, {
          missingGuardCode: "ERR_SEMANTIC_GUARD_REQUIRED",
          unresolvedConflictCode: "ERR_UNRESOLVED_CONFLICTS"
        });
      }

      injectFault(runtime, faultPlan, step, "before_commit");
      const next = {
        ...ref,
        previous_commit_id: ref.current_commit_id ?? null,
        current_commit_id: commitId,
        refgen: ref.refgen + 1,
        protected_ref: protectedRef
      };
      runtime.local.refs.set(refName, next);
      injectFault(runtime, faultPlan, step, "after_commit");
      emit(runtime, "ref.advance", { op_id: String(step.id ?? step.op), ref_name: refName, to_commit_id: commitId });
    }

    function opPush(step) {
      injectFault(runtime, faultPlan, step, "before_upload");
      const refName = String(step.ref_name ?? "");
      const localRef = runtime.local.refs.get(refName);
      if (!localRef) fail("ERR_REF_NOT_FOUND", `local ref not found: ${refName}`);
      const commitId = String(localRef.current_commit_id ?? "");
      if (!commitId) fail("ERR_COMMIT_MISSING", `local ref ${refName} has empty commit`);

      const commit = ensureCommitReadable(runtime.local, commitId);
      runtime.remote.commits.set(commitId, deepClone(commit));
      for (const objectId of commit.closure) {
        runtime.remote.objects.add(objectId);
      }
      injectFault(runtime, faultPlan, step, "after_upload_before_ref_cas");

      const remoteRef = runtime.remote.refs.get(refName) ?? {
        ref_name: refName,
        current_commit_id: null,
        previous_commit_id: null,
        refgen: 0,
        protected_ref: false
      };
      const allCommits = mapUnion(runtime.local.commits, runtime.remote.commits);
      if (remoteRef.current_commit_id === commitId) {
        emit(runtime, "sync.push.noop", { op_id: String(step.id ?? step.op), ref_name: refName });
        return;
      }

      if (
        remoteRef.current_commit_id === null ||
        isAncestor(allCommits, remoteRef.current_commit_id, commitId)
      ) {
        injectFault(runtime, faultPlan, step, "before_ref_cas");
        const next = {
          ...remoteRef,
          previous_commit_id: remoteRef.current_commit_id ?? null,
          current_commit_id: commitId,
          refgen: remoteRef.refgen + 1
        };
        runtime.remote.refs.set(refName, next);
        injectFault(runtime, faultPlan, step, "after_ref_cas");
        emit(runtime, "sync.push.ref-advanced", { op_id: String(step.id ?? step.op), ref_name: refName, to_commit_id: commitId });
        return;
      }

      const incomingName = `incoming/${String(step.device_id ?? "device-1")}/${refName}/${runtime.nowMs}`;
      runtime.remote.refs.set(incomingName, {
        ref_name: incomingName,
        current_commit_id: commitId,
        previous_commit_id: null,
        refgen: 0,
        protected_ref: false
      });
      runtime.remote.incomingRefs.add(incomingName);
      emit(runtime, "sync.push.diverged", { op_id: String(step.id ?? step.op), ref_name: refName, incoming_ref: incomingName });
    }

    function opPull(step) {
      injectFault(runtime, faultPlan, step, "before_fetch");
      const refName = String(step.ref_name ?? "");
      const remoteRef = runtime.remote.refs.get(refName);
      if (!remoteRef || !remoteRef.current_commit_id) {
        fail("ERR_SYNC_OBJECT_MISSING", `remote ref missing or empty: ${refName}`);
      }

      const remoteCommitId = String(remoteRef.current_commit_id);
      const remoteCommit = runtime.remote.commits.get(remoteCommitId);
      if (!remoteCommit) {
        fail("ERR_SYNC_OBJECT_MISSING", `remote commit missing: ${remoteCommitId}`);
      }

      const midpoint = Math.floor(remoteCommit.closure.length / 2);
      for (let index = 0; index < remoteCommit.closure.length; index += 1) {
        if (index === midpoint) injectFault(runtime, faultPlan, step, "mid_fetch");
        const objectId = remoteCommit.closure[index];
        if (!runtime.remote.objects.has(objectId)) {
          fail("ERR_SYNC_OBJECT_MISSING", `remote closure missing object: ${objectId}`);
        }
        runtime.local.objects.add(objectId);
      }
      runtime.local.commits.set(remoteCommitId, deepClone(remoteCommit));

      const localRef = runtime.local.refs.get(refName);
      if (!localRef) fail("ERR_REF_NOT_FOUND", `local ref not found: ${refName}`);
      if (localRef.current_commit_id === remoteCommitId) {
        emit(runtime, "sync.pull.noop", { op_id: String(step.id ?? step.op), ref_name: refName });
        return;
      }

      const allCommits = mapUnion(runtime.local.commits, runtime.remote.commits);
      const localHead = localRef.current_commit_id;
      const canFastForward =
        localHead === null || isAncestor(allCommits, String(localHead), remoteCommitId);

      if (canFastForward) {
        const protectedRef = step.protected_ref === true || localRef.protected_ref === true;
        if (protectedRef) {
          verifyProtectedGuard(runtime, step, localRef, remoteCommit, {
            missingGuardCode: "ERR_SYNC_PROTECTED_REF_GUARD_REQUIRED",
            unresolvedConflictCode: "ERR_CONFLICT_UNRESOLVED"
          });
        }
        injectFault(runtime, faultPlan, step, "before_local_ref_advance");
        const next = {
          ...localRef,
          previous_commit_id: localRef.current_commit_id ?? null,
          current_commit_id: remoteCommitId,
          refgen: localRef.refgen + 1,
          protected_ref: protectedRef
        };
        runtime.local.refs.set(refName, next);
        emit(runtime, "sync.pull.ref-advanced", {
          op_id: String(step.id ?? step.op),
          ref_name: refName,
          to_commit_id: remoteCommitId
        });
        return;
      }

      const remoteId = String(step.remote_id ?? executionProfile.defaultRemoteId);
      const incomingName = `incoming/${remoteId}/${refName}/${runtime.nowMs}`;
      runtime.local.refs.set(incomingName, {
        ref_name: incomingName,
        current_commit_id: remoteCommitId,
        previous_commit_id: null,
        refgen: 0,
        protected_ref: false
      });
      runtime.local.incomingRefs.add(incomingName);
      emit(runtime, "sync.pull.diverged", { op_id: String(step.id ?? step.op), ref_name: refName, incoming_ref: incomingName });
    }

    function opRecover(step) {
      runtime.crashed = false;
      emit(runtime, "runtime.recover", { op_id: String(step.id ?? step.op) });
    }

    function executeStep(rawStep) {
      const step = rawStep && typeof rawStep === "object" ? rawStep : { op: "noop" };
      if (runtime.crashed && step.op !== "recover") {
        throw createOpError("ERR_HARNESS_CRASHED", "runtime is crashed; recover before continuing");
      }
      switch (String(step.op ?? "noop")) {
        case "noop":
          emit(runtime, "noop", { op_id: String(step.id ?? "noop") });
          break;
        case "put_commit":
          opPutCommit(step);
          break;
        case "seed_ref":
          opSeedRef(step);
          break;
        case "seed_conflict":
          opSeedConflict(step);
          break;
        case "clear_conflicts":
          opClearConflicts(step);
          break;
        case "advance_time":
          opAdvanceTime(step);
          break;
        case "lease_acquire":
          opLeaseAcquire(step);
          break;
        case "ref_advance":
          opRefAdvance(step);
          break;
        case "push":
          opPush(step);
          break;
        case "pull":
          opPull(step);
          break;
        case "recover":
          opRecover(step);
          break;
        case "schedule": {
          const choices = Array.isArray(step.choices) ? step.choices : [];
          if (choices.length === 0) {
            throw createOpError("ERR_INVALID_INPUT", "schedule requires non-empty choices");
          }
          const index = Math.floor(rng() * choices.length);
          const choice = choices[index];
          emit(runtime, "schedule.pick", { op_id: String(step.id ?? step.op), choice_index: index });
          const derivedChoice = {
            ...(choice && typeof choice === "object" ? choice : { op: "noop" }),
            id: String(choice?.id ?? `${String(step.id ?? "schedule")}/choice-${index}`)
          };
          executeStep(derivedChoice);
          break;
        }
        default:
          throw createOpError("ERR_UNKNOWN_OPERATION", `unknown operation: ${step.op}`);
      }
    }

    const script = Array.isArray(scenario.script) ? scenario.script : [];
    for (const rawStep of script) {
      const step = rawStep && typeof rawStep === "object" ? rawStep : { op: "noop" };
      const normalizedStep = {
        ...step,
        id: String(step.id ?? step.op ?? `step-${runtime.eventSeq + 1}`)
      };
      try {
        executeStep(normalizedStep);
      } catch (error) {
        const record = toErrorRecord(error, normalizedStep, error?.phase ?? null);
        runtime.errors.push(record);
        emit(runtime, "error", record);
      }
    }

    const evaluation = evaluateExpectations(runtime, runtime.errors, scenario.expect ?? {});
    return {
      id: String(scenario.id ?? "unknown-scenario"),
      title: String(scenario.title ?? scenario.id ?? "Untitled scenario"),
      status: evaluation.ok ? "passed" : "failed",
      diagnostics: evaluation.diagnostics,
      errors: runtime.errors,
      events: runtime.events,
      snapshot: evaluation.snapshot
    };
  }

  return {
    executionProfile,
    runScenario
  };
}

export function runPersistenceFixtureSet(fixtureSet, options = {}) {
  const validation = validatePersistenceFixtureSet(fixtureSet);
  if (!validation.ok) {
    return {
      version: "1.0.0",
      ok: false,
      errors: validation.errors,
      summary: { scenarioCount: 0, passed: 0, failed: 0 },
      results: []
    };
  }

  const harness = createPersistenceFaultHarness({
    executionProfile: fixtureSet.executionProfile,
    seed: options.seed
  });

  const scenarios = Array.isArray(fixtureSet.scenarios) ? fixtureSet.scenarios : [];
  const requiredOnly = options.requiredOnly !== false;
  const selected = requiredOnly
    ? scenarios.filter((scenario) => String(scenario.status ?? "required") === "required")
    : scenarios;

  const results = selected.map((scenario) => harness.runScenario(scenario));
  const passed = results.filter((result) => result.status === "passed").length;
  const failed = results.length - passed;

  return {
    version: "1.0.0",
    ok: failed === 0,
    seed: options.seed ?? harness.executionProfile.seed,
    summary: {
      scenarioCount: results.length,
      passed,
      failed
    },
    results
  };
}
