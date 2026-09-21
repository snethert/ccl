"""Focused owner and compiled-module faults; prerequisite files are reused."""
import json,shutil,subprocess,tempfile
from pathlib import Path

def controls(out,node,wabt):
 source=(out/'inputs.mjs').read_text();check=(out/'check.mjs').read_text();wat=(out/'compiled/host_image.wat').read_text()
 store='(i32.store (call $special_location (i32.load offset=8 (local.get $tmp1))) (i32.load offset=12 (local.get $tmp1)))'
 head,entry=wat.split('(func (export "entry")')
 faults=[
 ('unicode-nfc','inputs.mjs',source,"const imageName=text(precompose(text(input.imageName)));","const imageName=text(text(input.imageName).normalize('NFC'));",'native host callback'),
 ('reversed-argv','inputs.mjs',source,'Array.from(input.arguments,text)','Array.from(input.arguments,text).reverse()','private input snapshot'),
 ('drop-empty-argv','inputs.mjs',source,'Array.from(input.arguments,text)','Array.from(input.arguments,text).filter(Boolean)','private input snapshot'),
 ('missing-image-root','check.mjs',check,'put(extra,symbol(21)+2)','put(extra,symbol(20)+2)','image moves'),
 ('missing-argv-root','check.mjs',check,'put(extra+4,symbol(22)+2)','put(extra+4,symbol(20)+2)','input value tag'),
 ('omitted-image-publication','compiled/host_image.wat',wat,store,'(nop)','POSTCONDITION'),
 ('wrong-image-completion','compiled/host_image.wat',wat,'(i32.const 1204)','(i32.const 1200)','COMPLETION_MISSING'),
 ('tsp-not-restored','compiled/host_image.wat',wat,entry,entry.replace('(return (local.get $value) (local.get $count))','(i32.store offset=76 (global.get $tcr) (i32.add (i32.load offset=76 (global.get $tcr)) (i32.const 16)))(return (local.get $value) (local.get $count))',1),'TCR preservation'),
 ]
 records=[];dest=out/'faults';dest.mkdir()
 for name,file,original,old,new,reason in faults:
  assert original.count(old)==1,(name,original.count(old));changed=original.replace(old,new)
  retained=dest/name;retained.mkdir();(retained/Path(file).name).write_text(changed)
  with tempfile.TemporaryDirectory(prefix='ccl-host-fault-') as d:
   d=Path(d)
   for p in out.iterdir():
    if p.is_file():shutil.copy(p,d/p.name)
   shutil.copytree(out/'compiled',d/'compiled');(d/file).write_text(changed)
   (d/'node.mjs').write_text((d/'node.mjs').read_text().replace('[4194304,2147483648]','[4194304]'))
   if file.endswith('.wat'):
    subprocess.run([str(wabt),str(d/file),'--enable-all','-o',str((d/file).with_suffix('.wasm'))],check=True,capture_output=True)
    shutil.copy((d/file).with_suffix('.wasm'),retained/'host_image.wasm')
   p=subprocess.run([str(node),str(d/'node.mjs'),str(d),str(d/'result.json')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=120)
   (retained/'execution.log').write_text(p.stdout)
   assert p.returncode and reason in p.stdout,(name,p.returncode,p.stdout[-2000:])
   records.append(dict(name=name,status='REJECTED',reason=reason,kind='assembled module' if file.endswith('.wat') else 'owner/fixture mutation'))
 (out/'controls.json').write_text(json.dumps(records,indent=2,sort_keys=True)+'\n')
 return records
