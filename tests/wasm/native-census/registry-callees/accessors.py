"""Recognize native accessor code instantiated from the two U1 compiler templates.

The slot-id is a parameter. Its contents and the current values of the called
symbol cells remain separate obligations; no generic-function bound is inferred.
"""
from collections import Counter
from pathlib import Path
import hashlib
import sys
from payloads import capture,read,save,source_key,literal_regions,require
from bodies import extract

HERE=Path(__file__).resolve().parent


def prototypes(functions,emissions,before,source):
    sys.path.insert(0,str(HERE.parent/'rich-observation'))
    from build_patch import form_end
    path=source/'level-1/l1-clos-boot.lisp';text=path.read_text();result={}
    for kind,arity,callee in [('reader',1,'SLOT-ID-VALUE'),('writer',2,'SET-SLOT-ID-VALUE')]:
        anchor='(defvar *'+kind+'-method-function-proto*'
        require(text.count(anchor)==1,'ACCESSOR_SOURCE_ANCHOR')
        # CCL's source note includes the FUNCTION reader prefix.
        start=text.index("#'(lambda ",text.index(anchor));end=form_end(text,start+2)
        candidates=[f for f in functions.values() if f['id'] in emissions
            and source_key(f['source'])=='level-1/l1-clos-boot.lisp'
            and (f['source_start'],f['source_end'])==(start,end)
            and any(e['afunc'] in before for e in emissions[f['id']])]
        require(len(candidates)==1,'ACCESSOR_TEMPLATE_IDENTITY');f=candidates[0]
        literals,_=literal_regions(f)
        require(len(literals)==2 and literals[1].get('name')=={'symbol':callee,'package':'CCL'}
                and ((f['bits']>>8)&63)==arity,'ACCESSOR_TEMPLATE_LAYOUT')
        result[kind]=dict(function=f['id'],arity=arity,callee=literals[1],code_words=f['code_words'],
            code=f['payload_hex'][:16*f['code_words']],source_span=[start,end],
            source_sha256=hashlib.sha256(text.encode()).hexdigest(),
            compiler_records=[e for e in emissions[f['id']] if e['afunc'] in before])
    return result


def classify(fn,method,templates):
    for kind,t in templates.items():
        if fn['code_words']!=t['code_words'] or fn['payload_hex'][:16*fn['code_words']]!=t['code']:continue
        if fn['id']!=fn['prototype'] or fn['words']!=t['code_words']+4:continue
        if fn['bits']!=((1<<28)|(t['arity']<<8)):continue
        execution,metadata=literal_regions(fn)
        if len(execution)!=2 or len(metadata)!=1:continue
        slot=execution[0];name=metadata[0]
        if not isinstance(slot,dict) or slot.get('type')!={'symbol':'SLOT-ID','package':'CCL'} or type(slot.get('object')) is not int:continue
        if execution[1]!=t['callee']:continue
        if name!={'object':method,'type':{'symbol':'STANDARD-'+kind.upper()+'-METHOD','package':'CCL'}}:continue
        return dict(kind=kind,function=fn['id'],method=method,template=t['function'],slot_id=slot['object'],
            called_symbol=t['callee'],parameterized_literals=[0],
            runtime_cell_values='UNRESOLVED',generic_dispatch_bound=False)
    return None


def run(output,source,evidence):
    functions,emissions,_,_,_=capture(output/'registries.jsonl.gz')
    before={int(k):v for k,v in read(output/'compiler-index-v2.json.gz')['before'].items()}
    templates=prototypes(functions,emissions,before,source)
    selection=[dict(compiler_records=[dict(e,before=before[e['afunc']]) for e in t['compiler_records']])
               for t in templates.values()]
    sample=next(iter(read(evidence/'2026-09-14-build-flow-r1/samples.json.gz').values()))
    fs,calls=extract(output/'build.jsonl.gz',selection,{int(k):v for k,v in sample['operators'].items()})
    for t in templates.values():
        ids={e['afunc'] for e in t['compiler_records']};actual=[c for c in calls if c['function'] in ids]
        require(len(actual)==1 and actual[0]['dependency']['category']=='global-binding'
                and actual[0]['symbol']['id']==t['callee']['symbol'],'ACCESSOR_REAL_IR_CALL')
        t['call']=actual[0]
    operations=read(output/'registry-loader-replay.json.gz')['operations'];joined=[];remaining=[]
    for op in operations:
        if op['compiler_bodies']:continue
        value=classify(functions[op['function']],op['method'],templates)
        if value:joined.append(dict(value,entry=op['entry'],operation=op['operation']))
        else:remaining.append(op)
    result=dict(templates=templates,instances=joined,remaining=remaining)
    save(output/'accessor-template-joins.json.gz',result)
    summary=dict(template_kinds=len(templates),method_operations_joined=len(joined),
        distinct_functions=len({r['function'] for r in joined}),kinds=dict(Counter(r['kind'] for r in joined)),
        remaining_method_body_operations=len(remaining),generic_dispatch_bounds_closed=0)
    save(output/'accessor-template-summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=HERE.parents[4]/'ccl-evidence');a=p.parse_args();run(a.output,a.source,a.evidence)
