#!/usr/bin/env python3
"""Export saved wrapper contents and qualify a bounded census graph update."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import gc
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time
from join import validate_capture,project,apply,canonical
from check import expected,check,check_graph
from test_controls import run as controls

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    with gzip.open(p,'rt') if p.suffix=='.gz' else p.open() as f:return json.load(f)
def save(p,x):
    if p.suffix=='.gz':
        with p.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as f:f.write((canonical(x)+'\n').encode())
    else:p.write_text(json.dumps(x,indent=2)+'\n')
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def run(store,base_path,work,out):
    if platform.system()!='Darwin' or platform.machine()!='x86_64':raise ValueError('requires reference macOS x86-64')
    for a,b in ((store,work),(store,out),(work,out)):
        if a==b or a in b.parents or b in a.parents:raise ValueError('separate store/work/output required')
    work.mkdir(parents=True,exist_ok=False);out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();pins=read(HERE/'inputs.json')
    report={'version':1,'status':'FAIL','review_disposition':'NOT_REVIEWED','command':sys.argv,'input_pins':pins,'commands':[],
            'scope':'Post-boot saved-image inspection only. No new startup hooks, native recompilation, FASLs or saved implementation image.'}
    try:
        paths={k:store/v['path'] for k,v in pins['inputs'].items()}
        for k,p in paths.items():
            if digest(p)!=pins['inputs'][k]['sha256']:raise ValueError('changed direct input: '+k)
        wanted=read(paths['base_record'])['output_sha256']
        if digest(base_path)!=wanted:raise ValueError('base graph identity')
        report['base_graph']={'path':str(base_path),'sha256':wanted}
        sources=[HERE/n for n in ('run.py','join.py','check.py','test_controls.py','export.lisp','inputs.json')]
        sources += [HERE.parent/'boot-observation/export.lisp',HERE.parent/'observer.lisp',ROOT/'level-0/l0-def.lisp',
                    ROOT/'level-0/l0-symbol.lisp',ROOT/'compiler/nx0.lisp',ROOT/'xdump/xx8664-fasload.lisp',ROOT/'xdump/xfasload.lisp',ROOT/'compiler/X86/X8664/x8664-arch.lisp',
                    ROOT/'doc/WASM/tools/check-census.py',ROOT/'doc/WASM/contracts/census.schema.json',
                    ROOT/'doc/WASM/stage0/inventory.json',ROOT/'doc/WASM/stage0/baseline.json']
        report['source_sha256']={str(p.relative_to(ROOT)):digest(p) for p in sources}
        kernel=work/'dx86cl64';shutil.copyfile(paths['kernel'],kernel);kernel.chmod(0o755)
        image=work/'image'
        with gzip.open(paths['image'],'rb') as s,image.open('wb') as d:shutil.copyfileobj(s,d)
        image_before=digest(image);legacy_bytes=gzip.decompress(paths['legacy_events'].read_bytes())
        native=[]
        for mode in ('legacy','extended','repeat'):
            stream=work/(mode+'.jsonl');sidecar=out/'wrappers.json' if mode=='extended' else work/(mode+'-wrappers.json')
            env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin','LANG':'C','LC_ALL':'C','CCL_DEFAULT_DIRECTORY':str(work),
                 'CCL_BOOT_CENSUS_OUTPUT':str(stream),'CCL_WRAPPER_OUTPUT':str(sidecar)}
            argv=[str(kernel),'--image-name',str(image),'--no-init','--batch']
            for p in (HERE.parent/'observer.lisp',HERE.parent/'boot-observation/export.lisp'):
                argv+=['--load',str(p)]
            if mode!='legacy':argv+=['--load',str(HERE/'export.lisp')]
            argv+=['--eval','(progn ('+('cl-user::export-boot-census' if mode=='legacy' else 'ccl-boot-wrappers::run')+') (ccl:quit))']
            row={'mode':mode,'argv':argv,'environment':env,'cwd':str(work),'timeout_seconds':60,'started':datetime.now(timezone.utc).isoformat()}
            try:
                with (out/(mode+'.log')).open('wb') as log:
                    child=subprocess.Popen(argv,env=env,cwd=work,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                    try:code=child.wait(timeout=60)
                    except BaseException:
                        try:os.killpg(child.pid,signal.SIGKILL)
                        except ProcessLookupError:pass
                        child.wait();raise
                row['exit_code']=code
                if code or stream.read_bytes()!=legacy_bytes:raise ValueError('native export changed legacy capture: '+mode)
                if mode!='legacy':
                    text=(out/(mode+'.log')).read_text()
                    for reason in ('WRAPPER-LAYOUT','WRAPPER-DISPATCH','WRAPPER-PAYLOAD'):
                        if 'NATIVE-CONTROL-REJECTED '+reason not in text:raise ValueError('native control missing: '+reason)
                    if mode=='repeat' and sidecar.read_bytes()!=(out/'wrappers.json').read_bytes():raise ValueError('wrapper re-export differs')
                native.append({'mode':mode,'status':'PASS','legacy_stream_sha256':hashlib.sha256(stream.read_bytes()).hexdigest(),
                               'wrapper_sha256':None if mode=='legacy' else digest(sidecar)})
            finally:report['commands'].append(row);save(out/'commands.json',report['commands'])
        if digest(image)!=image_before or digest(kernel)!=pins['inputs']['kernel']['sha256']:raise ValueError('native input changed')
        report['native']={'exports':native,'controls_rejected':3,'saved_image_unchanged':True,'wrapper_repeat_identical':True}
        print('PASS: legacy/default and extended exports preserve every old byte; wrapper export reproduces.',flush=True)
        gc.disable();legacy=read(paths['legacy_joins']);completion=json.loads(legacy_bytes.splitlines()[-1]);data=read(out/'wrappers.json')
        counts=validate_capture(data,legacy,completion['identities']);base=read(base_path)
        binding={'base_graph':wanted,'wrappers':digest(out/'wrappers.json'),'legacy_events':pins['inputs']['legacy_events']['sha256'],
                 'native_image':pins['inputs']['image']['sha256'],'source_inputs':report['source_sha256']}
        patch=project(base,data,binding);oracle=expected(base,data,binding);check(patch,oracle)
        graph=apply(base,patch);check_graph(base,graph,patch)
        tests=controls(data,legacy,completion['identities'],base,patch,oracle,graph)
        print('PASS: wrapper record bounds and '+str(tests['controls_rejected'])+' analysis controls; checking full census graph.',flush=True)
        contract=load('wrapper_census_contract',ROOT/'doc/WASM/tools/check-census.py');errors=contract.validate(graph)
        prefixes=('unresolved reachable edge from ','unimplemented reachable node ')
        unexpected=[e for e in errors if not e.startswith(prefixes)]
        if unexpected:raise ValueError('graph invariant: '+str(unexpected[:3]))
        base_counts=read(paths['base_run']) # producer's raw summary is separately located by its own pinned artifact
        # No rerun of the unchanged base validator: use the retained checked summary.
        prior_summary_path=paths['base_run'].parent/'summary.json'
        pin=next(r for r in base_counts['artifacts'] if r['path']=='summary.json')
        if digest(prior_summary_path)!=pin['sha256']:raise ValueError('base summary changed')
        prior_summary=read(prior_summary_path)
        errors_count={p.strip():sum(e.startswith(p) for e in errors) for p in prefixes}
        if (errors_count['unresolved reachable edge from']!=prior_summary['census_error_counts']['unresolved reachable edge from'] or
            errors_count['unimplemented reachable node']!=prior_summary['census_error_counts']['unimplemented reachable node']-counts['wrappers']):
            raise ValueError('unexpected change in closure obligations')
        save(out/'patch.json.gz',patch);save(out/'controls.json',tests)
        # Re-load the serialized patch and reapply it before the canonical graph
        # identity comparison. Full graph bytes remain disposable and reproducible.
        reloaded=read(out/'patch.json.gz');check(reloaded,oracle);rebuilt=apply(base,reloaded);check_graph(base,rebuilt,reloaded)
        materialized=work/'census.json.gz';save(materialized,rebuilt)
        if graph!=rebuilt:raise ValueError('materialization differs')
        summary={'version':1,'status':'WRAPPERS_JOINED_UNQUALIFIED','review_disposition':'NOT_REVIEWED',**counts,
                 'native_controls_rejected':3,'analysis_controls_rejected':tests['controls_rejected'],
                 'replaced_wrapper_nodes':counts['wrappers'],'added_nodes':len(patch['nodes']),'added_edges':len(patch['edges']),
                 'graph_nodes':len(graph['nodes']),'graph_edges':len(graph['edges']),
                 'legacy_exports_identical':True,'wrapper_repeat_identical':True,'schema_and_graph_invariants':'PASS',
                 'census_contract':'BLOCKED','census_error_counts':errors_count,
                 'stage0_gate':{'accepted':28,'missing':20,'unreviewed':0,'new_credit':0,'basis':'Accepted aggregate unchanged; gate not rerun.'}}
        save(out/'summary.json',summary)
        report.update(status='PASS',elapsed_seconds=round(time.monotonic()-started,3),
                      materialization={'path':str(materialized),'sha256':digest(materialized),'bytes':materialized.stat().st_size},
                      artifacts=[{'path':p.name,'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(out.iterdir()) if p.name!='run.json'])
        print(json.dumps(summary,indent=2))
    except BaseException as exc:report['error']=type(exc).__name__+': '+str(exc);raise
    finally:gc.enable();save(out/'run.json',report)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('evidence-root','base-graph','work','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run(a.evidence_root.resolve(),a.base_graph.resolve(),a.work.resolve(),a.output.resolve())
