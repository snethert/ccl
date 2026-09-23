"""Keep inherited CCL execution separate from this image's actual boot work."""
from pathlib import Path
import sys
import collections
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
    operators=c.read(base/'compiled/executed-operators.json')
    counts=collections.Counter()
    for row in operators:
        for name,count in row['operators']:counts[name]+=count
    result=dict(
      status='MEASURED',
      original_executions=dict(count=parent['original_definition_headline'],
        non_nil=parent['original_non_nil_headline'],fresh_credit=0,
        evidence=str(c.PARENT/'packet.json'),sha256=c.sha(c.PARENT/'packet.json'),
        scope='Inherited original-definition qualification, not 550 definitions re-executed on this one cold image.'),
      acode=dict(source=c.sha(base/'compiled/executed-operators.json'),
        definitions=len(operators),operators=len(counts),occurrences=sum(counts.values()),
        by_operator=dict(sorted(counts.items())),
        scope='Emitted operators associated with retained executed definitions; not a claim every branch was taken.'),
      startup=dict(entries=[r['definition'] for r in rows[:3]],
        oracle=[dict(entry=r['definition'],values=r['values']) for r in rows[:3]],
        classes=startup['values'][0],generic_functions=gfs,
        graph_nodes=len(graph['nodes']),generic_population=startup['values'][1],
        projection='Selected dependency graph of the pinned native image; not all 581 native GFs or all native methods.'),
      criteria=dict(replacement_cap=25,replacement_census_complete=False,
        ready_worklist_membership_complete=False,slot_credit=False,
        remaining=['Complete named replacement census against the 25 cap.',
                   'Join the selected-image dependency inventory to dispositions of the 35 retained native startup callbacks.',
                   'Qualify the complete selected image interface, including unresolved closure metadata, before LL15 slot credit.']))
    assert result['original_executions']['count']==550
    assert result['original_executions']['non_nil']==515
    assert len(gfs)==startup['values'][1]==33
    c.save(output,result)
    return result

if __name__=='__main__':measure(*map(Path,sys.argv[1:]))
