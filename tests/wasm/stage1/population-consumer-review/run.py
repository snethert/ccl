import argparse,hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];E=ROOT.parent/'ccl-evidence';P=E/'2026-09-21-stage1-population-consumers-r1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(args,log,**kw):
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=120,**kw)
def replace(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def derive():
 s=(ROOT/'tests/wasm/stage1/population-consumers/lower.lisp').read_text()
 s=replace(s," (labels ((api (x)"," (admit-population-consumer form)\n (labels ((api (x)")
 s=replace(s,'            ((and (member (car x) \'(flet labels)) (some (lambda (d) (api (car d))) (cadr x))) (error "population API shadow unsupported"))\n','')
 s=replace(s,'             (when (and (eq (car x) \'setf) (/= (length x) 3)) (error "multi-place population SETF unsupported"))\n','')
 return (HERE/'admit.lisp').read_text()+'\n'+s

def run(out):
 out.mkdir(parents=True,exist_ok=False)
 for n,h in read(P/'source-pins.json').items():assert sha(ROOT/n)==h,n
 for row in read(P/'packet.json')['files']:assert sha(P/row['path'])==row['sha256']
 save(out/'parent-binding.json',{n:sha(P/n) for n in ['packet.json','source-pins.json','verification.json']})
 lower=derive();(out/'lower.lisp').write_text(lower)
 kernel=E/'2026-09-12-native-census-r7/baseline/build/dx86cl64';image=E/'2026-09-16-stage1-1a-r2/native/baseline.image';inputs=read(P/'execution/inputs.json')
 for p in [kernel,image]:assert sha(p)==inputs[str(p)]
 controls=[]
 with tempfile.TemporaryDirectory(prefix='ccl-population-admission-') as d:
  w=Path(d);shutil.copy(kernel,w/'dx86cl64');(w/'dx86cl64').chmod(0o755);shutil.copy(image,w/'dx86cl64.image')
  def check(source,dest):
   command([w/'dx86cl64','--no-init','--batch','--load',HERE/'check.lisp'],dest.with_suffix('.log'),env={**os.environ,'POP_CASES':str(ROOT/'tests/wasm/stage1/population-consumers/consumers.lisp'),'POP_OLD':str(ROOT/'tests/wasm/stage1/population-consumers/lower.lisp'),'POP_NEW':str(source),'POP_REPORT':str(dest)})
  check(out/'lower.lisp',out/'execution.json')
  for name,a,b,why in [
   ('shadow','(when (api (car d))','(when nil','admission flet'),
   ('multi-place','(> (length x) 3)','nil','admission setf-first'),
   ('first-place-only',"(loop for (place value) on (cdr x) by #'cddr thereis (has-api place))",'(has-api (second x))','admission setf-second'),
   ('macro',"(member (car x) '(macrolet symbol-macrolet))",'nil','admission macrolet'),
   ('variable','(when (api x) (error','(when nil (error','admission parameter'),
   ('setter-reference',"((and (consp (second x)) (eq (car (second x)) 'setf) (api (second (second x))))",'(nil','admission setter-reference'),
   ('setter-arity','(unless (= (length x) 4)','(unless t','admission setter-arity'),
   ('pushnew-pop',"(member (car x) '(pushnew pop))",'nil','admission pushnew')]:
   f=out/(name+'.lisp');f.write_text(replace(lower,a,b))
   try:check(f,out/(name+'.json'))
   except subprocess.CalledProcessError:assert why in (out/(name+'.log')).read_text().lower(),name
   else:raise AssertionError(name+' escaped')
   controls.append(dict(name=name,diagnostic=why,status='REJECTED'))
 save(out/'controls.json',controls)
 result=read(out/'execution.json');save(out/'summary.json',dict(status='PASS',positive_forms=len(result['positive']),refusals=len(result['refusals']),controls=len(controls),scaffold_only=True,slot_credit=False))
 print(read(out/'summary.json'))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);run(p.parse_args().output.resolve())
