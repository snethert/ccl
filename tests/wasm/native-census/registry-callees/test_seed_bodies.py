"""Corrupt the native startup inputs at the identity and body boundaries."""
import argparse
from copy import deepcopy
from pathlib import Path
from payloads import read,save,require,rows
from seed_bodies import select,callback_bodies,special_bodies
from initial_marker_join import read_marker
from nested_bodies import pairs,qualify
HERE=Path(__file__).resolve().parent


def run(a):
    fs={r['id']:r for r in read(a.bodies/'functions.json.gz')};em={int(k):v for k,v in read(a.bodies/'emissions.json.gz').items()}
    before={int(k):v for k,v in read(a.bodies/'before.json.gz').items()};image=read(a.native/'observed/image.json')
    spec=read(HERE.parent/'startup-closure/seeds.json');selection=read(a.bodies/'selection.json')
    runtime=read(a.bodies/'runtime-inputs.json')[0];assembly=read(a.bodies/'assembly.json.gz');cp=read(a.bodies/'checkpoints.json.gz')
    captures={r['kind']:r for r in rows(a.native/'observed/registries.jsonl.gz') if r['kind'] in ('inspection-map','deferred-marker-read')}
    selection['mapping']={int(k):v for k,v in selection['mapping'].items()}
    require(select(image,spec,captures['inspection-map'],fs)==selection,'SEED_REPLAY_SELECTION')
    results=[]
    def refuses(name,fn,reason):
        try:fn()
        except ValueError as e:require(str(e).startswith(reason),'SEED_CONTROL_REASON '+name+' '+str(e))
        else:raise ValueError('SEED_CONTROL_ESCAPED '+name)
        results.append(dict(name=name,status='REJECTED'))
    bad=deepcopy(captures['inspection-map']);bad['entries'].pop()
    refuses('omit-inspected-function',lambda:select(image,spec,bad,fs),'SEED_OBJECT_MAPPING')
    bad=deepcopy(image);bad['kernel_entries']['builtins'][0]['function']=bad['kernel_entries']['builtins'][1]['function']
    refuses('substitute-builtin-slot',lambda:select(bad,spec,captures['inspection-map'],fs),'builtin function-cell identity differs')
    bad=deepcopy(spec);bad['entrypoints']=[r for r in bad['entrypoints'] if r['name']!='CCL::RESTORE-LISP-POINTERS']
    refuses('omit-restore-entry',lambda:select(image,bad,captures['inspection-map'],fs),'kernel source entry omitted')
    bad=deepcopy(captures['deferred-marker-read']);bad['symbol']=-1
    refuses('substitute-deferred-marker',lambda:read_marker(bad,fs,a.source),'INITIAL_MARKER_SYMBOL')
    bad=deepcopy(captures['deferred-marker-read']);bad['macro']['objects'][0]['elements'][0]={'integer':0}
    refuses('substitute-macro-role',lambda:read_marker(bad,fs,a.source),'INITIAL_MARKER_TAG')
    requested=set(selection['requested']);matched=read(a.bodies/'matches.json.gz')
    callback=next(m for m in matched if m.get('callback_witnesses'));code=callback['bootstrap_code']
    existing={m['bootstrap_code'] for m in matched}-{code};build=a.native/'observed/build.jsonl.gz'
    def cb(rt=runtime,functions=fs):return callback_bodies(rt,functions,em,before,build,requested,existing)
    require(len(cb())==1,'SEED_CALLBACK_POSITIVE')
    bad=deepcopy(runtime);entry=next(r for r in bad['callbacks'] if r['function']==code)
    entry['symbol']['objects'][0]['id']=-1;entry['symbol']['root']={'ref':-1}
    require(not cb(bad),'SEED_HOMONYM_ACCEPTED');results.append(dict(name='same-callback-name-other-symbol',status='REJECTED'))
    bad=deepcopy(fs)
    for i in callback['compiled_functions']:bad[i]['bits']^=1
    require(not cb(functions=bad),'SEED_CALLBACK_RUNTIME_FLAG_ACCEPTED');results.append(dict(name='changed-callback-arity-bit',status='REJECTED'))
    bad=deepcopy(fs)
    for i in callback['compiled_functions']:
        v=bytearray.fromhex(bad[i]['payload_hex']);v[5]^=1;bad[i]['payload_hex']=v.hex()
    require(not cb(functions=bad),'SEED_CALLBACK_CODE_ACCEPTED');results.append(dict(name='changed-callback-instruction',status='REJECTED'))
    candidates=read(a.bodies/'candidates.json.gz');child=callback['function_literal_correspondences'][0]['bootstrap_function']
    damaged=[m for m in candidates if m['bootstrap_code']!=child]
    rel,_=pairs(fs,damaged);qual=qualify(fs,damaged,rel)
    require(code not in {m['bootstrap_code'] for m in qual},'SEED_CALLBACK_NESTED_OMISSION')
    results.append(dict(name='missing-callback-inner-body',status='REJECTED'))
    remaining=requested-{m['bootstrap_code'] for m in matched}
    require(special_bodies(selection,fs,assembly,cp,runtime,remaining)==read(a.bodies/'special-bodies.json.gz'),'SEED_SPECIAL_REPLAY')
    bad=deepcopy(assembly)
    for d in bad:
        if d['name'] and d['name']['name']=='EQL':d['name']['id']=-1
    refuses('wrong-assembler-name-identity',lambda:special_bodies(selection,fs,bad,cp,runtime,remaining),'SEED_ASSEMBLY_BODY')
    gf=next(r for r in remaining if fs[r]['bits']&(1<<27));bad=deepcopy(fs)
    bad[gf]['literals'][2]={'object':-1,'type':fs[gf]['literals'][2]['type']}
    refuses('substituted-dispatch-table',lambda:special_bodies(selection,bad,assembly,cp,runtime,remaining),'SEED_GF_LITERAL_SLOTS')
    bad=deepcopy(fs);v=bytearray.fromhex(bad[gf]['payload_hex']);v[5]^=1;bad[gf]['payload_hex']=v.hex()
    refuses('changed-dispatch-instruction',lambda:special_bodies(selection,bad,assembly,cp,runtime,remaining),'SEED_GF_CODE_TEMPLATE')
    bad=deepcopy(selection);state=next(r for r in cp[0]['entries'] if r['gf']==gf)
    bad['requested'].remove(state['methods'][0]['function'])
    refuses('omit-dispatch-method-body',lambda:special_bodies(bad,fs,assembly,cp,runtime,remaining),'SEED_GF_METHOD_COVERAGE')
    save(a.output,dict(status='PASS',controls=results));print('PASS',len(results),'startup identity/body controls',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('native','bodies','source','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    try:run(a)
    except BaseException:
        import traceback
        a.output.with_suffix('.failure.txt').write_text(traceback.format_exc())
        a.output.with_suffix('.failed-source.py').write_bytes(Path(__file__).read_bytes())
        raise
