// D2 materializer for S0-LL21-c. One canonical template with an unshared,
// explicit-maximum memory import yields the unshared and shared profile
// binaries by changing exactly the limits flag byte. Every check fails closed:
// unsupported encodings, hash mismatches, wrong structural records, wrong
// features and wrong profiles are refused rather than guessed.
import { createHash } from 'node:crypto';
import { inspect } from './binary.mjs';

export const MATERIALIZER_VERSION = 2;
export const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const fail = reason => { throw Error(reason); };

// Locate the flags byte of the single env.memory import from the raw bytes.
export function memoryImportOffset(bytes) {
  if (Buffer.from(bytes.subarray(0, 8)).toString('hex') !== '0061736d01000000') fail('bad Wasm header');
  let p = 8;
  const uleb = end => {
    let value = 0;
    for (let i = 0; i < 5; i++) {
      if (p >= end) fail('truncated LEB');
      const b = bytes[p++];
      if (i === 4 && b > 15) fail('oversized LEB');
      value += (b & 127) * 2 ** (7 * i);
      if (!(b & 128)) return value;
    }
    fail('unterminated LEB');
  };
  const name = end => { const size = uleb(end); if (p + size > end) fail('truncated import name'); const s = new TextDecoder('utf-8', { fatal: true }).decode(bytes.subarray(p, p + size)); p += size; return s; };
  let memory = null;
  while (p < bytes.length) {
    const id = bytes[p++], size = uleb(bytes.length), end = p + size;
    if (end > bytes.length) fail('truncated section');
    if (id === 2) {
      const count = uleb(end);
      for (let i = 0; i < count; i++) {
        const module = name(end), field = name(end), kind = bytes[p++];
        if (kind === 0) uleb(end);
        else if (kind === 1) { p++; const flags = uleb(end); uleb(end); if (flags & 1) uleb(end); }
        else if (kind === 2) {
          if (memory) fail('unsupported import inventory: more than one memory');
          if (module !== 'env' || field !== 'memory') fail('unsupported memory import name');
          const offset = p, flags = bytes[p++];
          if (flags === 3) fail('template already declares shared memory');
          if (flags !== 1) fail('requires canonical unshared explicit-maximum memory');
          const minimum = uleb(end), maximum = uleb(end);
          if (minimum > maximum || maximum > 65536) fail('invalid memory limits');
          memory = { offset, minimum, maximum };
        } else fail('unsupported import kind');
      }
      if (p !== end) fail('malformed import section');
    }
    p = end;
  }
  if (!memory) fail('template must import env.memory');
  return memory;
}

const signature = (types, index) => ({ params: types[index].params, results: types[index].results });

export function inspectTemplate(bytes, abi) {
  if (!WebAssembly.validate(bytes)) fail('invalid template');
  const memory = memoryImportOffset(bytes);
  const m = inspect(bytes);
  const spec = abi.template;
  if (memory.minimum !== spec.memory.minimum || memory.maximum !== spec.memory.maximum) fail('memory limits differ from the interface');
  if (Number.isInteger(m.start)) fail('template has a start function');
  if (m.data.some(d => !d.passive)) fail('template has active data segments');
  const imports = {};
  for (const i of m.imports) {
    if (i.kind === 'memory') continue;
    if (i.kind !== 'function') fail('unsupported template import kind');
    imports[i.module + '.' + i.name] = signature(m.types, i.typeIndex);
  }
  const exports = {};
  for (const e of m.exports) {
    if (e.kind !== 0) fail('unsupported template export kind');
    exports[e.name] = signature(m.types, m.functionTypes[e.index]);
  }
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  if (!same(imports, spec.function_imports)) fail('function imports differ from the interface');
  if (!same(exports, spec.exports)) fail('exports differ from the interface');
  return { offset: memory.offset, minimum: memory.minimum, maximum: memory.maximum, imports, exports };
}

