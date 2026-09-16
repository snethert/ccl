"""LL15 v0.2 publication checker. Expectations come from fixed reviewed inputs.

A publication cannot supply or replace its own reference. Counts are descriptive;
full graph records, namespaces and native observations are checked independently.
"""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

def require(value, reason):
    if not value: raise ValueError(reason)
def sha(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
def identity(value): return hashlib.sha256(canonical(value)).hexdigest()
def read(path):
    with (gzip.open(path, 'rt') if Path(path).suffix == '.gz' else Path(path).open()) as f: return json.load(f)
def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
def populations(graph):
    groups = {}
    for edge in graph['edges']:
        if edge['resolution'] != 'complete':
            family = edge['evidence'].split('/')[1]
            groups.setdefault(family, []).append(dict(source=edge['from'], evidence=edge['evidence'], targets=edge['targets'], resolution=edge['resolution']))
    return {k: sorted(v, key=canonical) for k, v in sorted(groups.items())}

CLAIMS = dict(instrument_qualified=True, complete_closure=False, generated_code=False,
    native_implemented_nodes_are_not_target_implementations=True,
    complete_reference_edges_are_not_exhaustive_callee_bounds=True,
    private_recompilation_is_not_resident_identity=True,
    dispatch_events_do_not_assert_entry_or_completion=True,
    startup_and_correlated_build_are_distinct_executions=True,
    profile_dispositions_and_unqualified_lowerings_remain_obligations=True)
INITIALIZER_SCOPE = 'Observed cold-process boundary chain only; full build/reader/loader joins remain identified inputs, not a proved bootstrap prerequisite closure.'

class Reference:
    def __init__(self, evidence):
        self.evidence = Path(evidence).resolve(); self.pins = read(HERE/'inputs.json'); self.inputs = {}; self.packets = {}; self.cache = {}
        for name, spec in self.pins['packets'].items():
            path = self.pin('packet:'+name, self.evidence/spec['path'], spec['sha256'])
            self.packets[name] = (path, read(path))
        for name, spec in self.pins['direct'].items():
            self.pin(name, (ROOT if spec['root']=='source' else self.evidence)/spec['path'], spec['sha256'])
        self.graph = read(self.member('startup','graph/seed-graph.json.gz'))
        self.recipe = read(ROOT/self.pins['direct']['seed-recipe']['path'])
        self.selection = self.archive('tools','startup-analysis.tar.gz','bodies/selection.json')
        self.compile = read(self.member('tools','startup-compile-summary.json'))
        self.missing = self.archive('tools','startup-analysis.tar.gz','bindings/missing-bodies.json')
        # Retain the original native capture and original failures as references;
        # no temporary directory or withdrawn combined graph participates.
        self.member('tools','startup-native.tar.gz')
        self.member('capture','capture/build.jsonl.gz'); self.member('capture','capture/registries.jsonl.gz')
        run = read(self.member('capture','capture/run.json'))
        require(run['status']=='PASS' and run['source_restored'] and not run['r6']['unexplained'], 'REFERENCE_R6')
        self.originals = self.archive('tools','tool-checks.tar.gz','capture-controls/original-events.json')
        self.source_events = self.archive('tools','tool-checks.tar.gz','capture-controls/source-events.json')
        self.witnesses = {name:self.archive('tools','tool-checks.tar.gz','native-controls/'+name+'/answer.json')
                          for name in ('u1-witness','not-reached','budget')}
        initial = read(self.member('initializers','census.json.gz'))
        self.initializers = [r for r in initial['initializers'] if r['node'].startswith('identity:cold:')]
        require(len(self.initializers)==70, 'REFERENCE_INITIALIZER_SCOPE')
        self.member('lowering','joins.json.gz'); self.member('lowering','delta.json.gz')
        trace = read(ROOT/self.pins['direct']['trace-reconciliation']['path'])
        require(all(trace['checks'].values()), 'REFERENCE_TRACE_COVERAGE')
        old_trace = Path(trace['source_trace']['locator'])
        trace_path = self.evidence/old_trace.parent.name/old_trace.name
        self.pin('external-trace',trace_path,trace['source_trace']['sha256'])
        for row in read(trace_path)['artifacts']:
            self.pin('trace:'+row['path'],trace_path.parent/row['path'],row['sha256'])
        require(self.compile==dict(status='PASS',units=167,source_unchanged=True,fasls_written=False,native_output_code_identical=True),'REFERENCE_167_UNITS')
        self.unknowns = populations(self.graph)
        require({k:len(v) for k,v in self.unknowns.items()} == dict(body=272,call=614,**{'binding-values':2859,'registry-future':394,'runtime':415,'builtin-lowering':7}), 'REFERENCE_POPULATIONS')
        # Check the seed entry links against the same-execution selection, not names
        # from another capture; the recipe is a distinct reviewed input.
        expected_entries = [(r['name'], r['function']) for r in self.selection['entry_bindings']]
        nodes={n['id']:n for n in self.graph['nodes']}
        for i,(name,code) in enumerate(expected_entries):
            n='startup-live:entry:'+str(i)
            require(n in self.graph['seeds'] and name in nodes[n]['reason'],'REFERENCE_SEED_RECIPE')
            require(any(e['from']==n and e['targets']==['startup-live:function:'+str(code)] for e in self.graph['edges']),'REFERENCE_SEED_EDGE')
        self.graph_pins={k:identity(self.graph[k]) for k in self.graph}
        calls=self.archive('tools','startup-analysis.tar.gz','bindings/reached-calls.json.gz',compressed=True)
        partitions={'proven-native-ir-targets':[], 'known-symbol-unbounded-values':[], 'unqualified-builtin-lowering':[], 'unresolved-computed-callees':[]}
        for call in calls:
            category=call['dependency']['category']
            if category in ('self','lexical','lexical-function-value'):
                group='proven-native-ir-targets'
                require(call['dependency']['targets'] and all(t['kind']=='function' and 'startup-ir:afunc:'+str(t['id']) in nodes for t in call['dependency']['targets']),'REFERENCE_LOCAL_BOUND')
            elif category=='global-binding':group='known-symbol-unbounded-values'
            elif category=='builtin':group='unqualified-builtin-lowering'
            else:
                require(category in ('function-variable','computed-callee'),'REFERENCE_CALL_KIND');group='unresolved-computed-callees'
            partitions[group].append(call)
        self.call_partitions={k:sorted(v,key=canonical) for k,v in partitions.items()}
        require({k:len(v) for k,v in self.call_partitions.items()}=={'proven-native-ir-targets':395,'known-symbol-unbounded-values':13641,'unqualified-builtin-lowering':561,'unresolved-computed-callees':614},'REFERENCE_CALL_PARTITION')
        self.queries=self.expected_queries()

    def pin(self, name, path, expected):
        path=Path(path); require(path.is_file() and sha(path)==expected,'INPUT_IDENTITY '+name)
        root='source' if path.is_relative_to(ROOT) else 'evidence'
        self.inputs[name]=dict(root=root,path=str(path.relative_to(ROOT if root=='source' else self.evidence)),sha256=expected)
        return path
    def member(self, name, member):
        key=(name,member)
        if key not in self.cache:
            path, packet=self.packets[name]; rows=[r for r in packet['files'] if r['path']==member]
            require(len(rows)==1 and '..' not in Path(member).parts and not Path(member).is_absolute(),'INPUT_MEMBER '+name)
            self.cache[key]=self.pin(name+':'+member,path.parent/member,rows[0]['sha256'])
        return self.cache[key]
    def archive(self, name, archive, member, compressed=False):
        with tarfile.open(self.member(name,archive)) as tar:
            data=tar.extractfile(member).read()
            return json.loads(gzip.decompress(data) if compressed else data)
    def expected_queries(self):
        o=self.originals; b=o['body']; r=o['registry']; entry=o['materialization']['functions'][0]; removal=o['removal']
        gf=r['entries'][0]['gf']; afunc=entry['afunc']; registry=[]; material=[]
        with gzip.open(self.member('capture','capture/registries.jsonl.gz'),'rb') as stream:
            for line in stream:
                prefix=line[:100]
                if any(k in prefix for k in (b'"kind":"registry-checkpoint"',b'"kind":"mutation-enter"',b'"kind":"mutation-leave"',b'"kind":"compiler-materialization"')):
                    row=json.loads(line);kind=row['kind']
                    if kind=='registry-checkpoint':
                        registry.extend(dict(state=state,event=row['sequence'],kind=kind,stage=row['stage']) for state in row['entries'] if state['gf']==gf)
                    elif kind.startswith('mutation-'):
                        if row['gf']['gf']==gf:registry.append(row)
                    else:material.extend(dict(f,event=row['sequence'],build_event=row['build_event']) for f in row['functions'] if f['afunc']==afunc)
        require(registry and material,'REFERENCE_QUERY_POPULATIONS')
        objects={v['id']:v for v in removal['payload']['objects']}; pair=objects[removal['payload']['root']['ref']]
        symbol=objects[pair['car']['ref']];require(symbol['kind']=='symbol','REFERENCE_REMOVAL_SYMBOL')
        return {
          'body' : (dict(kind='body',id=b['id']),[b]),
          'registry': (dict(kind='registry',id=r['entries'][0]['gf']),registry),
          'materialization': (dict(kind='materialization',id=entry['afunc']),material),
          'binding': (dict(kind='binding-event',id=removal['sequence']),[dict(removal,symbol=symbol,semantics='removal-intent-before-store')]),
          'absent': (dict(kind='body',id=-1),[])}

    def check(self, pub):
        require(set(pub)=={'version','claims','inputs','compile','seed_recipe','graph','unknowns','missing_bodies','initializers','initializer_scope','queries','witnesses','call_partitions'},'PUBLICATION_FIELDS')
        require(pub['version']==1 and pub['claims']==CLAIMS,'SCOPE_PROMOTION')
        require(pub['inputs']==self.inputs,'INPUT_SET')
        require(pub['compile']==self.compile,'COMPILE_SCOPE')
        require(pub['seed_recipe']==self.recipe,'SEED_RECIPE')
        graph=pub['graph']; require(set(graph)==set(self.graph),'GRAPH_FIELDS')
        # Separate diagnostics make omissions and substitutions reviewable. Full
        # records and multiplicity are compared, including descriptive scope.
        for key in ('seeds','nodes','edges'):
            require(identity(graph[key])==self.graph_pins[key],'GRAPH_'+key.upper())
        require(all(identity(graph[k])==self.graph_pins[k] for k in graph if k not in ('seeds','nodes','edges')),'GRAPH_SCOPE')
        require(pub['unknowns']==self.unknowns,'UNRESOLVED_POPULATIONS')
        require(pub['missing_bodies']==self.missing,'MISSING_BODY_POPULATION')
        require(pub['call_partitions']==self.call_partitions,'CALL_BOUND_PARTITION')
        require(pub['initializer_scope']==INITIALIZER_SCOPE,'INITIALIZER_SCOPE')
        rows=pub['initializers']; table={r['node']:r for r in rows}
        require(len(table)==len(rows),'INITIALIZER_DUPLICATE')
        for row in rows:
            require(all(p in table and table[p]['rank']<row['rank'] for p in row['prerequisites']),'INITIALIZER_PREREQUISITE')
        require(rows==self.initializers,'INITIALIZER_RECORDS')
        require(set(pub['queries'])==set(self.queries),'QUERY_SET')
        for name,(question,expected) in self.queries.items():
            answer=pub['queries'][name]
            require(answer['question']==question and answer['namespace']==self.pins['packets']['capture']['id'],'QUERY_IDENTITY '+name)
            require(answer['exhaustive'] is False and answer['status']==('OBSERVED' if expected else 'NOT_OBSERVED'),'QUERY_SCOPE '+name)
            actual=answer['records']
            require(actual==expected,'QUERY_RECORDS '+name)
            require(answer['evidence']['packet_sha256']==self.pins['packets']['capture']['sha256'],'QUERY_CAPTURE '+name)
            require(answer['evidence']['inputs']=={n:self.inputs['capture:capture/'+n]['sha256'] for n in ('run.json','build.jsonl.gz','registries.jsonl.gz')},'QUERY_INPUTS '+name)
        require(set(pub['witnesses'])==set(self.witnesses),'WITNESS_SET')
        for name,expected in self.witnesses.items():
            answer=pub['witnesses'][name]
            require(answer['selections']==expected['selections'] and answer['source_sha256']==expected['source_sha256'] and answer['function']==expected['function'],'WITNESS_IDENTITY '+name)
            require(answer['namespace']==expected['namespace'] and answer['exhaustive'] is False and answer['status']==expected['status'],'WITNESS_SCOPE '+name)
            native=answer['native']; old=expected['native']
            for k in ('bound','dropped_events','total_events','scenario_equal','restored_code_identical','scenario_result','site','sites','reference_code','events'):
                require(native[k]==old[k],'WITNESS_'+k.upper()+' '+name)
            require(answer==expected,'WITNESS_RECORDS '+name)
        return dict(status='PASS',instrument=True,complete_closure=False,units=167,seeds=len(graph['seeds']),nodes=len(graph['nodes']),edges=len(graph['edges']),unresolved={k:len(v) for k,v in self.unknowns.items()},missing_bodies=len(self.missing),call_partitions={k:len(v) for k,v in self.call_partitions.items()},unqualified_nodes=dict(sorted(Counter(n['evidence'].split('/')[1] for n in graph['nodes'] if n['disposition']=='unresolved').items())))

    def make(self, queries, witnesses):
        return dict(version=1,claims=CLAIMS,inputs=self.inputs,compile=self.compile,seed_recipe=self.recipe,
            graph=self.graph,unknowns=self.unknowns,missing_bodies=self.missing,initializers=self.initializers,
            initializer_scope=INITIALIZER_SCOPE,queries=queries,witnesses=witnesses,call_partitions=self.call_partitions)

def write_publication(out, pub):
    out=Path(out);out.mkdir()
    # Deterministic gzip, with no path or timestamp in its header.
    with (out/'publication.json.gz').open('wb') as f:
        with gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0) as z:z.write(canonical(pub))
    save(out/'manifest.json',dict(version=1,file='publication.json.gz',sha256=sha(out/'publication.json.gz')))

def check_files(folder, reference):
    folder=Path(folder);m=read(folder/'manifest.json')
    require(m.get('file')=='publication.json.gz','PUBLICATION_PATH')
    require(sha(folder/m['file'])==m['sha256'],'PUBLICATION_ARTIFACT')
    return reference.check(read(folder/m['file']))
