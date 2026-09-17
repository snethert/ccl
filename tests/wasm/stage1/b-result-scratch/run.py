#!/usr/bin/env python3
import argparse,subprocess
from pathlib import Path
from support import HERE,compile_cases,read,save,sha,require
from mutants import mutations
from regressions import run as regressions

from replay import execute,run_mutant
from concurrent.futures import ProcessPoolExecutor

def run(evidence,native,qualification,out):
 require(not out.exists(),'NO_OVERWRITE');out.mkdir(parents=True)
 require(read(native/'run.json')['status']=='PASS' and read(qualification/'summary.json')['status']=='PASS','NATIVE_QUALIFICATION')
 require((native/'proposal/files/compiler/WASM32/wasm32-backend.lisp').read_bytes()==(HERE/'wasm32-backend.lisp').read_bytes(),'NATIVE_COMPILER_JOIN')
 save(out/'native-reference.json',{'native_report_sha256':sha(native/'run.json'),'qualification_sha256':sha(qualification/'summary.json')})
 compile_cases(evidence,out/'positive');code,command=execute(out/'positive',out/'execution.log',out/'execution.json');require(code==0,'POSITIVE_WASM '+str(out/'execution.log'))
 from copy_cost import run as copy_cost
 copy_cost(out/'positive',out/'copy-cost')
 regression=regressions(evidence,out/'positive',out/'regressions')
 from lazy_composition import run as lazy_composition
 composition=lazy_composition(out/'positive',out/'execution.json',out/'lazy-composition')
 from loader_controls import run as loader_controls
 loader=loader_controls(out/'positive',out/'loader-controls')
 from conditions import run as conditions
 condition=conditions(evidence,out/'conditions')
 from condition_lazy import run as condition_lazy
 condition_lazy(out/'conditions/compiled',out/'conditions/execution.json',out/'condition-lazy')
 from condition_controls import run as condition_controls
 condition_rejections=condition_controls(evidence,out/'condition-controls')
 from source_scope import run as source_scope
 scope_controls=source_scope(evidence,out/'source-scope')
 from result_demand import run as result_demand
 demand=result_demand(evidence,out/'result-demand')
 from storage_probes import run as storage_probes
 probes=storage_probes(evidence,out/'storage-probes')
 from storage_controls import run as storage_controls
 storage_controls_result=storage_controls(evidence,out/'storage-controls')
 commands=[command];controls=[];(out/'mutants').mkdir()
 tasks=[(name,text,str(evidence),str(out/'mutants')) for name,text in mutations((HERE/'wasm32-backend.lisp').read_text()).items()]
 with ProcessPoolExecutor(max_workers=3) as pool:
  for control,command in pool.map(run_mutant,tasks):controls.append(control);commands.append(command)
 save(out/'commands.json',commands);save(out/'controls.json',controls);target=read(out/'execution.json')
 summary={'status':'PASS','storage_probes':probes,'storage_controls':len(storage_controls_result),'small_scratch_modules':sum(r['small_scratch'] for r in read(out/'positive/root-contracts.json').values()),'source_scope_controls':len(scope_controls),'source_scope_refusals':len(__import__('conditions').SCOPE_REFUSALS),'result_demand_probe':demand,'condition_modules':condition['modules'],'condition_comparisons':condition['comparisons'],'condition_refusals':len(condition['condition_refusals']),'condition_mutants':len(condition_rejections),'condition_binding_inspections':condition['binding_inspections'],'condition_control_inspections':condition['control_inspections'],'storage_checks':target['storage_checks'],'modules':target['modules'],'native_cases':len(read(out/'positive/cases.json')),'comparisons':target['comparisons'],'static_refusals':len(read(out/'positive/refusals.json')),'mutants':len(controls),'tail_runs':len(target['tail_runs']),'tail_steps_per_run':100000,'tail_stack_bytes':2048,'tail_root_depth':2,'non_tail_checks':target['non_tail_checks'],'tail_checks':target['tail_checks'],'development_regressions':len(regression),'local_checks':target['local_checks'],'resource_refusals':target['resource_refusals'],'allocation_boundary_checks':target['allocation_boundary_checks'],'result_capacity_checks':target['result_capacity_checks'],'callable_checks':target['callable_checks'],'closure_checks':target['closure_checks'],'ownership_inspections':target['ownership_inspections'],'peak_root_frames':target['peak_root_frames'],'lazy_composition':composition['status'],'loader_controls':len(loader['positive']['checks']),'loader_mutants':len(loader['mutants']),'cleanup_entries':target['cleanup_entries'],'cleanup_resources':target['cleanup_resources'],'multiple_value_resources':target['multiple_value_resources'],'lexical_exit_checks':target['lexical_exit_checks'],'progv_checks':target['progv_checks'],'binding_inspections':target['binding_inspections'],'binding_checks':target['binding_checks'],'peak_bindings':target['peak_bindings'],'control_inspections':target['control_inspections'],'state_checks':target['state_checks'],'chain_checks':target['chain_checks'],'public_dispatches':target['public_dispatches'],'internal_entries':target['internal_entries'],'scope':'Per-callee four-word result-scratch proof with unchanged dynamic delivery. Unknown and larger result paths retain dynamic storage. Conditions and MVC semantics retained; no general primary-value truncation. No condition construction, implicit trap translation, debugger, restarts, GC or LL05/LL19 credit.'};save(out/'summary.json',summary);print('S1-B-RESULT-SCRATCH-PASS',summary)

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('evidence','native','qualification','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();run(a.evidence.resolve(),a.native.resolve(),a.qualification.resolve(),a.output.resolve())
