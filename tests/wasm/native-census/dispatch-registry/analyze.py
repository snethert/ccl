"""Registry checkpoint joins; installed methods are deliberately NOT call bounds."""
from collections import Counter
import copy
from native import require

SCOPE = 'Fresh native registry checkpoint and mutation witnesses; no original-build dynamic identity join, complete cache/class/combination state or exhaustive callee bound.'
NAMES = ['empty','base','warm-base','integer','warm-integer','replace-integer','remove-integer',
         'eql','eql-miss','around','remove-around','remove-all']
VALUES = [[],[10,11],[10,11],[20,21],[20,21],[30,31],[10,11],[40,41],[10,11],[140,141],[40,41],[10,11]]
COUNTS = [0,1,1,2,2,2,1,2,2,3,2,0]


def gf_bits(bits):
    # Independent literal reading of U1 library/lispequ.lisp, bits 27 and 28.
    return type(bits) is int and bits & ((1<<27)|(1<<28)) == 1<<27


def assess(data, independent):
    require(set(data)=={'version','namespace','scope','registry','probes','functions'}
            and data['version']==1 and data['namespace']=='fresh-native-registry'
            and data['scope']=='Sequential native checkpoint; no join to original dynamic objects or exhaustive runtime bound', 'CAPTURE_SCOPE')
    funcs = {r['id']:r for r in data['functions']}
    require(len(funcs)==len(data['functions']) and all(type(i) is int and i>0 for i in funcs), 'FUNCTION_IDENTITIES')
    for f in funcs.values():
        require(set(f)=={'id','prototype','name','bits','source','position'} and f['prototype'] in funcs
                and type(f['bits']) is int, 'FUNCTION_DESCRIPTOR')
    registry = data['registry']; steps = data['probes']['steps']; checks = data['probes']['checks']
    require([s['name'] for s in steps]==NAMES, 'PROBE_COVERAGE')
    gf = steps[0]['before']['gf']
    require(len({r['gf'] for r in registry})==len(registry)
            and {r['gf'] for r in registry}|{gf}=={i for i,r in funcs.items() if gf_bits(r['bits'])}, 'REGISTRY_COVERAGE')
    method_owners = {}

    def state(s):
        ident = s['gf']
        require(ident in funcs and gf_bits(s['bits']) and gf_bits(funcs[ident]['bits'])
                and s['native_standard_gf'] is True, 'GF_SUBTYPE')
        if s['status']=='UNINITIALIZED':
            require(set(s)=={'status','gf','name','unbound_slots','bits','native_standard_gf'}
                    and s['unbound_slots'] and set(s['unbound_slots'])<={1,2,4}, 'UNINITIALIZED_SCOPE')
            return
        require(set(s)=={'status','gf','name','bits','native_standard_gf','wrapper','slots_owner_matches',
                        'dcode','dispatch_table','dispatch_argnum','precedence','combination','standard_combination','methods'}
                and s['status']=='INITIALIZED' and s['slots_owner_matches'] is True, 'INITIALIZED_STATE')
        require(s['dcode'] in funcs and all(type(s[k]) is int and s[k]>0 for k in ('wrapper','dispatch_table','combination'))
                and type(s['dispatch_argnum']) is int and isinstance(s['precedence'],list), 'DISPATCH_FIELDS')
        require(len({m['id'] for m in s['methods']})==len(s['methods']), 'DUPLICATE_METHOD')
        for m in s['methods']:
            require(set(m)=={'id','owner','function','qualifiers','specializers'}
                    and type(m['id']) is int and m['id']>0 and m['owner']==ident, 'METHOD_OWNER')
            require(m['function'] in funcs and isinstance(m['qualifiers'],list)
                    and all(type(i) is int and i>0 for i in m['specializers']), 'METHOD_FIELDS')
            require(m['id'] not in method_owners or method_owners[m['id']]==ident, 'METHOD_SHARED_BETWEEN_GFS')
            method_owners[m['id']] = ident

    for s in registry:
        state(s)
    for n,(s,values,count) in enumerate(zip(steps,VALUES,COUNTS)):
        state(s['before']); state(s['after'])
        require(s['before']['gf']==gf and s['after']['gf']==gf
                and s['before']==s['after'] and len(s['after']['methods'])==count, 'PROBE_STATE')
        call = s['call']
        require(set(call)=={'status','values','condition'} and call['values']==values
                and call['status']==('ERROR' if n==0 else 'RETURN'), 'PROBE_RESULT '+s['name'])
        require(call['condition']==({'symbol':'NO-APPLICABLE-METHOD-EXISTS','package':'CCL'} if n==0 else None), 'PROBE_CONDITION')
    after = {s['name']:s['after'] for s in steps}
    base_method = after['base']['methods'][0]['function']
    require(after['base']['dcode']==base_method and after['remove-integer']['dcode']==base_method
            and after['integer']['dcode']!=base_method, 'DIRECT_AND_TABLE_DISPATCH')
    old = after['integer']['methods'][0]; new = after['replace-integer']['methods'][0]
    require(old['id']!=new['id'] and old['function']!=new['function']
            and old['qualifiers']==new['qualifiers'] and old['specializers']==new['specializers'], 'METHOD_REPLACEMENT')
    # A real U1 defect is retained as negative evidence, never made a correct
    # empty-registry behavior by changing the intended semantics.
    require(after['remove-all']['methods']==[] and after['remove-all']['dcode']==base_method
            and independent=={'status':'KNOWN_NATIVE_DEFECT_REPRODUCED',
                              'marker':'NATIVE-EMPTY-METHOD-ESCAPE methods=0 retained-dcode=true before=10,11 after=10,11'}, 'EMPTY_METHOD_ESCAPE')
    expected_changes = ['base','integer','replace-integer','remove-integer','eql','around','remove-around','remove-all']
    require([c['name'] for c in checks]==expected_changes+['FUNCTION','QUALIFIERS','SPECIALIZERS','DCODE','ordinary-function-with-dcode-literal'], 'CHECK_COVERAGE')
    require(all(c=={'name':name,'stale_refused':True} for c,name in zip(checks,expected_changes)), 'STALE_SNAPSHOT_REFUSAL')
    for control, field in zip(checks[8:12],('function','qualifiers','specializers','dcode')):
        old = control['old']; changed = control['changed']; state(old); state(changed)
        repaired = copy.deepcopy(changed)
        if field=='dcode':
            require(old[field]!=changed[field], 'DCODE_CHANGE'); repaired[field] = old[field]
        else:
            require(old['methods'][0][field]!=changed['methods'][0][field], 'METHOD_FIELD_CHANGE')
            repaired['methods'][0][field] = old['methods'][0][field]
        require(repaired==old, 'FIELD_CHANGE_ISOLATION')
    counter = checks[-1]
    require(counter['refused'] is True and counter['function'] in funcs and counter['literal'] in funcs
            and not gf_bits(funcs[counter['function']]['bits'])
            and funcs[counter['literal']]['name']=={'symbol':'%%ONE-ARG-DCODE','package':'CCL'}, 'LITERAL_NOT_SUBTYPE')
    initialized = [s for s in registry if s['status']=='INITIALIZED']
    target_ids = {s['dcode'] for s in initialized}
    method_ids = {m['function'] for s in initialized for m in s['methods']}
    facts = dict(version=1,scope=SCOPE,namespace='fresh-native-registry',census_gate_credit=False,
                 registry=registry, functions=data['functions'],
                 snapshot_methods_are_exhaustive_callees=False,
                 original_build_dynamic_identities_joined=0,
                 native_defect=dict(id='EMPTY_METHODS_RETAIN_DIRECT_DCODE',status='REPRODUCED_UNFIXED',
                                    expected='NO-APPLICABLE-METHOD', observed_values=[10,11],
                                    installed_methods=0, retained_function=base_method))
    summary = dict(scope=SCOPE,census_gate_credit=False,native_population=len(registry),
                   initialized=len(initialized),uninitialized=len(registry)-len(initialized),
                   registered_methods=sum(len(s['methods']) for s in initialized),
                   method_functions=len(method_ids), dcode_functions=len(target_ids),
                   direct_method_dcodes=sum(s['dcode'] in {m['function'] for m in s['methods']} for s in initialized),
                   standard_combinations=sum(s['standard_combination'] is True for s in initialized),
                   function_records=len(funcs), probe_calls=len(steps), stale_snapshot_refusals=8,
                   field_mutations=4,literal_counterexamples=1,native_empty_method_defect='REPRODUCED_UNFIXED',
                   ordinary_expected_calls=11,known_defect_calls=1,
                   original_build_dynamic_identities_joined=0,computed_calls_closed=0)
    return facts, summary


