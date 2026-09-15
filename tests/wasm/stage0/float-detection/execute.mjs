#!/usr/bin/env node
// Run the checked operations over a corpus: node execute.mjs BUNDLE CORPUS OUT
import fs from 'node:fs';
import path from 'node:path';
const [bundle, corpusPath, out] = process.argv.slice(2);
if (!bundle || !corpusPath || !out) throw Error('usage: node execute.mjs BUNDLE CORPUS OUT');
const corpus = JSON.parse(fs.readFileSync(corpusPath, 'utf8'));
const memory = new WebAssembly.Memory({ initial: 1, maximum: 1 });
const x = new WebAssembly.Instance(new WebAssembly.Module(fs.readFileSync(path.join(bundle, 'checked.wasm'))), { env: { memory } }).exports;
const f64 = new Float64Array(memory.buffer), f32 = new Float32Array(memory.buffer), u32 = new Uint32Array(memory.buffer), i32 = new Int32Array(memory.buffer);
const hex64 = () => u32[1].toString(16).padStart(8, '0') + u32[0].toString(16).padStart(8, '0');
const hex32 = () => u32[4].toString(16).padStart(8, '0');
const fromHex64 = h => { u32[6] = parseInt(h.slice(8), 16); u32[7] = parseInt(h.slice(0, 8), 16); return f64[3]; };
const fromHex32 = h => { u32[8] = parseInt(h, 16); return f32[8]; };
const results = [];
for (const c of corpus.cases) {
  const single = c.op.endsWith('32');
  const a = single ? fromHex32(c.a) : fromHex64(c.a), b = c.b === undefined ? undefined : (single ? fromHex32(c.b) : fromHex64(c.b));
  u32[0] = 0; u32[1] = 0; u32[2] = 0; u32[4] = 0;
  let status, error = null;
  try { status = b === undefined ? x[c.op](a) : x[c.op](a, b); } catch (e) { error = e.constructor.name; }
  const rec = { id: c.id, status: error ? null : status, error };
  if (c.op === 'trunc') { rec.result = hex64(); rec.integer = i32[2]; }
  else rec.result = single ? hex32() : hex64();
  if (rec.result !== undefined) {
    const v = c.op === 'trunc' || !single ? f64[0] : f32[4];
    rec.nan = v !== v;
  }
  results.push(rec);
}
fs.mkdirSync(out, { recursive: true });
fs.writeFileSync(path.join(out, 'observed.json'), JSON.stringify({ version: 1, node: process.version, v8: process.versions.v8, results }, null, 2) + '\n');
console.log('observed ' + results.length);
