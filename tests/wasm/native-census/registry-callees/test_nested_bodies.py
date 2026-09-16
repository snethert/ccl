"""Missing or substituted inner bodies invalidate their dependent outer body."""
from copy import deepcopy
from nested_bodies import pairs,qualify
from payloads import require


def run():
    def f(*targets):return dict(bits=1<<29,literals=[{'function':t} for t in targets])
    def m(a,b):return dict(bootstrap_code=a,compiled_functions=[b],compiler_records=[{'function':b}],
                         candidate_only=True,function_dependencies=[])
    fs={1:f(2),2:f(3),3:f(),11:f(12),12:f(13),13:f()}
    ms=[m(1,11),m(2,12),m(3,13)]
    rel,_=pairs(fs,ms);require(rel=={(1,11),(2,12),(3,13)},'NESTED_COMPLETE_CHAIN')
    missing,_=pairs(fs,ms[:2]);require(not missing,'MISSING_LEAF_INVALIDATES_PARENTS')
    altered=deepcopy(fs);altered[12]=f(14);altered[14]=f()
    rel,_=pairs(altered,ms);require(rel=={(3,13)},'SUBSTITUTED_INNER_BODY')
    cyclic={1:f(2),2:f(1),11:f(12),12:f(11)}
    rel,_=pairs(cyclic,ms[:2]);require(rel=={(1,11),(2,12)},'RECURSIVE_LITERAL_PAIR')
    rel,_=pairs(cyclic,ms[:1]);require(not rel,'MISSING_CYCLE_MEMBER')
    same={1:f(2),2:f(),11:f(2)}
    rel,_=pairs(same,ms[:1]);require(rel=={(1,11)},'EXACT_LITERAL_DOES_NOT_REQUIRE_RECOMPILE')
    result=qualify(same,ms[:1],rel)
    dep=result[0]['function_literal_correspondences'][0]
    require(not result[0].get('candidate_only') and dep['relation']=='EXACT_LITERAL_IDENTITY'
            and dep['function_identity'] and not dep['environment_identity'],'EXACT_LITERAL_SCOPE')
    rel,_=pairs(fs,ms);result=qualify(fs,ms,rel)
    require(all(not d['function_identity'] and not d['environment_identity']
                for m in result for d in m.get('function_literal_correspondences',[])),
            'BODY_RELATION_IS_NOT_OBJECT_IDENTITY')
    return dict(status='PASS',closed_relation_cases=8)


if __name__=='__main__':print(run())
