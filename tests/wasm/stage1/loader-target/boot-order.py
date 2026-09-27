"""Join actual target load events to the retained native cold-start order."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

# These are the native-root load exclusions in LEVEL-1/L1-BOOT-2, with the
# profile decision that justifies each. Their nested REQUIRE loads are omitted
# with the parent, rather than accidentally counted as independent runtime loads.
EXCLUDED={
    **dict.fromkeys(('x86-callback-support','x86-trap-support','x86-error-signal'),
                    'Native assembly signal/callback entries; Wasm uses checked services.'),
    **dict.fromkeys(('x86-threads-utils',), 'Single Worker; native thread machinery excluded.'),
    **dict.fromkeys(('l1-sockets','ffi-darwinx8664','db-io','sockets'),
                    'Native FFI/POSIX profile excluded.'),
    **dict.fromkeys(('subprims','x8632-arch','x8664-arch','vreg','vinsn','reg',
                    'backend','nx2','acode-rewrite','x862','optimizers','nfcomp','compile-ccl'),
                    'Decision A2: in-image compiler deferred.'),
    **dict.fromkeys(('backtrace-lds','backtrace','x86-disassemble','x86-lapmacros',
                    'x86-watch','edit-callers'), 'Native frame/code inspector deferred.'),
    'dumplisp':'Native image saving is outside the read-only READY profile.',
    'remote-lisp':'Remote native process transport is outside the single-Worker profile.',
}


def run(report, trace, partial=False):
    boot=json.loads(report.read_text());stack=[];rows=[];expected=[];returns=[]
    with gzip.open(trace,'rt') as stream:
        for line in stream:
            event=json.loads(line);kind=event['kind']
            if kind=='load-enter':
                file=event['payload']['file'];stem=Path(file).name.removesuffix('.dx64fsl')
                reason=next((r['descendant_exclusion'] for r in reversed(stack)
                             if r['descendant_exclusion']),None) or EXCLUDED.get(stem)
                path=None
                if reason is None:
                    if stem=='l1-error-system':
                        expected.append('/ccl/l1-fasls/w32-streams.w32fsl')
                    target={'linux-files':'w32-files','nx':'lambda-list'}.get(stem,stem)
                    directory='l1-fasls/' if '/l1-fasls/' in file and stem!='nx' else 'bin/'
                    if stem=='level-1':directory=''
                    path='/ccl/'+directory+target+'.w32fsl';expected.append(path)
                row=dict(native_sequence=event['sequence'],native_file=file,target=path,
                         disposition=reason or ('NX runtime metadata subset' if stem=='nx' else
                         'Wasm file service' if stem=='linux-files' else 'Retained load'),
                         descendant_exclusion=reason or ('NX compiler dependency' if stem=='nx' else None))
                rows.append(row);stack.append(row)
            elif kind=='load-return':
                row=stack.pop();assert row['native_file']==event['payload']['file']
                row['native_return']=event['sequence']
                if row['target']:returns.append(row['target'])
    # The retained native trace exits before the outer LEVEL-1 load returns.
    assert len(stack)==1 and stack[0]['native_file']=='level-1.dx64fsl'
    actual=[r['path'] for r in boot['loadEvents'] if r['event']=='open']
    startup=boot.get('startupLoads', ['/ccl/bin/loader-postimage.w32fsl'])
    complete=expected+startup
    assert actual==(complete[:len(actual)] if partial else complete), (
        'native/target load order',next(((i,a,b) for i,(a,b) in enumerate(zip(actual,complete)) if a!=b),
                                       ('length',len(actual),len(complete))))
    if not partial:
        assert boot['ready'] and boot['errorServiceMode']==1
        assert all(path in {r['path'] for r in boot['loadEvents'] if r['event']=='close'}
                   for path in returns+['/ccl/l1-fasls/w32-streams.w32fsl']+startup)
    return dict(status='PASS',scope='prefix only' if partial else 'complete READY load order',
                native_trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),
                boot_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),
                native_loads=len(rows),profile_loads=len(expected),actual_loads=len(actual),
                expected=complete,actual=actual,native_join=rows,
                additions=[dict(path='/ccl/l1-fasls/w32-streams.w32fsl',
                                before='/ccl/l1-fasls/l1-error-system.w32fsl',
                                reason='Host-backed standard streams required by A2.')])


if __name__=='__main__':
    result=run(Path(sys.argv[1]),Path(sys.argv[2]),'--partial' in sys.argv)
    Path(sys.argv[3]).write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],result['actual_loads'],'actual /',result['profile_loads'],'profile loads;',result['scope'])
