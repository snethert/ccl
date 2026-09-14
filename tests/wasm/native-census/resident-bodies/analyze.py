"""Join image offsets, native read-only objects and the original inventory."""
import hashlib
import json
import struct
from common import require,SCOPE
from image import parse


def missing_codes(delta):
    return sorted(int(e['from'].rsplit(':',1)[1]) for e in delta['edges']
                  if e['evidence'].startswith('binding-versions/body/') and e['resolution']=='unresolved')


def analyze(blob,original,fresh,export,requests):
    layout=parse(blob);fs=layout['functions'];n=len(fs)
    require(export.keys()=={'version','area','functions'} and export['version']==1
            and export['area']=='readonly','EXPORT_SCOPE')
    require(len(export['functions'])==n,'READONLY_FUNCTION_COUNT')
    # Only the complete read-only area is an identity anchor. The later dynamic
    # suffix may differ and is never normalized into the old namespace.
    require(len(original)>=n+2 and len(fresh)>=n+2,'INVENTORY_LENGTH')
    for rows in (original,fresh):
        final=json.loads(rows[-1])
        require(final['kind']=='inventory-return' and final['payload']=={'stage':'before'}
                and final['sequence']==len(rows),'INVENTORY_COMPLETION')
    require(original[:n+2]==fresh[:n+2],'READONLY_REPLAY_PREFIX')
    prefix=[json.loads(line) for line in original[:n+2]]
    require(prefix[0]['kind']=='snapshot' and prefix[1]['kind']=='inventory-enter'
            and prefix[1]['payload']=={'stage':'before'},'READONLY_PREFIX_START')
    old=[]
    for i,r in enumerate(prefix[2:]):
        require(r['sequence']==i+3 and r['kind']=='resident-function'
                and r['payload']['stage']=='before','READONLY_PREFIX_RECORD')
        p=r['payload']['function'];require(len(p['objects'])==1,'READONLY_DESCRIPTOR_GRAPH')
        fn=p['objects'][0]
        require(fn['kind']=='function' and p['root']=={'ref':fn['id']} and fn['id']==fn['code'],'READONLY_CODE_IDENTITY')
        old.append(dict(fn,literal_functions=r['payload']['literal_functions'],event=r['sequence']))
    addresses={};selected=[]
    require(requests==sorted(set(requests)),'REQUEST_SET')
    for i,(disk,prior,live) in enumerate(zip(fs,old,export['functions'])):
        require(set(live)=={'ordinal','id','code','address','total_words','code_words','description',
                           'source_end','selected','payload_hex'},'EXPORT_RECORD')
        require(live['ordinal']==i and live['id']==prior['id'] and live['code']==prior['code']
                and live['description']==prior['description'],'READONLY_REPLAY_IDENTITY')
        require(live['total_words']==disk['total_words'] and live['code_words']==disk['code_words'],
                'READONLY_WORD_BOUNDARIES')
        address=0x300000000000+disk['section_offset']+15
        require(live['address']==address,'READONLY_FILE_ADDRESS')
        addresses[address]=live['code']
        wanted=live['code'] in requests
        require(live['selected'] is wanted,'READONLY_SELECTION')
        if not wanted:require(live['payload_hex'] is None,'UNREQUESTED_BODY');continue
        text=live['payload_hex'];require(isinstance(text,str),'BODY_PAYLOAD_TYPE')
        try:payload=bytes.fromhex(text)
        except ValueError:raise ValueError('BODY_PAYLOAD_HEX')
        require(payload.hex()==text,'BODY_PAYLOAD_HEX')
        start=disk['file_offset']+8;expected=blob[start:start+disk['total_words']*8]
        require(payload==expected,'BODY_FILE_BYTES')
        require(live['source_end'] is None or type(live['source_end']) is int
                and prior['description']['position'] is not None
                and live['source_end']>=prior['description']['position'],'SOURCE_RANGE')
        selected.append(dict(code=live['code'],inventory_event=prior['event'],ordinal=i,**disk,
            description=prior['description'],source_end=live['source_end'],
            payload_sha256=hashlib.sha256(payload).hexdigest(),
            instruction_prefix_sha256=hashlib.sha256(payload[:disk['code_words']*8]).hexdigest(),
            literal_functions=prior['literal_functions']))
    for f in selected:
        literals=[]
        for slot in range(f['code_words'],f['total_words']-2):
            word=struct.unpack_from('<Q',blob,f['file_offset']+8+8*slot)[0]
            if word in addresses:
                target=addresses[word]
                require(target in f['literal_functions'],'FUNCTION_LITERAL_JOIN')
                literals.append(dict(slot=slot,image_word=word,target_code=target))
        f['readonly_function_literals']=literals
    reached={f['code'] for f in selected};remaining=sorted(set(requests)-reached)
    summary=dict(scope=SCOPE,census_gate_credit=False,readonly_functions=n,
        readonly_objects=sum(layout['readonly_object_counts'].values()),
        original_prefix_events=n+2,original_prefix_sha256=hashlib.sha256(b''.join(original[:n+2])).hexdigest(),
        requested_bodies=len(requests),image_bodies_witnessed=len(selected),bodies_without_this_witness=len(remaining),
        body_bytes=sum(f['total_words']*8 for f in selected),
        instruction_prefix_bytes=sum(f['code_words']*8 for f in selected),
        bodies_with_source_ranges=sum(f['source_end'] is not None for f in selected),
        readonly_function_literal_slots=sum(len(f['readonly_function_literals']) for f in selected),
        full_initial_inventory_equal=original==fresh,
        dynamic_inventory_identity_join=False,source_ir_bodies_closed=0,computed_calls_changed=False)
    return dict(version=1,scope=SCOPE,image_layout=layout,bodies=selected,remaining_codes=remaining),summary


def check(facts,summary,blob,original,fresh,export,requests):
    expected,report=analyze(blob,original,fresh,export,requests)
    require(facts==expected,'BODY_RECORDS')
    require(summary==report,'BODY_SUMMARY')
