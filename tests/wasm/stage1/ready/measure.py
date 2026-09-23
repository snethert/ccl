"""Keep inherited CCL execution separate from this image's actual boot work."""
from pathlib import Path
import sys
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
    result=dict(
      status='MEASURED',
      original_executions=dict(count=parent['original_definition_headline'],
        non_nil=parent['original_non_nil_headline'],fresh_credit=0,
        evidence=str(c.PARENT/'packet.json'),sha256=c.sha(c.PARENT/'packet.json'),
        scope='Inherited original-definition qualification, not 550 definitions re-executed on this one cold image.'),
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
    assert result['original_executions']['count']==550
    assert result['original_executions']['non_nil']==515
    assert len(gfs)==startup['values'][1]==33
    c.save(output,result)
    return result

if __name__=='__main__':measure(*map(Path,sys.argv[1:]))
