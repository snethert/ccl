import assert from 'node:assert/strict';

const align = (value, alignment) => Math.ceil(value / alignment) * alignment;
export function planMemory(metadata, contract, workers = 3) {
  const g = name => metadata.exportedGlobals[name].value;
  let next = align(g('__heap_base'), 16);
  const regions = [{ name: 'fixture-lowmem', start: 64, end: 136, alignment: 8 },
    { name: 'kernel-static-and-default-stack', start: g('__global_base'), end: g('__heap_base'), alignment: 16 }];
  const allocate = (name, bytes, alignment) => {
    const start = align(next, alignment); next = start + bytes;
    const r = { name, start, end: next, alignment }; regions.push(r); return r;
  };
  const plans = Array.from({ length: workers }, (_, id) => ({ id,
    tls: allocate(`worker-${id}-tls`, g('__tls_size'), g('__tls_align')),
    tcr: allocate(`worker-${id}-tcr`, contract.tcr_bytes, contract.tcr_alignment),
    lisp: allocate(`worker-${id}-explicit-stacks`, 2048, 16),
    stack: allocate(`worker-${id}-C-stack`, contract.c_stack_bytes, contract.c_stack_alignment) }));
  assert.ok(next <= contract.memory_pages.minimum * 65536, 'fixture memory too small');
  const map = { regions, workers: plans, tableReserved: metadata.reservedSlots, usedEnd: next };
  validateMap(map, contract.memory_pages.minimum * 65536);
  return map;
}

export function validateMap(map, bytes) {
  const sorted = [...map.regions].sort((a, b) => a.start - b.start);
  for (let i = 0; i < sorted.length; i++) {
    const r = sorted[i];
    assert.ok(Number.isInteger(r.start) && Number.isInteger(r.end) && r.start >= 0 && r.end > r.start && r.end <= bytes);
    assert.ok(r.alignment > 0 && (r.alignment & (r.alignment - 1)) === 0 && r.start % r.alignment === 0);
    if (i) assert.ok(sorted[i - 1].end <= r.start, `overlap: ${sorted[i - 1].name}/${r.name}`);
  }
  for (const w of map.workers) {
    for (const name of ['tls', 'tcr', 'lisp', 'stack']) assert.ok(sorted.some(r => JSON.stringify(r) === JSON.stringify(w[name])), 'worker ownership record differs from map');
    assert.ok(w.stack.end - w.stack.start >= 16384, 'undersized C stack');
  }
}

export function instantiate(kernelBytes, emittedBytes, memory, metadata, park = () => { throw Error('unexpected main-thread park'); }) {
  const emitted = new WebAssembly.Instance(new WebAssembly.Module(emittedBytes));
  const table = new WebAssembly.Table({ initial: metadata.tableMinimum, element: 'anyfunc' });
  const kernel = new WebAssembly.Instance(new WebAssembly.Module(kernelBytes), {
    env: { memory, __indirect_function_table: table }, bridge: { park }, emitted: { raise: emitted.exports.raise } });
  return { kernel, emitted, table };
}

export function setup(instance, memory, plan, metadata) {
  const k = instance.kernel.exports;
  assert.equal(k.__tls_size.value, metadata.exportedGlobals.__tls_size.value);
  k.__stack_pointer.value = plan.stack.end;
  k.__wasm_init_tls(plan.tls.start);
  assert.equal(k.__tls_base.value, plan.tls.start);
  k.set_tcr(plan.tcr.start);
  const words = new Uint32Array(memory.buffer);
  words.fill(0, plan.tcr.start / 4, plan.tcr.end / 4);
  assert.equal(k.get_tcr(), plan.tcr.start);
}

export function observe(memory, plan) {
  const w = new Uint32Array(memory.buffer), t = plan.tcr.start / 4;
  return { token: w[t], frame: w[t + 1], tcrBefore: w[t + 2], tcrAfter: w[t + 3], stackOk: w[t + 4] };
}

export function assertIsolation(observations, plans) {
  for (let i = 0; i < plans.length; i++) {
    const o = observations[i], p = plans[i];
    assert.ok(o.frame >= p.stack.start && o.frame + 256 <= p.stack.end, 'C frame outside owned stack');
    assert.equal(o.tcrBefore, p.tcr.start, 'wrong current TCR on entry');
    assert.equal(o.tcrAfter, p.tcr.start, 'current TCR changed during concurrent C activity');
    assert.equal(o.stackOk, 1, 'live C locals overwritten');
  }
  assert.equal(new Set(observations.map(o => o.frame)).size, observations.length, 'C stacks alias');
}
