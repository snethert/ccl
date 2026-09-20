#!/usr/bin/env python3
"""Audit-103 controls over the unchanged, hash-pinned integer service."""
import argparse,importlib.util,json,random,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=BASE.parents[3]
sys.path.insert(0,str(BASE))
import corpus
spec=importlib.util.spec_from_file_location('integer_original_runner',BASE/'run.py');prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
PACK='2026-09-19-stage1-integer-core-r1'
def cases():
 rows=corpus.cases()
 def add(name,op,a,b):
  values=corpus.expected(op,a,b);rows.append(dict(name=name,op=op,a=str(a),b=str(b),expected=list(map(str,values))))
 for op,pairs in [('mul',[(65,65),(128,127),(256,255),(512,512),(768,255),(1023,1)]),('truncate',[(65,32),(128,65),(256,127),(512,255),(768,383),(1024,511),(1024,1023),(1024,1)])]:
  for wa,wb in pairs:
   a=(1<<(wa*32-1))-17;b=(1<<(wb*32-1))-3
   for sa in [-1,1]:
    for sb in [-1,1]:add(f'wide-{op}-{wa}-{wb}-{sa}-{sb}',op,a*sa,b*sb)
 rng=random.Random(103)
 for i in range(72):
  op='mul' if i%2==0 else 'truncate';wa=rng.randrange(65,1024);wb=rng.randrange(1,1025-wa if op=='mul' else 1025)
  a=(rng.getrandbits(wa*32-2)|(1<<(wa*32-2)))*rng.choice([-1,1]);b=(rng.getrandbits(wb*32-2)|(1<<(wb*32-2)))*rng.choice([-1,1])
  add(f'wide-random-{i}',op,a,b)
 # This also gets an independent native answer, not just a resource assertion.
 q=(1<<64)+1;b=(1<<48)+3;r=(1<<40)+1
 add('two-bignum-results','truncate',q*b+r,b)
 return rows

def overlay():
 s=(BASE/'execute.mjs').read_text()
 old="refuse('misaligned-pointer'";assert s.count(old)==1;s=s.replace(old,"refuse('aligned-nonobject-header'")
 old=" let src=input,dest=out,value=null,chainSteps=0;";assert s.count(old)==1
 extra=''' // The quotient and remainder EACH require sixteen bytes. At sixteen
 // and twenty-four only the first fits; at thirty-two both fit exactly.
 const quotient=(1n<<64n)+1n,divisor=(1n<<48n)+3n,remainder=(1n<<40n)+1n;
 const dividend=quotient*divisor+remainder;
 for(const reserved of [16,24])refuse('combined-result-capacity-'+reserved,5,String(dividend),String(divisor),3,{limit:out+reserved});
 {
  const [av,bv]=prepare(String(dividend),String(divisor));const before=bytes.slice(out+32,limit),inputBefore=bytes.slice(input,inputEnd);
  assert.equal(invoke(5,av,bv,{limit:out+32}),0,'combined-result-exact-fit');
  assert.equal(decode(get(result)),String(quotient));assert.equal(decode(get(result+4)),String(remainder));
  assert.equal(get(result+8),2);assert.equal(get(result+12),out+32);
  assert.equal(get(result),out+6);assert.equal(get(result+4),out+22);
  assert.deepEqual(bytes.slice(out+32,limit),before,'exact-fit guard');assert.deepEqual(bytes.slice(input,inputEnd),inputBefore);
 }
 // Canonical but out-of-budget inputs: pin the existing diagnostic distinction.
 refuse('canonical-1025-digits-capacity',4,String(1n<<32768n),'0',3);
 refuse('canonical-1026-digits-shape',4,String(1n<<32800n),'0',2);
'''
 return s.replace(old,extra+old)

def run(e,out):
 out.mkdir(parents=True,exist_ok=False);pins=json.loads((e/PACK/'source-pins.json').read_text())
 for n,h in pins.items():assert prior.sha(ROOT/n)==h,n
 driver=out/'driver';driver.mkdir();shutil.copy(BASE/'integer.c',driver/'integer.c');(driver/'execute.mjs').write_text(overlay())
 prior.HERE=driver;prior.cases=cases
 prior.run(e,out/'execution')
 ex=out/'execution';assert (ex/'integer.wasm').read_bytes()==(e/PACK/'execution/integer.wasm').read_bytes(),'unchanged reviewed binary'
 fault=out/'first-value-only';fault.mkdir();code=(BASE/'integer.c').read_text();old='if((W)out+n+m>limit)return CAPACITY;';assert code.count(old)==1
 (fault/'integer.c').write_text(code.replace(old,'if((W)out+n>limit)return CAPACITY;'))
 prior.command([prior.CLANG,*prior.FLAGS,fault/'integer.c','-o',fault/'integer.wasm'],fault/'build.log')
 # Retain the escaped original control, not just the repaired rejection.
 prior.command([prior.NODE,BASE/'execute.mjs',fault/'integer.wasm',e/PACK/'execution/cases.json',fault/'original-controls.json'],fault/'original-controls.log')
 try:prior.command([prior.NODE,ex/'execute.mjs',fault/'integer.wasm',ex/'cases.json',fault/'new-controls.json'],fault/'new-controls.log')
 except subprocess.CalledProcessError:
  rejection=json.loads((fault/'new-controls.json').read_text());assert rejection['status']=='FAIL' and rejection['message'].startswith('combined-result-capacity-16'),rejection
 else:raise AssertionError('first-value-only allocation escaped')
 # Redundant alignment test is documentary, not a second rejection branch.
 alignment=out/'redundant-alignment';alignment.mkdir();old='if((p&7)||p<in';assert code.count(old)==1
 (alignment/'integer.c').write_text(code.replace(old,'if(p<in'))
 prior.command([prior.CLANG,*prior.FLAGS,alignment/'integer.c','-o',alignment/'integer.wasm'],alignment/'build.log')
 assert (alignment/'integer.wasm').read_bytes()==(ex/'integer.wasm').read_bytes()
 summary=json.loads((ex/'summary.json').read_text());summary.update(kind='AUXILIARY_INTEGER_REVIEW_FOLLOWUP',unchanged_binary_sha256=prior.sha(ex/'integer.wasm'),new_cases=len(cases())-len(corpus.cases()),mutants=summary['mutants']+1,original_first_value_fault='ESCAPED',new_first_value_fault='REJECTED: combined-result-capacity-16',redundant_alignment='REMOVAL_BINARY_IDENTICAL',exact_fit_checks=2)
 prior.save(out/'summary.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
