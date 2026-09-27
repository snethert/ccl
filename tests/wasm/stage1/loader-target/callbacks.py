"""Bind the 35 startup callbacks to native code, boot phases and target code."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import struct
import tarfile
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'loader'))
import comparison

EXCLUDED={
    'KERNEL-LOCKS':'Native mutex pointer revival is excluded; Wasm owns Lisp locks allocated by the file initializers.',
    '*FD-SET-SIZE*':'Native POSIX descriptor-set ABI is excluded.',
    '*MAX-OS-OPEN-FILES*':'Native process descriptor limit is excluded; namespace descriptors have their own bounded session.',
    '*LAST-RDTSC-TIME*':'x86 timestamp-counter state is excluded; monotonic time comes from the host service.',
    '*LISP-START-TIMEVAL*':'Native timeval pointer is excluded; elapsed time uses the Worker clock origin.',
    '*EVENT-DISPATCH-TASK*':'Periodic native event task is excluded by the scheduler-disabled profile.',
    'RESET-WINNERS':'NX compiler cache is excluded by A2.',
    'RESET-DB-FILES':'Native FFI interface databases are excluded.',
    '*STATIC-CONS-ADDRESS*':'Native static-cons address is excluded by the Wasm heap layout.',
    '*FREE-STATIC-CONS-ADDRESS*':'Native static-cons address is excluded by the Wasm heap layout.',
    'STARTUP-SHUTDOWN-PROCESSES':'Restoring saved native threads is excluded by the single-Worker profile.',
    '*IP-INTERFACES*':'Native POSIX network interface state is excluded.',
    'SPIN-COUNT':'Native inter-thread spin locks are excluded by the single-Worker profile.',
}


def functions(x):
    if isinstance(x,dict):
        if set(x)=={'function'}:yield x
        for value in x.values():yield from functions(value)
    elif isinstance(x,list):
        for value in x:yield from functions(value)


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def run(report, native, bundle_dirs):
    here=Path(__file__).resolve().parent
    selection=json.loads((here.parent/'startup-resets/selection.json').read_text())['callbacks']
    boot=json.loads(report.read_text())
    with gzip.open(native/'capture/joins.json.gz','rt') as stream:joins=json.load(stream)
    files={row['relative_path']:row for row in json.loads((native/'capture/files.json').read_text())['files']}
    readers={(r['file'],r['offset']):r for r in joins['readers']}
    events=boot['callbackEvents'];bundles={}
    for directory in bundle_dirs:
        manifest=json.loads((directory/'bundle-manifest.json').read_text())
        for row in manifest['files']:bundles[row['path']]=(directory,row)
    bundle_inputs={row['path']:row['sha256'] for row in boot['bundleInputs']}
    result=[];cache={};target_sets={}
    with tarfile.open(native/'baseline-fasls.tar.gz') as archive:
        for selected in selection:
            name=selected['name'];short=name.split('::')[-1];stem=Path(selected['source']).stem
            file=('l1-fasls/' if selected['source'].startswith('level-1/') or stem=='nx'
                  else 'library/' if stem=='sockets' else 'bin/')+stem+'.dx64fsl'
            if file not in cache:
                data=archive.extractfile(file).read()
                assert hashlib.sha256(data).hexdigest()==files[file]['sha256'], 'native observed FASL identity'
                decoder=comparison.base_comparator()['CompilerFasl'](data)
                cache[file]=(decoder,decoder.decode())
            decoder,roots=cache[file];found=[]
            for root in roots:
                for function in functions(root):
                    body=function['function'];constants=body['constants'];bits=constants[-1]
                    if not bits & (1<<29) and constants[-2]=={'symbol':name}:
                        span=decoder.spans[id(root)]
                        reader=readers.get((files[file]['file'],span[0]))
                        found.append(dict(code_sha256=hashlib.sha256(bytes.fromhex(body['code'])).hexdigest(),
                                          fasl_span=decoder.spans[id(function)],root_span=span,
                                          root_kind=next(iter(root)),reader=reader))
            assert len(found)==1,(name,'native body count',len(found))
            # INIT-LOGICAL-DIRECTORIES is a global function. Its direct call is
            # in a separate CATCH initializer, not the DEFUN's FASL record.
            if short=='INIT-LOGICAL-DIRECTORIES':
                candidates=[]
                for root in roots:
                    if 'call' not in root:continue
                    cs=root['call']['function']['constants']
                    if {'symbol':name} in cs and {'symbol':'KEYWORD::TOPLEVEL'} in cs:
                        candidates.append(readers[(files[file]['file'],decoder.spans[id(root)][0])])
                assert len(candidates)==1
                found[0]['reader']=candidates[0]
            entered=[e for e in events if e['name']==name and e['event']=='enter']
            returned=[e for e in events if e['name']==name and e['event']=='return']
            row=dict(name=name,group=selected['group'],registration_ordinal=selected['ordinal'],
                     native_snapshot_function=selected['function'],native_source=selected['source'],
                     native_source_position=selected['position'],native_fasl=file,
                     native_fasl_sha256=files[file]['sha256'],native_body=found[0])
            if short in EXCLUDED:
                assert not entered and not returned,(name,'excluded callback executed')
                row.update(disposition='EXCLUDED',reason=EXCLUDED[short])
            else:
                assert len(entered)==len(returned)==1,(name,'target callback events',len(entered),len(returned))
                a,b=entered[0],returned[0]
                assert a['code']==b['code'] and a['sequence']<b['sequence']
                assert all(e['group']==selected['group'] and e['ordinal']==selected['ordinal'] for e in (a,b))
                assert found[0]['reader'] and found[0]['reader'].get('return')
                directory,bundle=bundles[a['file']]
                assert bundle['sha256']==bundle_inputs[a['file']]
                if a['file'] not in target_sets:
                    data=(directory/bundle['bundle']).read_bytes()
                    assert hashlib.sha256(data).hexdigest()==bundle['sha256']
                    assert data[:8]==b'W32B\x01\x00\x00\x00'
                    size=struct.unpack_from('<I',data,8)[0]
                    target_sets[a['file']]=json.loads(data[16:16+size])['codeSet']
                code_manifest=target_sets[a['file']]
                code=next(r for r in code_manifest['modules'] if r['name']==a['module'])
                row.update(disposition='EXECUTED',phase='target FASL initializer',target_enter=a,target_return=b,
                           target_bundle_sha256=bundle['sha256'],target_code=code)
            result.append(row)
    assert len(result)==35
    native_order=[r['name'] for r in sorted((r for r in result if r['disposition']=='EXECUTED'),
                                          key=lambda r:r['native_body']['reader']['enter'])]
    assert [e['name'] for e in events if e['event']=='enter']==native_order, 'callback phase/order'
    return dict(status='PASS',boot_sha256=digest(report),selection_sha256=digest(here.parent/'startup-resets/selection.json'),
                native_joins_sha256=digest(native/'capture/joins.json.gz'),
                executed=sum(r['disposition']=='EXECUTED' for r in result),
                excluded=sum(r['disposition']=='EXCLUDED' for r in result),callbacks=result,
                scope='Native compiled callback body and enclosing observed FASL call are joined by exact encoded offsets; target entries and returns name installed code. Literal/global effects are retained in target_return. Thread, stack and logical-directory effects are asserted by the post-image witness. Native and Wasm machine code are different architectures; this is not code-byte equivalence.')


if __name__=='__main__':
    result=run(Path(sys.argv[1]),Path(sys.argv[2]),[Path(p) for p in sys.argv[4:]])
    Path(sys.argv[3]).write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],result['executed'],'executed,',result['excluded'],'excluded')
