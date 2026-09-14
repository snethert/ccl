"""Independent literal oracles and deliberately damaged observation controls."""
from copy import deepcopy
from analysis import check, controls, functions, require
from bounds import analyze
import layout_check
from reference import compare


def layout_probes(rows):
    def symbol(x):return 'COMMON-LISP::'+x
    x='KEYWORD::X';v='LOCAL-0'
    def predicate(reader,values):
        return [symbol('LET*'),[[v,[reader,x]]],[symbol('DECLARE'),[symbol('FIXNUM'),v]],
                [symbol('OR'),*[[symbol('='),v,i] for i in values]]]
    expected=[(['CCL::%MAKE-SFLOAT'],['CCL::%ALLOC-MISC',1,15]),
              (['CCL::%MAKE-DFLOAT'],['CCL::%ALLOC-MISC',3,23]),
              (['CCL::%NUMERATOR',x],['CCL::%SVREF',x,0]),
              (['CCL::%DENOMINATOR',x],['CCL::%SVREF',x,1]),
              (['CCL::IMMEDIATE-P-MACRO',x],predicate('CCL::LISPTAG',[0,3])),
              (['CCL::HASHED-BY-IDENTITY',x],predicate('CCL::TYPECODE',[0,3,58,114])),
              (['CCL::SYMPTR->SYMVECTOR',x],x),(['CCL::SYMVECTOR->SYMPTR',x],x)]
    require(rows==[dict(form=f,expansion=e) for f,e in expected],'LAYOUT_EXPANSIONS')
    return len(rows)


def callbacks(capture):
    check(capture)
    rows=[]
    for record in capture['captures']:
        family={f['function_id']:f for f in functions(record['function'])}
        for r in analyze(record):
            name=family[r['function_id']]['name']
            rows.append(dict(name=name,disposition=r['disposition'],targets=r['targets'],bindings=r.get('bindings',[])))
    expected={'CENSUS-LITERAL':True,'CENSUS-FLET':True,'CENSUS-PARAMETER':False,'CENSUS-ASSIGNED':False,
              'CENSUS-CAPTURED-WRITE':False,'CENSUS-SHADOWED':True,'CENSUS-CLOSED':True,'CENSUS-SEQUENTIAL-SCOPE':False}
    require(len(rows)==8,'CALLBACK_SITE_SET')
    for r in rows:
        name=r['name'].removeprefix('COMMON-LISP-USER::')
        require(name in expected and (r['disposition']=='BOUNDED_LEXICAL_PROTOTYPE')==expected[name],
                'CALLBACK_DISPOSITION '+name)
        require(len(r['targets'])==int(expected.pop(name)),'CALLBACK_TARGET_COUNT')
    return rows


def check_all(data):
    results=dict(target=check(data['target'],True),native=check(data['native'],True),
                 layout=layout_check.check(data['target']),callbacks=callbacks(data['callbacks']),
                 reference=compare(data['native'],data['reference']),layout_probes=layout_probes(data['layout_probes']))
    for key,message in (('guard','CENSUS-CODE-EXECUTION-FORBIDDEN'),('dump','CENSUS-FASL-PUBLICATION-FORBIDDEN')):
        c=data[key];check(c)
        require(c['status']=='INCOMPLETE' and message in c['problem']['message'] and
                c['eof_reached'] is False and not c['output_opcodes'],'REFUSAL '+key)
    c=data['failed_effect'];check(c)
    require(c['status']=='INCOMPLETE' and c['eof_reached'] and c['problem'] is None and len(c['gaps'])==1,
            'FAILED_EFFECT_STATUS')
    after=next(r for r in c['captures'] if r['function']['name']=='COMMON-LISP-USER::CENSUS-AFTER-FAILURE')
    require(after['prior_gaps']==[c['gaps'][0]['form']],'FAILED_EFFECT_TAINT')
    controls_rows=controls(data['target'])+controls(data['native'])
    def trial(name,key,mutate,checker,reason):
        altered=deepcopy(data[key]);mutate(altered)
        try:checker(altered)
        except ValueError as e:require(str(e)==reason,'CONTROL_REASON '+name+': '+str(e))
        else:raise ValueError('CONTROL_ESCAPED '+name)
        controls_rows.append(dict(name=name,status='REJECTED',reason=reason))
    trial('changed-target-tag','target',lambda c:next(r for r in c['layout_constants']if r['name']=='SUBTAG-SYMBOL').__setitem__('value',231),layout_check.check,'D1_CONSTANT subtag-symbol')
    trial('omitted-data-table-row','target',lambda c:next(r for r in c['layout_fields']if r['accessor']=='ARCH::TARGET-UVECTOR-SUBTAGS')['value'].pop(),layout_check.check,'D1_TABLE_SET')
    trial('wrong-native-code-byte','reference',lambda c:c['functions'][0].__setitem__('code','00'+c['functions'][0]['code'][2:]),lambda c:compare(data['native'],c),'REFERENCE_NATIVE_BYTES')
    trial('wrong-float-allocation-size','layout_probes',lambda c:c[1]['expansion'].__setitem__(1,2),layout_probes,'LAYOUT_EXPANSIONS')
    trial('capture-promoted-after-error','failed_effect',lambda c:next(r for r in c['captures']if r['function']['name']=='COMMON-LISP-USER::CENSUS-AFTER-FAILURE')['prior_gaps'].clear(),
          check,'CAPTURE_PRIOR_GAPS')
    # Assignment in either the parent or a child must still block a bound when
    # the redundant assignment flags are all cleared. This exercises structure.
    changed=deepcopy(data['callbacks'])
    for r in changed['captures']:
        for n in r['flow']['objects']:
            if n['kind']=='variable':n['assigned']=False
    require(callbacks(changed)==results['callbacks'],'WRITE_SCAN_WITHOUT_FLAGS')
    controls_rows.append(dict(name='cleared-assignment-flags',status='REJECTED',reason='STRUCTURAL_WRITES_STILL_UNBOUNDED'))
    return results,controls_rows
