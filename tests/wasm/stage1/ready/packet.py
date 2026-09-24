#!/usr/bin/env python3
"""Retain only new READY inputs/results; reference the existing compilation session."""
from pathlib import Path
import json
import shutil
import sys
import tarfile
from run import c,storage,run,summarize,HERE,local

def pack(root,dest,names):
    with tarfile.open(dest,'w:gz') as stream:
        for name in sorted(names):stream.add(root/name,arcname=name,recursive=False)

def corpus(out):
    from execute import bound_report
    report,_=bound_report(out/'base/execution-report.json')
    assert report['tier']=='full' and report['inherited_comparisons']==0
    return dict(status=report['status'],comparisons=report['fresh_comparisons'],
        cases=len(report['cases']),
        results_sha256=c.digest([{k:r[k] for k in ('id','results')} for r in report['cases']]),
        controls_sha256=c.digest([report['control_results'],report['extra_controls']]))

def native_identity(out,native):
    if (native/'proposal-identity.json').exists():
        identity=c.read(native/'proposal-identity.json')
        assert identity==c.inventory(out/'base/compiled/proposal/files'), 'native proposal identity'
        assert c.read(native/'results/run.json')['status']=='PASS'
        return dict(packet=None,native_rebuilt=True,source_identity=identity,
                    basis='Fresh native qualification of this complete proposal',
                    run_sha256=c.sha(native/'results/run.json'))
    identity=c.read(native/'native-proposal-identity.json')
    assert identity==c.inventory(out/'base/compiled/proposal/files'), 'native proposal identity'
    assert c.read(native/'native-run.json')['status']=='PASS'
    files=c.read(native/'packet.json')['files']
    names=('native-proposal-identity.json','native-run.json','native-results.tar.gz')
    c.verify_files(native,{name:files[name] for name in names})
    return dict(packet=native.name,packet_sha256=c.sha(native/'packet.json'),
                files={name:files[name] for name in names},
                source_identity=identity,native_rebuilt=False,
                basis='all proposed compiler and CCL source files byte-identical')

def retain(out,packet,native):
    for submitted,source in (('submitted/probes.lisp','startup.lisp'),
                             ('submitted/inputs.lisp','inputs.lisp'),
                             ('ready-worker.mjs','worker.mjs')):
        assert (out/'compiled'/submitted).read_bytes()==(HERE/source).read_bytes(), source
    assert (out/'base/driver/numeric-files.lisp').read_bytes()==(HERE/'numeric-files.lisp').read_bytes()
    for installed, source in (('ready-clos-methods.lisp','clos-methods.lisp'),('condition-methods.lisp','condition-methods.lisp'),('graph.lisp','graph.lisp')):
        assert (out/'base/driver'/installed).read_bytes()==(HERE/source).read_bytes()
    reuse=native_identity(out,native)
    summarize(out);packet.mkdir()
    c.save(packet/'full-corpus.json',corpus(out))
    pack(out/'base',packet/'full-execution.tar.gz',[
        'execution-report.json','execution-report.identity.json','execution-plan.json',
        'execution-environment.json','case-ids.json','compiled/native.json',
        'build-completion.json','compile.log','oracle.log','execution.log'])
    c.save(packet/'native-reuse.json',reuse)
    if reuse['native_rebuilt']:
        shutil.copyfile(native/'proposal-identity.json',packet/'native-proposal-identity.json')
        shutil.copyfile(native/'results/run.json',packet/'native-run.json')
        pack(native/'results',packet/'native-results.tar.gz',c.inventory(native/'results'))
    else:
        for name in ('native-proposal-identity.json','native-run.json'):
            shutil.copyfile(native/name,packet/name)
    backend=local('compiler').BACKEND
    for name in (backend,'level-0/WASM32/w32-lap.lisp','compiler/WASM32/wasm32-arch.lisp','level-0/l0-aprims.lisp','level-0/l0-misc.lisp'):
        target=packet/'proposal'/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(out/'base/compiled/proposal/files'/name,target)
    for name in ('runtime/collector.c','runtime/heap-image.mjs','collector.wasm'):
        dest=packet/'runtime-proposal'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(out/'compiled'/name,dest)
    for name in ('stream-controls.json','stream-shapes.json','registry-controls.json','lock-controls.json','lock-shapes.json','complex-controls.json','complex-shapes.json','summary.json','writer.json','reader.json','coverage.json','times.json','heap-keys.json',
                 'macro-calls.json','macro-controls.json','startup-support.json','closure.json','callbacks.json','replacements.json','admission-controls.json','census-controls.json','replacement-controls.json','guard-control.json','owner-controls.json','execution-reuse.json'):
        if (out/name).exists():shutil.copyfile(out/name,packet/name)
    compiled=out/'compiled'
    for name in ('ready-compile.json','probe-completion.json','class-image-code.json','class-image-code.sha256'):
        if (compiled/name).exists():shutil.copyfile(compiled/name,packet/name)
    c.save(packet/'build-identity.json',c.read(out/'base/build-invocation.json'))
    names=['probe-output/probe-modules.json','probe-output/probe-native.json','probe-output/probe-callers.json']
    names += ['probe-output/ready-modules.json','probe-output/ready-clos-methods.sexp']
    names += [str(p.relative_to(compiled)) for p in (compiled/'probe-output').glob('*.census-wat')]
    names += [str(p.relative_to(compiled)) for pattern in ('*.wat','*.wasm') for p in (compiled/'probe-output').glob(pattern)]
    names += ['compiled/symbols.json','compiled/pools.json']
    names += ['compiled/'+r['name']+'.wasm' for r in c.read(compiled/'probe-output/probe-modules.json')]
    pack(compiled,packet/'compiled-inputs.tar.gz',names)
    pack(out/'images',packet/'image.tar.gz',c.inventory(out/'images'))
    logs=[p.name for p in out.glob('*.log')]
    logs += [str(p.relative_to(out)) for p in c.files(out/'development')]
    if (compiled/'probe.log').exists():logs.append('compiled/probe.log')
    pack(out,packet/'logs.tar.gz',logs)
    pins={str(p.relative_to(c.ROOT)):c.sha(p) for directory in (HERE,HERE.parent/'class-image',HERE.parent/'bootstrap-validation') for p in c.files(directory)}
    pins.update({str(p.relative_to(c.ROOT)):c.sha(p) for p in (c.ROOT/'runtime/wasm32').glob('*.mjs')})
    for path in (HERE.parent/'startup-resets/selection.json',HERE.parent/'startup-runtime/classification.json',
                 c.ROOT/'doc/WASM/stage1/ready-decision.json',c.ROOT/backend,
                 c.ROOT/'runtime/wasm32/collector.c',c.ROOT/'level-0/l0-aprims.lisp',c.ROOT/'level-0/l0-misc.lisp',c.ROOT/'level-1/l1-processes.lisp',c.ROOT/'level-1/l1-streams.lisp',c.ROOT/'level-1/l1-io.lisp',c.ROOT/'compiler/WASM32/wasm32-arch.lisp',c.ROOT/'level-0/WASM32/w32-lap.lisp',c.ROOT/'level-0/l0-numbers.lisp',c.ROOT/'lib/sequences.lisp',c.ROOT/'lib/arrays-fry.lisp',
                 c.ROOT/'compiler/X86/X8632/x8632-vinsns.lisp',c.ROOT/'level-1/l1-aprims.lisp',
                 c.ROOT/'lib/numbers.lisp',c.ROOT/'level-0/l0-int.lisp',c.ROOT/'level-0/nfasload.lisp',c.ROOT/'lib/lists.lisp',
                 c.ROOT/'level-1/l1-typesys.lisp',c.ROOT/'level-1/l1-clos-boot.lisp'):
        pins[str(path.relative_to(c.ROOT))]=c.sha(path)
    c.save(packet/'pins.json',pins)
    shutil.copytree(HERE,packet/'source',ignore=shutil.ignore_patterns('__pycache__'))
    c.save(packet/'provenance.json',dict(parent=c.PARENT.name,parent_packet=c.sha(c.PARENT/'packet.json'),
       accepted_image='ce865269',image_acceptance_sha256=c.sha(c.ROOT/'doc/WASM/stage1/acceptance-class-image.json'),decision_sha256=c.sha(c.ROOT/'doc/WASM/stage1/ready-decision.json'),native_rebuild=reuse['native_rebuilt'],native_reuse=reuse['packet'],shared_source_changes=False,
       execution_during_retention=False,slot_credit=False))
    c.save(packet/'packet.json',dict(id='STAGE1-READY-JOIN-R12',files=c.inventory(packet),
                                   review_disposition='NOT_REVIEWED',slot_credit=False))
    c.verify_files(packet,c.read(packet/'packet.json')['files'])
    shutil.rmtree(out)

