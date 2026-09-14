import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const [bundle, casesPath, output] = process.argv.slice(2);
const read = name => fs.readFileSync(path.join(bundle, name));
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const abi = JSON.parse(read('abi.json'));
const manifest = JSON.parse(read('manifest.json'));
const map = JSON.parse(read('map.json'));
const cases = JSON.parse(fs.readFileSync(casesPath));
function u32(value) { return value >>> 0; }
function valid(value, kind) {
  const low = kind === 'u32' ? 0 : -2147483648;
  const high = kind === 'i32' ? 2147483647 : 4294967295;
  return Number.isInteger(value) && value >= low && value <= high;
}
const result = {version: 1, scope: 'HAND-BUILT WASM CONVERSIONS', node: process.version,
  v8: process.versions.v8, instantiated: false, records: []};
try {
  for (const [name, digest] of Object.entries(manifest.files)) {
    if (hash(read(name)) !== digest) throw Error('FILE_IDENTITY ' + name);
  }
  const {instance} = await WebAssembly.instantiate(read('module.wasm'));
  result.instantiated = true;
  const e = instance.exports;
  for (const c of cases) {
    const args = c.args.map(x => x === '$reserved' ? map.reserved_end : x);
    const row = {name: c.name, family: c.family, args, called: false};
    try {
      if (c.op === 'grow') {
        const oldView = new DataView(e.memory.buffer);
        const before = oldView.byteLength;
        const previous = e.memory.grow(args[0]);
        row.called = true;
        row.engine_pair = row.pair = [previous, 0];
        row.growth = {before_bytes: before, after_bytes: e.memory.buffer.byteLength,
          old_view_detached: oldView.buffer.byteLength === 0};
      } else {
        const sig = abi.exports[c.op];
        if (!sig || args.length !== sig.params.length) throw Error('UNKNOWN_INTERFACE');
        if (!args.every((x, i) => valid(x, sig.params[i]))) {
          row.engine_pair = null; row.pair = [0, 13];
        } else {
          row.called = true;
          const pair = e[c.op](...args);
          row.engine_pair = pair;
          row.pair = [sig.unsigned_result ? u32(pair[0]) : pair[0], pair[1]];
          if (pair[1] === 0 && (c.op === 'cons_store' || c.op === 'header_store')) {
            // Refresh after growth; use unsigned Number byte offsets directly.
            const view = new DataView(e.memory.buffer);
            row.bytes = Array.from(new Uint8Array(view.buffer, args[0], 8));
          }
        }
      }
    } catch (error) {
      row.error = {name: error.name, message: error.message};
    }
    result.records.push(row);
  }
  result.final_memory_bytes = e.memory.buffer.byteLength;
  result.status = 'OBSERVED';
} catch (error) {
  result.status = 'HARNESS_FAILURE';
  result.error = {name: error.name, message: error.message};
}
fs.writeFileSync(output, JSON.stringify(result, null, 2) + '\n');
