"""Check every changed native artifact, without a fixed FASL allowlist."""
import json,tarfile
from pathlib import Path
import comparison

def run(source,out,inputs,baseline,registered):
    changed=[n for n in baseline if baseline[n]!=registered[n]]
    rows=[]
    with tarfile.open(out/'baseline-fasls.tar.gz') as archive,tarfile.open(inputs/'source.tar') as sources:
        for name in changed:
            if name in ['bin/systems.dx64fsl','bin/compile-ccl.dx64fsl']:continue # existing exact registration comparator below
            before=archive.extractfile(name).read();after=(source/name).read_bytes()
            decoded=comparison.base_comparator()['CompilerFasl'](before).decode()
            logical=next(row['source'] for row in decoded if 'source' in row)
            assert logical.startswith('ccl:') and logical.endswith('.lisp.newest'),logical
            relative=logical[4:-7].replace(';','/')
            if relative.startswith('l1/'):relative='level-1/'+relative[3:]
            if relative.startswith('l0/'):relative='level-0/'+relative[3:]
            result=comparison.compare(before,after,sources.extractfile(relative).read().decode(),(source/relative).read_text(),relative)
            path=out/('decoded-'+name.replace('/','-')+'.json');path.write_text(json.dumps(result,sort_keys=True)+'\n')
            rows.append(dict(fasl=name,source=relative,functions=result['functions'],declared=len(result['declared_changes']['definitions']),gensyms=len(result['declared_changes']['debug_gensyms'])))
    (out/'all-native-comparisons.json').write_text(json.dumps(dict(status='PASS',changed=len(changed),byte_identical=len(baseline)-len(changed),rows=rows),indent=2)+'\n')
    return changed
