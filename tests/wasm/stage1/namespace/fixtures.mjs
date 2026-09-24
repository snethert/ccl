import {createHash} from 'node:crypto';
export const files = {
  '/ccl/a.bin': [0, 1, 127, 128, 255, 10, 65, 0],
  '/ccl/ab.bin': [42],
  '/ccl/empty': [],
  '/ccl/sub/text.lisp': [...Buffer.from('(in-package :cl-user)\n(+ 1 2)\n')],
  '/ccl/λ.lisp': [...Buffer.from('lambda')],
  '/other/a.bin': [99, 98]
};
export function manifest() {
  return {version: 1, cwd: '/ccl', cclRoot: '/ccl', entries: [
    ...['/', '/ccl', '/ccl/sub', '/other'].map(path => ({path, kind: 'directory'})),
    ...Object.entries(files).map(([path, values]) => {
      const bytes = new Uint8Array(values);
      return {path, kind: 'file', bytes, sha256: createHash('sha256').update(bytes).digest('hex')};
    })
  ]};
}
// Handles are mapped by name by both drivers; no native descriptor value is
// assumed. These requests are also the native oracle inputs, in this order.
export const trace = [
  ['stat', '/ccl/a.bin'], ['stat', '/ccl'], ['stat', '/ccl/empty'],
  ['realpath', 'sub/../a.bin'], ['realpath', './a.bin'],
  ['realpath', '//ccl//sub/./text.lisp'],
  ['realpath', '/ccl/sub/..'], ['realpath', '../other/a.bin'],
  ['stat', '/ccl/λ.lisp'], ['stat', 'ab.bin'],
  ['open', 'a', 'a.bin'], ['open', 'b', '/ccl/a.bin'],
  ['fstat', 'a'], ['pread', 'a', 2, 4], ['seek', 'a', 0, 'cur'],
  ['read', 'a', 3], ['read', 'b', 2], ['seek', 'a', -1, 'cur'],
  ['read', 'a', 3], ['pread', 'a', 7, 100], ['seek', 'a', 0, 'cur'],
  ['pread', 'a', 8, 4], ['pread', 'a', 100, 4], ['pread', 'a', 0, 0],
  ['seek', 'a', -2, 'end'], ['read', 'a', 50], ['read', 'a', 1],
  ['seek', 'a', 99, 'set'], ['read', 'a', 1], ['seek', 'a', 0, 'cur'],
  ['seek', 'a', 0, 'set'], ['read', 'a', 8], ['close', 'a'],
  ['read', 'b', 2], ['close', 'b'],
  ['open', 'e', 'empty'], ['read', 'e', 16], ['close', 'e'],
  ['open', 'u', 'λ.lisp'], ['read', 'u', 64], ['close', 'u'],
  ['open', 's', 'sub/text.lisp'], ['pread', 's', 10, 20], ['close', 's'],
  ['stat', 'missing'], ['realpath', 'missing'], ['open', 'x', 'missing'],
  ['realpath', 'a.bin/../ab.bin'], ['realpath', 'a.bin/'],
  ['opendir', 'd', '/ccl'], ['readdir', 'd'], ['readdir', 'd'],
  ['readdir', 'd'], ['readdir', 'd'], ['readdir', 'd'], ['readdir', 'd'],
  ['readdir', 'd'], ['readdir', 'd'], ['closedir', 'd']
];
export function replay(api, requests = trace) {
  const descriptors = new Map();
  return requests.map(([op, ...args], index) => {
    try {
      let result;
      if (op === 'open' || op === 'opendir') {
        const [name, path] = args;
        descriptors.set(name, api[op](path)); result = true;
      } else if (['stat', 'realpath'].includes(op)) result = api[op](...args);
      else result = api[op](descriptors.get(args[0]), ...args.slice(1));
      if (result instanceof Uint8Array) result = Array.from(result);
      if (op === 'stat' || op === 'fstat') result = [result.path, result.kind, result.size];
      return [index, result];
    } catch (error) {
      if (error.name !== 'NamespaceError') throw error;
      return [index, 'error'];
    }
  });
}
