// Reuse only exactly matching generated code and verified D2 artifacts.
// Changed modules still go through WABT and the ordinary materializer.
import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
const [out, reuse] = process.argv.slice(2), read = path => JSON.parse(fs.readFileSync(path));
const {write} = await import(pathToFileURL(out + '/write.mjs'));
const {inventory} = await import(pathToFileURL(out + '/d2.mjs'));
const policy = read(out + '/policy.json'), versions = read(out + '/versions.json'), cache = new Map();
let reused = 0, fresh = 0;
if (reuse) {
  if (JSON.stringify(read(reuse + '/policy.json')) !== JSON.stringify(policy) ||
      JSON.stringify(read(reuse + '/versions.json')) !== JSON.stringify(versions)) throw Error('Reuse configuration changed');
  for (const row of read(reuse + '/boot/artifacts/code-set.json').modules) {
    const stem = reuse + '/boot/artifacts/' + row.name;
    cache.set(sha256(fs.readFileSync(stem + '.wat')), {stem, row});
  }
}
const result = write(out + '/boot', out + '/boot/artifacts', policy, versions, (wat, stem, policy, versions) => {
  const prior = cache.get(sha256(wat));
  if (!prior) { fresh++; return inventory(wat, stem, policy, versions); }
  const {row} = prior, expected = {
    '.wat': sha256(wat), '.wasm': row.d2.outputs.full.binary_sha256,
    '.template.wasm': row.d2.classification.binary_sha256,
    '.sections.txt': row.d2.classification.sections_sha256,
    '.instructions.txt': row.d2.classification.instructions_sha256};
  const buffers = Object.entries(expected).map(([suffix, digest]) => {
    const bytes = fs.readFileSync(prior.stem + suffix);
    if (sha256(bytes) !== digest) throw Error('Reuse artifact changed: ' + prior.stem + suffix);
    return [suffix, bytes];
  });
  for (const [suffix, bytes] of buffers) fs.writeFileSync(stem + suffix, bytes);
  reused++;
  return Object.fromEntries(['generation', 'abi', 'layout', 'profile', 'd2', 'entries'].map(k => [k, row[k]]));
});
fs.writeFileSync(out + '/materialization-reuse.json', JSON.stringify({reuse: reuse ?? null, reused, fresh}, null, 2) + '\n');
console.log(JSON.stringify({...result, reused, fresh}));
