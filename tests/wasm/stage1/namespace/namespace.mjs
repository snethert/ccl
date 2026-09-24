// Read-only byte namespace. The owner supplies every byte before admission.
// No filesystem imports, host-path fallback, symlinks or mutable file contents.
import {sha256} from './sha256.mjs';

export class NamespaceError extends Error {
  constructor(code) { super(code); this.name = 'NamespaceError'; this.code = code; }
}
const need = (test, code) => { if (!test) throw new NamespaceError(code); };
const integer = value => Number.isSafeInteger(value) && value >= 0;
const encoder = new TextEncoder();
const MAX_PATH = 4096;
const MAX_HANDLE = 0x1fffffff;

function record(value, required, optional = []) {
  need(value !== null && typeof value === 'object' &&
       [Object.prototype, null].includes(Object.getPrototypeOf(value)), 'RECORD');
  const fields = Object.getOwnPropertyDescriptors(value);
  need(Reflect.ownKeys(fields).every(key => typeof key === 'string' &&
       required.concat(optional).includes(key) && 'value' in fields[key]), 'FIELDS');
  need(required.every(key => Object.hasOwn(fields, key)), 'FIELDS');
  return Object.fromEntries(Object.entries(fields).map(([key, descriptor]) => [key, descriptor.value]));
}
function pathText(value) {
  need(typeof value === 'string' && value.length > 0 && value.length <= MAX_PATH &&
       !value.includes('\0') && !value.includes('\\'), 'PATH');
  // UTF-8 replacement would make two different names indistinguishable.
  for (const char of value) {
    const code = char.codePointAt(0);
    need(code < 0xd800 || code > 0xdfff, 'PATH');
  }
  need(encoder.encode(value).length <= MAX_PATH, 'PATH');
  return value;
}
function canonical(value) {
  pathText(value);
  need(value.startsWith('/') && (value === '/' ||
       value.slice(1).split('/').every(part => part && part !== '.' && part !== '..')), 'CANONICAL_PATH');
  return value;
}
const parent = path => path.slice(0, path.lastIndexOf('/')) || '/';
const name = path => path.slice(path.lastIndexOf('/') + 1);

