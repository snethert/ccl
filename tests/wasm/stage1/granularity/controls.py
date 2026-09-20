from pathlib import Path
import shutil,subprocess
# Each fault executes the same real mapping/publication checker.
def run(out):
 source=(out/'bundle.mjs').read_text();faults=[
 ('inventory',"need(same(bundle.modules.map(x=>[x.name,x.code_id,x.generation]),expected.modules),'INVENTORY');",'', 'omitted-module'),
 ('role',"&&a.table===(role==='entry'?'public':'tail')",'', 'role'),
 ('signature',"need(same(a.signature,signatures[role])&&same(x.types[x.functions[b.index]],signatures[role]),'SIGNATURE');",'', 'signature'),
 ('range',"need(same(a.range,ranges.find(e=>e.role===role)),'RANGE');",'', 'body-range'),
 ('digest',"need(sha256(bytes)===m.d2.outputs.full.binary_sha256,'BINARY');",'', 'binary-digest'),
 ('versions',"need(same(m.abi,bundle.abi)&&same(m.layout,bundle.layout),'MODULE_VERSIONS');",'', 'layout'),
 ('rollback',"for(const slot of written){table.set(slot,null);tailTable.set(slot,null);}",'', 'rollback-public'),
 ('occupation',"for(const {record:m}of compiled)need(table.get(m.slot)===null&&tailTable.get(m.slot)===null,'OCCUPIED');",'', 'Missing expected exception')]
 rows=[]
 for name,a,b,diagnostic in faults:
  assert source.count(a)==1,name
  d=out/'faults'/name;d.mkdir(parents=True)
  for p in out.iterdir():
   if p.name=='faults':continue
   (d/p.name).symlink_to(p)
  (d/'bundle.mjs').unlink();(d/'bundle.mjs').write_text(source.replace(a,b));(d/'check.mjs').unlink();shutil.copy(out/'check.mjs',d/'check.mjs')
  with (d/'failure.log').open('w') as f:r=subprocess.run(['/usr/local/bin/node',str(d/'check.mjs'),str(out)],stdout=f,stderr=subprocess.STDOUT)
  text=(d/'failure.log').read_text();assert r.returncode!=0 and diagnostic in text,(name,text)
  rows.append(dict(name=name,status='REJECTED',diagnostic=diagnostic))
 return rows
