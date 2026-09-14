"""Project-wide observed call worklist; unresolved inputs never become bounds."""
from collections import Counter
import argparse
import gzip
import json
from pathlib import Path
from analysis import Graph, check, functions, read, require
from bounds import analyze
from run import save


def analyze_survey(directory, output):
    output.mkdir(parents=True,exist_ok=False)
    inventory=read(directory/'inventory.json');summary=read(directory/'summary.json')
    require(summary['status']=='COLLECTED' and summary['completed']==len(inventory['files']), 'SURVEY_COMPLETION')
    require([r['file'] for r in summary['files']]==inventory['files'], 'SURVEY_SOURCE_SET')
    counts=Counter();categories=Counter();reasons=Counter();operators=Counter();files=[]
    with gzip.GzipFile(filename='',fileobj=(output/'calls.jsonl.gz').open('wb'),mode='wb',mtime=0) as calls:
        for row in summary['files']:
            run_dir=directory/f"{row['ordinal']:03d}"
            run=read(run_dir/'run.json')
            require(run['input_sha256']==inventory['source_sha256'][row['file']], 'SURVEY_INPUT_JOIN')
            if row['status']=='SESSION_FAILED':
                files.append(dict(file=row['file'],status=row['status'],error=row['error']));continue
            cap=read(run_dir/'capture.json.gz');facts=check(cap)
            require(cap['status']==row['status'] and len(cap['forms'])==row['forms'], 'SURVEY_STATUS_JOIN')
            counts.update(facts)
            local=Counter()
            unjoined=[]
            if cap.get('output_graph'):
                output_graph=Graph(cap['output_graph'],False)
                emitted={e['native_function_id'] for r in cap.get('native_compilations',[]) for e in r['emissions']}
                emitted.update(r['guard_id'] for r in cap['captures'])
                for i,value in enumerate(output_graph.items({'ref':output_graph.root})):
                    item=output_graph.items(value)
                    if item[0] in (4,35,37):
                        fn=output_graph.node(item[1])
                        if fn['id'] not in emitted:unjoined.append(dict(output_index=i,opcode=item[0],function=fn))
            for record in cap['captures']+cap.get('native_compilations',[]):
                bounds={r['call_site']:r for r in analyze(record)};g=Graph(record['flow'])
                for function in functions(record['function']):
                    for call in function['calls']:
                        category=call['dependency']['category'];categories[category]+=1
                        item=dict(file=row['file'],source=record['source'],role=record.get('role','target-file-function'),
                                  function_id=function['function_id'],function_name=function['name'],
                                  site=call['site_id'],dependency=call['dependency'])
                        if call['site_id'] in bounds:
                            b=bounds[call['site_id']];item['lexical_bound']=b;local[b['disposition']]+=1
                            if b['disposition']=='UNRESOLVED':reasons[b['reason']]+=1
                        if category in ('function-variable','computed-callee'):
                            n=g.nodes[call['site_id']];callee=g.node(g.items(n['operands'])[0])
                            item['callee_operator']=callee.get('operator',callee['kind']) if callee else 'literal'
                            operators[item['callee_operator']]+=1
                        calls.write((json.dumps(item,sort_keys=True,separators=(',',':'))+'\n').encode())
            files.append(dict(file=row['file'],status=cap['status'],eof_reached=cap['eof_reached'],**facts,
                 bounds=dict(local),problem=cap['problem'],gaps=cap['gaps'],
                 native_macro_dependencies=len({e['selected_id'] for e in cap['expansions'] if e['source'] is None}),
                 unjoined_output_records=unjoined,
                 tainted_captures=sum(bool(r['prior_gaps']) for r in cap['captures']),
                 read_inputs=run['read_inputs']))
            save(output/'progress.json',dict(files=len(files),expected=len(inventory['files'])))
    totals=dict(counts);totals.update(files=len(files),completed_reads=sum(f.get('eof_reached',False) for f in files),
         successful_files=sum(f['status']=='CAPTURED' for f in files),
         lexical_bounds=sum(f.get('bounds',{}).get('BOUNDED_LEXICAL_PROTOTYPE',0) for f in files))
    result=dict(status='ANALYZED',qualified_census=False,totals=totals,
                call_categories=dict(categories),unresolved_lexical_reasons=dict(reasons),
                indirect_callee_operators=dict(operators),files=files,
                original_r7_bounds_changed=False,
                scope='Fresh independent file sessions; original r7 identities and target implementation dispositions are not inferred.')
    save(output/'analysis.json',result);(output/'progress.json').unlink();print(totals)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('survey',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();analyze_survey(a.survey,a.output)
