"""Exercise combined-source native FASLs and directed comparison refusals."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import comparison
from qualify import source_path


def run(native, inputs):
    name='l1-fasls/nx.dx64fsl'
    with tarfile.open(native/'results/baseline-fasls.tar.gz') as archive:
        before=archive.extractfile(name).read()
    # A successful gate restores the work tree to U1. Compare the retained
    # registered artifact, not the now-reversed native build directory.
    registered=native/'results/registered-nx.dx64fsl'
    after=(registered if registered.exists() else native/'work/ccl'/name).read_bytes()
    assert hashlib.sha256(after).hexdigest()==json.loads(
        (native/'results/registered-fasls.json').read_text())[name]
    decoder=comparison.base_comparator()['CompilerFasl']
    rows=decoder(after).decode()
    bindings={json.dumps(row['source'],sort_keys=True):source_path(row['source'])
              for row in decoder(before).decode()+rows if 'source' in row}
    with tarfile.open(inputs/'source.tar') as archive:
        old={key:archive.extractfile(path).read().decode() for key,path in bindings.items()}
    new={key:(native/'results/proposal/files'/path).read_text()
         if (native/'results/proposal/files'/path).exists() else old[key]
         for key,path in bindings.items()}
    result=comparison.compare(before,after,old,new,'compiler/nx.lisp')
    assert len(set(bindings.values()))>1

    def descend(x):
        if isinstance(x,(dict,list)):
            yield x
            for value in (x.values() if isinstance(x,dict) else x):yield from descend(value)
    # Compare the exact same decoded artifact first. The refusal controls then
    # differ in one field, so an unrelated before/after gensym difference cannot
    # make a broken control appear to pass.
    ns=comparison.comparator()
    def equal(a,b):
        assert a==b, 'native executable, non-debug constant, or ABI difference'
        return {}
    ns['check']=equal
    changed=rows
    class ControlDecoder:
        def __init__(self,data):self.data=data
        def decode(self):return copy.deepcopy(rows if self.data==b'before' else changed)
    ns['CompilerFasl']=ControlDecoder
    ns['compare'](b'before',b'after',new,new)
    refusals=[]
    for kind in ('executable-byte','non-location-bit','callee-identity',
                 'second-source-note-bounds','unknown-source','function-source-file','pc-map-bounds'):
        changed=copy.deepcopy(rows)
        functions=[x['function'] for x in descend(changed) if isinstance(x,dict) and set(x)=={'function'}]
        if kind=='executable-byte':
            f=functions[0];raw=bytearray.fromhex(f['code']);raw[0]^=1;f['code']=raw.hex()
        elif kind=='non-location-bit':functions[0]['constants'][-1]^=1
        elif kind=='callee-identity':
            c=next(c for f in functions for c in f['constants'][:-1]
                   if isinstance(c,dict) and set(c)=={'symbol'})
            c['symbol']='CCL::CHANGED-CALLEE'
        elif kind in ('second-source-note-bounds','unknown-source'):
            v=next(x['vector']['values'] for x in descend(changed)
                   if isinstance(x,dict) and set(x)=={'vector'} and x['vector'].get('subtag')==54
                   and len(x['vector']['values'])==4 and 'SOURCE-NOTE' in repr(x['vector']['values'][0])
                   and isinstance(x['vector']['values'][2],dict))
            if kind=='unknown-source':v[2]='ccl:missing.lisp.newest'
            else:
                # NX0 is longer than NX-BASIC. Make the active directive name
                # NX0 while the note names NX-BASIC; this bound is valid in the
                # wrong file, so ignoring the note's file cannot refuse it.
                wrong=max(new,key=lambda key:len(new[key]))
                end=len(new[json.dumps(v[2],sort_keys=True)])+1
                assert end<=len(new[wrong])
                for row in changed:
                    if 'source' in row:row['source']=json.loads(wrong)
                v[3]={'cons':[end,end]}
        elif kind=='function-source-file':
            from fasl import elements,symbol
            note=next(props[i+1]['vector']['values']
                      for f in functions if f['constants'][-1] & (1<<23)
                      for props in [elements(f['constants'][-2 if f['constants'][-1] & (1<<29) else -3])]
                      for i in range(0,len(props),2) if props[i]==symbol('CCL::%FUNCTION-SOURCE-NOTE'))
            other=max((key for key in new if json.loads(key)!=note[2]),key=lambda key:len(new[key]))
            note[2]=json.loads(other)
        else:
            from fasl import elements,symbol
            for f in functions:
                bits=f['constants'][-1]
                if not bits & (1<<23):continue
                slot=-2 if bits & (1<<29) else -3
                props=elements(f['constants'][slot]);found=False
                for i in range(0,len(props),2):
                    if props[i]==symbol('CCL::PC-SOURCE-MAP'):
                        value=props[i+1];value.clear()
                        value['u32vector']='0000000000000000ffffffffffffffff'
                        found=True;break
                if found:break
            assert found
        try:ns['compare'](b'before',b'after',new,new)
        except AssertionError as error:
            if kind=='second-source-note-bounds':assert str(error).startswith('source note bounds ')
            if kind=='function-source-file':assert str(error)=='native executable, non-debug constant, or ABI difference'
            refusals.append(dict(kind=kind,reason=str(error)))
        else:raise AssertionError('escaped comparison control '+kind)
    result['controls']=refusals;result['source_bindings']=bindings
    return result


if __name__=='__main__':
    result=run(Path(sys.argv[1]),Path(sys.argv[2]))
    Path(sys.argv[3]).write_text(json.dumps(result,sort_keys=True)+'\n')
    print('PASS',result['functions'],'functions;',len(result['controls']),'refusals')
