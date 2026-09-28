// Binary identity permits reuse; disassembly also depends on the output name.
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';

export function reuseCode(row, source, stem, wat) {
  if (row.wat_sha256 && row.wat_sha256 !== sha256(wat)) throw Error('Reuse source changed');
  const expected = {'.wasm': row.d2.outputs.full.binary_sha256,
    '.template.wasm': row.d2.classification.binary_sha256};
  const buffers = Object.entries(expected).map(([suffix, digest]) => {
    const bytes = fs.readFileSync(source + suffix);
    if (sha256(bytes) !== digest) throw Error('Reuse artifact changed: ' + source + suffix);
    return [suffix, bytes];
  });
  for (const [suffix, bytes] of buffers) fs.writeFileSync(stem + suffix, bytes);
  const current = relist(row, stem);
  return {wat_sha256: sha256(wat), ...Object.fromEntries(['generation', 'abi', 'layout', 'profile', 'd2', 'entries'].map(k => [k, current[k]]))};
}

export function relist(row, stem) {
  const result = structuredClone(row);
  for (const [flag, suffix, field] of [
    ['-x', '.sections.txt', 'sections_sha256'],
    ['-d', '.instructions.txt', 'instructions_sha256']]) {
    const bytes = execFileSync('/usr/local/bin/wasm-objdump', [flag, stem + '.template.wasm'],
      {maxBuffer: 64 * 1024 * 1024});
    result.d2.classification[field] = sha256(bytes);
  }
  return result;
}
