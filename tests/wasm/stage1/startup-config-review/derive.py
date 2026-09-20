"""Derive review corrections without changing the pinned R1 fixture sources."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[4]

def replace(s,old,new,count=1):
 assert s.count(old)==count,(old,s.count(old),count)
 return s.replace(old,new)

def tcr_check(s):
 old='[64,128,140,92,112,48].map(o=>get(TCR+o))'
 s=replace(s,old,'tcrWords.map(o=>get(TCR+o))',2)
 anchor=" const set=(n,x)=>{assert(n in fields);put(TCR+fields[n],x);};"
 s=replace(s,anchor,anchor+"\n assert.equal(read(dir,'tcr.json').size_bytes,256);assert.equal(fields.tsp,76);assert.equal(fields.csp,88);assert.equal(fields.mv_count,116);\n const tcrWords=Array.from({length:64},(_,i)=>4*i).filter(o=>o!==fields.mv_count);")
 s=replace(s,"'caller and allocation restored'","'TCR preservation'")
 s=replace(s,'  const values=Array.from',"  assert.equal(get(TCR+fields.mv_count),pair[1],'TCR result count');\n  const values=Array.from")
 return s

def derive(out):
 src=ROOT/'tests/wasm/stage1/startup-config'
 shutil.copytree(src,out,ignore=shutil.ignore_patterns('__pycache__'))
 p=out/'compile.lisp';s=p.read_text()
 s=replace(s,'ccl::*spin-lock-tries* ccl::*spin-lock-timeouts*))','ccl::*spin-lock-tries* ccl::*spin-lock-timeouts* ccl::*cpu-count*))')
 s=replace(s,' (setq sources (nreverse sources))',' (setq sources (nreverse sources))\n (load (merge-pathnames "native-cpu.lisp" *load-pathname*))')
 s=replace(s,' ;; Each external read is replaced once; every other native form remains intact.',' ;; CPU-COUNT retains its source cache lookup/store; only its foreign acquisition is substituted.')
 s=replace(s,'(dolist (g *config-globals*)(set g sentinel))','(dolist (g *config-globals*)(set g sentinel))\n         (set \'ccl::*cpu-count* (if (= sentinel 37) nil (if (= cpu 1) 2 1)))')
 s=replace(s,'(replacement (nth i (list page ticks nil stack cpu)))','(replacement (nth i (list page ticks nil stack (cpu-with-owner-value cpu))))')
 old='(lambda (tries timeouts cpu done) (multiple-value-prog1 (progn (set tries (if (eq cpu 1) 1 1024))(set timeouts 0) timeouts)(rplaca done 105)))'
 new='(lambda (tries timeouts cpu cache done) (multiple-value-prog1 (let* ((known (symbol-value cache)) (count (if known known (set cache cpu)))) (set tries (if (eq count 1) 1 1024))(set timeouts 0) timeouts)(rplaca done 105)))'
 s=replace(s,old,new)
 s=replace(s,'s5 s6 s7 done','s5 s6 s7 s8 done',2)
 s=replace(s,'(symbol-value s6)(symbol-value s7))','(symbol-value s6)(symbol-value s7)(symbol-value s8))',2)
 p.write_text(s)
 p=out/'run.py';s=p.read_text()
 s=replace(s,"HERE.parent/'constants'","ROOT/'tests/wasm/stage1/constants'")
 s=replace(s,"shutil.copy(HERE/'compile.lisp',driver/'compile.lisp')","shutil.copy(HERE/'compile.lisp',driver/'compile.lisp')\n shutil.copy(HERE/'native-cpu.lisp',driver/'native-cpu.lisp')")
 s=replace(s,"g=[sentinel]*3+x['defaults']+[sentinel]*2;rows=[]","g=[sentinel]*3+x['defaults']+[sentinel]*2+['nil' if sentinel==37 else 2 if x['cpuCount']==1 else 1];rows=[]")
 s=replace(s,"step([(6,1 if x['cpuCount']==1 else 1024),(7,0)],'CCL::*SPIN-LOCK-TIMEOUTS*')","cpu=x['cpuCount'] if g[8]=='nil' else g[8]\n step([(6,1 if cpu==1 else 1024),(7,0),(8,cpu)],'CCL::*SPIN-LOCK-TIMEOUTS*')")
 p.write_text(s)
 p=out/'check.mjs';s=tcr_check(p.read_text())
 s=replace(s,'length:8','length:9',2);s=replace(s,'i<8','i<9');s=replace(s,'i===6?8:1','i===6?9:1')
 s=replace(s,'[6,7],[]]','[6,7,8],[]]')
 s=replace(s,'...cfg.defaults,sentinel,sentinel]','...cfg.defaults,sentinel,sentinel,sentinel===37?\'nil\':cfg.cpuCount===1?2:1]')
 s=replace(s,'const state=initial.slice(),steps=[];','const state=initial.slice(),steps=[],cpu=initial[8]===\'nil\'?cfg.cpuCount:initial[8];')
 s=replace(s,'[[6,cfg.cpuCount===1?1:1024],[7,0]]','[[6,cpu===1?1:1024],[7,0],[8,cpu]]')
 s=replace(s,'[symbol(6),symbol(7),encode(cfg.cpuCount),done]','[symbol(6),symbol(7),encode(cfg.cpuCount),symbol(8),done]')
 p.write_text(s)
 p=out/'assess.py';s=p.read_text();s=replace(s,"+[row['sentinel']]*2,'preflight'","+[row['sentinel']]*2+['nil' if ri==0 else 2 if cases[ci]['input']['cpuCount']==1 else 1],'preflight'")
 s=replace(s,'native_source_comparisons=1440','distinct_native_answers=360,native_source_comparisons=1440')
 p.write_text(s)
 # Native CPU dependency is read at a pinned byte position, never synthesized
 # from the proposed target emitter's cache implementation.
 b=(ROOT/'level-1/linux-files.lisp').read_bytes();pos=b.index(b'(defun cpu-count ()')
 cpu=(Path(__file__).parent/'native-cpu.lisp').read_text().replace('CPU_SOURCE_POSITION',str(pos));(out/'native-cpu.lisp').write_text(cpu)
 return out
