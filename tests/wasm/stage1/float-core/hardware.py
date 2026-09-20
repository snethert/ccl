import math,subprocess
from corpus import OPS,value,coerce,ieee,bits,flags

def run(out,rows,driver):
 selected=[];seen=set()
 for row in rows:
  if row['op'] not in OPS[:4] or '64' in [row['a']['kind'],row['b']['kind']]:continue
  a,_=coerce(row['a'],32,True,1);b,_=coerce(row['b'],32,True,1)
  if math.isnan(a) or math.isnan(b):continue
  key=(row['op'],bits(a,32),bits(b,32))
  if key in seen:continue
  seen.add(key);s,r=ieee.expected(row['op'],a,b,ieee.SINGLE);selected.append(dict(op=key[0],a=key[1],b=key[2],result=bits(r,32),flags=flags(s)))
 driver.save(out/'hardware-cases.json',selected)
 (out/'hardware-input.txt').write_text(''.join(f'{OPS.index(r["op"])} {r["a"]} {r["b"]}\n' for r in selected))
 driver.command(['/usr/bin/clang','-O0',driver.HERE/'native-f32.c','-o',out/'native-f32'],out/'hardware-build.log')
 driver.save(out/'hardware-run.command.json',dict(argv=[str(out/'native-f32')],stdin=str(out/'hardware-input.txt'),stdout=str(out/'hardware-results.txt')))
 with (out/'hardware-input.txt').open() as src,(out/'hardware-results.txt').open('w') as dst:subprocess.run([out/'native-f32'],stdin=src,stdout=dst,check=True)
 got=(out/'hardware-results.txt').read_text().splitlines();assert len(got)==len(selected)
 for row,line in zip(selected,got):
  raw,f=line.split();integer=int(raw,16)
  actual='nan' if integer&0x7f800000==0x7f800000 and integer&0x7fffff else raw
  assert (actual,int(f))==(row['result'],row['flags']),(row,line)
 driver.save(out/'hardware.json',dict(status='PASS',cases=len(got),compiler='/usr/bin/clang',source_sha256=driver.sha(driver.HERE/'native-f32.c')))
