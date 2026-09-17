"""Executed cost witness, not a timing benchmark or a production optimization.

Count entry modes, descriptor creation, arena allocations and release visits in
an observation-only WAT derivative. Compare with unmodified binaries and native
CCL. A scalar-mode-off mutation demonstrates why a boolean toggle is unsound.
"""
from pathlib import Path
import shutil, subprocess
from support import HERE, require, read, save
from source_scope import compile_probe

SOURCES = {
    'h_signal': '(lambda (x) (signal x))',
    'd_one': '(lambda (x) x)',
    'd_many': '(lambda (p) (rplaca p 101) (values p ' + ' '.join(map(str, range(1,130))) + '))',
    'd_take': '(lambda ('+' '.join('x'+str(i) for i in range(130))+') (values (car x0) x129))',
    'd_scalar': '(lambda (p) (multiple-value-call (function d_one) (values (d_one (d_one (car p))))))',
    'd_first': '(lambda (p) (multiple-value-call (function d_one) (values (car (d_many p)))))',
    'd_discard': '(lambda (p) (multiple-value-call (function d_one) (progn (d_many p) (values 7))))',
    'd_cleanup': '(lambda (p) (multiple-value-call (function d_one) (unwind-protect (values 7) (d_many p))))',
    'd_full': '(lambda (p) (multiple-value-call (function d_take) (d_many p)))',
    'd_local_full': '(lambda (p) (multiple-value-call (function d_one) (values (multiple-value-bind (a b c d e) (d_many p) e))))',
}
CASES = [dict(id=name, function=name, args=['n0'], nodes=[[3,5]], bindings={}, capacity=4,
              expected=dict(status='RETURN', values=value, nodes=[[3 if name=='d_scalar' else 101,5]], specials=[101,103,'unbound']))
         for name,value in [('d_scalar',[3]),('d_first',[101]),('d_discard',[7]),('d_cleanup',[7]),('d_full',[101,129]),('d_local_full',[4])]]


def execute(compiled, script, output):
    argv=['/usr/local/bin/node',str(script),str(compiled),str(output)]
    save(output.with_suffix('.command.json'),argv)
    with output.with_suffix('.log').open('w') as log:
        result=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    return result.returncode


