// A namespace file and its code inventory share one admitted bundle identity.
// The byte stream exposes the ordinary FASL payload; code is installed only
// when that stream's opcode 72 requests its exact compiler record.
import {createNamespace} from './namespace.mjs';
import {admitTargetBundle, decodeTargetBundle, decodeTargetContainer, targetContainerVersion} from './target-bundle.mjs';
import {targetCodeService} from './target-code-service.mjs';
import {fileClient} from './file-client.mjs';
import {admitCodeArchive} from './code-archive.mjs';
import {sha256} from './sha256.mjs';

const need = (ok, why) => { if (!ok) throw Error('target load: ' + why); };
export function bundleNamespace({files, cwd = '/ccl', cclRoot = '/ccl', measure = (_phase, run) => run(), directoryOnly=false, retainCode=true, discardInputs=false}) {
  const entries = new Map([['/', {path: '/', kind: 'directory'}]]), bundles = new Map(), containers = new Map();
  try{
  for (const file of files) {
    need(!entries.has(file.path), 'DUPLICATE_FILE');
    const v2=file.container!==undefined||targetContainerVersion(file.bytes)===2;
    const decoded=file.container?{manifest:file.container,fasl:file.fasl??new Uint8Array()}:
      measure('namespace.decode', () => (v2?decodeTargetContainer:decodeTargetBundle)(file.bytes, file.sha256), {path: file.path});
    if(v2){
      need(/^[0-9a-f]{64}$/.test(decoded.manifest.archive_sha256)&&Array.isArray(decoded.manifest.units)&&
        decoded.manifest.units.every(n=>typeof n==='string')&&new Set(decoded.manifest.units).size===decoded.manifest.units.length,'CONTAINER');
    }
    const fasl=directoryOnly?new Uint8Array():decoded.fasl;
    let parent = file.path.slice(0, file.path.lastIndexOf('/')) || '/';
    while (parent !== '/') {
      need(!entries.has(parent) || entries.get(parent).kind === 'directory', 'PARENT');
      entries.set(parent, {path: parent, kind: 'directory'});
      parent = parent.slice(0, parent.lastIndexOf('/')) || '/';
    }
    entries.set(file.path, {path: file.path, kind: 'file', bytes: fasl, sha256: sha256(fasl)});
    if(v2)containers.set(file.path,{archive_sha256:decoded.manifest.archive_sha256,units:[...decoded.manifest.units]});
    else if(retainCode)bundles.set(file.path, {bytes: new Uint8Array(file.bytes), digest: file.sha256,
      modules: decoded.manifest.codeSet.modules});
  }
  }finally{if(discardInputs)for(const file of files){delete file.bytes;delete file.fasl;}}
  for (const path of [cwd, cclRoot]) if (!entries.has(path)) entries.set(path, {path, kind: 'directory'});
  const namespace = createNamespace({version: 1, entries: [...entries.values()], cwd, cclRoot});entries.clear();
  const path = value => /^ccl:/i.test(value) ? cclRoot + '/' + value.slice(4).replaceAll(';', '/') : value;
  const session = () => {
    const inner = namespace.session();
    return Object.freeze({...inner,
      open: (name, mode) => inner.open(path(name), mode),
      stat: name => inner.stat(path(name)), realpath: name => inner.realpath(path(name))});
  };
  return Object.freeze({namespace, bundles, containers, session,ownership:()=>({fasl:namespace.storage(),
    v1Bundles:{bytes:[...bundles.values()].reduce((n,b)=>n+b.bytes.byteLength,0),count:bundles.size}})});
}

