"""Account for the whole 95-cell batch; source candidates do not alias objects."""
from collections import Counter
from definition_join import missing_cells,require

def classify(histories,facts,source_work):
    missing=missing_cells(histories);compiled={};declared={}
    for r in facts['compiled']:compiled.setdefault(r['symbol']['id'],[]).append(r)
    for r in facts['declarations']:
        for e in r['entries']:declared.setdefault(e['symbol']['id'],[]).append(dict(event=r['event'],entry=e))
    remaining=set(missing)-set(compiled)-set(declared)
    require(set(compiled).isdisjoint(declared) and set(compiled)|set(declared)<=set(missing),'BATCH_PARTITION')
    candidates={r['symbol_id']:r for r in source_work['records']}
    require(set(candidates)==remaining and len(candidates)==len(source_work['records']),'REMAINING_SOURCE_WORK')
    result=[]
    for ident,h in sorted(missing.items()):
        candidate=candidates.get(ident)
        if candidate:require(candidate['descriptor'] in h['descriptors'],'SOURCE_LOOKUP_DESCRIPTOR')
        kind=('COMPILED_NAME_IDENTITY' if ident in compiled else 'ACCESSOR_DECLARATION_IDENTITY' if ident in declared else candidate['category'])
        result.append(dict(symbol_id=ident,node='identity:build:binding-cell:'+str(ident),descriptors=h['descriptors'],
                           call_sites=h['call_count'],category=kind,compiled=compiled.get(ident,[]),
                           declarations=declared.get(ident,[]),source_candidates=candidate,
                           runtime_value_witness=False,runtime_bound='UNRESOLVED'))
    counts=Counter(r['category'] for r in result)
    return dict(version=1,scope='Accounted source/compiler provenance; all 95 runtime cell values remain unwitnessed.',
                counts=dict(sorted(counts.items())),call_sites=sum(r['call_sites'] for r in result),records=result)
