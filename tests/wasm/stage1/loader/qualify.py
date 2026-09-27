"""Check every changed native artifact, without a fixed FASL allowlist."""
import json,tarfile
from pathlib import Path
import comparison

def source_path(logical):
    if isinstance(logical,dict):
        from fasl import elements,symbol
        parts=logical['istruct']
        assert len(parts)==6 and parts[0]=={'istruct-cell':symbol('COMMON-LISP::LOGICAL-PATHNAME')}
        directory=elements(parts[1]);assert directory[0]==symbol('KEYWORD::ABSOLUTE')
        assert parts[4]=='ccl' and parts[5]==symbol('KEYWORD::NEWEST')
        logical='ccl:'+';'.join(directory[1:]+[parts[2]+'.'+parts[3]])+'.newest'
    assert logical.startswith('ccl:') and logical.endswith('.lisp.newest'),logical
    relative=logical[4:-7].replace(';','/')
    if relative.startswith('l1/'):relative='level-1/'+relative[3:]
    if relative.startswith('l0/'):relative='level-0/'+relative[3:]
    return relative

def run(source,out,inputs,baseline,registered):
    changed=[n for n in baseline if baseline[n]!=registered[n]]
    rows=[]
    with tarfile.open(out/'baseline-fasls.tar.gz') as archive,tarfile.open(inputs/'source.tar') as sources:
        for name in changed:
            if name in ['bin/systems.dx64fsl','bin/compile-ccl.dx64fsl']:continue # existing exact registration comparator below
            before=archive.extractfile(name).read();after=(source/name).read_bytes()
            decoded=comparison.base_comparator()['CompilerFasl'](before).decode()
            logical=next(row['source'] for row in decoded if 'source' in row)
            relative=source_path(logical)
            bindings={json.dumps(row['source'],sort_keys=True):source_path(row['source'])
                      for row in decoded+comparison.base_comparator()['CompilerFasl'](after).decode() if 'source' in row}
            old={key:sources.extractfile(path).read().decode() for key,path in bindings.items()}
            new={key:(source/path).read_text() for key,path in bindings.items()}
            if len(bindings)==1:old=next(iter(old.values()));new=next(iter(new.values()))
            result=comparison.compare(before,after,old,new,relative)
            result['source_bindings']=bindings
            path=out/('decoded-'+name.replace('/','-')+'.json');path.write_text(json.dumps(result,sort_keys=True)+'\n')
            rows.append(dict(fasl=name,source=relative,functions=result['functions'],declared=len(result['declared_changes']['definitions']),gensyms=len(result['declared_changes']['debug_gensyms'])))
    (out/'all-native-comparisons.json').write_text(json.dumps(dict(status='PASS',changed=len(changed),byte_identical=len(baseline)-len(changed),rows=rows),indent=2)+'\n')
    return changed
