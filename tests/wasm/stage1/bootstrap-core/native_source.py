"""Explain source-location changes; compare every code byte and other constant.

The three source files intentionally gain Wasm reader branches. They are not
unchanged-input byte-identity samples. PC/source maps are debugger metadata,
identified only in the function-info slot selected by the native lfun bits.
"""
import copy, hashlib, struct, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'registration'))
from fasl import CompilerFasl, elements, symbol

def compare(before, after, source_before, source_after):
    notes=[]; maps=[]; code=[]
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
        notes.append(dict(side=side,path=path,start=start,end=end))
        x[3]={'source-location':True}
        return True
    def walk(x,source,side,path):
        if isinstance(x,list):return [walk(v,source,side,path+[i]) for i,v in enumerate(x)]
        if not isinstance(x,dict):return x
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
                    else:kept.extend([key,value])
                # Preserve every property other than the explicitly recorded map.
                tail=None
                for v in reversed(kept):tail={'cons':[v,tail]}
                cs[slot]=tail
            f['constants']=walk(cs,source,side,path+['function','constants'])
            return {'function':f}
        y={k:walk(v,source,side,path+[k]) for k,v in x.items()}
        if set(y)=={'vector'}:note(y['vector'],source,side,path)
        return y
    a=CompilerFasl(before).decode();b=CompilerFasl(after).decode()
    na=walk(a,source_before,'before',[]);nb=walk(b,source_after,'after',[])
    assert na==nb,'native executable, non-debug constant, or ABI difference'
    return dict(status='PASS',before_sha256=hashlib.sha256(before).hexdigest(),after_sha256=hashlib.sha256(after).hexdigest(),
                decoded_forms=len(a),functions=sum(r['side']=='before' for r in code),
                code=code,source_notes=notes,pc_source_maps=maps,
                scope='Intentional shared-source artifacts: identical executable bytes and non-location data; source notes and PC/source debugger maps recorded separately. No raw FASL identity claim.')
