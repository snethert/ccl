"""Replay the reviewed graph operations; no identity joins are inferred."""
import hashlib
import json
from support import compressed,require


def materialize(v,pins,tools):
    hashes={k:p['sha256'] for k,p in pins['inputs'].items()}
    stages=[];graph=v['base']
    require(v['emission']['version']==2 and v['emission']['base_sha256']==hashes['base'],'EMISSION_BASE')
    graph=tools['emission'].apply_delta(graph,v['emission'])
    graph['inputs_sha256']=hashlib.sha256(json.dumps({'base':graph['inputs_sha256'],'delta':hashes['emission']},sort_keys=True).encode()).hexdigest()
    require(v['boot']['input_binding']['base']==hashes['base'] and
            v['boot']['input_binding']['emission_delta']==hashes['emission'],'BOOT_INPUT_BINDING')
    graph=tools['boot'].apply_delta(graph,v['boot'])
    identity=hashlib.sha256(compressed(graph,sort_keys=False,level=6,legacy_stream=True)).hexdigest()
    require(identity==v['boot_materialization']['output_sha256'],'BOOT_MATERIALIZATION')
    stages.append(dict(stage='boot',sha256=identity,nodes=len(graph['nodes']),edges=len(graph['edges'])))
    require(v['wrappers']['input_binding']['base_graph']==identity,'WRAPPER_BASE')
    graph=tools['wrappers'].apply(graph,v['wrappers'])
    identity=hashlib.sha256(compressed(graph)).hexdigest()
    require(identity==v['wrapper_run']['materialization']['sha256']==v['flow']['base_sha256'],'WRAPPER_MATERIALIZATION')
    stages.append(dict(stage='wrappers',sha256=identity,nodes=len(graph['nodes']),edges=len(graph['edges'])))
    graph=dict(graph,nodes=graph['nodes']+v['flow']['nodes'],edges=graph['edges']+v['flow']['edges'],
               profile=graph['profile']+'; '+v['flow']['scope'])
    graph=tools['bindings'].apply(graph,v['bindings'])
    graph=tools['literals'].apply(graph,v['literals'])
    require((len(graph['nodes']),len(graph['edges']))==
            (v['prior_summary']['graph_nodes'],v['prior_summary']['graph_edges']),'PRIOR_GRAPH_COUNTS')
    stages.append(dict(stage='resident-literals',nodes=len(graph['nodes']),edges=len(graph['edges'])))
    return graph,stages
