import shutil,json,subprocess
from derive import replace
from run import build,command,NODE,save

def run(out):
 source=(out/'hash.c').read_text();controls=[]
 cases=[
 ('identity-only', 'U x[KEY_DEPTH],y[KEY_DEPTH],used=1;', 'return a==b; U x[KEY_DEPTH],y[KEY_DEPTH],used=1;', 'eql lookup 9,10'),
 ('eql-list-equality', 'if(MODE==2&&(a&7)==1)', 'if((a&7)==1)', 'eql lookup 31,32'),
 ('equal-no-cdr', 'x[used]=L(a-1);y[used++]=L(b-1);', 'x[used]=NIL;y[used++]=NIL;', 'equal lookup'),
 ('double-padding', 'if(!words_equal(a+2,b+2,2))', 'if(!words_equal(a-2,b-2,3))', 'double ignores padding'),
 ('string-identity', '||(MODE==2&&tag==191)){if(!words_equal', '||0){if(!words_equal', 'equal lookup 22,23'),
 ('bit-padding', 'if((byte_at(a-2+i)&mask)!=(byte_at(b-2+i)&mask))', 'if(byte_at(a-2+i)!=byte_at(b-2+i))', 'bit unused bits'),
 ('address-hash', 'U at=content_hash(key,n),free=NONE;', 'U at=hash(key,n),free=NONE;', 'eql moved lookup'),
 ('full-pointer-match', 'if(same(L(key_slot(b,i)),key))found=1;', 'if(L(key_slot(b,i))==key)found=1;', 'status'),
 ('duplicate-pointer-match', 'if(present!=EMPTY&&same(present,k))return BAD_TABLE;', 'if(present==k)return BAD_TABLE;', 'duplicate eql rehash'),
 ('missing-count-publication', 'S(result+8,op==0?2:1);', '/* omitted */', 'count publication'),
 ]
 for name,a,b,why in cases:
  d=out/'faults'/name;d.mkdir(parents=True)
  for n in ['native.json','owner.mjs','check.mjs','generated.mjs','adapter.wasm','collector.wasm']:shutil.copy(out/n,d/n)
  shutil.copytree(out/'compiled',d/'compiled')
  (d/'hash.c').write_text(replace(source,a,b))
  for mode,kind in [(1,'eql'),(2,'equal')]:build(d/'hash.c',d/(kind+'.wasm'),mode)
  try:command([NODE,d/'check.mjs',d,d/'execution.json'],d/'rejected.log')
  except subprocess.CalledProcessError:
   log=(d/'rejected.log').read_text();assert why in log,(name,log[-1500:]);controls.append(dict(name=name,status='REJECTED',diagnostic=why))
  else:raise AssertionError(name+' escaped')
 save(out/'controls.json',controls)
