import shutil,subprocess,json
from derive import HERE,replace
def run(out):
 faults=[
  ('padding','sha256.mjs','tail[remaining]=0x80','tail[remaining]=0','vector-empty'),
  ('length-endian','sha256.mjs','(bytes.length*8)>>>0);','(bytes.length*8)>>>0,true);','vector-abc'),
  ('offset','bytes.mjs','value.buffer, value.byteOffset, value.byteLength','value.buffer, 0, value.byteLength','offset-'),
  ('snapshot-alias','bytes.mjs','new Uint8Array(byteView(value))','byteView(value)','snapshot-view-copy'),
  ('utf8','bytes.mjs','encoder.encode(text)','Uint8Array.from(text,c=>c.charCodeAt(0)&255)','utf8-nonascii'),
  ('collector-binding','collector-owner.mjs',"sha256(bytes)===digest","true",'collector-binding-false'),
  ('integer-binding','integer-service.mjs','sha256(bytes)!==digest','false','integer-binding-false'),
  ('float-binding','float-service.mjs','hash(bytes)!==digest','false','float-binding-false'),
  ('detector-binding','float-service.mjs','hash(detectorBytes)!==detectorDigest','false','detector-binding-false'),
  ('scalar-binding','scalar-service.mjs','sha256(scalarBytes)===scalarDigest','true','scalar-binding-false'),
  ('loader-binding','loader.mjs','sha(bytes)===record.sha256','true','loader-digest'),
  ('loader-snapshot','loader.mjs','snapshotBytes(o.readBytes(row.record.name))','o.readBytes(row.record.name)','loader-owned-snapshot-view'),
  ('installer-snapshot','installer.mjs','snapshotBytes(readBytes(r.name))','readBytes(r.name)','installer snapshot publication failure'),
 ]
 rows=[]
 for name,file,a,b,diagnostic in faults:
  dest=out/'mutants'/name;dest.mkdir(parents=True);shutil.copytree(out/'proposal',dest/'proposal')
  target=dest/'proposal'/file;target.write_text(replace(target.read_text(),a,b))
  for n in ['checks.mjs','binding-browser.mjs']:shutil.copy(out/n,dest/n)
  shutil.copy(HERE/'quick-check.mjs',dest/'quick-check.mjs')
  command=['node',str(dest/'quick-check.mjs'),str(out)]
  (dest/'command.json').write_text(json.dumps(command)+'\n')
  with (dest/'failure.log').open('w') as f:p=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,timeout=120)
  text=(dest/'failure.log').read_text()
  assert p.returncode!=0 and diagnostic in text,(name,p.returncode,text[-3000:])
  rows.append(dict(name=name,status='REJECTED',diagnostic=diagnostic))
 (out/'controls.json').write_text(json.dumps(rows,indent=2)+'\n')
 return rows
