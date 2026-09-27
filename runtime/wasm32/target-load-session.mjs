// A namespace file and its code inventory share one admitted bundle identity.
// The byte stream exposes the ordinary FASL payload; code is installed only
// when that stream's opcode 72 requests its exact compiler record.
import {createNamespace} from './namespace.mjs';
import {admitTargetBundle, decodeTargetBundle} from './target-bundle.mjs';
import {targetCodeService} from './target-code-service.mjs';
import {fileClient} from './file-client.mjs';
import {sha256} from './sha256.mjs';

const need = (ok, why) => { if (!ok) throw Error('target load: ' + why); };
export function bundleNamespace({files, cwd = '/ccl', cclRoot = '/ccl', measure = (_phase, run) => run()}) {
  const entries = new Map([['/', {path: '/', kind: 'directory'}]]), bundles = new Map();
  for (const file of files) {
    need(!entries.has(file.path), 'DUPLICATE_FILE');
    const decoded = measure('namespace.decode', () => decodeTargetBundle(file.bytes, file.sha256), {path: file.path});
    let parent = file.path.slice(0, file.path.lastIndexOf('/')) || '/';
    while (parent !== '/') {
      need(!entries.has(parent) || entries.get(parent).kind === 'directory', 'PARENT');
      entries.set(parent, {path: parent, kind: 'directory'});
      parent = parent.slice(0, parent.lastIndexOf('/')) || '/';
    }
    entries.set(file.path, {path: file.path, kind: 'file', bytes: decoded.fasl, sha256: sha256(decoded.fasl)});
    bundles.set(file.path, {bytes: new Uint8Array(file.bytes), digest: file.sha256,
      modules: decoded.manifest.codeSet.modules});
  }
  for (const path of [cwd, cclRoot]) if (!entries.has(path)) entries.set(path, {path, kind: 'directory'});
  const namespace = createNamespace({version: 1, entries: [...entries.values()], cwd, cclRoot});
  const path = value => /^ccl:/i.test(value) ? cclRoot + '/' + value.slice(4).replaceAll(';', '/') : value;
  const session = () => {
    const inner = namespace.session();
    return Object.freeze({...inner,
      open: (name, mode) => inner.open(path(name), mode),
      stat: name => inner.stat(path(name)), realpath: name => inner.realpath(path(name))});
  };
  return Object.freeze({namespace, bundles, session});
}

export function targetLoadSession({files, memory, env, owner, versions, policy, capabilities,
  nextCode, nextSlot, post, pinned, onOpen = () => {}, onClose = () => {}, onInstall = () => {},
  measure = (_phase, run) => run(), onAdmission = () => {}}) {
  const source = measure('namespace.create', () => bundleNamespace({files, measure})), paths = source.session(), open = new Map();
  const get = p => new DataView(memory.buffer).getUint32(p, true);
  const put = (p, v) => new DataView(memory.buffer).setUint32(p, v, true);
  const string = word => {
    need(word % 8 === 6 && word >= 6 && (get(word - 6) & 255) === 191, 'PATH');
    const n = get(word - 6) >>> 8; need(n <= 4096 && word - 2 + 4 * n <= memory.buffer.byteLength, 'PATH');
    return Array.from({length: n}, (_, i) => String.fromCodePoint(get(word - 2 + 4 * i))).join('');
  };
  const allocate = bytes => owner.atSafepoint(o => {
    o.ensure(bytes); const p = get(env.tcr + 48); put(env.tcr + 48, p + bytes); return p;
  });
  const client = fileClient({memory, tcr: env.tcr, post, pinned, allocate,
    collect: () => {}, // A completed request is a safepoint; collection is demand driven.
    refuse: why => { throw Error('target file: ' + why); }});
  const rootCells = values => {
    const roots = owner.atSafepoint(o => o.rootCells(values));
    return {...roots, release: () => owner.atSafepoint(() => roots.release())};
  };
  return Object.freeze({
    file(args) {
      const op = get(args) >> 2, fd = get(args + 4) >> 2;
      let pending;
      if (op === 0) {
        const name = string(get(args + 4));
        // Missing-file errno belongs to the ordinary namespace operation.
        let path;
        try { path = paths.realpath(name); } catch (e) { if (e.code !== 'NOT_FOUND') throw e; }
        const bundle = source.bundles.get(path);
        if (bundle && get(args + 8) === 0) {
          const codeIds = {}, slots = {};
          let code = nextCode, slot = nextSlot;
          for (const row of bundle.modules) { codeIds[row.code_id] = code++; slots[row.code_id] = slot++; }
          const timed = (phase, run) => measure(phase, run, {path});
          const session = timed('bundle.admit', () => admitTargetBundle({...bundle, env, capabilities, versions, policy,
            codeIds, slots, rootCells, measure: timed}));
          onAdmission(path);
          pending = {path, install: targetCodeService({memory, session}), session, code, slot};
        }
      }
      const result = client(args), value = result >> 2;
      if (op === 0 && value >= 0) {
        need(pending, 'BUNDLE_SESSION'); nextCode = pending.code; nextSlot = pending.slot;
        open.set(value, pending); onOpen(pending.path, value);
      }
      if (op === 3 && value >= 0) { const prior = open.get(fd); open.delete(fd); if (prior) onClose(prior.path, fd); }
      return result;
    },
    install(args) {
      const fd = get(args + 8); need(fd % 4 === 0 && open.has(fd >> 2), 'CLOSED_SESSION');
      const file = open.get(fd >> 2), result = file.install(get(args), get(args + 4));
      onInstall(file.path, file.session.entries());
      return result;
    },
    openFiles: () => [...open.values()].map(row => row.path)
  });
}
