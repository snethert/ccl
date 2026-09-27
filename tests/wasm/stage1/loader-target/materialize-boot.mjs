// Reuse only exactly matching generated code and verified D2 artifacts.
// Changed modules still go through WABT and the ordinary materializer.
import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
import {reuseCode} from './reuse.mjs';
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
  const result = reuseCode(prior.row, prior.stem, stem, wat);
  reused++;
  return result;
});
fs.writeFileSync(out + '/materialization-reuse.json', JSON.stringify({reuse: reuse ?? null, reused, fresh}, null, 2) + '\n');
console.log(JSON.stringify({...result, reused, fresh}));
