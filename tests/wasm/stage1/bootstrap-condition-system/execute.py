from pathlib import Path
import json,subprocess,sys,shutil
h=Path(__file__).resolve().parent;g=h.parent/'bootstrap-generic-dispatch';r=h.parents[3];p=h.parent/'bootstrap-values';o=Path(sys.argv[1]).resolve();d=o/'driver'
sys.path.insert(0,str(d));import encode
encode.Encoder.__init__.__defaults__=(r/'doc/WASM/contracts/wasm32-layout.v1.json',16*1024*1024)
from pool import compile_pool
prior=h.parent/'bootstrap-numeric-dispatch'
def fixture(name):
 for directory in (h,h.parent/'lap-primitives',h.parent/'bootstrap-generic-dispatch',h.parent/'bootstrap-gcd',h.parent/'bootstrap-limb-division',h.parent/'bootstrap-limb-multiply',h.parent/'bootstrap-numeric-dispatch',h.parent/'bootstrap-clos-accessors',h.parent/'bootstrap-lexpr-spread'):
  if (directory/name).exists():return directory/name
 raise FileNotFoundError(name)

owners=json.loads((o/'compiled/symbols.json').read_text());pool=compile_pool(json.loads((o/'compiled/pools.json').read_text()),{x['id']:7000006+32*i for i,x in enumerate(owners)})
mat=pool.at(2097152);(o/'compiled/materialized.json').write_text(json.dumps(dict(image=mat.image.hex(),roots=mat.roots)))
# Move up to 16 KiB of literal-pool vectors, prioritizing the dispatch entries.
# The remaining literal image stays pinned, leaving room in the 64 KiB heap
# for complete CLOS graphs and collecting restart/constructor paths.
import struct
raw=mat.image;origin=2097152;vectors={};pending=list(mat.roots)
while pending:
 word=pending.pop()
 if word in vectors or word&7 != 6 or not origin+6 <= word < origin+len(raw):continue
 start=word-6-origin;header=struct.unpack_from('<I',raw,start)[0]
 if header&255 != 250:continue
 count=header>>8;size=8*((count+2)//2)
 vectors[word]=raw[start:start+size]
 pending.extend(struct.unpack_from('<'+str(count)+'I',raw,start+4))
# A pinned object must never retain an old alias of a copied vector. Keep the
# transitive vector children of every pinned non-vector in the pinned image.
from bisect import bisect_right
objects=sorted((offset,tag) for _,offset,tag in pool.objects)
starts=[offset for offset,_ in objects]
pinned=set();edges={}
for slot,target,tag in pool.fixups:
 owner_offset,owner_tag=objects[bisect_right(starts,slot)-1]
 owner_word=origin+owner_offset+owner_tag;target_word=origin+target+tag
 if target_word in vectors:
  if owner_word not in vectors:pinned.add(target_word)
  else:edges.setdefault(owner_word,[]).append(target_word)
modules=json.loads((o/'compiled/modules.json').read_text())
priority={mat.roots[i] for i,m in enumerate(modules) if m['name'].startswith('core_generic')}
budget=0
for word in sorted(vectors,key=lambda word:(word not in priority,word)):
 if len(vectors[word]) <= budget:budget-=len(vectors[word])
 else:pinned.add(word)
pending=list(pinned)
while pending:
 for child in edges.get(pending.pop(),[]):
  if child not in pinned:pinned.add(child);pending.append(child)
for word in pinned:vectors.pop(word)
def moving_vectors(base):
 offsets={};image=bytearray()
 for old,data in sorted(vectors.items()):
  offsets[old]=base+len(image)+6;image.extend(data)
 for old,new in offsets.items():
  start=new-6-base;count=struct.unpack_from('<I',image,start)[0]>>8
  for i in range(count):
   offset=start+4+4*i;word=struct.unpack_from('<I',image,offset)[0]
   struct.pack_into('<I',image,offset,offsets.get(word,word))
 return dict(image=image.hex(),roots=[offsets.get(word,word) for word in mat.roots])
(o/'compiled/moving-pools.json').write_text(json.dumps({str(b):moving_vectors(b) for b in [8388608,2146500608]}))
sys.path.insert(0,str(h));import backend
runtime=o/'runtime';runtime.mkdir(exist_ok=True)
for f in (r/'runtime/wasm32').glob('*.mjs'):shutil.copy(f,runtime/f.name)
for name,text in backend.runtime_files().items():(runtime/name).write_text(text)
for name in ('install.mjs','check.mjs','gf-check.mjs','installer-check.mjs','metadata-check.mjs','bignum-check.mjs'):shutil.copy(fixture(name),o/name)
sys.path.insert(0,str(h.parent/"bootstrap-core"));import probe;probe.build(o/'compiled')
clang='/usr/local/opt/llvm/bin/clang';baseflags=['--target=wasm32','-O2','-nostdlib','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--max-memory=2147549184','-Wl,-z,stack-size=65536']
for name,extra in [('collector',['-matomics','-mbulk-memory','-Wl,--shared-memory','-Wl,--global-base=1048576','-Wl,--export=collect','-Wl,--export=__stack_pointer']),('integer',['-Wl,--global-base=65536','-Wl,--export=integer_calculate','-Wl,--export=integer_workspace_bytes'])]:
 subprocess.run([clang,*baseflags,*extra,(runtime/f'{name}.c' if (runtime/f'{name}.c').exists() else r/f'runtime/wasm32/{name}.c'),'-o',o/f'{name}.wasm'],check=True)
import importlib.util
spec=importlib.util.spec_from_file_location('math_build',r/'runtime/wasm32/build-float.py');build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build);build.build(o,runtime)
subprocess.run([clang,*baseflags,'-matomics','-mbulk-memory','-Wl,--shared-memory','-Wl,--global-base=1048576','-Wl,--export=ht_size','-Wl,--export=ht_init','-Wl,--export=ht_run',r/'runtime/wasm32/hash.c','-o',o/'hash.wasm'],check=True)
subprocess.run(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions',r/'runtime/wasm32/hash-adapter.wat','-o',o/'hash-adapter.wasm'],check=True)
subprocess.run(['/usr/local/bin/wat2wasm',r/'runtime/wasm32/float-detector.wat','-o',o/'detector.wasm'],check=True)
shutil.copy(r.parent/'ccl-evidence/2026-09-21-stage1-population-pushnew-r1/execution/eql.wasm',o/'eql.wasm')
subprocess.run(['/usr/local/bin/wat2wasm','--enable-tail-call',r/'runtime/wasm32/stub.wat','-o',o/'stub.wasm'],check=True)
shutil.copy(h/'graph.mjs',o/'graph.mjs')
with (o/'execution.log').open('w') as log:subprocess.run(['/usr/local/bin/node',o/'check.mjs',o,o/'execution.json'],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=600)

shutil.copy(fixture('istruct-check.mjs'),o/'istruct-check.mjs')
subprocess.run(['/usr/local/bin/node',o/'istruct-check.mjs',o/'collector.wasm',o/'istruct-checks.json'],check=True)

shutil.copy(g/'population-check.mjs',o/'population-check.mjs')
subprocess.run(['/usr/local/bin/node',o/'population-check.mjs',o/'collector.wasm',o/'population-checks.json'],check=True)
# The generic-dispatch census and changed-site controls belong to that
# fixture's own derivation, which is integrated and accepted; this fixture
# keeps the structure, population and owner checks that run on any corpus.
owner_check=o/'owner-check';owner_check.mkdir(exist_ok=True)
for path in (o/'runtime').glob('*.mjs'):shutil.copy(path,owner_check/path.name)
shutil.copy(owner_check/'collector-owner.mjs',owner_check/'owner.mjs')
shutil.copy(h.parent/'collector-owner/check.mjs',owner_check/'check.mjs')
with (owner_check/'run.log').open('w') as log:
 subprocess.run(['/usr/local/bin/node',owner_check/'check.mjs',o/'collector.wasm',owner_check/'results.json'],stdout=log,stderr=log,check=True)
assert json.loads((owner_check/'results.json').read_text())['checks']==40
