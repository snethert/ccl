import { createHash } from 'node:crypto';

export const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');

// Deliberately admits only one env.memory import with wasm32 explicit min/max.
// Every unsupported import/limits encoding fails; this is an initial proof scope.
export function inspectTemplate(bytes) {
  if (Buffer.from(bytes.subarray(0, 8)).toString('hex') !== '0061736d01000000') throw Error('bad Wasm header');
  let p = 8;
  const uleb = end => {
    let value = 0;
    for (let i = 0; i < 5; i++) {
      if (p >= end) throw Error('truncated LEB');
      const b = bytes[p++];
      if (i === 4 && b > 15) throw Error('oversized LEB');
      value += (b & 127) * 2 ** (7 * i);
      if (!(b & 128)) return value;
    }
    throw Error('unterminated LEB');
  };
  const name = end => {
    const size = uleb(end);
    if (p + size > end) throw Error('truncated import name');
    const result = new TextDecoder('utf-8', { fatal: true }).decode(bytes.subarray(p, p + size));
    p += size;
    return result;
  };
  let memory;
  while (p < bytes.length) {
    const id = bytes[p++];
    const size = uleb(bytes.length), end = p + size;
    if (end > bytes.length) throw Error('truncated section');
    if (id === 2) {
      if (memory || uleb(end) !== 1) throw Error('unsupported import inventory');
      if (name(end) !== 'env' || name(end) !== 'memory' || bytes[p++] !== 2) throw Error('unsupported import');
      const offset = p;
      if (bytes[p++] !== 1) throw Error('requires canonical unshared explicit-maximum memory');
      const minimum = uleb(end), maximum = uleb(end);
      if (minimum > maximum || maximum > 65536 || p !== end) throw Error('invalid memory limits');
      memory = { offset, minimum, maximum };
    }
    p = end;
  }
  if (!memory || !WebAssembly.validate(bytes)) throw Error('invalid template');
  return memory;
}

export function materialize(bytes, record, shared) {
  if (sha256(bytes) !== record.template_sha256) throw Error('template hash mismatch');
  const actual = inspectTemplate(bytes);
  for (const key of ['offset', 'minimum', 'maximum']) {
    if (actual[key] !== record[key]) throw Error(`wrong structural ${key}`);
  }
  if (record.version !== 1 || record.original_byte !== 1 || typeof shared !== 'boolean') throw Error('unsupported materialization contract');
  const result = Uint8Array.from(bytes);
  result[actual.offset] = shared ? 3 : 1;
  if (!WebAssembly.validate(result)) throw Error('invalid materialized binary');
  return result;
}
