"""Exercise the real image/prefix/body oracles, including the node suffix."""
from copy import deepcopy
import json
import struct
from common import require
from analyze import analyze,check


def run(blob,old,fresh,export,requests,facts,summary):
    result=[]
    def reject(name,fn,reason):
        try:fn()
        except ValueError as e:
            require(str(e)==reason,'CONTROL_REASON '+name+': '+str(e));result.append(dict(name=name,reason=reason))
        else:raise ValueError('CONTROL_ESCAPED '+name)
    def exported(name,index,mutate,reason):
        e=dict(export);e['functions']=list(e['functions']);e['functions'][index]=deepcopy(e['functions'][index])
        mutate(e['functions'][index]);reject(name,lambda:analyze(blob,old,fresh,e,requests),reason)
    selected=next(i for i,r in enumerate(export['functions']) if r['selected'])
    unselected=next(i for i,r in enumerate(export['functions']) if not r['selected'])
    exported('wrong-code-id',0,lambda r:r.update(code=r['code']+1),'READONLY_REPLAY_IDENTITY')
    exported('wrong-description',0,lambda r:r['description'].update(name='invented'),'READONLY_REPLAY_IDENTITY')
    exported('wrong-address',0,lambda r:r.update(address=r['address']+16),'READONLY_FILE_ADDRESS')
    exported('wrong-boundary',0,lambda r:r.update(code_words=r['code_words']+1),'READONLY_WORD_BOUNDARIES')
    exported('missing-requested-body',selected,lambda r:r.update(selected=False),'READONLY_SELECTION')
    exported('missing-payload',selected,lambda r:r.update(payload_hex=None),'BODY_PAYLOAD_TYPE')
    exported('unexpected-payload',unselected,lambda r:r.update(payload_hex='00'),'UNREQUESTED_BODY')
    def flip(r,index):
        b=bytearray.fromhex(r['payload_hex']);b[index]^=1;r['payload_hex']=b.hex()
    exported('changed-instruction-byte',selected,lambda r:flip(r,8),'BODY_FILE_BYTES')
    exported('changed-immediate-word',selected,lambda r:flip(r,r['code_words']*8),'BODY_FILE_BYTES')
    e=dict(export,functions=export['functions'][:-1])
    reject('omitted-readonly-function',lambda:analyze(blob,old,fresh,e,requests),'READONLY_FUNCTION_COUNT')
    e=dict(export,functions=[export['functions'][1],export['functions'][0]]+export['functions'][2:])
    reject('swapped-readonly-functions',lambda:analyze(blob,old,fresh,e,requests),'READONLY_REPLAY_IDENTITY')
    e=dict(export,area='dynamic')
    reject('promote-dynamic-region',lambda:analyze(blob,old,fresh,e,requests),'EXPORT_SCOPE')
    f=list(fresh);r=json.loads(f[2]);r['payload']['function']['objects'][0]['description']['name']='different';f[2]=(json.dumps(r)+'\n').encode()
    reject('changed-original-prefix',lambda:analyze(blob,old,f,export,requests),'READONLY_REPLAY_PREFIX')
    reject('truncated-inventory',lambda:analyze(blob,old,fresh[:-1],export,requests),'INVENTORY_COMPLETION')
    def image(name,offset,fmt,value,reason):
        b=bytearray(blob);struct.pack_into(fmt,b,offset,value)
        reject(name,lambda:analyze(bytes(b),old,fresh,export,requests),reason)
    header=facts['image_layout']['header_offset'];ro=facts['image_layout']['sections'][1]
    image('wrong-trailer',len(blob)-16,'I',0,'IMAGE_TRAILER')
    image('wrong-image-abi',header+32,'I',0,'IMAGE_HEADER_PROFILE')
    image('wrong-image-base',header+56,'Q',0,'IMAGE_BASE_PROFILE')
    image('wrong-section-class',header+64+32,'Q',72,'IMAGE_SECTION_PROFILE')
    image('oversized-section',header+64+32+16,'Q',len(blob)*16,'IMAGE_SECTION_EXTENT')
    image('unknown-readonly-object',ro['offset'],'B',255,'READONLY_HEADER')
    fn=facts['image_layout']['functions'][0]
    image('invalid-code-boundary',fn['file_offset']+8,'I',0,'FUNCTION_CODE_BOUNDARY')
    f=dict(facts,bodies=facts['bodies'][:-1])
    reject('omit-derived-body',lambda:check(f,summary,blob,old,fresh,export,requests),'BODY_RECORDS')
    f=dict(facts,remaining_codes=[])
    reject('erase-unjoined-worklist',lambda:check(f,summary,blob,old,fresh,export,requests),'BODY_RECORDS')
    s=dict(summary,source_ir_bodies_closed=len(facts['bodies']))
    reject('promote-bytes-to-ir-closure',lambda:check(facts,s,blob,old,fresh,export,requests),'BODY_SUMMARY')
    # A changed dynamic descriptor is allowed only outside the anchored region.
    # It cannot alter any selected body or acquire an old code identity.
    f=list(fresh);index=summary['original_prefix_events'];r=json.loads(f[index])
    require(r['kind']=='resident-function','DYNAMIC_PROBE_KIND')
    r['payload']['function']['objects'][0]['description']['name']='dynamic-probe';f[index]=(json.dumps(r)+'\n').encode()
    got,report=analyze(blob,old,f,export,requests)
    require(got==facts and report==summary,'DYNAMIC_SUFFIX_PROMOTED')
    return dict(status='PASS',controls_rejected=len(result),controls=result,
                positive_probes=['dynamic-suffix-cannot-change-readonly-joins'])