def verify(packet,out):
    c.verify_files(packet,c.read(packet/'packet.json')['files'])
    c.verify_files(c.ROOT,c.read(packet/'pins.json'))
    reuse=c.read(packet/'native-reuse.json')
    if reuse['packet']:
        parent=c.STORE/reuse['packet']
        assert c.sha(parent/'packet.json')==reuse['packet_sha256']
        c.verify_files(parent,reuse['files'])
    else:
        assert reuse['native_rebuilt'] and reuse['run_sha256']==c.sha(packet/'native-run.json')
        assert reuse['source_identity']==c.read(packet/'native-proposal-identity.json')
    result=run(out)
    assert corpus(out)==c.read(packet/'full-corpus.json')
    assert c.inventory(out/'base/compiled/proposal/files')==c.read(packet/'native-proposal-identity.json')
    assert c.read(packet/'native-run.json')['status']=='PASS'
    for name in (local('compiler').BACKEND,'level-0/WASM32/w32-lap.lisp','compiler/WASM32/wasm32-arch.lisp','level-0/l0-aprims.lisp','level-0/l0-misc.lisp'):
        assert (out/'base/compiled/proposal/files'/name).read_bytes()==(packet/'proposal'/name).read_bytes(),name
    for name in ('runtime/collector.c','runtime/heap-image.mjs','collector.wasm'):
        assert (out/'compiled'/name).read_bytes()==(packet/'runtime-proposal'/name).read_bytes(),name
    assert result==c.read(packet/'summary.json')
    assert c.read(out/'coverage.json')==c.read(packet/'coverage.json')
    for name in ('stream-controls.json','stream-shapes.json','registry-controls.json','lock-controls.json','lock-shapes.json','complex-controls.json','complex-shapes.json','macro-calls.json','macro-controls.json','startup-support.json','closure.json','callbacks.json','replacements.json','admission-controls.json','census-controls.json','replacement-controls.json','guard-control.json','owner-controls.json'):
        assert c.read(out/name)==c.read(packet/name),name
    return dict(status='PASS',execution_rebuilt=True,native_rebuilt=False,
                native_reuse='exact complete proposal-source identity',summary=result)

if __name__=='__main__':
    action,packet,out,*native=sys.argv[1:];packet,out=Path(packet),Path(out)
    with storage.lease([out]):
        result=retain(out,packet,Path(native[0])) if action=='retain' else verify(packet,out)
        print(json.dumps(result or {'status':'PASS','retained':str(packet)}))
