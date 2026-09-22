"""Explain source-location changes; compare every code byte and other constant.

The edited source files intentionally gain Wasm reader branches. They are not
unchanged-input byte-identity samples. PC/source maps are debugger metadata,
identified only in the function-info slot selected by the native lfun bits.
"""
import copy, hashlib, struct, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'registration'))
from fasl import elements, symbol
from decoder import CompilerFasl

def compare(before, after, source_before, source_after):
    notes=[]; maps=[]; code=[]; empty_info=[]
    def note(v,source,side,path):
        if v.get('subtag')!=54:return False
        x=v['values']
        if len(x)!=4 or 'SOURCE-NOTE' not in repr(x[0]):return False
        span=x[3]
        if isinstance(span,int):start,n=divmod(span,1<<14);end=start+n
        else:
            assert isinstance(span,dict) and set(span)=={'cons'},'source note encoding'
            start,end=span['cons']
        assert 0<=start<=end<=len(source),'source note bounds'
        notes.append(dict(side=side,path=path,start=start,end=end,parent=copy.deepcopy(x[1]),file=x[2]))
        x[1]=None
        x[3]={'source-location':True}
        return True
    def walk(x,source,side,path):
        if isinstance(x,list):return [walk(v,source,side,path+[i]) for i,v in enumerate(x)]
        if not isinstance(x,dict):return x
        if set(x)=={'location'}:
            if x['location'] is not None:
                assert set(x['location'])=={'vector'} and note(copy.deepcopy(x['location']['vector']),source,side,path), 'location record'
            return {'location':None}
        if set(x)=={'function'}:
            f=copy.deepcopy(x['function']);cs=f['constants'];bits=cs[-1]
            assert isinstance(bits,int),'function bits'
            raw=bytes.fromhex(f['code']);code.append(dict(side=side,path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
            if bits & (1<<23):
                slot=-2 if bits & (1<<29) else -3
                props=elements(cs[slot]);assert len(props)%2==0,'function info plist'
                kept=[]
                for i in range(0,len(props),2):
                    key,value=props[i:i+2]
                    if key==symbol('CCL::PC-SOURCE-MAP'):
                        assert isinstance(value,dict) and len(value)==1,'pc map type'
                        kind,data=next(iter(value.items()));width={'u8vector':1,'u16vector':2,'u32vector':4}[kind]
                        blob=bytes.fromhex(data);assert len(blob)%(4*width)==0,'pc map shape'
                        vals=list(struct.unpack('<'+{1:'B',2:'H',4:'I'}[width]*(len(blob)//width),blob))
                        for j in range(0,len(vals),4):
                            a,b,c,d=vals[j:j+4]
                            assert 0<=a<=b<=len(raw) and 0<=c<=d<=len(source),'pc map bounds'
                        maps.append(dict(side=side,path=path,encoding=kind,entries=vals))
                    elif key==symbol('CCL::%FUNCTION-SOURCE-NOTE'):
                        assert isinstance(value,dict) and set(value)=={'vector'}, 'function source note'
                        assert note(copy.deepcopy(value['vector']),source,side,path), 'function source note shape'
                    else:kept.extend([key,value])
                # Preserve every property other than the explicitly recorded map.
                tail=None
                for v in reversed(kept):tail={'cons':[v,tail]}
                cs[slot]=tail
                if not kept:
                    # Only location properties were present. Conditionalizing
                    # the DEFUN can remove the entire debug-info slot and its
                    # presence bit. Preserve every executable byte and all
                    # other bits; record the original slot and properties.
                    empty_info.append(dict(side=side,path=path,slot=slot,bits=bits,properties=props))
                    del cs[slot]
                    cs[-1]=bits & ~(1<<23)
            f['constants']=walk(cs,source,side,path+['function','constants'])
            return {'function':f}
        y={k:walk(v,source,side,path+[k]) for k,v in x.items()}
        if set(y)=={'vector'}:note(y['vector'],source,side,path)
        return y
    a=CompilerFasl(before).decode();b=CompilerFasl(after).decode()
    na=walk(a,source_before,'before',[]);nb=walk(b,source_after,'after',[])
    # The reader may omit a repeated top-level location directive after a
    # conditionalized definition loses its source note. Every present directive
    # was validated above; these are loader debugger state, not executable forms.
    na=[x for x in na if not (isinstance(x,dict) and set(x)=={'location'})]
    nb=[x for x in nb if not (isinstance(x,dict) and set(x)=={'location'})]
    assert na==nb,'native executable, non-debug constant, or ABI difference'
    return dict(status='PASS',before_sha256=hashlib.sha256(before).hexdigest(),after_sha256=hashlib.sha256(after).hexdigest(),
                decoded_forms=len(a),after_decoded_forms=len(b),non_location_forms=len(na),functions=sum(r['side']=='before' for r in code),
                code=code,source_notes=notes,pc_source_maps=maps,empty_location_info_slots=empty_info,
                scope='Identical code bytes and non-location data. Bounded source notes, their parent links and presence/absence in decoded location records and the %FUNCTION-SOURCE-NOTE property are retained separately, along with PC/source maps. Conditionalized definitions may lose their source-note property and an otherwise empty debug-info slot/presence bit. No other function property or bit is omitted; no raw FASL identity claim.')


def controls(before, after, source_before, source_after):
    """The location allowance must still reject code and non-location changes."""
    global CompilerFasl
    decoder=CompilerFasl
    original=decoder(after).decode()
    def functions(x):
        if isinstance(x,dict):
            if set(x)=={'function'}:yield x['function']
            for v in x.values():yield from functions(v)
        elif isinstance(x,list):
            for v in x:yield from functions(v)
    rejected=[]
    for kind in ('executable-byte','non-location-bit','callee-identity'):
        changed=copy.deepcopy(original)
        fs=list(functions(changed))
        if kind=='executable-byte':
            f=fs[0];raw=bytearray.fromhex(f['code']);raw[0]^=1;f['code']=raw.hex()
        elif kind=='non-location-bit':fs[0]['constants'][-1]^=1
        else:
            constant=next(c for f in fs for c in f['constants'][:-1]
                          if isinstance(c,dict) and set(c)=={'symbol'})
            constant['symbol']='CCL::CHANGED-CALLEE'
        class ChangedDecoder:
            def __init__(self,data):self.data=data
            def decode(self):return copy.deepcopy(changed) if self.data==after else decoder(self.data).decode()
        try:
            CompilerFasl=ChangedDecoder
            try:compare(before,after,source_before,source_after)
            except AssertionError:rejected.append(kind)
            else:raise AssertionError('native comparison control escaped: '+kind)
        finally:CompilerFasl=decoder
    return rejected
