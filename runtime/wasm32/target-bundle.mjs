// Runtime code loading. The file owns its FASL, module bytes and templates;
// none of these are recovered from a cross-loaded heap or a build directory.
import {snapshotBytes, utf8} from './bytes.mjs';
import {sha256} from './sha256.mjs';
import {compile, publish, PACKAGING} from './bundle.mjs';

const need = (ok, why) => { if (!ok) throw Error('target bundle: ' + why); };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const uint = n => Number.isSafeInteger(n) && n >= 0 && n <= 0xffffffff;
const MAGIC = 0x42323357, HEADER = 16, MAX_BYTES = 512 * 1024 * 1024;

export function installRecord(record) {
  const value = [...record]; value[0] = 6; value[4] = null;
  value[8] = record[8] === null ? null : record[8].map(installRecord);
  return value;
}

// The trusted producer supplies the inventory; the namespace authenticates
// the resulting file digest. Lengths delimit every inline byte source.
export function encodeTargetBundle({codeSet, units, fasl, readBytes, readTemplate}) {
  const set = structuredClone(codeSet), data = snapshotBytes(fasl), chunks = [];
  for (const row of set.modules) {
    const bytes = snapshotBytes(readBytes(row.name));
    const template = snapshotBytes(readTemplate(row.name));
    chunks.push(bytes, template);
    row.byte_length = bytes.length;
    row.template_length = template.length;
  }
  const manifest = utf8(JSON.stringify({version: 1, codeSet: set, units,
    fasl_sha256: sha256(data)}));
  const size = HEADER + manifest.length + data.length + chunks.reduce((n, b) => n + b.length, 0);
  need(size <= MAX_BYTES, 'SIZE');
  const output = new Uint8Array(size), view = new DataView(output.buffer);
  [MAGIC, 1, manifest.length, data.length].forEach((n, i) => view.setUint32(i * 4, n, true));
  let offset = HEADER;
  for (const chunk of [manifest, data, ...chunks]) { output.set(chunk, offset); offset += chunk.length; }
  return output;
}

export function decodeTargetBundle(input, digest) {
  const bytes = snapshotBytes(input);
  need(bytes.length >= HEADER && bytes.length <= MAX_BYTES, 'SIZE');
  need(sha256(bytes) === digest, 'DIGEST');
  const view = new DataView(bytes.buffer);
  need(view.getUint32(0, true) === MAGIC && view.getUint32(4, true) === 1, 'VERSION');
  let offset = HEADER;
  const take = size => {
    need(uint(size) && size <= bytes.length - offset, 'TRUNCATED');
    const part = bytes.slice(offset, offset + size); offset += size; return part;
  };
  const manifest = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(take(view.getUint32(8, true))));
  need(manifest.version === 1 && manifest.codeSet?.packaging === PACKAGING &&
    Array.isArray(manifest.codeSet.modules) && Array.isArray(manifest.units), 'MANIFEST');
  const fasl = take(view.getUint32(12, true));
  need(sha256(fasl) === manifest.fasl_sha256, 'FASL_DIGEST');
  const modules = new Map();
  for (const row of manifest.codeSet.modules) {
    need(typeof row.name === 'string' && !modules.has(row.name), 'MODULE_NAME');
    modules.set(row.name, {bytes: take(row.byte_length), template: take(row.template_length)});
  }
  need(offset === bytes.length, 'TRAILING_BYTES');
  return {manifest, fasl, modules};
}

