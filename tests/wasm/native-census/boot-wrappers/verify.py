#!/usr/bin/env python3
"""Reconstruct a retained wrapper graph update without another native export."""
import argparse
import gc
import gzip
import json
from pathlib import Path
from run import HERE,ROOT,read,save,digest
from join import validate_capture,project,apply
from check import expected,check,check_graph


def verify(store,base_path,packet,out):
    out.mkdir(parents=True,exist_ok=False);report={'status':'FAIL'}
    try:
        gc.disable();run=read(packet/'run.json')
        if run['status']!='PASS':raise ValueError('producer did not pass')
        if digest(base_path)!=run['base_graph']['sha256']:raise ValueError('base graph changed')
        for name in ('wrappers.json','patch.json.gz'):
            row=next(r for r in run['artifacts'] if r['path']==name)
            if digest(packet/name)!=row['sha256']:raise ValueError('retained artifact changed: '+name)
        pin=run['input_pins']['inputs']['legacy_joins'];legacy_path=store/pin['path']
        if digest(legacy_path)!=pin['sha256']:raise ValueError('legacy joins changed')
        dependencies={p:h for p,h in run['source_sha256'].items() if Path(p).name in ('join.py','check.py','run.py')}
        for p,h in dependencies.items():
            if digest(ROOT/p)!=h:raise ValueError('materialization source changed: '+p)
        base=read(base_path);data=read(packet/'wrappers.json');patch=read(packet/'patch.json.gz')
        # The native producer verified the old stream byte-for-byte. The bound
        # retained patch records that same stream/image and the expanded bytes.
        binding={'base_graph':run['base_graph']['sha256'],'wrappers':digest(packet/'wrappers.json'),
                 'legacy_events':run['input_pins']['inputs']['legacy_events']['sha256'],
                 'native_image':run['input_pins']['inputs']['image']['sha256'],'source_inputs':run['source_sha256']}
        if patch['input_binding']!=binding:raise ValueError('capture binding changed')
        stream_pin=run['input_pins']['inputs']['legacy_events'];stream_path=store/stream_pin['path']
        if digest(stream_path)!=stream_pin['sha256']:raise ValueError('legacy stream changed')
        with gzip.open(stream_path,'rt') as stream:
            for line in stream: last=line
        completion=json.loads(last)
        if completion['kind']!='complete':raise ValueError('legacy completion missing')
        validate_capture(data,read(legacy_path),completion['identities'])
        reproduced=project(base,data,binding)
        if reproduced!=patch:raise ValueError('patch reproduction differs')
        check(patch,expected(base,data,binding));graph=apply(base,patch);check_graph(base,graph,patch)
        target=out/'census.json.gz';save(target,graph);identity=digest(target)
        if identity!=run['materialization']['sha256']:raise ValueError('materialized graph differs')
        report.update(status='PASS',patch_reproduced=True,graph_identical=True,output_sha256=identity,
                      graph_nodes=len(graph['nodes']),graph_edges=len(graph['edges']),
                      source_sha256={**dependencies,str(Path(__file__).resolve().relative_to(ROOT)):digest(Path(__file__))},
                      inputs={'base_graph':run['base_graph']['sha256'],'patch':digest(packet/'patch.json.gz'),
                              'wrappers':digest(packet/'wrappers.json'),'legacy_joins':pin['sha256'],
                              'legacy_events':stream_pin['sha256']},
                      retention='Retain this verification record; full graph is reproducible and not duplicated in the evidence packet.')
        print('PASS: retained patch and full wrapper graph reproduce byte-for-byte.',flush=True)
    except BaseException as exc:report['error']=type(exc).__name__+': '+str(exc);raise
    finally:gc.enable();save(out/'verification.json',report)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('evidence-root','base-graph','packet','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();verify(a.evidence_root.resolve(),a.base_graph.resolve(),a.packet.resolve(),a.output.resolve())