export async function targetLoadSession({files, archives=[], readArchive, onInput=()=>{}, onBuffers=()=>{}, onManifest=()=>{}, generations=2, memory, env, owner, versions, policy, capabilities,
  nextCode, nextSlot, slotOffset=nextSlot-nextCode, post, pinned, onOpen = () => {}, onClose = () => {}, onInstall = () => {},
  measure = (_phase, run) => run(), onAdmission = () => {}}) {
  const source = measure('namespace.create', () => bundleNamespace({files, measure, directoryOnly:true,discardInputs:true})), paths = source.session(), open = new Map();
  const admitted=new Map();
  let v1Modules=0,v1Instances=0;
  for(const descriptor of archives){
    let a=readArchive?await readArchive(descriptor):descriptor;
    onInput('admission-start',a);
    try{
    need(!admitted.has(a.digest),'DUPLICATE_ARCHIVE');
    const archive=measure('archive.admit',()=>admitCodeArchive({...a,env,capabilities,versions,policy,slotOffset,maxGenerations:generations,measure,onBuffers,onManifest,
      allocateCode:(n,journal)=>{const base=nextCode,slot=nextSlot;nextCode+=n;nextSlot+=n;
        journal.push(()=>{nextCode=base;nextSlot=slot;});return base;},
      reserveRoots:(n,journal)=>{const block=owner.atSafepoint(o=>o.reserveRootBlock(n));
        journal.push(()=>owner.atSafepoint(()=>block.release()));return block;},
      registerRoots:(block,cells,journal)=>{owner.atSafepoint(()=>block.register(cells));
        journal.push(()=>owner.atSafepoint(()=>block.unregister(cells)));}}));
    archive.prepare();admitted.set(a.digest,archive);onAdmission(a.digest);
    }finally{a.bytes=null;a.manifest=null;onInput('admission-end',a);a=null;}
  }
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
        const container=source.containers.get(path);
        if(container&&get(args+8)===0){
          const archive=admitted.get(container.archive_sha256);need(archive,'ARCHIVE_ABSENT');
          const token=Symbol(path);archive.reserve(token,container.units);
          const session={install:(name,record,symbols)=>archive.install(token,name,record,symbols),entries:()=>archive.entries(token)};
          pending={path,token,archive,session,install:targetCodeService({memory,session})};
        }
        const bundle = source.bundles.get(path);
        if (bundle && get(args + 8) === 0) {
          const codeIds = {}, slots = {};
          let code = nextCode, slot = nextSlot;
          for (const row of bundle.modules) { codeIds[row.code_id] = code++; slots[row.code_id] = slot++; }
          const timed = (phase, run) => measure(phase, run, {path});
          const session = timed('bundle.admit', () => admitTargetBundle({...bundle, env, capabilities, versions, policy,
            codeIds, slots, rootCells, measure: timed}));
          v1Modules+=bundle.modules.length;
          onAdmission(path);
          pending = {path, install: targetCodeService({memory, session}), session, code, slot, installed:0};
        }
      }
      let result;
      try{result=client(args);}catch(e){pending?.archive?.release(pending.token);throw e;}
      const value=result>>2;
      if(op===0&&value<0)pending?.archive?.release(pending.token);
      if (op === 0 && value >= 0) {
        need(pending, 'BUNDLE_SESSION'); if(!pending.archive){nextCode = pending.code; nextSlot = pending.slot;}
        open.set(value, pending); onOpen(pending.path, value);
      }
      if (op === 3 && value >= 0) { const prior = open.get(fd); open.delete(fd); if (prior) {prior.archive?.release(prior.token);onClose(prior.path, fd);} }
      return result;
    },
    install(args) {
      const fd = get(args + 8); need(fd % 4 === 0 && open.has(fd >> 2), 'CLOSED_SESSION');
      const file = open.get(fd >> 2), result = file.install(get(args), get(args + 4));
      const entries=file.session.entries();
      if(!file.archive){v1Instances+=entries.length-file.installed;file.installed=entries.length;}
      onInstall(file.path, entries);
      return result;
    },
    closeSessions(){const abandoned=[...open.values()].map(r=>r.path);
      for(const row of open.values())row.archive?.release(row.token);open.clear();return abandoned;},
    ownership:()=>source.ownership(),
    archives:()=>[...admitted.values()].map(a=>a.storage()),
    productCounts:()=>({modules:admitted.size+v1Modules,instances:v1Instances+[...admitted.values()].reduce((n,a)=>n+a.storage().generations,0)}),
    openFiles: () => [...open.values()].map(row => row.path)
  });
}
