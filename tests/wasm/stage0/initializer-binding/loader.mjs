// S0-LL15-a bootstrap loader. Validates the closure manifest against the
// supplied modules before anything is instantiated, seeds the loader's own
// dependencies (phase 0) before any bundle exists, binds every initializer to
// its prerequisites' physical completion words and required service state,
// checks each completion physically after the initializer returns, and
// publishes ready only when every required initializer has completed. Every
// refusal names its reason and happens before dependents run.
const fail = (reason, stage, extra = {}) => { const e = Error(reason); e.refusal = { reason, stage, ...extra }; throw e; };

export function validate(manifest, supplied) {
  const byId = new Map();
  for (const i of manifest.initializers) {
    if (byId.has(i.id)) fail('DUPLICATE_INITIALIZER ' + i.id, 'manifest');
    byId.set(i.id, i);
  }
  const ordinals = new Set(manifest.initializers.map(i => i.ordinal));
  if (ordinals.size !== manifest.initializers.length) fail('DUPLICATE_ORDINAL', 'manifest');
  const phases = new Set(manifest.phases.map(p => p.phase));
  for (const [name, m] of Object.entries(manifest.modules)) {
    if (!phases.has(m.phase)) fail('UNKNOWN_PHASE ' + name, 'manifest');
    if (m.role === 'loader' && m.phase !== 0) fail('LOADER_DEPENDENCY_NOT_SEEDED ' + name, 'manifest');
    if (m.role !== 'loader' && m.phase === 0) fail('BUNDLE_IN_LOADER_PHASE ' + name, 'manifest');
  }
  for (const i of manifest.initializers) {
    const m = manifest.modules[i.module];
    if (!m) fail('UNKNOWN_MODULE ' + i.id, 'manifest');
    if (!m.exports.includes(i.id)) fail('UNDECLARED_INITIALIZER_EXPORT ' + i.id, 'manifest');
    if (i.phase < m.phase) fail('INITIALIZER_BEFORE_MODULE_PHASE ' + i.id, 'manifest');
    if (m.role === 'loader' && i.phase !== 0) fail('LOADER_DEPENDENCY_NOT_SEEDED ' + i.id, 'manifest');
    for (const p of i.prerequisites) {
      const q = byId.get(p);
      if (!q) fail('UNKNOWN_PREREQUISITE ' + i.id + ' -> ' + p, 'manifest');
      if (q.phase > i.phase) fail('FORWARD_PHASE_DEPENDENCY ' + i.id + ' -> ' + p, 'manifest');
    }
    if (m.deferred) fail('DEFERRED_REQUIRED_MODULE ' + i.module, 'manifest');
  }
  // Topological order within phases; a cycle has no acyclic effect schedule.
  const order = [];
  for (const phase of [...phases].sort((a, b) => a - b)) {
    const pending = manifest.initializers.filter(i => i.phase === phase).sort((a, b) => a.ordinal - b.ordinal);
    const done = new Set(order.map(i => i.id));
    let progress = true;
    while (pending.length && progress) {
      progress = false;
      for (let k = 0; k < pending.length; k++) {
        if (pending[k].prerequisites.every(p => done.has(p))) { order.push(pending[k]); done.add(pending[k].id); pending.splice(k, 1); progress = true; break; }
      }
    }
    if (pending.length) {
      // Name the members of the cycle itself, not the dependents it blocks.
      let cycle = pending;
      for (;;) {
        const kept = cycle.filter(i => cycle.some(j => j.prerequisites.includes(i.id)));
        if (kept.length === cycle.length) break;
        cycle = kept;
      }
      fail('INITIALIZATION_CYCLE ' + cycle.map(i => i.id).sort().join(','), 'manifest', { blocked: pending.map(i => i.id).sort() });
    }
  }
  // Every required module must be supplied and must actually export its initializers with the declared shape.
  const moduleOrder = Object.keys(manifest.modules);
  for (const name of moduleOrder) {
    if (!supplied[name]) fail('REQUIRED_MODULE_OMITTED ' + name, 'modules');
    if (!WebAssembly.validate(supplied[name])) fail('INVALID_MODULE ' + name, 'modules');
    const compiled = new WebAssembly.Module(supplied[name]);
    const exports = new Map(WebAssembly.Module.exports(compiled).map(e => [e.name, e.kind]));
    const imports = WebAssembly.Module.imports(compiled).map(i => i.module + '.' + i.name).sort();
    if (JSON.stringify(imports) !== JSON.stringify([...manifest.modules[name].imports].sort())) fail('IMPORT_MISMATCH ' + name, 'modules');
    for (const i of manifest.initializers.filter(i => i.module === name)) {
      if (exports.get(i.id) !== 'function') fail('MISSING_INITIALIZER_EXPORT ' + name + '.' + i.id, 'modules');
    }
  }
  return { order, moduleOrder };
}

