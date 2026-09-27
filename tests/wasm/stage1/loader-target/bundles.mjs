import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
import {materialize} from './materialize.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
import {decodeTargetBundle} from '../../../../runtime/wasm32/target-bundle.mjs';
import {reuseCode} from './reuse.mjs';
const args = process.argv.slice(2), compact = args.includes('--compact');
const [out, reuse] = args.filter(a => !['--compact','--v1'].includes(a));
if(!args.includes('--v1')){await import('./archive-build.mjs');}else{
const read = n => JSON.parse(fs.readFileSync(out + '/' + n));
const {inventory} = await import(pathToFileURL(out + '/d2.mjs'));
const manifest = read('bundles.json'), versions = read('versions.json'), policy = read('policy.json');
const completed = [];
let reused = 0, fresh = 0;
const reusedFiles = [];
const old = reuse ? JSON.parse(fs.readFileSync(reuse + '/bundle-manifest.json')).files : [];
if (reuse) for (const [name, value] of [['policy.json', policy], ['versions.json', versions]])
  if (JSON.stringify(JSON.parse(fs.readFileSync(reuse + '/' + name))) !== JSON.stringify(value))
    throw Error('Reuse configuration changed: ' + name);
for (const file of manifest.files) {
  const previous = old.find(row => row.path === file.path), cache = new Map();
  // Compact outputs remain reusable as complete files when both compiler
  // products match exactly. Their module names (and listing names) stay fixed.
  if (previous && previous.stem === file.stem &&
      sha256(fs.readFileSync(out + '/' + file.stem + '.records.json')) ===
        sha256(fs.readFileSync(reuse + '/' + previous.stem + '.records.json')) &&
      sha256(fs.readFileSync(out + '/' + file.stem + '.w32fsl')) ===
        sha256(fs.readFileSync(reuse + '/' + previous.stem + '.w32fsl'))) {
    const bytes = fs.readFileSync(reuse + '/' + previous.bundle);
    const prior = decodeTargetBundle(bytes, previous.sha256);
    if (!Buffer.from(prior.fasl).equals(fs.readFileSync(out + '/' + file.stem + '.w32fsl')))
      throw Error('Reuse FASL changed: ' + file.path);
    file.bundle = file.stem + '.w32bundle'; file.sha256 = previous.sha256;
    fs.writeFileSync(out + '/' + file.bundle, bytes);
    reused += prior.manifest.codeSet.modules.length;
    reusedFiles.push({path: file.path, sha256: file.sha256,
      records: sha256(fs.readFileSync(out + '/' + file.stem + '.records.json'))});
    completed.push(file);
    fs.writeFileSync(out + '/bundle-manifest.json', JSON.stringify({...manifest, files: completed}, null, 2) + '\n');
    continue;
  }
  if (previous) {
    const prior = decodeTargetBundle(fs.readFileSync(reuse + '/' + previous.bundle), previous.sha256);
    for (const row of prior.manifest.codeSet.modules) {
      const stem = reuse + '/' + previous.stem + '/' + row.name;
      if (fs.existsSync(stem + '.wat')) cache.set(sha256(fs.readFileSync(stem + '.wat')), {stem, row});
    }
  }
  const materializeCode = (wat, stem, policy, versions) => {
    const prior = cache.get(sha256(wat));
    if (!prior) { fresh++; return inventory(wat, stem, policy, versions); }
    const result = reuseCode(prior.row, prior.stem, stem, wat);
    reused++;
    return result;
  };
  const bytes = materialize({records: read(file.stem + '.records.json'),
    fasl: fs.readFileSync(out + '/' + file.stem + '.w32fsl'), out: out + '/' + file.stem,
    versions, policy, inventory: materializeCode});
  file.bundle = file.stem + '.w32bundle'; file.sha256 = sha256(bytes);
  fs.writeFileSync(out + '/' + file.bundle, bytes);
  completed.push(file);
  fs.writeFileSync(out + '/bundle-manifest.json', JSON.stringify({...manifest, files: completed}, null, 2) + '\n');
  // The bundle owns both engine binaries and their checked D2 identities;
  // records.json owns the WAT. Listings can be regenerated from those bytes.
  // Bound RAM use to one file's disposable materialization at a time.
  if (compact) fs.rmSync(out + '/' + file.stem, {recursive: true});
}
fs.writeFileSync(out + '/bundle-manifest.json', JSON.stringify(manifest, null, 2) + '\n');
fs.writeFileSync(out + '/materialization-reuse.json', JSON.stringify({reuse: reuse ?? null, reused, fresh, compact, reusedFiles}, null, 2) + '\n');
console.log(JSON.stringify(manifest));

}
