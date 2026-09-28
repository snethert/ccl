import fs from 'node:fs';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
import {relist, reuseCode} from './reuse.mjs';
import {decodeTargetBundle} from '../../../../runtime/wasm32/target-bundle.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
import {readRecords} from './record-reader.mjs';

const out = process.argv[2];
const bytes = fs.readFileSync(out + '/modules.w32bundle');
const decoded = decodeTargetBundle(bytes, sha256(bytes));
const row = decoded.manifest.codeSet.modules[0], source = out + '/modules/' + row.name;
const wat = readRecords(out + '/records.json').units[0].record[4];
const directory = out + '/reuse-check';
fs.mkdirSync(directory, {recursive: true});
const stem = directory + '/renumbered';
for (const suffix of ['.wasm', '.template.wasm'])
  fs.copyFileSync(source + suffix, stem + suffix);
const reused = relist(row, stem);
assert.notEqual(reused.d2.classification.sections_sha256, row.d2.classification.sections_sha256);
const {inventory} = await import(pathToFileURL(out + '/d2.mjs'));
const read = name => JSON.parse(fs.readFileSync(out + '/' + name));
const fresh = inventory(wat, stem, read('policy.json'), read('versions.json'));
for (const name of ['generation', 'abi', 'layout', 'profile', 'd2', 'entries'])
  assert.deepEqual(reused[name], fresh[name], name);
const refusals = [], suffixes = ['.wasm', '.template.wasm'];
const cache = directory + '/cache', refused = directory + '/refused';
for (const suffix of suffixes) {
  for (const name of suffixes) {
    fs.copyFileSync(source + name, cache + name);
    fs.rmSync(refused + name, {force: true});
  }
  const altered = fs.readFileSync(cache + suffix); altered[0] ^= 1;
  fs.writeFileSync(cache + suffix, altered);
  assert.throws(() => reuseCode(row, cache, refused, wat), /Reuse artifact changed/);
  assert(suffixes.every(name => !fs.existsSync(refused + name)), 'refusal publishes no artifacts');
  refusals.push(suffix);
}
// WAT is supplied by the pinned producer; listings are regenerated from the
// authenticated template. Neither is a retained cache file any longer.
assert.throws(() => reuseCode(row, source, refused, wat + '\n'), /Reuse source changed/);
refusals.push('source-digest');
const result = {status: 'PASS', refusals, renamedModule: row.name, binary: sha256(bytes),
  reusedClassification: reused.d2.classification};
fs.writeFileSync(out + '/reuse-check.json', JSON.stringify(result, null, 2) + '\n');
console.log('PASS: renamed reuse matches fresh classification; source and both binary identities refuse tampering');
