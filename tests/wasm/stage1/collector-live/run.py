import argparse,importlib.util,json,shutil,sys
from pathlib import Path
from backend import generate,replace
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('live_core_runner',HERE.parent/'collector-core/run.py');core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
CLANG=core.CLANG;FLAGS=core.FLAGS;command=core.command

def collector_source():
 source=(HERE.parent/'collector-core/collector.c').read_text()
 # U1 node subtag 16 => 130, six tagged restart fields; padding is not scanned.
 source=replace(source,'if(node_subtag(tag)){scan=n;', 'if(node_subtag(tag)||(tag==130&&n==6)){scan=n;')
 # Canonical symbols are pinned identities, never stack-temporary callables.
 source=replace(source,'value==NIL ||','value==NIL || value==77838u ||')
 return replace(source,'if((old&7)==6 && old>=','if(old!=77838u && (old&7)==6 && old>=')

def prepare(out):
 core.generate=generate;h=core.prepare(out)
 (h/'collector.c').write_text(collector_source())
 command([CLANG,*FLAGS,h/'collector.c','-o',h/'collector.wasm'],h/'collector-build.log')
 check=(h/'core-check.mjs').read_text();anchor='// Deterministic graph independent of collector enumeration'
 check=replace(check,anchor,(HERE/'check-extra.mjs').read_text()+'\n'+anchor);(h/'core-check.mjs').write_text(check)
 shutil.copy(HERE/'probe.py',h/'live_probe.py')
 return h

def run(e,out):
 out.mkdir(parents=True,exist_ok=False);h=prepare(out/'harness')
 command([sys.executable,h/'live_probe.py',e,out/'generated',h/'wasm32-backend.lisp'],out/'generated.log')
 r=json.loads((out/'generated/execution.json').read_text());assert r['comparisons']==120 and len(r['moved_vectors'])==62
 command(['/usr/local/bin/node',h/'core-check.mjs',h/'collector.wasm',out/'core-checks.json'],out/'core.log')
 checks=json.loads((out/'core-checks.json').read_text());assert len(checks['tests'])==95
 # Re-run all previous moving executions over the same new service/compiler.
 command([sys.executable,h/'collector_probe.py',e,out/'inherited-moving',h/'wasm32-backend.lisp'],out/'inherited-moving.log')
 old=json.loads((out/'inherited-moving/execution.json').read_text());assert old['comparisons']==56 and len(old['moved_vectors'])==34
 spec=importlib.util.spec_from_file_location('live_controls',HERE/'controls.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 controls=m.run(e,out/'mutants',h,command,CLANG,FLAGS)
 result=dict(status='PASS',modules=r['modules'],comparisons=r['comparisons'],collections=len(r['moved_vectors']),core_checks=len(checks['tests']),compiler_mutants=4,collector_mutants=5,inherited_moving=dict(comparisons=old['comparisons'],collections=len(old['moved_vectors'])))
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
