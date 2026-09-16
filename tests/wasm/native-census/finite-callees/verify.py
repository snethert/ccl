#!/usr/bin/env python3
"""Recompute every finite/unknown result and check the applied working graph."""
import argparse
from pathlib import Path
from run import ROOT,HERE,read,digest,require,replay,convert,native_checks,integrate,save


def verify(output,base,store):
    report=read(output/'summary.json')
    require(report['status']=='PASS' and report['census_status']=='BLOCKED' and report['gate_credit'] is False,'RUN_SCOPE')
    require(digest(base)==report['base_sha256'],'VERIFIER_BASE')
    require(digest(output/'census.json.gz')==report['graph_sha256'],'VERIFIER_GRAPH')
    for p in (output/'executed-sources').iterdir():
        if p.is_file():require(p.read_bytes()==(HERE/p.name).read_bytes(),'EXECUTED_SOURCE '+p.name)
    pins=read(HERE.parent/'builtin-slots/inputs.json')['inputs']
    values={}
    for name in ('calls','samples'):
        p=store/pins[name]['path'];require(digest(p)==pins[name]['sha256'],'VERIFIER_INPUT');values[name]=read(p)
    ops={int(k):v for k,v in next(iter(values['samples'].values()))['operators'].items()}
    proofs=read(output/'proofs.json.gz');calls={(c['function_id'],c['site_id']):c for c in values['calls']}
    replay(output/'selected-ir.jsonl.gz',proofs,calls,ops)
    native=native_checks(read(output/'native-probes.json'),convert)
    controls=read(output/'controls.json');require(all(controls[k]==v for k,v in native.items()),'VERIFIER_NATIVE')
    hist=store/'2026-09-14-binding-versions-r1/histories.json.gz'
    require(digest(hist)=='4054a5980aa83a5d22b2749f90683acab663ed3a405d9276cabd4053c544bd69','VERIFIER_HISTORIES')
    b=read(base);g=read(output/'census.json.gz');d=read(output/'delta.json.gz');hs=read(hist)
    integrate.check(b,g,d,proofs,hs)
    require(integrate.controls(b,g,d,proofs,hs)==controls['integration'],'VERIFIER_INTEGRATION')
    good=[r for r in proofs if r['status']=='FINITE_EXPRESSION'];remaining=[r for r in proofs if r['status']=='UNRESOLVED']
    require(len(proofs)==report['original_open_calls'] and len(good)==report['finite_expression_bounds'] and
            len(remaining)==report['remaining_computed_calls'] and read(output/'remaining-calls.json.gz')==remaining,
            'VERIFIER_PARTITION')
    result=dict(status='PASS',replayed_sites=len(proofs),finite_expressions=len(good),remaining=len(remaining),
                native_probes=native['native_probes'],controls_rejected=native['controls_rejected']+len(controls['integration']),
                graph_identical=True,publication=False)
    save(output/'verification.json',result);print(result)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--base',type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence');a=p.parse_args()
    verify(a.output.resolve(),a.base.resolve(),a.evidence.resolve())
