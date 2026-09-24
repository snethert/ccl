"""Keep inherited CCL execution separate from this image's actual boot work."""
from pathlib import Path
import sys
import tarfile
import json
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c

def measure(base,probe,output):
    parent=c.read(c.PARENT/'summary.json')
    owners={x['id']:x for x in c.read(probe/'compiled/symbols.json')}
    rows=c.read(probe/'compiled/native.json')
    startup=next(x for x in rows if x['definition']=='READY-START')
    graph=startup['args'][0]['graph']
    gfs=[dict(binding=owners.get(n.get('binding')),name=owners.get(graph['nodes'][n['generic'][1]['ref']]['fields'][1].get('value',{}).get('symbol')),fields=n['generic'])
         for n in graph['nodes'] if 'generic' in n]
    closure=c.read(output.parent/'closure.json')
    numeric_names=['ABS','COMPLEX','REALPART','IMAGPART']
    lock_sources={
        'MAKE-LOCK':'ccl:level-0;l0-aprims.lisp',
        '%MAKE-LOCK':'ccl:level-0;l0-aprims.lisp',
        'LOCK-NAME':'ccl:level-0;l0-aprims.lisp',
        '%LOCK-RECURSIVE-LOCK-OBJECT':'ccl:level-0;l0-misc.lisp',
        '%UNLOCK-RECURSIVE-LOCK-OBJECT':'ccl:level-0;l0-misc.lisp',
        'GRAB-LOCK':'ccl:level-1;l1-processes.lisp',
        'RELEASE-LOCK':'ccl:level-1;l1-processes.lisp',
        'TRY-LOCK':'ccl:level-1;l1-processes.lisp'}
    new_names=numeric_names+list(lock_sources)
    nil_only=['%UNLOCK-RECURSIVE-LOCK-OBJECT','RELEASE-LOCK']
    prior=c.STORE/'2026-09-24-stage1-ready-join-r9'
    manifest=c.read(prior/'packet.json')['files']
    assert c.sha(prior/'full-execution.tar.gz')==manifest['full-execution.tar.gz']
    with tarfile.open(prior/'full-execution.tar.gz') as archive:
        old_rows=json.load(archive.extractfile('compiled/native.json'))
    assert not set(new_names)&{row['definition'] for row in old_rows}
    witnesses={}
    for name in new_names:
        package='COMMON-LISP' if name in numeric_names else 'CCL'
        matches=[m for m in closure['modules'] if m['name']==package+'::'+name]
        assert len(matches)==1 and matches[0]['source']==lock_sources.get(name,'ccl:level-0;l0-numbers.lisp')
        witnesses[name]=matches[0]
    witness=next(row for row in rows if row['definition']=='READY-NUMERIC-SEQUENCES')
    assert witness['values'] and witness['values']!=[None]
    locks=next(row for row in rows if row['definition']=='READY-RECURSIVE-LOCKS')
    assert locks['values'] and locks['values']!=[None]

    result=dict(
      status='MEASURED',
      original_executions=dict(count=parent['original_definition_headline']+len(new_names),
        non_nil=parent['original_non_nil_headline']+len(new_names)-len(nil_only),fresh_credit=len(new_names),
        nil_only=nil_only,lock_native_witness_sha256=c.digest(locks),
        inherited_count=parent['original_definition_headline'],
        new_names=new_names,whole_file_modules=witnesses,
        prior_execution_archive_sha256=manifest['full-execution.tar.gz'],
        native_witness_sha256=c.digest(witness),
        evidence=str(c.PARENT/'packet.json'),sha256=c.sha(c.PARENT/'packet.json'),
        scope='550 inherited originals plus four numeric and eight lock definitions executed by the two READY support callers. Target lock primitive replacements are excluded from original credit. The earlier originals are not all exercised by this cold image.'),
      acode=dict(**closure['acode'],source=c.sha(output.parent/'closure.json'),
        scope='READY entry and projected-callable dependency census; includes conservative unresolved/indirect paths listed in closure.json, not the corpus census or a branch-execution count.'),
      closure=dict(modules=len(closure['modules']),missing=closure['missing'],
        indirect_modules=closure['indirect_modules'],complete=closure['complete']),
      replacement_census=c.read(output.parent/'replacements.json'),
      callbacks=dict(count=35,complete=False,source=c.sha(output.parent/'callbacks.json')),
      startup=dict(entries=[r['definition'] for r in [r for r in rows if r['definition'] in ('READY-INITIALIZE','READY-CHECK','READY-START')]],
        oracle=[dict(entry=r['definition'],values=r['values']) for r in [r for r in rows if r['definition'] in ('READY-INITIALIZE','READY-CHECK','READY-START')]],
        classes=startup['values'][0],generic_functions=gfs,
        graph_nodes=len(graph['nodes']),generic_population=startup['values'][1],
        projection='Selected dependency graph of the pinned native image; not all 581 native GFs or all native methods.'),
      criteria=dict(replacement_cap=25,replacement_census_complete=False,
        ready_worklist_membership_complete=False,slot_credit=False,
        remaining=['Resolve the missing and indirect edges listed in closure.json.',
                   'Finish native antecedent/branch attribution in replacements.json before asserting the 25 cap.',
                   'Discharge callbacks.json against the completed dependency inventory.',
                   'Qualify the complete selected image interface, including unresolved closure metadata, before LL15 slot credit.']))
    assert result['original_executions']['count']==562
    assert result['original_executions']['non_nil']==525
    assert len(gfs)==startup['values'][1]==50
    c.save(output,result)
    return result

if __name__=='__main__':measure(*map(Path,sys.argv[1:]))
