#!/usr/bin/env python3
import json,subprocess,sys
from pathlib import Path
from pool import compile_pool
HERE=Path(__file__).resolve().parent

def canonical(graph,roots):
    source={r['id']:r['value'] for r in graph['objects']};ids={};queue=[]
    def val(v):
        if 'ref' not in v:return v
        n=v['ref']
        if n not in ids:ids[n]=len(queue);queue.append(n)
        return {'ref':ids[n]}
    result={'roots':[val(v) for v in roots],'objects':[]}
    for n in queue:
        node=source[n].copy()
        if node['kind']=='cons':node.update(car=val(node['car']),cdr=val(node['cdr']))
        if node['kind']=='general-vector':node['elements']=[val(x) for x in node['elements']]
        result['objects'].append(node)
    return result

def run(out):
    read=lambda n:json.loads((out/n).read_text())
    symbols={'WASM32-COMPILER::POOL-OWNER':620006,'WASM32-COMPILER::pool-owner':620038}
    p=compile_pool(read('pools.json'),symbols);m=p.at(1048576)
    (out/'materialized.json').write_text(json.dumps({'base':m.base,'image':m.image.hex(),'roots':m.roots,'objects':[{'id':i,'offset':o,'tag':t} for i,o,t in p.objects],'symbols':symbols}))
    native=read('native.json');nodes={r['id']:r['value'] for r in native['objects']}
    tops=[x for x in read('modules.json') if x['top']]
    if len(tops)!=len(native['roots']):raise ValueError('native corpus count')
    expected={m['name']:canonical(native,nodes[v['ref']]['elements']) for m,v in zip(tops,native['roots'])}
    (out/'expected.json').write_text(json.dumps(expected))
    subprocess.run(['/usr/local/bin/wat2wasm','--enable-tail-call',str(HERE/'stub.wat'),'-o',str(out/'lazy-stub.wasm')],check=True,capture_output=True)
    r=subprocess.run(['/usr/local/bin/node',str(HERE/'execute_compiled.mjs'),str(out)],capture_output=True,text=True)
    (out/'execution.log').write_text(r.stdout+r.stderr)
    if r.returncode:raise RuntimeError(str(out/'execution.log'))
    (out/'execution.json').write_text(r.stdout);print(r.stdout)
if __name__=='__main__':run(Path(sys.argv[1]).resolve())
