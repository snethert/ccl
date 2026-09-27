import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
import {materialize} from './materialize.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
import {decodeTargetBundle} from '../../../../runtime/wasm32/target-bundle.mjs';
const [out, reuse] = process.argv.slice(2), read = n => JSON.parse(fs.readFileSync(out + '/' + n));
const {inventory} = await import(pathToFileURL(out + '/d2.mjs'));
const manifest = read('bundles.json'), versions = read('versions.json'), policy = read('policy.json');
const completed = [];
let reused = 0, fresh = 0;
const old = reuse ? JSON.parse(fs.readFileSync(reuse + '/bundle-manifest.json')).files : [];
if (reuse) for (const [name, value] of [['policy.json', policy], ['versions.json', versions]])
  if (JSON.stringify(JSON.parse(fs.readFileSync(reuse + '/' + name))) !== JSON.stringify(value))
    throw Error('Reuse configuration changed: ' + name);
for (const file of manifest.files) {
  const previous = old.find(row => row.path === file.path), cache = new Map();
  if (previous) {
    const prior = decodeTargetBundle(fs.readFileSync(reuse + '/' + previous.bundle), previous.sha256);
    for (const row of prior.manifest.codeSet.modules) {
      const stem = reuse + '/' + previous.stem + '/' + row.name;
      cache.set(sha256(fs.readFileSync(stem + '.wat')), {stem, row});
    }
  }
  const materializeCode = (wat, stem, policy, versions) => {
    const prior = cache.get(sha256(wat));
    if (!prior) { fresh++; return inventory(wat, stem, policy, versions); }
    const {row} = prior;
    const buffers = Object.entries({'.wat': sha256(wat), '.wasm': row.d2.outputs.full.binary_sha256,
      '.template.wasm': row.d2.classification.binary_sha256,
      '.sections.txt': row.d2.classification.sections_sha256,
      '.instructions.txt': row.d2.classification.instructions_sha256}).map(([suffix, digest]) => {
        const bytes = fs.readFileSync(prior.stem + suffix);
        if (sha256(bytes) !== digest) throw Error('Reuse artifact changed: ' + prior.stem + suffix);
        return [suffix, bytes];
      });
    for (const [suffix, bytes] of buffers) fs.writeFileSync(stem + suffix, bytes);
    reused++;
    return Object.fromEntries(['generation', 'abi', 'layout', 'profile', 'd2', 'entries'].map(k => [k, row[k]]));
  };
  const bytes = materialize({records: read(file.stem + '.records.json'),
    fasl: fs.readFileSync(out + '/' + file.stem + '.w32fsl'), out: out + '/' + file.stem,
    versions, policy, inventory: materializeCode});
  file.bundle = file.stem + '.w32bundle'; file.sha256 = sha256(bytes);
  fs.writeFileSync(out + '/' + file.bundle, bytes);
  completed.push(file);
  fs.writeFileSync(out + '/bundle-manifest.json', JSON.stringify({...manifest, files: completed}, null, 2) + '\n');
}
fs.writeFileSync(out + '/bundle-manifest.json', JSON.stringify(manifest, null, 2) + '\n');
fs.writeFileSync(out + '/materialization-reuse.json', JSON.stringify({reuse: reuse ?? null, reused, fresh}, null, 2) + '\n');
console.log(JSON.stringify(manifest));
