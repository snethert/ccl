"""Execute the source compiler, isolation, lexical-bound and layout controls."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from copy import deepcopy
from pathlib import Path
import re
import subprocess
from analysis import read, require
from check_probes import check_all
import reference
from run import HERE, digest, save, session


def retained(directory):
    data={k:read(directory/k/'capture.json.gz') for k in
          ('target','native','callbacks','guard','dump','failed_effect')}
    data['reference']=read(directory/'reference/reference.json')
    data['layout_probes']=read(directory/'layout/probes.json')
    reproduction={}
    for key in ('target','native','callbacks'):
        first=read(directory/key/'capture.json.gz');second=read(directory/(key+'-repeat')/'capture.json.gz')
        changes=[]
        a=deepcopy(first);b=deepcopy(second)
        require(len(a['forms'])==len(b['forms']),'PROBE_FORM_COUNT '+key)
        for index,(x,y) in enumerate(zip(a['forms'],b['forms'])):
            if x['name']!=y['name']:
                # These fields are bounded PRINT previews of FCOMP's second
                # operand, not semantic identities. Retain both originals.
                # Only printed-object addresses may differ, only here. The
                # complete graph, function identities, code, observations and
                # every other field must compare exactly; no FASL is rewritten.
                u=x['name'];v=y['name']
                require(isinstance(u,str) and isinstance(v,str) and '#<' in u and '#<' in v and
                        re.sub(r'#x[0-9A-Fa-f]+(?=>)','#xADDRESS',u)==re.sub(r'#x[0-9A-Fa-f]+(?=>)','#xADDRESS',v),
                        'PROBE_PREVIEW_DIFFERENCE '+key)
                changes.append(dict(form=index,first=u,second=v))
                x['name']=y['name']=None
        require(a==b,'PROBE_REPRODUCTION '+key)
        reproduction[key]=dict(raw_equal=first==second,diagnostic_preview_differences=changes,
                               all_other_fields_equal=True)
    results,controls=check_all(data);results['reproduction']=reproduction
    return results,controls


def run(store,work,directory):
    directory.mkdir(parents=True,exist_ok=False)
    cases=[(k,HERE/'corpus.lisp',m) for k,m in
           (('target','normal'),('target-repeat','normal'),('native','native'),('native-repeat','native'),
            ('guard','execute-guard'),('dump','dump'))]
    cases += [('callbacks',HERE/'callback-corpus.lisp','normal'),
              ('callbacks-repeat',HERE/'callback-corpus.lisp','normal'),
              ('failed_effect',HERE/'failure-corpus.lisp','continue')]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(session,store,work,directory/k,source,mode,90) for k,source,mode in cases]
        for f in futures:f.result()
    reference.run(directory/'native',directory/'reference')
    out=directory/'layout';out.mkdir()
    base=read(directory/'native/run.json');args=base['argv'][:]
    args[-1]='(progn (load '+json.dumps(str(HERE/'layout-probes.lisp'))+') (ccl-source-closure::layout-probes) (ccl:quit))'
    env=base['environment']|{'CCL_CLOSURE_OUTPUT':str(out/'probes.json')}
    record=dict(argv=args,environment=env,source_sha256=digest(HERE/'layout-probes.lisp'))
    (out/'source.lisp').write_bytes((HERE/'layout-probes.lisp').read_bytes())
    try:
        with (out/'command.log').open('wb') as log:
            p=subprocess.run(args,env=env,cwd=Path(args[0]).parent,stdout=log,stderr=subprocess.STDOUT,timeout=60)
        record['exit_code']=p.returncode;require(p.returncode==0,'LAYOUT_SESSION')
    finally:save(out/'run.json',record)
    results,controls=retained(directory)
    save(directory/'summary.json',results);save(directory/'controls.json',controls)
    print('PASS',len(controls),'controls; graph/code repetition with printed-address differences retained')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('evidence-root','work','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();run(a.evidence_root.resolve(),a.work.resolve(),a.output.resolve())
