"""A matched inner body must not inherit its different caller's known callback."""
import json
from copy import deepcopy
from pathlib import Path
import tempfile
from bodies import extract,make,apply,PREFIX
from payloads import read,require


def run(native):
    raw=read(native);ops={x['id']:x['name'] for x in raw['snapshot']['operators']}
    corpus=['local-parameter','two-local-callers','captured-local-parameter']
    tested=[]
    for case in corpus:
        capture=next(c for c in raw['captures'] if c['case']==case)
        inner=capture['function']['inner_functions'][0]
        matches=[dict(bootstrap_code=1,metadata_disposition='UNRESOLVED',
            compiler_records=[dict(afunc=inner['function_id'],before={'event':1})])]
        event=dict(sequence=1,kind='before-pass2',payload=capture)
        with tempfile.TemporaryDirectory(prefix='ccl-body-control-') as work:
            path=Path(work)/'native.jsonl';path.write_text(json.dumps(event)+'\n')
            functions,calls=extract(path,matches,ops)
        base=dict(nodes=[{'id':'identity:build:code:1'}],edges=[
            {'from':'identity:build:code:1','evidence':'binding-versions/body/1','resolution':'unresolved','targets':[]}])
        delta=make(base,matches,functions,calls);graph=apply(base,delta)
        # These native callers provide fixed #'1+ or #'1- arguments. That
        # proof is intentionally unavailable when reusing only the callee.
        edges=[e for e in delta['edges'] if e['evidence'].startswith('correlated-build/call/')]
        require(edges and all(e['resolution']=='unresolved' and not e['targets'] for e in edges),
                'BORROWED_PARENT_ARGUMENTS '+case)
        parent=PREFIX+'afunc:'+str(capture['function']['function_id'])
        require(all(n['id']!=parent for n in delta['nodes']),'UNRELATED_PARENT_ATTACHED '+case)
        require(graph['edges'][0]['resolution']=='complete','BODY_REFERENCE_NOT_CONNECTED')
        data=deepcopy(matches)
        data[0]['data_dependencies']=[dict(index=0,disposition='UNRESOLVED',callable=False)]
        augmented=make(base,data,functions,calls)
        retained=[n for n in augmented['nodes'] if n['id'].startswith(PREFIX+'data:')]
        require(len(retained)==1 and retained[0]['disposition']=='unresolved','BODY_DATA_GAP_ERASED')
        require([e for e in augmented['edges'] if e['evidence'].startswith('correlated-build/call/')]==edges,
                'DATA_SUBSTITUTION_CHANGED_COMPUTED_BOUND')
        for field,value,reason in [('candidate_only',True,'UNQUALIFIED_BODY_CANDIDATES')]:
            damaged=deepcopy(matches);damaged[0][field]=value
            try:make(base,damaged,functions,calls)
            except ValueError as e:require(str(e)==reason,'WRONG_BODY_CANDIDATE_REFUSAL')
            else:raise ValueError('POTENTIAL_BODY_PROMOTED')
        data[0]['data_dependencies'][0]['callable']=True
        try:make(base,data,functions,calls)
        except ValueError as e:require(str(e)=='BODY_DATA_DISPOSITION','WRONG_CALLABLE_REFUSAL')
        else:raise ValueError('CALLABLE_DOWNGRADED_TO_DATA')
        tested.append(case)
    return dict(status='PASS',native_caller_contexts_not_borrowed=tested)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('native',type=Path);print(run(p.parse_args().native))
