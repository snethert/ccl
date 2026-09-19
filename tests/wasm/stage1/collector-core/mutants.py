"""Mutate the actual C service, compile, require a named independent assertion."""
import json,subprocess
from pathlib import Path

def run(h,out,clang,flags,check):
 out.mkdir();source=(Path(__file__).parent/'collector.c').read_text();rows=[]
 variants=[
  ('false-success','fail(s,code);return s->error;','fail(s,code);return 0;','unknown-header'),
  ('lost-root','STORE(updates(s)[index].slot,updates(s)[index].value);','(void)updates(s)[index];','roots actually moved'),
  ('lost-edges','scan=o->scan;p=o->moved;','scan=0;p=o->moved;','cycle-sharing'),
  ('raw-as-roots','scan=0;size=4+(W)bytes;','scan=n;size=4+(W)bytes;','raw-payload-not-roots'),
  ('raw-width','case 215: case 223:return n*2;','case 215: case 223:return n*4;','raw-width-215'),
  ('stack-environment','if(i==1 && (original&7)==6','if(i==9 && (original&7)==6','stack capture cell moved'),
  ('wrong-tag','if((tag==1)!=(o->scan==0xffffffffu))','if(0)','tag-mismatch'),
  ('stale-vector','(Update){s->tcr+104,p-2}','(Update){s->tcr+104,base}','raw interior root moved'),
 ]
 for name,old,new,why in variants:
  assert source.count(old)==1,name
  c=out/(name+'.c');c.write_text(source.replace(old,new));wasm=out/(name+'.wasm')
  argv=[clang,*flags,str(c),'-o',str(wasm)]
  with (out/(name+'-compile.log')).open('w') as f:subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,check=True)
  with (out/(name+'.log')).open('w') as f:r=subprocess.run(['/usr/local/bin/node',str(check),str(wasm),str(out/(name+'.json'))],stdout=f,stderr=subprocess.STDOUT,timeout=60)
  log=(out/(name+'.log')).read_text();assert r.returncode!=0 and 'AssertionError' in log and why in log,(name,log)
  rows.append(dict(name=name,status='REJECTED',oracle=why))
 (out/'controls.json').write_text(json.dumps(rows,indent=2)+'\n');return rows