export function bootstrap(manifest, supplied, memory) {
  const events = []; const ledger = []; const ran = [];
  const words = new Int32Array(memory.buffer);
  let core = null;
  const note = code => { events.push(code); if (core) core.exports.note(code); };
  const refuse = (reason, stage, extra = {}) => { note(800); return { refusal: { reason, stage, ran: [...ran], ...extra }, events, ledger }; };
  let plan;
  try { plan = validate(manifest, supplied); }
  catch (e) { if (e.refusal) return refuse(e.refusal.reason, e.refusal.stage); throw e; }
  const instances = {};
  const instantiate = name => {
    const index = plan.moduleOrder.indexOf(name);
    const imports = { env: { memory } };
    if (manifest.modules[name].role !== 'loader') {
      if (!core) fail('BUNDLE_BEFORE_LOADER ' + name, 'load');
      imports.loader = { note: core.exports.note, complete: core.exports.complete, completed: core.exports.completed };
    }
    instances[name] = new WebAssembly.Instance(new WebAssembly.Module(supplied[name]), imports);
    if (manifest.modules[name].role === 'loader') core = instances[name];
    note(500 + index);
  };
  const run = i => {
    const declared = new Map(manifest.initializers.map(x => [x.id, x]));
    for (const p of i.prerequisites) {
      const q = declared.get(p);
      const observed = core.exports.completed(q.ordinal);
      if (observed !== q.completion) fail('COMPLETION_MISMATCH ' + i.id + ' <- ' + p, 'prerequisites', { observed, expected: q.completion });
    }
    for (const s of i.requires_state) {
      if (words[s.address / 4] !== s.value) fail('STATE_MISMATCH ' + i.id + ' @' + s.address, 'prerequisites', { observed: words[s.address / 4], expected: s.value });
    }
    note(200 + i.ordinal);
    if (core.exports.completed(i.ordinal) !== 0) fail('ALREADY_COMPLETED ' + i.id, 'run');
    note(300 + i.ordinal);
    let code;
    try { code = instances[i.module].exports[i.id](); }
    catch (e) { fail('INITIALIZER_FAILED ' + i.id, 'run', { error: e.constructor.name }); }
    ran.push(i.id);
    const word = core.exports.completed(i.ordinal), counter = words[1152 / 4 + i.ordinal];
    if (code !== i.completion) fail('COMPLETION_MISMATCH ' + i.id, 'completion', { observed: code, expected: i.completion });
    if (word !== i.completion) fail('COMPLETION_NOT_WRITTEN ' + i.id, 'completion', { observed: word, expected: i.completion });
    if (counter !== 1) fail('EXECUTION_COUNT ' + i.id, 'completion', { observed: counter });
    note(400 + i.ordinal);
    ledger.push({ id: i.id, ordinal: i.ordinal, completion: word, counter });
  };
  try {
    for (const name of plan.moduleOrder.filter(n => manifest.modules[n].role === 'loader')) instantiate(name);
    for (const i of plan.order.filter(i => i.phase === 0)) run(i);
    for (const name of plan.moduleOrder.filter(n => manifest.modules[n].role !== 'loader')) instantiate(name);
    for (const i of plan.order.filter(i => i.phase !== 0)) run(i);
  } catch (e) { if (e.refusal) return refuse(e.refusal.reason, e.refusal.stage, e.refusal); throw e; }
  // Ready publication: every required initializer's word equals its declaration, once more from memory.
  for (const i of manifest.initializers) {
    if (core.exports.completed(i.ordinal) !== i.completion) return refuse('READY_INCOMPLETE ' + i.id, 'ready');
  }
  const checksum = manifest.initializers.reduce((x, i) => x ^ i.completion, 0);
  words[manifest.ready.generation_word / 4] = 1; words[manifest.ready.count_word / 4] = manifest.initializers.length; words[manifest.ready.checksum_word / 4] = checksum;
  note(700);
  return { ready: { generation: 1, count: manifest.initializers.length, checksum, order: plan.order.map(i => i.id) }, events, ledger };
}