export function createNamespace(configuration) {
  const config = record(configuration, ['version', 'entries', 'cwd', 'cclRoot'], ['limits']);
  need(config.version === 1, 'VERSION');
  const limits = {entries: 65536, bytes: 64 * 1024 * 1024, handles: 256, ids: MAX_HANDLE, read: 1024 * 1024};
  if (config.limits !== undefined) {
    const supplied = record(config.limits, [], Object.keys(limits));
    for (const [key, value] of Object.entries(supplied)) {
      need(integer(value) && value > 0 && value <= limits[key], 'LIMIT');
      limits[key] = value;
    }
  }
  need(Array.isArray(config.entries) && config.entries.length <= limits.entries, 'ENTRIES');
  const tree = new Map();
  let total = 0;
  for (const entry of config.entries) {
    const item = record(entry, ['path', 'kind'], ['bytes', 'sha256']);
    const path = canonical(item.path);
    need(!tree.has(path), 'DUPLICATE');
    need(item.kind === 'file' || item.kind === 'directory', 'KIND');
    let bytes, digest;
    if (item.kind === 'file') {
      need(item.bytes instanceof Uint8Array && item.bytes.buffer instanceof ArrayBuffer, 'BYTES');
      need(typeof item.sha256 === 'string' && /^[0-9a-f]{64}$/.test(item.sha256), 'DIGEST');
      need(item.bytes.byteLength <= limits.bytes - total, 'BYTE_LIMIT');
      bytes = new Uint8Array(item.bytes); // private immutable snapshot
      digest = sha256(bytes);
      need(digest === item.sha256, 'DIGEST');
      total += bytes.length;
    } else {
      need(!Object.hasOwn(item, 'bytes') && !Object.hasOwn(item, 'sha256'), 'DIRECTORY_DATA');
    }
    tree.set(path, {path, kind: item.kind, bytes, digest, children: []});
  }
  need(tree.get('/')?.kind === 'directory', 'ROOT');
  for (const item of tree.values()) {
    if (item.path === '/') continue;
    const directory = tree.get(parent(item.path));
    need(directory?.kind === 'directory', 'PARENT');
    directory.children.push(name(item.path));
  }
  for (const item of tree.values()) item.children.sort();
  const cwd = canonical(config.cwd), cclRoot = canonical(config.cclRoot);
  need(tree.get(cwd)?.kind === 'directory' && tree.get(cclRoot)?.kind === 'directory', 'BASE_DIRECTORY');
  const inventory = [...tree.values()].sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0)
    .map(item => item.kind === 'file' ? [item.path, item.kind, item.bytes.length, item.digest] : [item.path, item.kind]);
  const identity = sha256(JSON.stringify({version: 1, cwd, cclRoot, limits, inventory}));

  function resolve(input) {
    pathText(input);
    let path = input.startsWith('/') ? '/' : cwd;
    const parts = input.split('/');
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      // Check the traversed prefix even before '.' or '..'. '/file/../x'
      // cannot become a valid path by lexical cancellation of a non-directory.
      need(tree.get(path)?.kind === 'directory', 'NOT_DIRECTORY');
      if (!part || part === '.') continue;
      if (part === '..') path = parent(path);
      else {
        path = path === '/' ? '/' + part : path + '/' + part;
        need(tree.has(path), 'NOT_FOUND');
      }
      if (i === parts.length - 1) return tree.get(path);
    }
    return tree.get(path);
  }
  const stat = item => Object.freeze({path: item.path, kind: item.kind,
                                     size: item.kind === 'file' ? item.bytes.length : 0});

  function session() {
    const handles = new Map();
    let next = 1;
    function handle(fd, kind) {
      need(Number.isInteger(fd) && handles.has(fd), 'BAD_HANDLE');
      const value = handles.get(fd);
      if (kind) need(value.item.kind === kind, 'HANDLE_KIND');
      return value;
    }
    function open(path, kind) {
      const item = resolve(path);
      need(item.kind === kind, kind === 'file' ? 'IS_DIRECTORY' : 'NOT_DIRECTORY');
      need(handles.size < limits.handles && next <= limits.ids, 'HANDLE_LIMIT');
      const fd = next++;
      handles.set(fd, {item, position: 0});
      return fd;
    }
    function readAt(value, offset, count) {
      need(integer(offset) && integer(count) && count <= limits.read &&
           offset <= Number.MAX_SAFE_INTEGER - count, 'RANGE');
      const bytes = value.item.bytes;
      return bytes.slice(Math.min(offset, bytes.length), Math.min(offset + count, bytes.length));
    }
    const api = {
      realpath: path => resolve(path).path,
      stat: path => stat(resolve(path)),
      open(path, mode = 'read') { need(mode === 'read', 'READ_ONLY'); return open(path, 'file'); },
      fstat: fd => stat(handle(fd, 'file').item),
      pread: (fd, offset, count) => readAt(handle(fd, 'file'), offset, count),
      read(fd, count) {
        const value = handle(fd, 'file');
        const bytes = readAt(value, value.position, count);
        value.position += bytes.length;
        return bytes;
      },
      seek(fd, offset, origin = 'set') {
        const value = handle(fd, 'file');
        need(Number.isSafeInteger(offset), 'RANGE');
        need(['set', 'cur', 'end'].includes(origin), 'ORIGIN');
        const position = offset + (origin === 'set' ? 0 : origin === 'cur' ? value.position : value.item.bytes.length);
        need(integer(position), 'RANGE');
        value.position = position;
        return position;
      },
      close(fd) { handle(fd, 'file'); handles.delete(fd); return true; },
      opendir: path => open(path, 'directory'),
      readdir(fd) {
        const value = handle(fd, 'directory');
        if (value.position === value.item.children.length) return null;
        return value.item.children[value.position++];
      },
      closedir(fd) { handle(fd, 'directory'); handles.delete(fd); return true; }
    };
    return Object.freeze(api);
  }
  return Object.freeze({identity, cwd, cclRoot, session});
}