def instrument(compiled, out):
    out.mkdir();(out/'installed').mkdir()
    for name in ('modules.json','cases.json','root-contracts.json'):
        shutil.copy(compiled/name,out/name)
    for p in (compiled/'installed').glob('*.wasm'):
        if p.stem.startswith('observe_'):
            shutil.copy(p,out/'installed'/p.name);continue
        wat=(compiled/(p.stem+'.wat')).read_text()
        def replace(old,new):
            nonlocal wat
            require(wat.count(old)==1,'DEMAND_OBSERVER_SITE '+old)
            wat=wat.replace(old,new)
        replace('(import "env" "memory"','(import "demandprobe" "event" (func $demand_event (param i32 i32))) (import "env" "memory"')
        site='(local.set $dynamic_results (i32.const 0))' if read(compiled/'root-contracts.json')[p.stem]['small_scratch'] else '(local.set $dynamic_results (i32.load offset=20 (local.get $context)))'
        replace(site,site+' (call $demand_event (i32.const 0) (local.get $dynamic_results)) (call $demand_event (i32.const 5) (i32.load offset=20 (local.get $context)))')
        site='(local.set $result_descriptor (local.get $top))'
        require(wat.count(site)==2,'MAIN_AND_ERROR_DESCRIPTOR_SITES')
        wat=wat.replace(site,site+' (call $demand_event (i32.const 1) (i32.const 48))')
        for fn,stage in [('rv_alloc',2),('rv_release',3)]:
            a=wat.index('(func $'+fn+' ');b=wat.index('(call $rv_check)',a)
            wat=wat[:b]+'(call $demand_event (i32.const '+str(stage)+') (i32.const 1)) '+wat[b:]
        a=wat.index('(func $rv_release ');b=wat.index('(local.set $size (call $rv_block_size',a)
        wat=wat[:b]+'(call $demand_event (i32.const 4) (i32.const 1)) '+wat[b:]
        source=out/(p.stem+'.wat');source.write_text(wat)
        subprocess.run(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions','--enable-tail-call',str(source),'-o',str(out/'installed'/p.name)],check=True,capture_output=True)
    script=(HERE/'conditions.mjs').read_text()
    script=script.replace('const conditionRefusals=[];', 'let demandEvents=[];const demandRows=[];const conditionRefusals=[];')
    old='{env:{memory,tcr,table,tail_table,code_registry:4096,call_error,type_error,nonlocal_exit},symbols,keywords,codes}'
    require(script.count(old)==1,'DEMAND_IMPORT')
    script=script.replace(old,'{demandprobe:{event:(stage,value)=>demandEvents.push({module:m.name,stage,value})},env:{memory,tcr,table,tail_table,code_registry:4096,call_error,type_error,nonlocal_exit},symbols,keywords,codes}')
    script=script.replace('for(const c of cases){','for(const c of cases){demandEvents=[];')
    script=script.replace("inspect('returned '+c.id);", "inspect('returned '+c.id);demandRows.push({id:c.id,start,observed,events:demandEvents});")
    script=script.replace("parentPort.postMessage({status:'PASS',", "parentPort.postMessage({status:'PASS',demandRows,")
    (out/'observe.mjs').write_text(script)


def run(evidence,out):
    require(not out.exists(),'NO_OVERWRITE');out.mkdir()
    compile_probe(evidence,out/'compiled',None,SOURCES,CASES,[])
    require(execute(out/'compiled',HERE/'conditions.mjs',out/'ordinary.json')==0,'DEMAND_ORDINARY')
    instrument(out/'compiled',out/'observed')
    require(execute(out/'observed',out/'observed/observe.mjs',out/'observed.json')==0,'DEMAND_OBSERVED')
    observed=read(out/'observed.json');rows=observed.pop('demandRows')
    require(observed==read(out/'ordinary.json'),'OBSERVER_PRESERVES_RESULTS')
    totals=[]
    for name in [c['id'] for c in CASES]:
        variants=[r for r in rows if r['id']==name];require(len(variants)==4,'DEMAND_VARIANTS')
        require(all(r['events']==variants[0]['events'] for r in variants),'DEMAND_REPEATABILITY')
        events=variants[0]['events']
        total=dict(id=name,entries=sum(e['stage']==0 for e in events),
                   dynamic_entries=sum(e['stage']==0 and e['value']==1 for e in events),
                   dynamic_recipients=sum(e['stage']==5 and e['value']==1 for e in events),
                   callee_descriptors=sum(e['stage']==1 for e in events),
                   arena_allocations=sum(e['stage']==2 for e in events),
                   releases=sum(e['stage']==3 for e in events),
                   release_block_visits=sum(e['stage']==4 for e in events))
        totals.append(total)
    require(totals[0]['arena_allocations']==0 and totals[0]['callee_descriptors']==0 and totals[0]['dynamic_entries']==0 and totals[0]['dynamic_recipients']==2 and totals[0]['releases']==1,'PROVEN_SMALL_STORAGE')
    require(all(t['arena_allocations']>0 for t in totals[1:]),'LARGE_INTERMEDIATE_RESULTS')
    # Deliberately wrong fix: disable dynamic mode in the many-valued callee
    # used at the scalar d_first site. Keep all other paths and the caller intact.
    shutil.copytree(out/'compiled', out/'mutant')
    module=out/'mutant/d_many.wat'
    wat=module.read_text()
    old='(local.set $dynamic_results (i32.load offset=20 (local.get $context)))'
    require(wat.count(old)==1,'CALLEE_TOGGLE_SITE')
    module.write_text(wat.replace(old,'(local.set $dynamic_results (i32.const 0))'))
    subprocess.run(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions','--enable-tail-call',str(module),'-o',str(out/'mutant/installed/d_many.wasm')],check=True,capture_output=True)
    code=execute(out/'mutant',HERE/'conditions.mjs',out/'mutant.json')
    log=(out/'mutant.log').read_text()
    require(code!=0 and 'AssertionError' in log and 'd_first' in log,'SCALAR_TOGGLE_REJECTED')
    summary=dict(status='PASS',comparisons=len(CASES)*4,counts=totals,
                 scalar_mode_off='REJECTED at d_first: 130-value callee in scalar operand position',
                 scope='Executed operation counts only. Proven-small callees retain dynamic delivery but use fixed scratch without a descriptor or release. Unproven/large callees retain dynamic storage; no general primary-value truncation or timing claim.')
    save(out/'summary.json',summary)
    return summary

if __name__=='__main__':
    import sys
    print(run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