// The runner supplies each binary's disassembly classification: feature
// families actually used, and whether wait/notify instructions appear.
export function manifest(bytes, abi, classification) {
  const structure = inspectTemplate(bytes, abi);
  if (classification.wait) fail('template contains wait or notify instructions');
  return { version: MATERIALIZER_VERSION, template_sha256: sha256(bytes), original_byte: 1, ...structure,
    features: [...classification.features].sort(), materializer_version: MATERIALIZER_VERSION };
}

export function materialize(bytes, record, abi, profile, classification, admission) {
  if (record.version !== MATERIALIZER_VERSION || record.materializer_version !== MATERIALIZER_VERSION) fail('unsupported materialization contract');
  if (sha256(bytes) !== record.template_sha256) fail('template hash mismatch');
  const actual = inspectTemplate(bytes, abi);
  for (const key of ['offset', 'minimum', 'maximum']) if (actual[key] !== record[key]) fail('wrong structural ' + key);
  if (JSON.stringify(actual.imports) !== JSON.stringify(record.imports)) fail('import inventory mismatch');
  if (JSON.stringify(actual.exports) !== JSON.stringify(record.exports)) fail('export inventory mismatch');
  if (record.original_byte !== 1 || bytes[actual.offset] !== 1) fail('wrong original limits byte');
  if (classification.wait) fail('template contains wait or notify instructions');
  if (JSON.stringify([...classification.features].sort()) !== JSON.stringify(record.features)) fail('feature requirement mismatch');
  const rules = abi.profiles[profile];
  if (!rules) fail('unknown profile');
  if (!admission || admission[profile] !== true) fail('profile not admitted on the target engine');
  const shared = rules.memory === 'shared';
  const result = Uint8Array.from(bytes);
  result[actual.offset] = shared ? 3 : 1;
  if (!WebAssembly.validate(result)) fail('invalid materialized binary');
  const binary = sha256(result);
  if (shared === false && binary !== record.template_sha256) fail('unshared materialization must preserve the template bytes');
  return { bytes: result, record: { profile, shared, template_sha256: record.template_sha256, binary_sha256: binary, materializer_version: MATERIALIZER_VERSION,
    offset: actual.offset, patched_byte: shared ? 3 : 1, limits: { minimum: actual.minimum, maximum: actual.maximum }, imports: record.imports, exports: record.exports, features: record.features, bytes: result.length } };
}

// Installation identity is the final binary hash, never the template hash.
export function install(bytes, record) {
  if (record.materializer_version !== MATERIALIZER_VERSION) fail('stale materializer version');
  if (record.shared && record.binary_sha256 === record.template_sha256) fail('template hash is not an installed-binary identity');
  if (sha256(bytes) !== record.binary_sha256) fail('installed binary hash mismatch');
  if (!WebAssembly.validate(bytes)) fail('invalid installed binary');
  return new WebAssembly.Module(bytes);
}

export function checkRuntime(bytes, profile, abi, classification) {
  const rules = abi.profiles[profile]?.runtime_rules;
  if (!rules) fail('unknown profile');
  if (!WebAssembly.validate(bytes)) fail('invalid runtime');
  if (classification.wait && !rules.wait_allowed) fail('runtime carries a wait path the profile prohibits');
  if (!classification.wait && rules.wait_allowed) fail('full-profile runtime lacks its wait path');
  const m = inspect(bytes);
  const memory = m.imports.filter(i => i.kind === 'memory');
  if (memory.length !== 1 || memory[0].flags !== rules.memory_flags) fail('runtime memory declaration does not match the profile');
  const functions = m.imports.filter(i => i.kind === 'function').map(i => i.module + '.' + i.name).sort();
  if (JSON.stringify(functions) !== JSON.stringify([...rules.function_imports].sort())) fail('runtime imports do not match the profile');
  if (!m.exports.some(e => e.name === 'request' && e.kind === 0)) fail('runtime lacks the request export');
  return { memory: memory[0] ? { flags: memory[0].flags, minimum: memory[0].minimum, maximum: memory[0].maximum } : null, function_imports: functions };
}