// Installation is synchronous and never reenters Lisp. Version-5 compiler
// records import stable addresses of collector-owned root cells; their values
// can move. Older version-4 records require stable tagged imports.
export function admitTargetBundle({bytes, digest, env, capabilities = {}, versions, policy,
  slots, codeIds, stableReference, rootCells, measure = (_phase, run) => run()}) {
  env = {...env}; slots = {...slots}; codeIds = {...codeIds};
  capabilities = Object.fromEntries(Object.entries(capabilities).map(([name, value]) => [name, {...value}]));
  const {manifest, fasl, modules} = measure('bundle.decode', () => decodeTargetBundle(bytes, digest));
  const set = manifest.codeSet, units = new Map(), rows = new Map();
  need(typeof stableReference === 'function' || typeof rootCells === 'function', 'REFERENCE_AUTHORITY');
  need(env.table !== env.tail_table, 'DISTINCT_TABLES');
  const view = () => new DataView(env.memory.buffer);
  const get = p => view().getUint32(p, true), put = (p, n) => view().setUint32(p, n, true);
  const registry = env.code_registry;
  need(uint(registry) && registry % 8 === 0 && registry + 8 <= env.memory.buffer.byteLength, 'REGISTRY');
  const capacity = get(registry);
  need(get(registry + 4) === 1 && registry + 8 + 16 * capacity <= env.memory.buffer.byteLength, 'REGISTRY');
  const ids = new Set(), slotSet = new Set();
  for (const row of set.modules) {
    need(!rows.has(row.code_id), 'CODE_ID');
    const id = codeIds[row.code_id], slot = slots[row.code_id];
    need(uint(id) && id > 0 && id < capacity && id <= 536870911 && !ids.has(id), 'CODE_ID');
    need(uint(slot) && slot > 0 && slot < env.table.length && slot < env.tail_table.length && !slotSet.has(slot), 'SLOT');
    need(row.version === 4 && row.signature === 17 && row.role === 23, 'CODE_ROLE');
    need(['values', 'root-cells'].includes(row.symbol_mode ?? 'values'), 'SYMBOL_MODE');
    need(Array.isArray(row.symbols) && Array.isArray(row.codes), 'IMPORTS');
    ids.add(id); slotSet.add(slot); rows.set(row.code_id, row);
  }
  for (const unit of manifest.units) {
    need(typeof unit.name === 'string' && !units.has(unit.name) && rows.has(unit.root) &&
      uint(unit.symbol_count) && Array.isArray(unit.modules) && unit.modules.includes(unit.root) &&
      new Set(unit.modules).size === unit.modules.length && unit.modules.every(id => rows.has(id)), 'UNIT');
    need([4, 5, 6].includes(unit.record_version) && /^[0-9a-f]{64}$/.test(unit.record_sha256), 'CODE_RECORD');
    units.set(unit.name, unit);
    const owned = new Set(unit.modules);
    for (const id of unit.modules) {
      const row = rows.get(id), wires = new Set();
      need((row.symbol_mode === 'root-cells') === (unit.record_version >= 5), 'SYMBOL_MODE');
      for (const s of row.symbols) {
        need(typeof s.wire === 'string' && !wires.has(s.wire) && uint(s.index) && s.index < unit.symbol_count, 'SYMBOL_WIRE');
        wires.add(s.wire);
      }
      const codes = new Set();
      for (const c of row.codes) {
        need(typeof c.name === 'string' && !codes.has(c.name) && owned.has(c.code_id), 'CODE_IMPORT');
        codes.add(c.name);
      }
      for (const i of row.d2.outputs.full.imports) {
        if (i.module === 'symbols') need(wires.has(i.name), 'SYMBOL_IMPORT');
        if (i.module === 'codes') need(codes.has(i.name), 'CODE_IMPORT');
        need(i.module !== 'keywords', 'KEYWORD_IMPORT');
      }
    }
  }
  const owned = manifest.units.flatMap(u => u.modules);
  need(owned.length === rows.size && new Set(owned).size === rows.size, 'COMPLETE_UNITS');
  // Preflight every module, including template materialization and role checks,
  // before a single target function can be published.
  const compiled = measure('bundle.compile', () => compile(set, {...versions, modules: set.modules.map(m => [m.name, m.code_id, m.generation]),
    table_capacity: Math.min(env.table.length, env.tail_table.length), reserved_slots: [0], slots},
    name => modules.get(name).bytes, name => modules.get(name).template, policy));
  const installed = new Map();
  const empty = row => {
    const id = codeIds[row.code_id], slot = slots[row.code_id];
    need([0, 4, 8, 12].every(o => get(registry + 8 + 16 * id + o) === 0), 'CODE_OCCUPIED');
    need(env.table.get(slot) === null && env.tail_table.get(slot) === null, 'SLOT_OCCUPIED');
  };
  for (const row of set.modules) empty(row);
  return Object.freeze({
    fasl: () => snapshotBytes(fasl),
    install(name, record, symbolValues) {
      const unit = units.get(name);
      need(unit && sha256(JSON.stringify(record)) === unit.record_sha256, 'CODE_RECORD');
      need(Array.isArray(symbolValues) && symbolValues.length === unit.symbol_count, 'SYMBOL_COUNT');
      const values = [...symbolValues];
      const rooted = unit.record_version >= 5;
      for (const value of values) need(uint(value) && (rooted || stableReference?.(value)), 'MOVABLE_IMPORT');
      need(!rooted || typeof rootCells === 'function', 'ROOT_AUTHORITY');
      const old = installed.get(name);
      if (old) {
        need(same(old.roots ? old.roots.values() : old.values, values), 'IMPORT_IDENTITY');
        for (const {record: row, instance} of old.instances) {
          const id = codeIds[row.code_id], slot = slots[row.code_id], p = registry + 8 + 16 * id;
          need(same([get(p), get(p + 4), get(p + 8), get(p + 12)], [slot, 4, 17, 23]), 'REGISTRY_CHANGED');
          need(env.table.get(slot) === instance.exports.entry && env.tail_table.get(slot) === instance.exports.tail_entry, 'TABLE_CHANGED');
        }
        return codeIds[unit.root];
      }
      const wanted = new Set(unit.modules), imports = new Map();
      const group = compiled.filter(m => wanted.has(m.record.code_id));
      for (const {record: row} of group) empty(row);
      const roots = rooted ? measure('bundle.roots', () => rootCells(values)) : null;
      const references = roots ? roots.slots : values;
      let instances;
      try {
      for (const {record: row} of group) {
        imports.set(row.name, {env,
          ...Object.fromEntries(['owner', 'integer', 'floating'].filter(n => capabilities[n]).map(n => [n, {...capabilities[n]}])),
          symbols: Object.fromEntries(row.symbols.map(s => [s.wire, references[s.index]])),
          codes: Object.fromEntries(row.codes.map(c => [c.name, codeIds[c.code_id] * 4]))});
      }
      // publish() instantiates the entire graph before touching paired tables.
      instances = measure('bundle.publish', () => publish(group, name => imports.get(name), env.table, env.tail_table));
      } catch (error) { roots?.release(); throw error; }
      for (const {record: row} of group) {
        const p = registry + 8 + 16 * codeIds[row.code_id];
        [slots[row.code_id], 4, 17, 23].forEach((word, i) => put(p + 4 * i, word));
      }
      installed.set(name, {values: rooted ? null : values, roots,
        instances: instances.map(entry => ({...entry, imports: imports.get(entry.record.name)}))});
      return codeIds[unit.root];
    },
    installed: () => [...installed.keys()],
    entries: () => [...installed.values()].flatMap(unit => unit.instances.map(entry =>
      ({...entry, codeId: codeIds[entry.record.code_id]})))
  });
}
