"""Literal fault expectations, checked independently against WABT disassembly."""
import hashlib
import json
import re
from pathlib import Path

HERE=Path(__file__).resolve().parent
ENTRIES={1:(701,'fixed','(i32)->(i32)',0),2:(702,'fixed','(i32)->(i32)',1),
         3:(703,'generic','(i32)->(i32)',2),4:(704,'bridge','()->(i64)',3),5:(705,'dispatch','(i32)->(i32)',4)}
LIMITS=dict(errors=3,frames=4,message=160,bytes=8192)
def require(x,why):
    if not x:raise ValueError(why)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def disassembly(text):
    current=None;result={}
    for line in text.splitlines():
        m=re.match(r'^[0-9a-f]+ func\[(\d+)\]',line)
        if m:current=int(m[1]);require(current not in result,'DISASSEMBLY_FUNCTION');result[current]=[];continue
        m=re.match(r'^\s*([0-9a-f]+):\s+([0-9a-f ]+)\|\s+(.*)$',line)
        if not m:continue
        require(current in ENTRIES,'DISASSEMBLY_OWNER')
        parts=m[3].split();name=parts[0]
        operands=[]
        if name in ('i32.const','i64.const','local.get','call'):operands=[int(parts[1])]
        if name=='i32.load':operands=list(map(int,parts[1:]))
        if name=='call_indirect':
            mtype=re.fullmatch(r'call_indirect (\d+) \(type (\d+)\)',m[3]);require(mtype,'INDIRECT_DISASSEMBLY')
            operands=[int(mtype[2]),int(mtype[1])]
        result[current].append(dict(offset=int(m[1],16),name=name,operands=operands))
    require(list(result)==list(ENTRIES),'DISASSEMBLY_BOUND')
    return result

def frame(index,operation,ops):
    found=[x for x in ops[index] if x['name']==operation];require(len(found)==1,'FAULT_OPCODE_UNIQUE')
    code,kind,sig,slot=ENTRIES[index]
    return dict(function_index=index,logical_code_id=code,entry_kind=kind,signature=sig,slot=slot,
                operation=operation,binary_offset=found[0]['offset'])

def check(o,case,bundle):
    require(o['configuration']==case,'CASE_IDENTITY')
    require(o['scope']=='HAND-BUILT WASM DIAGNOSTIC FIXTURE','EVIDENCE_SCOPE')
    if case.get('preflight'):
        reason={'stale-binary':'BUILD_FILE_IDENTITY module.wasm','stale-map':'BUILD_MAP_IDENTITY','abi-signature':'MAP_ENTRY_IDENTITY'}[case['preflight']]
        require(o['status']=='PRE_EXECUTION_REFUSAL' and not o['instantiated'] and not o['returns'] and not o['exceptions'] and
                o['error']==dict(name='Error',message=reason),'PREFLIGHT_REFUSAL')
        return dict(name=case['name'],status='EXPECTED_BUILD_REFUSAL',reason=reason)
    require(o['status']=='OBSERVED' and o['instantiated'],'REAL_EXECUTION')
    manifest=read(bundle/'manifest.json')
    build=dict(manifest_sha256=sha(bundle/'manifest.json'),binary_sha256=sha(bundle/'module.wasm'),module=manifest['module'])
    require(o['build']==build,'BUILD_IDENTITY')
    ops=disassembly((bundle/'disassembly.txt').read_text())
    require(o['map']==read(bundle/'map.json'),'MATERIALIZED_MAP')
    require(o['map']['imports']==[dict(module='host',name='observed',signature='(i32)->()')] and
            o['map']['exports']==dict(invoke=3,indirect=5),'MAP_INTERFACE')
    require(len(o['map']['functions'])==5,'MAP_BOUND')
    for f in o['map']['functions']:
        code,kind,sig,slot=ENTRIES[f['index']]
        require(f==dict(index=f['index'],logical_code_id=code,entry_kind=kind,signature=sig,slot=slot,operations=ops[f['index']]),'DECODED_MAP')
    r=o['report'];require(r['limits']==LIMITS,'LIMIT_POLICY')
    raw=o['exceptions'];expected=[];returns=[];ordinal=0
    for invocation in case['calls']:
        arg=invocation['argument'];name=invocation['export']
        if name=='invoke' and arg==0 and not case.get('host_error'):
            returns.append(7 if case['cohort']=='a' else 9);continue
        require(ordinal<len(raw),'EXCEPTION_BOUND');actual=raw[ordinal];ordinal+=1
        op='call_indirect' if name=='indirect' else {1:'unreachable',2:'i32.load',3:'i32.div_s',0:None}[arg]
        index=5 if name=='indirect' else 1
        host=case.get('host_error',False);unavailable=host or case.get('hide_stack',False) or case.get('obscure_top',False)
        expected_name='Error' if host else 'RuntimeError'
        message=('H'*4096 if host else 'null function or function signature mismatch' if name=='indirect' and arg==3 else
                 'table index is out of bounds' if name=='indirect' else
                 {1:'unreachable',2:'memory access out of bounds',3:'divide by zero'}[arg])
        require(actual['name']==expected_name and actual['message']==message,'REAL_EXCEPTION')
        if not host:
            wanted=[frame(index,op,ops)]+([frame(2,'call',ops),frame(3,'call',ops)] if name=='invoke' else [])
            locations=[]
            for line in actual['wasm_locations']:
                m=re.search(r'wasm-function\[(\d+)\]:0x([0-9a-f]+)',line);require(m,'ENGINE_LOCATION')
                locations.append((int(m[1]),int(m[2],16)))
            require(locations==[(f['function_index'],f['binary_offset']) for f in wanted],'ACTUAL_FAULT_LOCATION')
        else:wanted=[]
        frames=[] if unavailable else wanted
        last=None if name=='indirect' else dict(event_id=900,logical_code_id=703,attribution='CONTEXT_ONLY')
        expected.append(dict(phase='execution',build=build,classification='UNAVAILABLE' if unavailable else 'WASM_FAULT',
            error_name=expected_name,message=message[:160],fault=frames[0] if frames else None,frames=frames,last_observed=last))
    require(ordinal==len(raw) and o['returns']==returns,'EXECUTION_COUNTS')
    require(r['failures']==len(expected) and r['dropped']==max(0,len(expected)-3) and len(r['errors'])==min(len(expected),3),'REPORT_BOUNDS')
    for actual,expected_diag in zip(r['errors'],expected):
        require(actual['build']==build,'DIAGNOSTIC_BUILD')
        if expected_diag['classification']=='UNAVAILABLE':require(actual['fault'] is None and actual['frames']==[] and actual['classification']=='UNAVAILABLE','NO_FALSE_ATTRIBUTION')
        require(actual['fault']==expected_diag['fault'],'FAULT_FRAME')
        require(actual==expected_diag,'DIAGNOSTIC_CONTENT')
    require(r['first_failure']==(expected[0] if expected else None),'FIRST_FAILURE')
    rendered=json.dumps(r,separators=(',',':'),ensure_ascii=False).encode()
    require(o['diagnostic_bytes']==len(rendered) and len(rendered)<=8192,'BYTE_BOUND')
    require(set(r)=={'version','limits','first_failure','errors','failures','dropped'} and r['version']==1,'REPORT_FIELDS')
    return dict(name=case['name'],status='PASS',failures=len(expected),recorded=min(len(expected),3),dropped=max(0,len(expected)-3),bytes=len(rendered))
