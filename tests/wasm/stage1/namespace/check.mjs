import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
import fs from 'node:fs';
import path from 'node:path';
import {manifest, replay} from './fixtures.mjs';
const out = process.argv[2];
const {createNamespace, NamespaceError} = await import(pathToFileURL(path.join(out, 'runtime/namespace.mjs')));
const checks = [];
function refuses(label, code, action) {
  assert.throws(action, error => error instanceof NamespaceError && error.code === code, label);
  checks.push(label);
}
function admission(label, code, mutate) {
  const input = manifest(); mutate(input); refuses(label, code, () => createNamespace(input));
}
admission('version', 'VERSION', m => m.version = 2);
admission('unknown-field', 'FIELDS', m => m.ignored = true);
admission('missing-field', 'FIELDS', m => delete m.cwd);
admission('getter-not-invoked', 'FIELDS', m => Object.defineProperty(m, 'cwd', {get() { throw Error('getter ran'); }}));
admission('non-record', 'RECORD', m => Object.setPrototypeOf(m, []));
admission('entry-limit', 'ENTRIES', m => m.limits = {entries: 1});
admission('entry-array', 'ENTRIES', m => m.entries = {});
admission('limit-positive', 'LIMIT', m => m.limits = {read: 0});
admission('limit-bound', 'LIMIT', m => m.limits = {read: 1048577});
admission('limit-integer', 'LIMIT', m => m.limits = {read: 1.5});
admission('limit-field', 'FIELDS', m => m.limits = {threads: 1});
admission('duplicate', 'DUPLICATE', m => m.entries.push(m.entries[0]));
admission('symlink', 'KIND', m => m.entries[4].kind = 'symlink');
admission('not-bytes', 'BYTES', m => m.entries[4].bytes = [1]);
admission('shared-bytes', 'BYTES', m => m.entries[4].bytes = new Uint8Array(new SharedArrayBuffer(8)));
admission('hash-only', 'BYTES', m => delete m.entries[4].bytes);
admission('malformed-digest', 'DIGEST', m => m.entries[4].sha256 = 'X');
admission('wrong-digest', 'DIGEST', m => m.entries[4].bytes[0] = 25);
admission('total-bytes', 'BYTE_LIMIT', m => m.limits = {bytes: 8});
admission('directory-bytes', 'DIRECTORY_DATA', m => m.entries[0].bytes = new Uint8Array());
admission('directory-digest', 'DIRECTORY_DATA', m => m.entries[0].sha256 = '0'.repeat(64));
admission('no-root', 'ROOT', m => m.entries.shift());
admission('absent-parent', 'PARENT', m => m.entries[4].path = '/absent/file');
admission('file-parent', 'PARENT', m => m.entries[5].path = '/ccl/a.bin/file');
admission('cwd-not-directory', 'BASE_DIRECTORY', m => m.cwd = '/ccl/a.bin');
admission('ccl-root-not-directory', 'BASE_DIRECTORY', m => m.cclRoot = '/absent');
for (const invalid of ['relative', '/ccl/../bad', '/ccl//bad', '/ccl/'])
  admission('noncanonical-' + invalid, 'CANONICAL_PATH', m => m.entries[4].path = invalid);
for (const invalid of [null, '', '/bad\0x', '/bad\\x', '/\ud800', '/\udfff', '/' + 'x'.repeat(4096), '/' + 'λ'.repeat(2048)])
  admission('path-' + JSON.stringify(invalid), 'PATH', m => m.entries[4].path = invalid);
const input = manifest();
const ns = createNamespace(input), api = ns.session();
const rows = replay(api);
const native = JSON.parse(fs.readFileSync(path.join(out, 'native.json')));
// CCL's Darwin path service cancels these non-directory components. The
// namespace walks existing directory components, so these are explicit
// refused-input differences, not native-compatible result credit.
const differences = [
  {index: 47, native: '/ccl/ab.bin', target: 'error'},
  {index: 48, native: '/ccl/a.bin', target: 'error'}
];
for (const row of differences) {
  assert.equal(native[row.index][1], row.native);
  assert.equal(rows[row.index][1], row.target);
}
assert.deepEqual(rows.filter(row => !differences.some(d => d.index === row[0])),
                 native.filter(row => !differences.some(d => d.index === row[0])));
