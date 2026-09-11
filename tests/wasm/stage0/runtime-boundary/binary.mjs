// A deliberately narrow structural reader for this linked wasm32 C fixture.
// Unsupported encodings fail closed; linker globals, imports and elements are
// read from final bytes, not guessed from a default address partition.
import assert from 'node:assert/strict';
const names = { 0x7f: 'i32', 0x7e: 'i64', 0x7d: 'f32', 0x7c: 'f64', 0x70: 'funcref' };

export function inspect(bytes) {
  assert.equal(Buffer.from(bytes.subarray(0, 8)).toString('hex'), '0061736d01000000');
  let p = 8, end = bytes.length;
  const byte = () => { if (p >= end) throw Error('truncated Wasm'); return bytes[p++]; };
  const leb = (signed = false) => {
    let n = 0, b, i = 0;
    do { b = byte(); n += (b & 127) * 2 ** (7 * i++); if (i > 5) throw Error('unsupported LEB'); } while (b & 128);
    if (signed && (b & 64)) n -= 2 ** (7 * i);
    return signed ? n | 0 : n;
  };
  const str = () => { const n = leb(); if (p + n > end) throw Error('truncated name'); const s = new TextDecoder('utf-8', { fatal: true }).decode(bytes.subarray(p, p + n)); p += n; return s; };
  const type = () => { const t = names[byte()]; if (!t) throw Error('unsupported type'); return t; };
  const vector = f => { const n = leb(); return Array.from({ length: n }, f); };
  const limits = () => { const flags = leb(); assert.ok(flags <= 3); const minimum = leb(); return { flags, minimum, maximum: flags & 1 ? leb() : null }; };
  const constant = () => { assert.equal(byte(), 0x41, 'expected i32.const'); const n = leb(true) >>> 0; assert.equal(byte(), 0x0b); return n; };
  const m = { types: [], imports: [], functionTypes: [], globals: [], exports: [], elements: [], data: [], sections: [] };
  while (p < bytes.length) {
    end = bytes.length;
    const sectionStart = p, id = byte(), size = leb(); end = p + size;
    m.sections.push({ id, start: sectionStart, payload: p, end });
    assert.ok(end <= bytes.length);
    if (id === 1) m.types = vector(() => { assert.equal(byte(), 0x60); return { params: vector(type), results: vector(type) }; });
    else if (id === 2) m.imports = vector(() => {
      const module = str(), name = str(), kind = byte();
      if (kind === 0) { const typeIndex = leb(); m.functionTypes.push(typeIndex); return { module, name, kind: 'function', typeIndex }; }
      if (kind === 1) return { module, name, kind: 'table', element: type(), ...limits() };
      if (kind === 2) return { module, name, kind: 'memory', ...limits() };
      throw Error('unsupported C-kernel import kind');
    });
    else if (id === 3) m.functionTypes.push(...vector(() => leb()));
    else if (id === 6) m.globals = vector(() => ({ type: type(), mutable: byte(), value: constant() }));
    else if (id === 7) m.exports = vector(() => ({ name: str(), kind: byte(), index: leb() }));
    else if (id === 8) m.start = leb();
    else if (id === 9) m.elements = vector(() => { assert.equal(leb(), 0, 'unsupported element form'); return { offset: constant(), functions: vector(() => leb()) }; });
    else if (id === 11) m.data = vector(() => {
      const flagPosition = p, flag = leb(); assert.ok(flag === 0 || flag === 1, 'unsupported data segment');
      const offset = flag === 0 ? constant() : null, size = leb();
      assert.ok(p + size <= end); p += size;
      return { passive: flag === 1, offset, size, flagPosition };
    });
    else if (id === 12) m.dataCount = leb();
    else { p = end; }
    assert.equal(p, end, `unconsumed section ${id}`);
  }
  return m;
}

export function preflight(bytes, contract) {
  assert.ok(WebAssembly.validate(bytes), 'invalid linked Wasm');
  const m = inspect(bytes);
  const memory = m.imports.filter(i => i.kind === 'memory');
  assert.equal(memory.length, 1);
  assert.deepEqual(memory[0], { module: 'env', name: 'memory', kind: 'memory', flags: 3,
    minimum: contract.memory_pages.minimum, maximum: contract.memory_pages.maximum });
  const tables = m.imports.filter(i => i.kind === 'table');
  assert.equal(tables.length, 1);
  assert.equal(tables[0].module + '.' + tables[0].name, 'env.__indirect_function_table');
  assert.equal(tables[0].element, 'funcref');
  const actual = Object.fromEntries(m.imports.filter(i => i.kind === 'function').map(i => [i.module + '.' + i.name, m.types[i.typeIndex]]));
  assert.deepEqual(actual, contract.allowed_function_imports, 'unapproved/mistyped function imports');
  assert.ok(m.data.length > 0 && m.data.every(d => d.passive), 'active shared initialization rejected before instantiation');
  assert.equal(m.dataCount, m.data.length);
  assert.ok(Number.isInteger(m.start), 'missing process-once linker start');
  m.exportedGlobals = Object.fromEntries(m.exports.filter(e => e.kind === 3).map(e => [e.name, m.globals[e.index]]));
  const g = name => { const e = m.exportedGlobals[name]; assert.ok(e, `missing linker global ${name}`); return e.value; };
  assert.ok(m.exportedGlobals.__stack_pointer.mutable, 'C SP must be instance-private mutable global');
  assert.ok(g('__global_base') <= g('__data_end'));
  assert.ok(g('__data_end') <= g('__stack_low') && g('__stack_low') < g('__stack_high'));
  assert.ok(g('__stack_high') <= g('__heap_base'));
  assert.equal(g('__tls_align') & (g('__tls_align') - 1), 0);
  assert.ok(g('__tls_align') > 0 && g('__tls_size') > 0);
  m.reservedSlots = [0];
  for (const segment of m.elements) {
    for (let i = 0; i < segment.functions.length; i++) {
      const slot = segment.offset + i;
      assert.ok(slot < tables[0].minimum && !m.reservedSlots.includes(slot), 'conflicting C entry reservations');
      m.reservedSlots.push(slot);
    }
  }
  assert.ok(m.reservedSlots.length > 1, 'fixture C function pointer must have a reservation');
  m.tableMinimum = tables[0].minimum;
  return m;
}