def check(facts,summary,data,independent):
    expected, report = assess(data,independent)
    require(facts==expected,'REGISTRY_FACTS')
    require(summary==report,'REGISTRY_SUMMARY')


def controls(data,independent,facts,summary):
    rows = []
    def reject(name,reason,call):
        try:
            call()
        except ValueError as e:
            require(str(e)==reason, 'CONTROL_REASON '+name+': '+str(e))
            rows.append(dict(name=name,status='REJECTED',reason=reason))
        else:
            raise ValueError('CONTROL_ESCAPED '+name)
    for name,reason,mutate in [
        ('omit-registry-entry','REGISTRY_COVERAGE',lambda d:d['registry'].pop()),
        ('duplicate-registry-entry','REGISTRY_COVERAGE',lambda d:d['registry'].append(copy.deepcopy(d['registry'][-1]))),
        ('invent-generic-subtype','GF_SUBTYPE',lambda d:d['registry'][0].update(bits=0)),
        ('wrong-slot-owner','INITIALIZED_STATE',lambda d:next(s for s in d['registry'] if s['status']=='INITIALIZED').update(slots_owner_matches=False)),
        ('wrong-method-owner','METHOD_OWNER',lambda d:next(s for s in d['registry'] if s.get('methods'))['methods'][0].update(owner=-1)),
        ('missing-method-function','METHOD_FIELDS',lambda d:next(s for s in d['registry'] if s.get('methods'))['methods'][0].update(function=-1)),
        ('duplicate-method','DUPLICATE_METHOD',lambda d:next(s for s in d['registry'] if s.get('methods'))['methods'].append(copy.deepcopy(next(s for s in d['registry'] if s.get('methods'))['methods'][0]))),
        ('missing-probe','PROBE_COVERAGE',lambda d:d['probes']['steps'].pop()),
        ('drop-second-result','PROBE_RESULT base',lambda d:d['probes']['steps'][1]['call']['values'].pop()),
        ('conceal-native-defect','PROBE_RESULT remove-all',lambda d:d['probes']['steps'][-1]['call'].update(status='ERROR',values=[])),
        ('trust-stale-checkpoint','STALE_SNAPSHOT_REFUSAL',lambda d:d['probes']['checks'][0].update(stale_refused=False)),
        ('accept-ordinary-literal-function','LITERAL_NOT_SUBTYPE',lambda d:d['probes']['checks'][-1].update(refused=False)),
    ]:
        damaged = copy.deepcopy(data); mutate(damaged)
        reject(name,reason,lambda:assess(damaged,independent))
    for offset,reason in [(8,'METHOD_FIELD_CHANGE'),(9,'METHOD_FIELD_CHANGE'),(10,'METHOD_FIELD_CHANGE'),(11,'DCODE_CHANGE')]:
        damaged = copy.deepcopy(data)
        damaged['probes']['checks'][offset]['changed'] = copy.deepcopy(damaged['probes']['checks'][offset]['old'])
        reject('omit-live-'+damaged['probes']['checks'][offset]['name'].lower(),reason,lambda:assess(damaged,independent))
    for name,mutate in [
        ('invent-original-build-join',lambda f:f.update(original_build_dynamic_identities_joined=465)),
        ('promote-method-list-to-callee-bound',lambda f:f.update(snapshot_methods_are_exhaustive_callees=True)),
        ('promote-gate-credit',lambda f:f.update(census_gate_credit=True)),
        ('erase-uninitialized-object',lambda f:f.update(registry=[r for r in f['registry'] if r['status']=='INITIALIZED'])),
        ('erase-native-defect',lambda f:f.update(native_defect=None)),
        ('invent-method',lambda f:next(s for s in f['registry'] if s.get('methods'))['methods'].append({'id':999999})),
    ]:
        damaged = copy.deepcopy(facts); mutate(damaged)
        reject(name,'REGISTRY_FACTS',lambda:check(damaged,summary,data,independent))
    reject('missing-independent-reproduction','EMPTY_METHOD_ESCAPE',lambda:assess(data,{}))
    check(facts,summary,data,independent)
    return dict(controls_rejected=len(rows),controls=rows)