input.entries[4].bytes.fill(77); input.entries[4].path = '/elsewhere'; input.cwd = '/other';
assert.deepEqual(Array.from(api.pread(api.open('/ccl/a.bin'), 0, 2)), [0, 1]);
assert.equal(api.realpath('/../../ccl/a.bin'), '/ccl/a.bin');
checks.push('virtual-root-parent-clamps');
const originalIdentity = ns.identity;
const reordered = manifest(); reordered.entries.reverse();
assert.equal(createNamespace(reordered).identity, originalIdentity);
const changedBase = manifest(); changedBase.cwd = '/other';
assert.notEqual(createNamespace(changedBase).identity, originalIdentity);
checks.push('caller-mutation', 'order-independent-identity', 'cwd-bound-identity');
const limited = createNamespace({...manifest(), limits: {ids: 2}}).session();
const one = limited.open('a.bin'); limited.close(one);
const two = limited.open('ab.bin'); limited.close(two);
refuses('lifetime-handle-exhaustion', 'HANDLE_LIMIT', () => limited.open('empty'));
refuses('exhaustion-keeps-stale-handles-dead', 'BAD_HANDLE', () => limited.read(one, 1));
const s = createNamespace({...manifest(), limits: {handles: 2, read: 8}}).session();
const a = s.open('a.bin'), b = s.open('ab.bin');
refuses('open-limit', 'HANDLE_LIMIT', () => s.open('empty'));
s.close(b); const e = s.open('empty'); assert.equal(e, 3, 'refused open consumed handle');
refuses('stale-handle', 'BAD_HANDLE', () => s.read(b, 1));
refuses('unknown-handle', 'BAD_HANDLE', () => s.read(999, 1));
refuses('noninteger-handle', 'BAD_HANDLE', () => s.read(1.5, 1));
refuses('write-open', 'READ_ONLY', () => s.open('empty', 'write'));
refuses('open-directory', 'IS_DIRECTORY', () => s.open('/ccl'));
refuses('open-file-as-directory', 'NOT_DIRECTORY', () => s.opendir('a.bin'));
refuses('missing-name', 'NOT_FOUND', () => s.stat('absent'));
refuses('file-traversal', 'NOT_DIRECTORY', () => s.realpath('a.bin/../ab.bin'));
refuses('file-trailing-slash', 'NOT_DIRECTORY', () => s.stat('a.bin/'));
for (const [offset, count] of [[-1, 1], [0, -1], [0.5, 1], [0, 1.5], [NaN, 1], [0, Infinity], [0, 9], [Number.MAX_SAFE_INTEGER, 1]])
  refuses('range-' + offset + '-' + count, 'RANGE', () => s.pread(a, offset, count));
assert.equal(s.seek(a, 2), 2);
refuses('seek-before-start', 'RANGE', () => s.seek(a, -3, 'cur'));
refuses('seek-overflow', 'RANGE', () => s.seek(a, Number.MAX_SAFE_INTEGER, 'cur'));
refuses('seek-fractional', 'RANGE', () => s.seek(a, 0.5));
refuses('seek-origin', 'ORIGIN', () => s.seek(a, 0, 'middle'));
refuses('read-invalid-count', 'RANGE', () => s.read(a, 9));
assert.equal(s.seek(a, 0, 'cur'), 2, 'refusal changed file position');
const copy = s.pread(a, 0, 8); copy.fill(88);
assert.equal(s.pread(a, 0, 1)[0], 0, 'returned view leaked immutable contents');
assert.deepEqual([...s.pread(a, Number.MAX_SAFE_INTEGER, 0)], []);
s.close(e); const d = s.opendir('/ccl');
for (const op of ['fstat', 'pread', 'read', 'seek', 'close'])
  refuses('directory-handle-' + op, 'HANDLE_KIND', () => s[op](d, 0, 0));
for (const op of ['readdir', 'closedir'])
  refuses('file-handle-' + op, 'HANDLE_KIND', () => s[op](a));
assert.equal(s.readdir(d), 'a.bin', 'wrong-kind call advanced directory cursor');
s.closedir(d); refuses('stale-directory', 'BAD_HANDLE', () => s.readdir(d));
s.close(a); refuses('double-close', 'BAD_HANDLE', () => s.close(a));
const other = ns.session(); refuses('session-isolation', 'BAD_HANDLE', () => other.read(1, 1));
assert.equal(other.open('ab.bin'), 1); assert.deepEqual([...other.read(1, 1)], [42]);
checks.push('refusal-preserves-cursors', 'read-copy', 'session-isolation-positive');
fs.writeFileSync(path.join(out, 'namespace.json'), JSON.stringify({status: 'PASS', identity: ns.identity, native_comparisons: rows.length - differences.length, rows, differences, checks}, null, 2) + '\n');
console.log(JSON.stringify({status: 'PASS', native_comparisons: rows.length - differences.length, controls: checks.length}));
