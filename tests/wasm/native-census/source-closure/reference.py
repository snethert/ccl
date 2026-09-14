"""Compare output native code with a session having no observer wrappers."""
import argparse
import json
from pathlib import Path
import subprocess
from analysis import Graph, read, require
from run import digest, save, HERE


def compare(observed, reference):
    require(reference['observation_wrappers'] is False and reference['fasl_written'] is False,
            'REFERENCE_SCOPE')
    require(observed['output_opcodes']==reference['output_opcodes'],'REFERENCE_OUTPUT_RECORDS')
    outputs=Graph(observed['output_graph'],function_root=False)
    code={e['native_function_id']:e['code'] for r in observed['native_compilations'] for e in r['emissions']
          if e['native_function_id'] is not None}
    actual=[]
    for i,value in enumerate(outputs.items({'ref':outputs.root})):
        row=outputs.items(value)
        if row[0] in (4,35,37):
            fn=outputs.node(row[1]);require(fn and fn['id'] in code,'REFERENCE_FUNCTION_JOIN')
            actual.append(dict(index=i,opcode=row[0],name=fn['name'],code=code[fn['id']]))
    require(actual==reference['functions'],'REFERENCE_NATIVE_BYTES')
    return dict(functions=len(actual),bytes=sum(len(r['code'])//2 for r in actual),equal=True,
                scope='FCOMP output function code prefixes; no claim about arbitrary constant objects')


def run(observation, output):
    output.mkdir(parents=True,exist_ok=False)
    record=json.loads((observation/'run.json').read_text());args=record['argv'][:]
    args[-1]='(progn (load '+json.dumps(str(HERE/'reference.lisp'))+') (ccl-source-closure::reference) (ccl:quit))'
    env=record['environment']|{'CCL_CLOSURE_OUTPUT':str(output/'reference.json')}
    result=dict(status='FAIL',argv=args,environment=env,observation_sha256=digest(observation/'capture.json.gz'),
                source_sha256={n:digest(HERE/n) for n in ('reference.py','reference.lisp')})
    try:
        with (output/'command.log').open('wb') as log:
            p=subprocess.run(args,env=env,cwd=Path(args[0]).parent,stdout=log,stderr=subprocess.STDOUT,timeout=60)
        result['exit_code']=p.returncode;require(p.returncode==0,'REFERENCE_SESSION')
        report=compare(read(observation/'capture.json.gz'),read(output/'reference.json'))
        save(output/'comparison.json',report);result['status']='PASS'
        print(report)
    finally:save(output/'run.json',result)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('observation',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.observation.resolve(),a.output.resolve())
