#!/usr/bin/env python3
"""Recheck a retained boot fragment and materialize the complete exchange graph."""
import argparse
import gc
from pathlib import Path
import sys
from join_identities import HERE, ROOT, read, save, digest
from join_boot import bind_inputs, load_base
from boot_join import apply_delta
from check_boot import expectations, check, check_materialized
from assemble import load_tool


def materialize(evidence, packet, output):
    output.mkdir(parents=True,exist_ok=False)
    report={'status':'FAIL','command':sys.argv}
    try:
        gc.disable();run=read(packet/'run.json')
        if run['status']!='PASS':raise ValueError('producer did not pass')
        pins=run['input_pins'];paths=bind_inputs(evidence,pins)
        record=next(r for r in run['artifacts'] if r['path']=='delta.json.gz')
        if digest(packet/'delta.json.gz')!=record['sha256']:raise ValueError('fragment bytes changed')
        dependencies={p:h for p,h in run['source_sha256'].items() if Path(p).name in
                      ('boot_join.py','check_boot.py','join_boot.py','join_identities.py','assemble.py','lowering_join.py','identity_join.py','exchange.py','effects.py')}
        for p,h in dependencies.items():
            if digest(ROOT/p)!=h:raise ValueError('materialization source changed: '+p)
        reader=load_tool('boot_materialization_reader',HERE.parent/'boot-observation/analyze.py')
        base=load_base(paths,pins);delta=read(packet/'delta.json.gz')
        expected=expectations(base,reader.read(paths['boot_events']),read(paths['boot_joins']),
                              read(paths['boot_files']),read(paths['origins']),{k:v['sha256'] for k,v in pins['inputs'].items()})
        check(delta,expected);graph=apply_delta(base,delta);check_materialized(base,graph,delta)
        target=output/'census.json.gz';save(target,graph);actual=digest(target)
        original=run.get('materialization',{}).get('sha256')
        if original is not None and actual!=original:raise ValueError('full graph differs from producer materialization')
        report.update(status='PASS',nodes=len(graph['nodes']),edges=len(graph['edges']),
                      output_sha256=actual,output_bytes=target.stat().st_size,
                      producer_graph_identical=None if original is None else True,
                      fragment_sha256=record['sha256'],input_pins=pins,
                      source_sha256={**dependencies,str(Path(__file__).resolve().relative_to(ROOT)):digest(Path(__file__))},
                      retention='Full graph is reproducible from pinned base and fragment; retain only this verification record in the packet.')
        print('PASS: full exchange graph materialized and checked; producer identity '+str(report['producer_graph_identical']),flush=True)
    except BaseException as exc:
        report['error']=type(exc).__name__+': '+str(exc);raise
    finally:
        gc.enable();save(output/'materialization.json',report)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('evidence-root','packet','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();materialize(a.evidence_root.resolve(),a.packet.resolve(),a.output.resolve())
